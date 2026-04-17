"""Core detection and redaction engine."""

import hashlib
import logging
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from datadetector.fake_generator import FakeDataGenerator

from datadetector.analysis import ContextAnalyzer
from datadetector.context import ContextFilter, ContextHint, KeywordRegistry
from datadetector.models import (
    FindResult,
    Match,
    RedactionResult,
    RedactionStrategy,
    ScoringConfig,
    TransformerConfig,
    ValidationResult,
)
from datadetector.nlp import NLPConfig, NLPProcessor
from datadetector.registry import PatternRegistry

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
        nlp_config: Optional[NLPConfig] = None,
        transformer_config: Optional[TransformerConfig] = None,
        scoring_config: Optional[ScoringConfig] = None,
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
            nlp_config: Optional NLP configuration for language detection, tokenization,
                       and stopword filtering. If None, NLP features are disabled.
            transformer_config: Optional Transformer config for NER detection (Way 1)
                              and ML context classification (Way 2). Requires:
                              pip install data-detector[transformer]
            scoring_config: Optional scoring weights and thresholds. Controls initial
                          scores, keyword boosts, ML weights, and min_score filtering.
        """
        self.registry = registry
        self.default_mask_char = default_mask_char
        self.hash_algorithm = hash_algorithm
        self.scoring = scoring_config or ScoringConfig()

        # Context filtering support
        self.enable_context_filtering = enable_context_filtering
        self.keyword_registry: Optional[KeywordRegistry]
        self.context_filter: Optional[ContextFilter]
        if enable_context_filtering:
            self.keyword_registry = keyword_registry or KeywordRegistry()
            self.context_filter = ContextFilter(self.keyword_registry)
        else:
            self.keyword_registry = None
            self.context_filter = None

        # NLP preprocessing support
        self.nlp_config = nlp_config
        self.nlp_processor = None
        if nlp_config and nlp_config.is_enabled():
            self.nlp_processor = NLPProcessor(nlp_config)

        # Context Analysis (Pipeline Step 3) -- pass transformer config for Way 2
        self.analyzer = ContextAnalyzer(
            transformer_config=transformer_config,
            scoring_config=self.scoring,
        )

        # NER Detection (Way 1) -- lazy-loaded
        self.transformer_config = transformer_config
        self._ner_detector: Any = None  # None=not loaded, False=failed

    def _get_ner_detector(self) -> Any:
        """Lazy-load the Transformer NER detector. Returns None if unavailable."""
        if self._ner_detector is not None:
            return self._ner_detector if self._ner_detector is not False else None

        if not self.transformer_config or not self.transformer_config.is_ner_enabled():
            self._ner_detector = False
            return None

        try:
            from datadetector.transformer_ner import TransformerNERDetector

            self._ner_detector = TransformerNERDetector(self.transformer_config)
            return self._ner_detector
        except ImportError:
            logger.debug("transformer_ner not available, NER detection disabled")
            self._ner_detector = False
            return None

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

        # Apply NLP preprocessing if enabled
        search_text = text
        preprocessed = None
        if self.nlp_processor:
            preprocessed = self.nlp_processor.preprocess(text)
            search_text = preprocessed.processed_text
            logger.debug(
                f"NLP preprocessing: lang={preprocessed.detected_language}, "
                f"tokens={len(preprocessed.tokens) if preprocessed.tokens else 'N/A'}"
            )

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
            for regex_match in pattern.compiled.finditer(search_text):
                start, end = regex_match.span()
                matched_value = regex_match.group(0)

                # For exactly_matches patterns, enforce token boundaries:
                # the match must not be embedded in a larger alphanumeric token,
                # and must not be a plain alphabetic word (to avoid false positives
                # from broad patterns like generic passport matching "Contact")
                if pattern.match_type == "exactly_matches":
                    if start > 0 and search_text[start - 1].isalnum():
                        continue
                    if end < len(search_text) and search_text[end].isalnum():
                        continue
                    if matched_value.isascii() and matched_value.isalpha():
                        continue

                # Map back to original positions if NLP preprocessing was used
                if preprocessed:
                    start, end = preprocessed.map_to_original(start, end)
                    matched_value = text[start:end]

                # Apply verification function if specified
                has_verification = pattern.verification_func is not None
                passed_verification = False
                if has_verification:
                    if not pattern.verification_func(matched_value):
                        logger.debug(
                            f"Pattern {pattern.full_id} matched but failed "
                            f"verification: {matched_value}"
                        )
                        continue
                    passed_verification = True

                # Check for overlaps if not allowed
                if not allow_overlaps:
                    if any(self._spans_overlap((start, end), (m.start, m.end)) for m in matches):
                        # Since patterns are sorted by priority, we already have
                        # the best match for this span.
                        continue

                # Get matched text if allowed by policy
                matched_text = None
                if include_matched_text and pattern.policy.store_raw:
                    matched_text = matched_value

                # Verified matches start at higher confidence
                initial_score = (
                    self.scoring.initial_verified if passed_verification
                    else self.scoring.initial_unverified
                )

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
                    score=initial_score,
                    verified=passed_verification,
                )
                matches.append(match)

                # Early termination: stop after first match if requested
                if stop_on_first_match:
                    break

            # Break outer loop if stopping on first match and we found one
            if stop_on_first_match and matches:
                break

        # Step 2.5: Resolve overlaps if multiple matches were collected
        if not allow_overlaps and len(matches) > 1:
            # Re-sort matches by position then length (longer first)
            matches.sort(key=lambda m: (m.start, m.end - m.start), reverse=True)

            # This is a bit complex if we want to honor priority AND position.
            # But since we collected matches in priority order, we can keep the
            # ones that came first.

            resolved_matches: List[Match] = []
            # We already have them in a mostly priority-first order from the loop.
            # Let's re-verify and filter out overlapping ones that were added later.
            for m in matches:
                if not any(
                    self._spans_overlap((m.start, m.end), (rm.start, rm.end))
                    for rm in resolved_matches
                ):
                    resolved_matches.append(m)
            matches = resolved_matches

        # Step 2.75: NER Detection (Way 1 - Transformer)
        # Run NER model alongside regex to find entities regex might miss.
        # Skip if we already found matches in stop_on_first_match mode.
        if not (stop_on_first_match and matches):
            ner_detector = self._get_ner_detector()
            if ner_detector:
                ner_matches = ner_detector.detect(text)
                for nm in ner_matches:
                    overlapping = [
                        m for m in matches
                        if self._spans_overlap((nm.start, nm.end), (m.start, m.end))
                    ]
                    if not overlapping or allow_overlaps:
                        # NER found something regex missed -- add it
                        matches.append(nm)
                    else:
                        # NER and regex agree on the same span -- boost regex score
                        for m in overlapping:
                            m.context_evidence.append(
                                f"NER-corroboration:{nm.category.value}"
                            )
                            m.score = min(0.99, m.score + self.scoring.ner_corroboration_boost)
                            m.detection_method = "regex+ner"

        # Step 3: Context Analysis
        # Analyze surrounding text to boost confidence using keywords and ML classifier
        if self.analyzer:
            matches = self.analyzer.analyze(text, matches)

        # Step 4: min_score filtering
        if self.scoring.min_score > 0:
            matches = [m for m in matches if m.score >= self.scoring.min_score]

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
