"""MLOps gate: pipeline-friendly PII scanning over text, RAG records, and training data.

This module turns Data Detector's detection into a CI/MLOps *gate*. Each
``scan_*`` helper returns a :class:`GateReport` that is JSON-serializable and
carries an exit code, so the same logic can run:

- in **tests / isolation** — pure library calls, no network or external services
  (text and JSONL paths need only core dependencies); or
- in **MLOps pipelines** — via the ``data-detector gate`` CLI, which writes a
  JSON report and returns a non-zero exit code when PII crosses a threshold.

Privacy by default: matched PII values are **not** included in the report unless
``show_matches=True`` is passed; only category, severity, score, and location.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from datadetector.engine import Engine
from datadetector.models import Severity

# Severity ordering used for gate thresholds (low is least severe).
_SEVERITY_ORDER: List[str] = [
    Severity.LOW.value,
    Severity.MEDIUM.value,
    Severity.HIGH.value,
    Severity.CRITICAL.value,
]


def _severity_rank(severity: str) -> int:
    """Return the ordinal rank of a severity string (unknown → lowest)."""
    try:
        return _SEVERITY_ORDER.index(severity)
    except ValueError:
        return 0


@dataclass
class GateFinding:
    """A single PII finding, safe to serialize into a report."""

    category: str
    severity: str
    ns_id: str
    score: float
    location: str  # where it was found, e.g. "stdin", "record[3].response"
    start: int
    end: int
    match_length: int
    matched_text: Optional[str] = None  # populated only when show_matches=True

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.matched_text is None:
            d.pop("matched_text")
        return d


@dataclass
class GateReport:
    """Aggregated result of a gate scan over one input source."""

    target: str  # "text" | "rag" | "training-data"
    source: str  # human-readable description of the input
    scanned_items: int  # texts / records / fields scanned
    items_with_pii: int
    findings: List[GateFinding] = field(default_factory=list)
    namespaces: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    schema_version: str = "1.0"

    @property
    def findings_count(self) -> int:
        return len(self.findings)

    @property
    def has_pii(self) -> bool:
        return bool(self.findings)

    @property
    def by_severity(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        return counts

    @property
    def by_category(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for f in self.findings:
            counts[f.category] = counts.get(f.category, 0) + 1
        return counts

    @property
    def max_severity(self) -> Optional[str]:
        if not self.findings:
            return None
        return max((f.severity for f in self.findings), key=_severity_rank)

    def gate_triggered(self, fail_on: str = Severity.LOW.value) -> bool:
        """True if any finding meets/exceeds the ``fail_on`` severity threshold."""
        threshold = _severity_rank(fail_on)
        return any(_severity_rank(f.severity) >= threshold for f in self.findings)

    def exit_code(self, fail_on: str = Severity.LOW.value) -> int:
        """Exit code for the gate: 2 on error, 1 if gate triggered, else 0."""
        if self.errors:
            return 2
        return 1 if self.gate_triggered(fail_on) else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "target": self.target,
            "source": self.source,
            "scanned_items": self.scanned_items,
            "items_with_pii": self.items_with_pii,
            "findings_count": self.findings_count,
            "max_severity": self.max_severity,
            "by_severity": self.by_severity,
            "by_category": self.by_category,
            "namespaces": self.namespaces,
            "findings": [f.to_dict() for f in self.findings],
            "errors": self.errors,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def _findings_from_text(
    engine: Engine,
    text: str,
    location: str,
    namespaces: Optional[List[str]],
    show_matches: bool,
) -> List[GateFinding]:
    """Run the engine on one text and convert matches into findings.

    When ``show_matches`` is set, the raw value is sliced from the source span
    directly. This is an explicit caller opt-in and intentionally bypasses the
    per-pattern ``store_raw`` policy that otherwise withholds raw values.
    """
    result = engine.find(text, namespaces=namespaces)
    findings: List[GateFinding] = []
    for m in result.matches:
        length = m.end - m.start
        findings.append(
            GateFinding(
                category=m.category.value,
                severity=m.severity.value,
                ns_id=m.ns_id,
                score=round(m.score, 4),
                location=location,
                start=m.start,
                end=m.end,
                match_length=length,
                matched_text=(text[m.start : m.end] if show_matches else None),
            )
        )
    return findings


def scan_text(
    engine: Engine,
    text: str,
    *,
    source: str = "text",
    namespaces: Optional[List[str]] = None,
    show_matches: bool = False,
) -> GateReport:
    """Scan a single block of text for PII."""
    findings = _findings_from_text(engine, text, source, namespaces, show_matches)
    return GateReport(
        target="text",
        source=source,
        scanned_items=1,
        items_with_pii=1 if findings else 0,
        findings=findings,
        namespaces=list(namespaces) if namespaces else [],
    )


# Default record fields scanned for RAG-style JSONL inputs.
DEFAULT_RAG_FIELDS: Tuple[str, ...] = (
    "query",
    "prompt",
    "document",
    "context",
    "response",
    "completion",
    "answer",
    "text",
    "content",
    "messages",
)


def _iter_record_texts(record: Dict[str, Any], fields: Iterable[str]) -> Iterator[Tuple[str, str]]:
    """Yield (subpath, text) pairs for the configured fields present in a record.

    Handles plain string fields and chat-style ``messages`` lists of
    ``{"role", "content"}`` dicts.
    """
    for fname in fields:
        if fname not in record:
            continue
        value = record[fname]
        if isinstance(value, str):
            yield fname, value
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    content = item.get("content")
                    role = item.get("role", "")
                    if isinstance(content, str):
                        label = f"{fname}[{i}].{role}" if role else f"{fname}[{i}].content"
                        yield label, content
                elif isinstance(item, str):
                    yield f"{fname}[{i}]", item


def scan_rag_records(
    engine: Engine,
    records: Iterable[Dict[str, Any]],
    *,
    source: str = "rag",
    fields: Iterable[str] = DEFAULT_RAG_FIELDS,
    namespaces: Optional[List[str]] = None,
    show_matches: bool = False,
) -> GateReport:
    """Scan an iterable of RAG/training records (parsed JSONL objects) for PII.

    Each record is scanned across its text-bearing fields; ``scanned_items`` counts
    records, and ``items_with_pii`` counts records with at least one finding.
    """
    field_list = tuple(fields)
    findings: List[GateFinding] = []
    scanned = 0
    with_pii = 0

    for idx, record in enumerate(records):
        scanned += 1
        if not isinstance(record, dict):
            continue
        record_findings: List[GateFinding] = []
        for subpath, text in _iter_record_texts(record, field_list):
            location = f"{source}:record[{idx}].{subpath}"
            record_findings.extend(
                _findings_from_text(engine, text, location, namespaces, show_matches)
            )
        if record_findings:
            with_pii += 1
            findings.extend(record_findings)

    return GateReport(
        target="rag",
        source=source,
        scanned_items=scanned,
        items_with_pii=with_pii,
        findings=findings,
        namespaces=list(namespaces) if namespaces else [],
    )


def scan_training_data(
    engine: Engine,
    uri: str,
    *,
    backend: str = "jsonl",
    namespaces: Optional[List[str]] = None,
    sample_limit: int = 100,
    strategy: str = "sample",
    extra_params: Optional[Dict[str, Any]] = None,
    show_matches: bool = False,
) -> GateReport:
    """Scan a training-data source (JSONL dir/file or HuggingFace dataset) for PII.

    Uses the TrainingDataAdapter + DataExplorer pipeline. The ``jsonl`` backend is
    fully offline and needs no optional dependencies, making it suitable for
    isolated test/CI environments.
    """
    # Imported lazily so the core import path stays light.
    from datadetector.adapters.training_data import TrainingDataAdapter
    from datadetector.data_explorer import DataExplorer
    from datadetector.resource_models import (
        ConnectionConfig,
        DataResource,
        ResourceType,
        ScanStrategy,
    )

    params: Dict[str, Any] = {"backend": backend}
    if extra_params:
        params.update(extra_params)

    resource = DataResource(
        name=uri,
        resource_type=ResourceType.TRAINING_DATA,
        connection=ConnectionConfig(uri=uri, params=params),
    )
    explorer = DataExplorer(engine, sample_limit=sample_limit, namespaces=namespaces)

    findings: List[GateFinding] = []
    errors: List[str] = []
    scanned_fields = 0
    pii_fields = 0

    try:
        with TrainingDataAdapter(resource) as adapter:
            result = explorer.scan(adapter, strategy=ScanStrategy(strategy))
    except Exception as e:  # noqa: BLE001 - surfaced as a gate error, not a crash
        return GateReport(
            target="training-data",
            source=uri,
            scanned_items=0,
            items_with_pii=0,
            findings=[],
            namespaces=list(namespaces) if namespaces else [],
            errors=[f"{type(e).__name__}: {e}"],
        )

    errors.extend(result.errors)
    scanned_fields = result.total_fields
    pii_fields = result.pii_fields

    for cr in result.container_results:
        container_name = cr.container.name
        for fr in cr.field_results:
            if not fr.pii_detected:
                continue
            severity = fr.max_severity.value if fr.max_severity else Severity.MEDIUM.value
            categories = [c.value for c in fr.categories] or ["other"]
            ns_id = fr.ns_ids[0] if fr.ns_ids else ""
            location = f"{container_name}.{fr.field_info.name}"
            for category in categories:
                findings.append(
                    GateFinding(
                        category=category,
                        severity=severity,
                        ns_id=ns_id,
                        score=round(fr.combined_score, 4),
                        location=location,
                        start=0,
                        end=0,
                        match_length=fr.match_count,
                        matched_text=None,  # field-level scan never emits raw values
                    )
                )

    report = GateReport(
        target="training-data",
        source=uri,
        scanned_items=scanned_fields,
        items_with_pii=pii_fields,
        findings=findings,
        namespaces=list(namespaces) if namespaces else [],
        errors=errors,
    )
    return report
