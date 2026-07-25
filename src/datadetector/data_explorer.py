"""Data Explorer: scan any resource adapter for PII.

The DataExplorer orchestrates PII detection across any data resource by:
1. Analyzing field metadata (names, types, comments) for PII indicators
2. Sampling actual values and running Engine.find() for pattern matching
3. Combining scores to produce confidence-rated results

Works with any ResourceAdapter implementation (Database, Kafka, API, FileStorage).
"""

import logging
import time
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Set

from datadetector.context import ContextHint, create_context_from_field_name
from datadetector.engine import Engine
from datadetector.models import Category, Match, Severity
from datadetector.resource_adapter import ResourceAdapter
from datadetector.resource_models import (
    ContainerInfo,
    ContainerScanResult,
    FieldInfo,
    FieldScanResult,
    PIIConfidence,
    ResourceScanResult,
    ScanStatus,
    ScanStrategy,
)

logger = logging.getLogger(__name__)

# SQL types that are unlikely to contain PII text
_SKIP_TYPES = {
    "blob",
    "binary",
    "varbinary",
    "bytea",
    "image",
    "boolean",
    "bool",
    "bit",
}

# SQL types that are more likely to contain PII
_TEXT_TYPES = {
    "varchar",
    "nvarchar",
    "char",
    "nchar",
    "text",
    "ntext",
    "clob",
    "string",
    "str",
}


