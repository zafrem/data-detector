"""Serialization utilities for resource scan results and models."""

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Dict, Type, TypeVar, List

from datadetector.models import Category, Match, Severity
from datadetector.resource_models import (
    ConnectionConfig,
    ContainerInfo,
    ContainerScanResult,
    ContainerType,
    DataResource,
    FieldInfo,
    FieldScanResult,
    PIIConfidence,
    ResourceScanResult,
    ResourceType,
    ScanStatus,
    ScanStrategy,
)

T = TypeVar("T")


class DataclassJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles dataclasses and enums."""

    def default(self, o: Any) -> Any:
        if is_dataclass(o):
            return asdict(o)
        if isinstance(o, Enum):
            return o.value
        return super().default(o)


def to_dict(obj: Any) -> Dict[str, Any]:
    """Convert a dataclass (or nested structure) to a dict."""
    return json.loads(json.dumps(obj, cls=DataclassJSONEncoder))


def from_dict(data: Dict[str, Any], cls: Type[T]) -> T:
    """Instantiate a dataclass from a dictionary (minimal recursive handling)."""
    if data is None:
        return None
        
    if cls == ResourceScanResult:
        # Manually reconstruct nested objects
        resource_data = data.get("resource")
        resource = DataResource(
            name=resource_data["name"],
            resource_type=ResourceType(resource_data["resource_type"]),
            connection=ConnectionConfig(
                uri=resource_data["connection"].get("uri"),
                params=resource_data["connection"].get("params", {}),
            ),
            description=resource_data.get("description", ""),
            tags=resource_data.get("tags", []),
            owner=resource_data.get("owner"),
        )

        container_results = []
        for cr_data in data.get("container_results", []):
            container_info_data = cr_data["container"]
            container = ContainerInfo(
                name=container_info_data["name"],
                container_type=ContainerType(container_info_data["container_type"]),
                metadata=container_info_data.get("metadata", {}),
            )

            field_results = []
            for fr_data in cr_data.get("field_results", []):
                fi_data = fr_data["field_info"]
                field_info = FieldInfo(
                    name=fi_data["name"],
                    container_name=fi_data["container_name"],
                    data_type=fi_data.get("data_type", "unknown"),
                    nullable=fi_data.get("nullable", True),
                    description=fi_data.get("description", ""),
                    metadata=fi_data.get("metadata", {}),
                )

                matches = []
                for m_data in fr_data.get("matches", []):
                    matches.append(
                        Match(
                            ns_id=m_data["ns_id"],
                            pattern_id=m_data["pattern_id"],
                            namespace=m_data["namespace"],
                            category=Category(m_data["category"]),
                            start=m_data["start"],
                            end=m_data["end"],
                            matched_text=m_data.get("matched_text"),
                            mask=m_data.get("mask"),
                            severity=Severity(m_data["severity"]),
                            score=m_data.get("score", 0.5),
                            verified=m_data.get("verified", False),
                            context_evidence=m_data.get("context_evidence", []),
                            detection_method=m_data.get("detection_method", "regex"),
                        )
                    )

                field_results.append(
                    FieldScanResult(
                        field_info=field_info,
                        pii_detected=fr_data.get("pii_detected", False),
                        confidence=PIIConfidence(fr_data.get("confidence", "none")),
                        categories=[Category(c) for c in fr_data.get("categories", [])],
                        severities=[Severity(s) for s in fr_data.get("severities", [])],
                        matches=matches,
                        metadata_score=fr_data.get("metadata_score", 0.0),
                        sample_score=fr_data.get("sample_score", 0.0),
                        combined_score=fr_data.get("combined_score", 0.0),
                        sample_count=fr_data.get("sample_count", 0),
                        match_count=fr_data.get("match_count", 0),
                        ns_ids=fr_data.get("ns_ids", []),
                    )
                )

            container_results.append(
                ContainerScanResult(
                    container=container,
                    field_results=field_results,
                    scan_duration_ms=cr_data.get("scan_duration_ms", 0.0),
                )
            )

        return ResourceScanResult(
            resource=resource,
            container_results=container_results,
            strategy=ScanStrategy(data.get("strategy", "sample")),
            scanned_at=data.get("scanned_at"),
            scan_started_at=data.get("scan_started_at"),
            scan_finished_at=data.get("scan_finished_at"),
            scan_duration_ms=data.get("scan_duration_ms", 0.0),
            status=ScanStatus(data.get("status", "completed")),
            errors=data.get("errors", []),
        )

    # Add other classes as needed or use a more robust library like dataclasses-json
    raise ValueError(f"Deserialization for {cls} not implemented")
