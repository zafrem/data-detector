"""Core detection and redaction engine."""

import hashlib
import logging
from typing import TYPE_CHECKING, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from datadetector.fake_generator import FakeDataGenerator

from datadetector.models import (
    FindResult,
    Match,
    RedactionResult,
    RedactionStrategy,
    ValidationResult,
)
from datadetector.registry import PatternRegistry
from datadetector.context import ContextHint, ContextFilter, KeywordRegistry

logger = logging.getLogger(__name__)

# Lazy import for fake data generator to avoid circular dependencies
_fake_generator: Optional[Union["FakeDataGenerator", bool]] = None


def _get_fake_generator() -> Optional["FakeDataGenerator"]:
    """Get or create fake data generator instance."""
    global _fake_generator
    if _fake_generator is None:
        try:
            from datadetector.fake_generator import FakeDataGenerator

            _fake_generator = FakeDataGenerator()
        except ImportError:
            logger.warning(
                "FakeDataGenerator not available. Install faker package "
                "to use FAKE redaction strategy."
            )
            _fake_generator = False
    return _fake_generator if _fake_generator is not False else None  # type: ignore[return-value]


class Engine:
    """
    Core engine for PII detection, validation, and redaction.

    The engine uses a PatternRegistry to perform pattern matching operations.
    """

    def __init__(
        self,
        registry: PatternRegistry,
        default_mask_char: str = "*",
        hash_algorithm: str = "sha256",
        keyword_registry: Optional[KeywordRegistry] = None,
        enable_context_filtering: bool = True,
    ) -> None:
        """
        Initialize engine with pattern registry.

        Args:
            registry: PatternRegistry with loaded patterns
            default_mask_char: Default character to use for masking
            hash_algorithm: Hash algorithm for hashing strategy
            keyword_registry: Optional keyword registry for context filtering.
                            If None and enable_context_filtering=True, creates default.
            enable_context_filtering: Whether to enable context-aware filtering.
                                    Set to False to disable the feature entirely.
        """
        self.registry = registry
        self.default_mask_char = default_mask_char
        self.hash_algorithm = hash_algorithm

        # Context filtering support
        self.enable_context_filtering = enable_context_filtering
        if enable_context_filtering:
            self.keyword_registry = keyword_registry or KeywordRegistry()
            self.context_filter = ContextFilter(self.keyword_registry)
        else:
            self.keyword_registry = None
            self.context_filter = None

    def find(
        self,
        text: str,
        namespaces: Optional[List[str]] = None,
        allow_overlaps: bool = False,
        include_matched_text: bool = False,
        stop_on_first_match: bool = False,
        context: Optional[ContextHint] = None,
    ) -> FindResult:
        """
        Find all PII matches in text.

        Args:
            text: Text to search
            namespaces: List of namespaces to search (e.g., ["kr", "common"]).
                       If None, searches all namespaces.
            allow_overlaps: Whether to allow overlapping matches
            include_matched_text: Whether to include matched text in results
                                 (respects pattern policy)
            stop_on_first_match: If True, stop searching after finding the first match.
                               This can significantly improve performance when you only
                               need to detect if PII exists, not find all occurrences.
                               Patterns are checked in priority order (low to high).
            context: Optional context hint for pattern filtering. Significantly improves
                    performance by only checking relevant patterns based on keywords,
                    categories, or field names. Example:
                    ContextHint(keywords=["ssn", "bank_account"])

        Returns:
            FindResult with all matches
        """
        if namespaces is None:
            namespaces = list(self.registry.namespaces.keys())

        matches: List[Match] = []

        # Collect patterns from requested namespaces
        patterns = []
        for ns in namespaces:
            patterns.extend(self.registry.get_namespace_patterns(ns))

        # Apply context filtering if enabled and context provided
        if context is not None and self.enable_context_filtering and self.context_filter:
            # Get pattern IDs before filtering
            all_pattern_ids = [p.full_id for p in patterns]

            # Filter pattern IDs based on context
            filtered_pattern_ids = self.context_filter.filter_patterns(context, all_pattern_ids)

            # Keep only filtered patterns
            patterns = [p for p in patterns if p.full_id in filtered_pattern_ids]

            logger.debug(
                f"Context filtering: {len(all_pattern_ids)} -> {len(patterns)} patterns "
                f"(keywords={context.keywords}, categories={context.categories})"
            )

        # Sort patterns by priority (lower = higher priority)
        # This ensures high-priority patterns are checked first.
        # When allow_overlaps=False, higher-priority matches will take precedence
        # at overlapping positions, saving redundant regex checks.
        patterns.sort(key=lambda p: (p.priority, p.full_id))

        # Search for each pattern
        for pattern in patterns:
            for regex_match in pattern.compiled.finditer(text):
                start, end = regex_match.span()
                matched_value = regex_match.group(0)

                # Apply verification function if specified
                if pattern.verification_func is not None:
                    if not pattern.verification_func(matched_value):
                        logger.debug(
                            f"Pattern {pattern.full_id} matched but failed "
                            f"verification: {matched_value}"
                        )
                        continue

                # Check for overlaps if not allowed
                if not allow_overlaps:
                    if any(self._spans_overlap((start, end), (m.start, m.end)) for m in matches):
                        continue

                # Get matched text if allowed by policy
                matched_text = None
                if include_matched_text and pattern.policy.store_raw:
                    matched_text = matched_value

                match = Match(
                    ns_id=pattern.full_id,
                    pattern_id=pattern.id,
                    namespace=pattern.namespace,
                    category=pattern.category,
                    start=start,
                    end=end,
                    matched_text=matched_text,
                    mask=pattern.mask,
                    severity=pattern.policy.severity,
                )
                matches.append(match)

                # Early termination: stop after first match if requested
                if stop_on_first_match:
                    break

            # Break outer loop if stopping on first match and we found one
            if stop_on_first_match and matches:
                break

        # Sort matches by position
        matches.sort(key=lambda m: (m.start, m.end))

        return FindResult(
            text=text,
            matches=matches,
            namespaces_searched=namespaces,
        )

    def validate(self, text: str, ns_id: str) -> ValidationResult:
        """
        Validate text against a specific pattern.

        Args:
            text: Text to validate
            ns_id: Full namespace/id (e.g., "kr/mobile")

        Returns:
            ValidationResult indicating if text matches pattern

        Raises:
            ValueError: If pattern not found
        """
        pattern = self.registry.get_pattern(ns_id)
        if pattern is None:
            raise ValueError(f"Pattern not found: {ns_id}")

        regex_match = pattern.compiled.fullmatch(text)
        is_valid = regex_match is not None

        # Apply verification function if specified
        if is_valid and pattern.verification_func is not None:
            is_valid = pattern.verification_func(text)
            if not is_valid:
                logger.debug(f"Pattern {pattern.full_id} matched but failed verification: {text}")

        match = None
        if is_valid and regex_match:
            matched_text = None
            if pattern.policy.store_raw:
                matched_text = text

            match = Match(
                ns_id=pattern.full_id,
                pattern_id=pattern.id,
                namespace=pattern.namespace,
                category=pattern.category,
                start=0,
                end=len(text),
                matched_text=matched_text,
                mask=pattern.mask,
                severity=pattern.policy.severity,
            )

        return ValidationResult(
            text=text,
            ns_id=ns_id,
            is_valid=is_valid,
            match=match,
        )

    def redact(
        self,
        text: str,
        namespaces: Optional[List[str]] = None,
        strategy: Optional[RedactionStrategy] = None,
        allow_overlaps: bool = False,
        context: Optional[ContextHint] = None,
    ) -> RedactionResult:
        """
        Redact PII from text.

        Args:
            text: Text to redact
            namespaces: List of namespaces to search. If None, searches all.
            strategy: Redaction strategy (mask/hash/tokenize). If None, uses mask.
            allow_overlaps: Whether to allow overlapping matches
            context: Optional context hint for pattern filtering. Improves performance
                    by only checking relevant patterns.

        Returns:
            RedactionResult with redacted text and match information
        """
        if strategy is None:
            strategy = RedactionStrategy.MASK

        # Find all matches
        find_result = self.find(
            text,
            namespaces=namespaces,
            allow_overlaps=allow_overlaps,
            include_matched_text=True,
            context=context,
        )

        if not find_result.has_matches:
            return RedactionResult(
                original_text=text,
                redacted_text=text,
                strategy=strategy,
                matches=[],
                redaction_count=0,
            )

        # Build redacted text by replacing matches from end to start
        # (to preserve positions)
        redacted = text
        for match in reversed(find_result.matches):
            original = text[match.start : match.end]
            replacement = self._get_replacement(original, match, strategy)
            redacted = redacted[: match.start] + replacement + redacted[match.end :]

        return RedactionResult(
            original_text=text,
            redacted_text=redacted,
            strategy=strategy,
            matches=find_result.matches,
            redaction_count=len(find_result.matches),
        )

    def _get_replacement(self, original: str, match: Match, strategy: RedactionStrategy) -> str:
        """Get replacement text for a match based on strategy."""
        if strategy == RedactionStrategy.MASK:
            # Use pattern mask if available, otherwise use default masking
            if match.mask:
                return match.mask
            return self.default_mask_char * len(original)

        elif strategy == RedactionStrategy.HASH:
            # Return hash of original text
            hasher = hashlib.new(self.hash_algorithm)
            hasher.update(original.encode("utf-8"))
            return f"[HASH:{hasher.hexdigest()[:16]}]"

        elif strategy == RedactionStrategy.TOKENIZE:
            # Return token reference
            return f"[TOKEN:{match.ns_id}:{match.start}]"

        elif strategy == RedactionStrategy.FAKE:
            # Generate realistic fake data based on pattern type
            fake_gen = _get_fake_generator()
            if fake_gen is None:
                # Fallback to masking if faker not available
                logger.warning("FAKE strategy requested but faker not available, using MASK")
                return self.default_mask_char * len(original)

            try:
                # Generate fake data from pattern
                fake_value = fake_gen.from_pattern(match.ns_id)
                if fake_value:
                    return fake_value
            except Exception as e:
                logger.warning(f"Failed to generate fake data for {match.ns_id}: {e}")

            # Fallback to masking
            return self.default_mask_char * len(original)

        return self.default_mask_char * len(original)

    @staticmethod
    def _spans_overlap(span1: Tuple[int, int], span2: Tuple[int, int]) -> bool:
        """Check if two spans overlap."""
        start1, end1 = span1
        start2, end2 = span2
        return not (end1 <= start2 or end2 <= start1)