class DataExplorer:
    """Scan any registered resource for PII using the pluggable adapter pattern.

    Example:
        >>> from datadetector import Engine, load_registry
        >>> from datadetector.adapters.database import DatabaseAdapter
        >>>
        >>> engine = Engine(registry=load_registry())
        >>> explorer = DataExplorer(engine)
        >>> with DatabaseAdapter(resource) as adapter:
        ...     result = explorer.scan(adapter)
        ...     for cr in result.container_results:
        ...         for fr in cr.field_results:
        ...             if fr.pii_detected:
        ...                 print(f"{fr.field_info.qualified_name}: {fr.categories}")
    """

    def __init__(
        self,
        engine: Engine,
        sample_limit: int = 100,
        metadata_weight: float = 0.3,
        sample_weight: float = 0.7,
        confidence_threshold: float = 0.3,
        namespaces: Optional[List[str]] = None,
        column_hints: Optional[Dict[str, ContextHint]] = None,
        on_container_scanned: Optional[Callable[[ContainerScanResult], None]] = None,
    ) -> None:
        """Initialize DataExplorer.

        Args:
            engine: PII detection engine with loaded pattern registry.
            sample_limit: Maximum sample values per field.
            metadata_weight: Weight for field-name-based score (0.0-1.0).
            sample_weight: Weight for sample-value-based score (0.0-1.0).
            confidence_threshold: Combined score threshold for PII detection.
            namespaces: Pattern namespaces to use (e.g., ["kr", "us"]). None = all.
            column_hints: Optional mapping of field names to explicit ContextHints
                         for overriding auto-detection.
            on_container_scanned: Optional callback invoked after each container scan.
        """
        self.engine = engine
        self.sample_limit = sample_limit
        self.metadata_weight = metadata_weight
        self.sample_weight = sample_weight
        self.confidence_threshold = confidence_threshold
        self.namespaces = namespaces
        self.column_hints = column_hints or {}
        self.on_container_scanned = on_container_scanned

    def scan(
        self,
        adapter: ResourceAdapter,
        strategy: ScanStrategy = ScanStrategy.SAMPLE,
        containers: Optional[List[str]] = None,
    ) -> ResourceScanResult:
        """Scan a resource for PII.

        Args:
            adapter: Connected ResourceAdapter instance.
            strategy: Scan depth (metadata_only, sample, full).
            containers: Optional list of container names to scan. None = all.

        Returns:
            ResourceScanResult with per-container, per-field results.
        """
        start_time = time.time()
        scan_started_at = datetime.now(timezone.utc).isoformat()
        errors: List[str] = []
        container_results: List[ContainerScanResult] = []
        status = ScanStatus.RUNNING

        try:
            all_containers = adapter.list_containers()
        except Exception as e:
            error_msg = f"Failed to list containers: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            scan_finished_at = datetime.now(timezone.utc).isoformat()
            return ResourceScanResult(
                resource=adapter.resource,
                container_results=[],
                strategy=strategy,
                scanned_at=scan_started_at,
                scan_started_at=scan_started_at,
                scan_finished_at=scan_finished_at,
                scan_duration_ms=(time.time() - start_time) * 1000,
                status=ScanStatus.FAILED,
                errors=errors,
            )

        # Filter containers if specific ones requested
        if containers is not None:
            container_set = set(containers)
            all_containers = [c for c in all_containers if c.name in container_set]

        for container in all_containers:
            try:
                result = self._scan_container(adapter, container, strategy)
                container_results.append(result)

                if self.on_container_scanned:
                    self.on_container_scanned(result)

            except Exception as e:
                error_msg = f"Error scanning container '{container.name}': {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        scan_finished_at = datetime.now(timezone.utc).isoformat()
        elapsed_ms = (time.time() - start_time) * 1000
        status = ScanStatus.COMPLETED if not errors else ScanStatus.FAILED

        return ResourceScanResult(
            resource=adapter.resource,
            container_results=container_results,
            strategy=strategy,
            scanned_at=scan_started_at,
            scan_started_at=scan_started_at,
            scan_finished_at=scan_finished_at,
            scan_duration_ms=elapsed_ms,
            status=status,
            errors=errors,
        )

    def _scan_container(
        self,
        adapter: ResourceAdapter,
        container: ContainerInfo,
        strategy: ScanStrategy,
    ) -> ContainerScanResult:
        """Scan all fields in one container."""
        start_time = time.time()

        fields = adapter.list_fields(container.name)
        field_results: List[FieldScanResult] = []

        for field_info in fields:
            try:
                result = self._scan_field(adapter, field_info, strategy)
                field_results.append(result)
            except Exception as e:
                logger.warning(f"Error scanning field '{field_info.qualified_name}': {e}")
                field_results.append(FieldScanResult(field_info=field_info))

        elapsed_ms = (time.time() - start_time) * 1000
        return ContainerScanResult(
            container=container,
            field_results=field_results,
            scan_duration_ms=elapsed_ms,
        )

    def _scan_field(
        self,
        adapter: ResourceAdapter,
        field_info: FieldInfo,
        strategy: ScanStrategy,
    ) -> FieldScanResult:
        """Scan a single field for PII.

        Algorithm:
        1. Score field name/metadata for PII likelihood
        2. If strategy >= SAMPLE: sample values, run Engine.find() on each
        3. Combine scores with weights
        4. Determine PIIConfidence from combined score
        """
        # Skip binary/blob types
        data_type_lower = field_info.data_type.lower()
        if any(skip in data_type_lower for skip in _SKIP_TYPES):
            return FieldScanResult(field_info=field_info)

        # Step 1: Metadata scoring
        metadata_score, context_hint = self._analyze_metadata(field_info)

        # Step 2: Sample scoring (if applicable)
        sample_score = 0.0
        sample_count = 0
        match_count = 0
        all_categories: Set[Category] = set()
        all_severities: Set[Severity] = set()
        all_ns_ids: Set[str] = set()
        all_matches: List[Match] = []

        if strategy != ScanStrategy.METADATA_ONLY:
            try:
                limit = self.sample_limit
                if strategy == ScanStrategy.FULL:
                    limit = 0  # Adapter handles "all"

                samples = adapter.sample_values(
                    field_info.container_name,
                    field_info.name,
                    limit=limit if limit > 0 else self.sample_limit,
                )
                sample_count = len(samples)

                if sample_count > 0:
                    for value in samples:
                        if not value or not value.strip():
                            continue

                        find_result = self.engine.find(
                            value,
                            namespaces=self.namespaces,
                            context=context_hint,
                            include_matched_text=True,
                            stop_on_first_match=True,
                        )

                        if find_result.has_matches:
                            match_count += 1
                            for m in find_result.matches:
                                all_categories.add(m.category)
                                all_severities.add(m.severity)
                                all_ns_ids.add(m.ns_id)
                            # Keep a few representative matches
                            if len(all_matches) < 5:
                                all_matches.extend(find_result.matches[:1])

                    sample_score = match_count / sample_count if sample_count > 0 else 0.0

            except Exception as e:
                logger.warning(f"Could not sample values for '{field_info.qualified_name}': {e}")

        # Step 3: Combine scores
        if strategy == ScanStrategy.METADATA_ONLY:
            combined_score = metadata_score
        else:
            combined_score = (
                self.metadata_weight * metadata_score + self.sample_weight * sample_score
            )

        # Step 4: Determine confidence and detection
        confidence = self._score_to_confidence(combined_score)
        pii_detected = combined_score >= self.confidence_threshold and (
            confidence != PIIConfidence.NONE
        )

        # If metadata scored high but no samples matched, lower confidence
        if (
            strategy != ScanStrategy.METADATA_ONLY
            and metadata_score > 0.5
            and sample_count > 0
            and match_count == 0
        ):
            confidence = PIIConfidence.LOW
            pii_detected = metadata_score >= 0.7

        categories_list = sorted(all_categories, key=lambda c: c.value)
        severities_list = sorted(
            all_severities,
            key=lambda s: {
                Severity.LOW: 0,
                Severity.MEDIUM: 1,
                Severity.HIGH: 2,
                Severity.CRITICAL: 3,
            }.get(s, 0),
        )

        return FieldScanResult(
            field_info=field_info,
            pii_detected=pii_detected,
            confidence=confidence,
            categories=categories_list,
            severities=severities_list,
            matches=all_matches,
            metadata_score=metadata_score,
            sample_score=sample_score,
            combined_score=combined_score,
            sample_count=sample_count,
            match_count=match_count,
            ns_ids=sorted(all_ns_ids),
        )

    def _analyze_metadata(
        self,
        field_info: FieldInfo,
    ) -> "tuple[float, Optional[ContextHint]]":
        """Score field name/type/description for PII likelihood.

        Uses create_context_from_field_name() from context.py to extract
        keywords from the field name, then checks if any patterns match.

        Returns:
            Tuple of (score, context_hint) where score is 0.0-1.0.
        """
        # Check explicit column hints first
        if field_info.name in self.column_hints:
            return (0.8, self.column_hints[field_info.name])
        if field_info.qualified_name in self.column_hints:
            return (0.8, self.column_hints[field_info.qualified_name])

        # Create context from field name
        context_hint = create_context_from_field_name(field_info.name)

        score = 0.0

        # Score based on keywords found
        if context_hint.keywords:
            # Check if any keyword matches known PII-related terms
            pii_keywords = {
                "ssn",
                "social_security",
                "email",
                "phone",
                "mobile",
                "cell",
                "passport",
                "rrn",
                "credit_card",
                "card_number",
                "bank",
                "account",
                "iban",
                "address",
                "zip",
                "postal",
                "name",
                "first_name",
                "last_name",
                "surname",
                "birth",
                "dob",
                "date_of_birth",
                "ip",
                "ip_address",
                "password",
                "pwd",
                "secret",
                "token",
                "national_id",
                "identification",
                "driver_license",
                "licence",
                "taxpayer",
            }
            matched_keywords = set(context_hint.keywords) & pii_keywords
            if matched_keywords:
                score = min(0.9, 0.5 + 0.15 * len(matched_keywords))

        # Score boost for text-like types
        data_type_lower = field_info.data_type.lower()
        if any(t in data_type_lower for t in _TEXT_TYPES):
            score = min(1.0, score + 0.05)

        # Score from description/comment
        if field_info.description:
            desc_lower = field_info.description.lower()
            pii_desc_terms = [
                "personal",
                "pii",
                "sensitive",
                "private",
                "confidential",
                "social security",
                "passport",
                "phone number",
                "email address",
            ]
            for term in pii_desc_terms:
                if term in desc_lower:
                    score = min(1.0, score + 0.2)
                    break

        return (score, context_hint)

    @staticmethod
    def _score_to_confidence(score: float) -> PIIConfidence:
        """Map combined score to PIIConfidence enum."""
        if score >= 0.9:
            return PIIConfidence.CONFIRMED
        elif score >= 0.7:
            return PIIConfidence.HIGH
        elif score >= 0.5:
            return PIIConfidence.MEDIUM
        elif score >= 0.2:
            return PIIConfidence.LOW
        return PIIConfidence.NONE
