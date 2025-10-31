"""Asynchronous core detection and redaction engine."""

import asyncio
import hashlib
import logging
from typing import List, Optional, Tuple

from datadetector.models import (
    FindResult,
    Match,
    RedactionResult,
    RedactionStrategy,
    ValidationResult,
)
from datadetector.registry import PatternRegistry

logger = logging.getLogger(__name__)


class AsyncEngine:
    """
    Asynchronous engine for PII detection, validation, and redaction.

    The engine uses a PatternRegistry to perform pattern matching operations
    asynchronously, allowing for concurrent processing of multiple texts or
    patterns.

    Example:
        >>> import asyncio
        >>> from datadetector import load_registry
        >>> from datadetector.async_engine import AsyncEngine
        >>>
        >>> async def main():
        >>>     registry = load_registry()
        >>>     engine = AsyncEngine(registry)
        >>>     result = await engine.find("text with PII")
        >>>     return result
        >>>
        >>> asyncio.run(main())
    """

    def __init__(
        self,
        registry: PatternRegistry,
        default_mask_char: str = "*",
        hash_algorithm: str = "sha256",
    ) -> None:
        """
        Initialize async engine with pattern registry.

        Args:
            registry: PatternRegistry with loaded patterns
            default_mask_char: Default character to use for masking
            hash_algorithm: Hash algorithm for hashing strategy
        """
        self.registry = registry
        self.default_mask_char = default_mask_char
        self.hash_algorithm = hash_algorithm

    async def find(
        self,
        text: str,
        namespaces: Optional[List[str]] = None,
        allow_overlaps: bool = False,
        include_matched_text: bool = False,
        stop_on_first_match: bool = False,
    ) -> FindResult:
        """
        Asynchronously find all PII matches in text.

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

        Returns:
            FindResult with all matches
        """
        # Run the CPU-bound pattern matching in an executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._find_sync,
            text,
            namespaces,
            allow_overlaps,
            include_matched_text,
            stop_on_first_match,
        )

    def _find_sync(
        self,
        text: str,
        namespaces: Optional[List[str]],
        allow_overlaps: bool,
        include_matched_text: bool,
        stop_on_first_match: bool,
    ) -> FindResult:
        """Synchronous implementation of find (called from executor)."""
        if namespaces is None:
            namespaces = list(self.registry.namespaces.keys())

        matches: List[Match] = []

        # Collect patterns from requested namespaces
        patterns = []
        for ns in namespaces:
            patterns.extend(self.registry.get_namespace_patterns(ns))

        # Sort patterns by priority (lower = higher priority)
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

    async def find_batch(
        self,
        texts: List[str],
        namespaces: Optional[List[str]] = None,
        allow_overlaps: bool = False,
        include_matched_text: bool = False,
        stop_on_first_match: bool = False,
    ) -> List[FindResult]:
        """
        Asynchronously find PII matches in multiple texts concurrently.

        This method processes multiple texts in parallel, which is more efficient
        than calling find() sequentially for each text.

        Args:
            texts: List of texts to search
            namespaces: List of namespaces to search
            allow_overlaps: Whether to allow overlapping matches
            include_matched_text: Whether to include matched text in results
            stop_on_first_match: If True, stop searching after finding first match

        Returns:
            List of FindResult objects, one for each input text
        """
        tasks = [
            self.find(
                text,
                namespaces=namespaces,
                allow_overlaps=allow_overlaps,
                include_matched_text=include_matched_text,
                stop_on_first_match=stop_on_first_match,
            )
            for text in texts
        ]
        return await asyncio.gather(*tasks)

    async def validate(self, text: str, ns_id: str) -> ValidationResult:
        """
        Asynchronously validate text against a specific pattern.

        Args:
            text: Text to validate
            ns_id: Full namespace/id (e.g., "kr/mobile")

        Returns:
            ValidationResult indicating if text matches pattern

        Raises:
            ValueError: If pattern not found
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._validate_sync, text, ns_id)

    def _validate_sync(self, text: str, ns_id: str) -> ValidationResult:
        """Synchronous implementation of validate (called from executor)."""
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

    async def validate_batch(
        self,
        texts: List[str],
        ns_id: str,
    ) -> List[ValidationResult]:
        """
        Asynchronously validate multiple texts against a specific pattern.

        Args:
            texts: List of texts to validate
            ns_id: Full namespace/id (e.g., "kr/mobile")

        Returns:
            List of ValidationResult objects, one for each input text

        Raises:
            ValueError: If pattern not found
        """
        tasks = [self.validate(text, ns_id) for text in texts]
        return await asyncio.gather(*tasks)

    async def redact(
        self,
        text: str,
        namespaces: Optional[List[str]] = None,
        strategy: Optional[RedactionStrategy] = None,
        allow_overlaps: bool = False,
    ) -> RedactionResult:
        """
        Asynchronously redact PII from text.

        Args:
            text: Text to redact
            namespaces: List of namespaces to search. If None, searches all.
            strategy: Redaction strategy (mask/hash/tokenize). If None, uses mask.
            allow_overlaps: Whether to allow overlapping matches

        Returns:
            RedactionResult with redacted text and match information
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._redact_sync,
            text,
            namespaces,
            strategy,
            allow_overlaps,
        )

    def _redact_sync(
        self,
        text: str,
        namespaces: Optional[List[str]],
        strategy: Optional[RedactionStrategy],
        allow_overlaps: bool,
    ) -> RedactionResult:
        """Synchronous implementation of redact (called from executor)."""
        if strategy is None:
            strategy = RedactionStrategy.MASK

        # Find all matches
        find_result = self._find_sync(
            text,
            namespaces=namespaces,
            allow_overlaps=allow_overlaps,
            include_matched_text=True,
            stop_on_first_match=False,
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

    async def redact_batch(
        self,
        texts: List[str],
        namespaces: Optional[List[str]] = None,
        strategy: Optional[RedactionStrategy] = None,
        allow_overlaps: bool = False,
    ) -> List[RedactionResult]:
        """
        Asynchronously redact PII from multiple texts concurrently.

        Args:
            texts: List of texts to redact
            namespaces: List of namespaces to search
            strategy: Redaction strategy (mask/hash/tokenize)
            allow_overlaps: Whether to allow overlapping matches

        Returns:
            List of RedactionResult objects, one for each input text
        """
        tasks = [
            self.redact(
                text,
                namespaces=namespaces,
                strategy=strategy,
                allow_overlaps=allow_overlaps,
            )
            for text in texts
        ]
        return await asyncio.gather(*tasks)

    def _get_replacement(self, original: str, match: Match, strategy: RedactionStrategy) -> str:
        """Get replacement text for a match based on strategy."""
        if strategy == RedactionStrategy.MASK:
            if match.mask:
                return match.mask
            return self.default_mask_char * len(original)

        elif strategy == RedactionStrategy.HASH:
            hasher = hashlib.new(self.hash_algorithm)
            hasher.update(original.encode("utf-8"))
            return f"[HASH:{hasher.hexdigest()[:16]}]"

        elif strategy == RedactionStrategy.TOKENIZE:
            return f"[TOKEN:{match.ns_id}:{match.start}]"

        return self.default_mask_char * len(original)

    @staticmethod
    def _spans_overlap(span1: Tuple[int, int], span2: Tuple[int, int]) -> bool:
        """Check if two spans overlap."""
        start1, end1 = span1
        start2, end2 = span2
        return not (end1 <= start2 or end2 <= start1)
