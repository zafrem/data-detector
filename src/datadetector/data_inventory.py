"""Data Inventory Generator: aggregate scan results into a PII catalog.

Converts ResourceScanResult objects into a unified DataInventory that
catalogs all PII fields across resources. Supports export to JSON, CSV,
YAML, and HTML formats, plus diffing between inventory snapshots.
"""

import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import IO, Any, Dict, List, Optional

import yaml

from datadetector.resource_models import (
    Category,
    DataInventory,
    InventoryDiff,
    InventoryEntry,
    InventoryFormat,
    MaskingPolicy,
    MaskingStrategy,
    PIIConfidence,
    ResourceScanResult,
    ScanMetadata,
    Severity,
)

logger = logging.getLogger(__name__)


class DataInventoryGenerator:
    """Aggregates ResourceScanResult objects into a unified DataInventory.

    Example:
        >>> generator = DataInventoryGenerator()
        >>> generator.add_scan_result(db_result)
        >>> generator.add_scan_result(kafka_result)
        >>> inventory = generator.generate()
        >>> print(f"Found {inventory.total_pii_fields} PII fields")
        >>> generator.export(inventory, InventoryFormat.HTML, open("report.html", "w"))
    """

    def __init__(self) -> None:
        self._scan_results: List[ResourceScanResult] = []

    def add_scan_result(self, result: ResourceScanResult) -> None:
        """Add a scan result to be included in inventory generation.

        Args:
            result: ResourceScanResult from DataExplorer.scan().
        """
        self._scan_results.append(result)

    def generate(self) -> DataInventory:
        """Generate the full inventory from accumulated scan results.

        Iterates all scan results and creates InventoryEntry for each
        field where pii_detected is True. Includes scan timing, sample
        counts, and recommended masking policies.

        Returns:
            DataInventory with all PII entries and scan metadata.
        """
        entries: List[InventoryEntry] = []
        scan_metadata_list: List[ScanMetadata] = []

        for scan_result in self._scan_results:
            resource = scan_result.resource

            # Collect scan metadata
            scan_metadata_list.append(
                ScanMetadata(
                    resource_name=resource.name,
                    resource_type=resource.resource_type,
                    strategy=scan_result.strategy,
                    scan_started_at=scan_result.scan_started_at or scan_result.scanned_at,
                    scan_finished_at=scan_result.scan_finished_at,
                    scan_duration_ms=scan_result.scan_duration_ms,
                    total_containers=len(scan_result.container_results),
                    total_fields=scan_result.total_fields,
                    pii_fields=scan_result.pii_fields,
                    status=scan_result.status,
                    errors=list(scan_result.errors),
                )
            )

            for container_result in scan_result.container_results:
                for field_result in container_result.field_results:
                    if not field_result.pii_detected:
                        continue

                    masking_policy = _recommend_masking_policy(field_result)

                    entries.append(
                        InventoryEntry(
                            resource_name=resource.name,
                            resource_type=resource.resource_type,
                            container_name=field_result.field_info.container_name,
                            field_name=field_result.field_info.name,
                            data_type=field_result.field_info.data_type,
                            categories=list(field_result.categories),
                            max_severity=field_result.max_severity,
                            confidence=field_result.confidence,
                            ns_ids=list(field_result.ns_ids),
                            match_ratio=field_result.match_ratio,
                            sample_count=field_result.sample_count,
                            match_count=field_result.match_count,
                            owner=resource.owner,
                            tags=list(resource.tags),
                            scan_started_at=(scan_result.scan_started_at or scan_result.scanned_at),
                            scan_finished_at=scan_result.scan_finished_at,
                            masking_policy=masking_policy,
                        )
                    )

        return DataInventory(
            entries=entries,
            generated_at=datetime.now(timezone.utc).isoformat(),
            scan_metadata=scan_metadata_list,
        )

    def export(
        self,
        inventory: DataInventory,
        fmt: InventoryFormat = InventoryFormat.JSON,
        output: Optional[IO[str]] = None,
    ) -> str:
        """Export inventory to the specified format.

        Args:
            inventory: DataInventory to export.
            fmt: Export format (json, csv, yaml, html).
            output: Optional writable file object. If provided, writes to it.

        Returns:
            The formatted string.
        """
        if fmt == InventoryFormat.JSON:
            result = self._export_json(inventory)
        elif fmt == InventoryFormat.CSV:
            result = self._export_csv(inventory)
        elif fmt == InventoryFormat.YAML:
            result = self._export_yaml(inventory)
        elif fmt == InventoryFormat.HTML:
            result = self._export_html(inventory)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        if output is not None:
            output.write(result)

        return result

    @staticmethod
    def diff(
        previous: DataInventory,
        current: DataInventory,
    ) -> InventoryDiff:
        """Compute diff between two inventory snapshots.

        Compares entries by (resource_name, container_name, field_name) key.

        Args:
            previous: Old inventory snapshot.
            current: New inventory snapshot.

        Returns:
            InventoryDiff with added, removed, and changed entries.
        """
        prev_map = {e.key: e for e in previous.entries}
        curr_map = {e.key: e for e in current.entries}

        prev_keys = set(prev_map.keys())
        curr_keys = set(curr_map.keys())

        added = [curr_map[k] for k in sorted(curr_keys - prev_keys)]
        removed = [prev_map[k] for k in sorted(prev_keys - curr_keys)]

        changed = []
        unchanged_count = 0
        for key in sorted(prev_keys & curr_keys):
            old_entry = prev_map[key]
            new_entry = curr_map[key]
            if _entries_differ(old_entry, new_entry):
                changed.append((old_entry, new_entry))
            else:
                unchanged_count += 1

        return InventoryDiff(
            added=added,
            removed=removed,
            changed=changed,
            unchanged_count=unchanged_count,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def summary(inventory: DataInventory) -> Dict[str, Any]:
        """Generate a summary of the inventory.

        Returns:
            Dict with total counts and breakdowns by category, severity,
            resource type, and confidence.
        """
        by_category: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        by_resource: Dict[str, int] = {}
        by_confidence: Dict[str, int] = {}
        resources: set = set()

        for entry in inventory.entries:
            resources.add(entry.resource_name)
            by_resource[entry.resource_name] = by_resource.get(entry.resource_name, 0) + 1
            if entry.max_severity:
                sev = entry.max_severity.value
                by_severity[sev] = by_severity.get(sev, 0) + 1
            conf = entry.confidence.value
            by_confidence[conf] = by_confidence.get(conf, 0) + 1
            for cat in entry.categories:
                by_category[cat.value] = by_category.get(cat.value, 0) + 1

        return {
            "total_pii_fields": inventory.total_pii_fields,
            "total_resources": len(resources),
            "generated_at": inventory.generated_at,
            "by_category": by_category,
            "by_severity": by_severity,
            "by_resource": by_resource,
            "by_confidence": by_confidence,
        }

    # ── Export format implementations ──

    def _export_json(self, inventory: DataInventory) -> str:
        """Export as JSON."""
        data = {
            "generated_at": inventory.generated_at,
            "total_pii_fields": inventory.total_pii_fields,
            "scan_metadata": [_scan_metadata_to_dict(m) for m in inventory.scan_metadata],
            "entries": [_entry_to_dict(e) for e in inventory.entries],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _export_csv(self, inventory: DataInventory) -> str:
        """Export as CSV."""
        output = io.StringIO()
        fieldnames = [
            "resource_name",
            "resource_type",
            "container_name",
            "field_name",
            "data_type",
            "categories",
            "max_severity",
            "confidence",
            "match_ratio",
            "ns_ids",
            "owner",
            "tags",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for entry in inventory.entries:
            writer.writerow(
                {
                    "resource_name": entry.resource_name,
                    "resource_type": entry.resource_type.value,
                    "container_name": entry.container_name,
                    "field_name": entry.field_name,
                    "data_type": entry.data_type,
                    "categories": ";".join(c.value for c in entry.categories),
                    "max_severity": entry.max_severity.value if entry.max_severity else "",
                    "confidence": entry.confidence.value,
                    "match_ratio": f"{entry.match_ratio:.2f}",
                    "ns_ids": ";".join(entry.ns_ids),
                    "owner": entry.owner or "",
                    "tags": ";".join(entry.tags),
                }
            )

        return output.getvalue()

    def _export_yaml(self, inventory: DataInventory) -> str:
        """Export as YAML."""
        data = {
            "generated_at": inventory.generated_at,
            "total_pii_fields": inventory.total_pii_fields,
            "scan_metadata": [_scan_metadata_to_dict(m) for m in inventory.scan_metadata],
            "entries": [_entry_to_dict(e) for e in inventory.entries],
        }
        return yaml.dump(data, default_flow_style=False, allow_unicode=True)

    def _export_html(self, inventory: DataInventory) -> str:
        """Export as self-contained HTML report."""
        summary = self.summary(inventory)

        severity_colors = {
            "critical": "#dc3545",
            "high": "#fd7e14",
            "medium": "#ffc107",
            "low": "#28a745",
        }

        # Build summary cards
        summary_cards = f"""
        <div class="summary">
            <div class="card">
                <div class="card-value">{summary['total_pii_fields']}</div>
                <div class="card-label">PII Fields</div>
            </div>
            <div class="card">
                <div class="card-value">{summary['total_resources']}</div>
                <div class="card-label">Resources</div>
            </div>
            <div class="card">
                <div class="card-value">{summary.get('by_severity', {}).get('critical', 0)}</div>
                <div class="card-label">Critical</div>
            </div>
            <div class="card">
                <div class="card-value">{summary.get('by_severity', {}).get('high', 0)}</div>
                <div class="card-label">High</div>
            </div>
        </div>"""

        # Build scan metadata section
        scan_info_rows = ""
        for m in inventory.scan_metadata:
            started = m.scan_started_at or "N/A"
            finished = m.scan_finished_at or "N/A"
            duration = f"{m.scan_duration_ms:.0f}ms" if m.scan_duration_ms else "N/A"
            scan_info_rows += f"""
            <tr>
                <td>{m.resource_name}</td>
                <td><span class="badge type">{m.resource_type.value}</span></td>
                <td>{m.strategy.value}</td>
                <td>{started}</td>
                <td>{finished}</td>
                <td>{duration}</td>
                <td>{m.total_fields}</td>
                <td>{m.pii_fields}</td>
                <td><span class="badge" style="background:{
                    '#28a745' if m.status.value == 'completed' else '#dc3545'
                }">{m.status.value}</span></td>
            </tr>"""

        scan_section = ""
        if scan_info_rows:
            scan_section = f"""
        <h2>Scan History</h2>
        <table>
        <thead>
        <tr>
            <th>Resource</th><th>Type</th><th>Strategy</th>
            <th>Started</th><th>Finished</th><th>Duration</th>
            <th>Fields</th><th>PII Fields</th><th>Status</th>
        </tr>
        </thead>
        <tbody>{scan_info_rows}</tbody>
        </table>
        <br>"""

        # Build table rows
        rows = ""
        for entry in inventory.entries:
            sev = entry.max_severity.value if entry.max_severity else "n/a"
            sev_color = severity_colors.get(sev, "#6c757d")
            cats = ", ".join(c.value for c in entry.categories)
            masking = entry.masking_policy.strategy.value if entry.masking_policy else "n/a"
            mask_pattern = entry.masking_policy.mask_pattern or "" if entry.masking_policy else ""
            samples = (
                f"{entry.match_count}/{entry.sample_count}" if entry.sample_count > 0 else "n/a"
            )
            rows += f"""
            <tr>
                <td>{entry.resource_name}</td>
                <td><span class="badge type">{entry.resource_type.value}</span></td>
                <td>{entry.container_name}</td>
                <td><strong>{entry.field_name}</strong></td>
                <td>{cats}</td>
                <td><span class="badge" style="background:{sev_color}">{sev}</span></td>
                <td>{entry.confidence.value}</td>
                <td>{samples}</td>
                <td>{entry.match_ratio:.0%}</td>
                <td><span class="badge" style="background:#6610f2">{masking}</span></td>
                <td><code>{mask_pattern}</code></td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>PII Data Inventory Report</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           margin: 2rem; background: #f8f9fa; color: #212529; }}
    h1 {{ color: #343a40; }}
    .meta {{ color: #6c757d; margin-bottom: 1.5rem; }}
    .summary {{ display: flex; gap: 1rem; margin-bottom: 2rem; }}
    .card {{ background: white; border-radius: 8px; padding: 1.5rem;
             box-shadow: 0 1px 3px rgba(0,0,0,0.1); min-width: 120px;
             text-align: center; }}
    .card-value {{ font-size: 2rem; font-weight: bold; color: #343a40; }}
    .card-label {{ color: #6c757d; margin-top: 0.25rem; }}
    table {{ width: 100%; border-collapse: collapse; background: white;
             border-radius: 8px; overflow: hidden;
             box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
    th {{ background: #343a40; color: white; padding: 0.75rem;
          text-align: left; font-weight: 600; }}
    td {{ padding: 0.75rem; border-bottom: 1px solid #dee2e6; }}
    tr:hover {{ background: #f1f3f5; }}
    .badge {{ display: inline-block; padding: 0.2rem 0.5rem; border-radius: 4px;
              color: white; font-size: 0.8rem; font-weight: 600; }}
    .badge.type {{ background: #6c757d; }}
</style>
</head>
<body>
<h1>PII Data Inventory Report</h1>
<div class="meta">Generated: {inventory.generated_at or 'N/A'}</div>
{summary_cards}
{scan_section}
<h2>PII Field Inventory</h2>
<table>
<thead>
<tr>
    <th>Resource</th>
    <th>Type</th>
    <th>Container</th>
    <th>Field</th>
    <th>PII Categories</th>
    <th>Severity</th>
    <th>Confidence</th>
    <th>Samples</th>
    <th>Match Ratio</th>
    <th>Masking</th>
    <th>Pattern</th>
</tr>
</thead>
<tbody>
{rows}
</tbody>
</table>
</body>
</html>"""

    @staticmethod
    def load_json(path: str) -> DataInventory:
        """Load a previously saved JSON inventory for diffing.

        Args:
            path: Path to JSON inventory file.

        Returns:
            DataInventory loaded from file.
        """
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        entries: List[InventoryEntry] = []
        for e in data.get("entries", []):
            categories = [Category(c) for c in e.get("categories", [])]
            max_sev = Severity(e["max_severity"]) if e.get("max_severity") else None
            confidence = PIIConfidence(e.get("confidence", "none"))

            from datadetector.resource_models import ResourceType

            entries.append(
                InventoryEntry(
                    resource_name=e["resource_name"],
                    resource_type=ResourceType(e["resource_type"]),
                    container_name=e["container_name"],
                    field_name=e["field_name"],
                    data_type=e.get("data_type", "unknown"),
                    categories=categories,
                    max_severity=max_sev,
                    confidence=confidence,
                    ns_ids=e.get("ns_ids", []),
                    match_ratio=e.get("match_ratio", 0.0),
                    owner=e.get("owner"),
                    tags=e.get("tags", []),
                )
            )

        return DataInventory(
            entries=entries,
            generated_at=data.get("generated_at"),
        )

    @staticmethod
    def load_json_str(json_str: str) -> DataInventory:
        """Load inventory from a JSON string.

        Args:
            json_str: JSON string of a previously exported inventory.

        Returns:
            DataInventory loaded from the string.
        """
        data = json.loads(json_str)

        from datadetector.resource_models import ResourceType

        entries: List[InventoryEntry] = []
        for e in data.get("entries", []):
            categories = [Category(c) for c in e.get("categories", [])]
            max_sev = Severity(e["max_severity"]) if e.get("max_severity") else None
            confidence = PIIConfidence(e.get("confidence", "none"))

            entries.append(
                InventoryEntry(
                    resource_name=e["resource_name"],
                    resource_type=ResourceType(e["resource_type"]),
                    container_name=e["container_name"],
                    field_name=e["field_name"],
                    data_type=e.get("data_type", "unknown"),
                    categories=categories,
                    max_severity=max_sev,
                    confidence=confidence,
                    ns_ids=e.get("ns_ids", []),
                    match_ratio=e.get("match_ratio", 0.0),
                    sample_count=e.get("sample_count", 0),
                    match_count=e.get("match_count", 0),
                    owner=e.get("owner"),
                    tags=e.get("tags", []),
                    scan_started_at=e.get("scan_started_at"),
                    scan_finished_at=e.get("scan_finished_at"),
                )
            )

        return DataInventory(
            entries=entries,
            generated_at=data.get("generated_at"),
        )


# ── Helpers ──


def _entry_to_dict(entry: InventoryEntry) -> Dict[str, Any]:
    """Convert InventoryEntry to a JSON-serializable dict."""
    result: Dict[str, Any] = {
        "resource_name": entry.resource_name,
        "resource_type": entry.resource_type.value,
        "container_name": entry.container_name,
        "field_name": entry.field_name,
        "data_type": entry.data_type,
        "categories": [c.value for c in entry.categories],
        "max_severity": entry.max_severity.value if entry.max_severity else None,
        "confidence": entry.confidence.value,
        "ns_ids": entry.ns_ids,
        "match_ratio": entry.match_ratio,
        "sample_count": entry.sample_count,
        "match_count": entry.match_count,
        "owner": entry.owner,
        "tags": entry.tags,
        "scan_started_at": entry.scan_started_at,
        "scan_finished_at": entry.scan_finished_at,
    }
    if entry.masking_policy:
        result["masking_policy"] = {
            "strategy": entry.masking_policy.strategy.value,
            "mask_pattern": entry.masking_policy.mask_pattern,
            "preserve_format": entry.masking_policy.preserve_format,
            "notes": entry.masking_policy.notes,
        }
    else:
        result["masking_policy"] = None
    return result


def _scan_metadata_to_dict(meta: ScanMetadata) -> Dict[str, Any]:
    """Convert ScanMetadata to a JSON-serializable dict."""
    return {
        "resource_name": meta.resource_name,
        "resource_type": meta.resource_type.value,
        "strategy": meta.strategy.value,
        "scan_started_at": meta.scan_started_at,
        "scan_finished_at": meta.scan_finished_at,
        "scan_duration_ms": meta.scan_duration_ms,
        "total_containers": meta.total_containers,
        "total_fields": meta.total_fields,
        "pii_fields": meta.pii_fields,
        "status": meta.status.value,
        "errors": meta.errors,
    }


def _recommend_masking_policy(field_result: Any) -> MaskingPolicy:
    """Recommend a masking policy based on PII categories and severity.

    Rules:
    - CRITICAL severity (SSN, passport) → HASH or ENCRYPT
    - HIGH severity (credit card, bank) → TOKENIZE
    - Email → FAKE (preserve format with fake data)
    - Phone → MASK with format preservation
    - Default → MASK
    """
    from datadetector.models import Category as Cat

    categories = set(field_result.categories)
    severity = field_result.max_severity
    mask_pattern = None

    # Check for the mask pattern from matches
    if field_result.matches:
        for m in field_result.matches:
            if hasattr(m, "mask") and m.mask:
                mask_pattern = m.mask
                break

    if severity and severity.value == "critical":
        return MaskingPolicy(
            strategy=MaskingStrategy.HASH,
            mask_pattern=mask_pattern,
            notes="Critical severity — hash recommended to prevent reconstruction",
        )

    if Cat.CREDIT_CARD in categories or Cat.BANK in categories:
        return MaskingPolicy(
            strategy=MaskingStrategy.TOKENIZE,
            mask_pattern=mask_pattern,
            preserve_format=True,
            notes="Financial data — tokenize for reversible protection",
        )

    if Cat.EMAIL in categories:
        return MaskingPolicy(
            strategy=MaskingStrategy.FAKE,
            mask_pattern=mask_pattern,
            preserve_format=True,
            notes="Email — fake data preserves format for testing",
        )

    if Cat.PHONE in categories:
        return MaskingPolicy(
            strategy=MaskingStrategy.MASK,
            mask_pattern=mask_pattern or "***-****-****",
            preserve_format=True,
            notes="Phone — mask with format preservation",
        )

    return MaskingPolicy(
        strategy=MaskingStrategy.MASK,
        mask_pattern=mask_pattern,
        notes="Default masking strategy",
    )


def _entries_differ(a: InventoryEntry, b: InventoryEntry) -> bool:
    """Check if two inventory entries differ in meaningful ways."""
    return (
        set(c.value for c in a.categories) != set(c.value for c in b.categories)
        or a.max_severity != b.max_severity
        or a.confidence != b.confidence
    )
