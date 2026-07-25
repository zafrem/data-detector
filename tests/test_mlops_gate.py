"""Unit tests for the MLOps gate module (datadetector.mlops).

Covers the pure report/finding logic (no engine required) and the library-level
scan_* helpers against the real engine. All paths here run offline.
"""

import json

import pytest

from datadetector import (
    Engine,
    GateFinding,
    GateReport,
    ScoringConfig,
    load_registry,
    scan_rag_records,
    scan_text,
    scan_training_data,
)


@pytest.fixture(scope="module")
def engine():
    """Engine with placeholder filtering off so test PII is detected."""
    return Engine(load_registry(), scoring_config=ScoringConfig(filter_placeholders=False))


def _finding(severity, category="phone", ns_id="kr/mobile_01"):
    return GateFinding(
        category=category,
        severity=severity,
        ns_id=ns_id,
        score=0.95,
        location="x",
        start=0,
        end=1,
        match_length=1,
    )


# ── Pure report logic (no engine) ────────────────────────────────────────────


class TestGateReportLogic:
    def test_empty_report_is_clean(self):
        report = GateReport(target="text", source="x", scanned_items=1, items_with_pii=0)
        assert report.has_pii is False
        assert report.findings_count == 0
        assert report.max_severity is None
        assert report.gate_triggered("low") is False
        assert report.exit_code("low") == 0

    def test_severity_aggregation(self):
        report = GateReport(
            target="text",
            source="x",
            scanned_items=1,
            items_with_pii=1,
            findings=[_finding("low"), _finding("high"), _finding("high", category="email")],
        )
        assert report.findings_count == 3
        assert report.max_severity == "high"
        assert report.by_severity == {"low": 1, "high": 2}
        assert report.by_category == {"phone": 2, "email": 1}

    @pytest.mark.parametrize(
        "fail_on,expected",
        [("low", True), ("medium", True), ("high", True), ("critical", False)],
    )
    def test_threshold_gating(self, fail_on, expected):
        """A single 'high' finding triggers for low/medium/high but not critical."""
        report = GateReport(
            target="text",
            source="x",
            scanned_items=1,
            items_with_pii=1,
            findings=[_finding("high")],
        )
        assert report.gate_triggered(fail_on) is expected
        assert report.exit_code(fail_on) == (1 if expected else 0)

    def test_errors_force_exit_code_2(self):
        report = GateReport(
            target="training-data",
            source="x",
            scanned_items=0,
            items_with_pii=0,
            errors=["boom"],
        )
        # Errors dominate even when no findings are present.
        assert report.exit_code("low") == 2

    def test_to_dict_omits_matched_text_by_default(self):
        report = GateReport(
            target="text",
            source="x",
            scanned_items=1,
            items_with_pii=1,
            findings=[_finding("high")],
        )
        d = report.to_dict()
        assert "matched_text" not in d["findings"][0]
        assert d["schema_version"] == "1.0"
        assert d["max_severity"] == "high"

    def test_to_json_is_valid_and_roundtrips_fields(self):
        report = GateReport(
            target="text",
            source="src",
            scanned_items=2,
            items_with_pii=1,
            findings=[_finding("medium")],
            namespaces=["kr"],
        )
        parsed = json.loads(report.to_json())
        assert parsed["target"] == "text"
        assert parsed["scanned_items"] == 2
        assert parsed["namespaces"] == ["kr"]
        assert parsed["findings_count"] == 1

    def test_show_matches_finding_includes_value(self):
        f = GateFinding(
            category="phone",
            severity="high",
            ns_id="kr/mobile_01",
            score=0.9,
            location="x",
            start=0,
            end=13,
            match_length=13,
            matched_text="010-1234-5678",
        )
        assert f.to_dict()["matched_text"] == "010-1234-5678"


# ── Library scan helpers (real engine, offline) ──────────────────────────────


class TestScanText:
    def test_detects_phone_and_gates(self, engine):
        report = scan_text(engine, "Call 010-1234-5678 now", namespaces=["kr"])
        assert report.has_pii
        assert report.target == "text"
        assert report.scanned_items == 1
        assert report.items_with_pii == 1
        assert any(f.category == "phone" for f in report.findings)
        assert report.exit_code("low") == 1

    def test_clean_text_passes(self, engine):
        report = scan_text(engine, "the quick brown fox", namespaces=["kr"])
        assert not report.has_pii
        assert report.exit_code("low") == 0

    def test_matched_text_hidden_unless_requested(self, engine):
        hidden = scan_text(engine, "Call 010-1234-5678", namespaces=["kr"])
        assert all(f.matched_text is None for f in hidden.findings)
        shown = scan_text(engine, "Call 010-1234-5678", namespaces=["kr"], show_matches=True)
        assert any(f.matched_text for f in shown.findings)


class TestScanRagRecords:
    def test_flat_fields_and_record_counts(self, engine):
        records = [
            {"query": "hi", "response": "your phone is 010-1234-5678"},
            {"query": "no pii here", "response": "all good"},
        ]
        report = scan_rag_records(engine, records, namespaces=["kr"])
        assert report.target == "rag"
        assert report.scanned_items == 2
        assert report.items_with_pii == 1
        assert report.findings[0].location.endswith("response")

    def test_chat_messages_format(self, engine):
        records = [{"messages": [{"role": "user", "content": "call 010-1234-5678"}]}]
        report = scan_rag_records(engine, records, namespaces=["kr"])
        assert report.items_with_pii == 1
        assert "messages[0].user" in report.findings[0].location

    def test_custom_fields_limit_scope(self, engine):
        records = [{"safe": "010-1234-5678", "response": "clean"}]
        # 'safe' is not a default field and not requested → nothing scanned.
        report = scan_rag_records(engine, records, fields=["response"], namespaces=["kr"])
        assert report.has_pii is False

    def test_non_dict_records_are_skipped(self, engine):
        report = scan_rag_records(engine, ["not a dict", 42], namespaces=["kr"])
        assert report.scanned_items == 2
        assert report.has_pii is False


class TestScanTrainingData:
    def test_jsonl_dir_offline(self, engine, tmp_path):
        f = tmp_path / "train.jsonl"
        f.write_text(
            '{"instruction":"x","output":"email me at a@b.com and call 010-1234-5678"}\n'
            '{"instruction":"y","output":"nothing sensitive"}\n',
            encoding="utf-8",
        )
        report = scan_training_data(engine, str(tmp_path), namespaces=["kr", "comm"])
        assert report.target == "training-data"
        assert report.scanned_items > 0
        assert report.items_with_pii >= 1
        assert report.has_pii
        # Field-level findings never leak raw values.
        assert all(f.matched_text is None for f in report.findings)

    def test_missing_path_is_reported_as_error_not_crash(self, engine):
        report = scan_training_data(engine, "/nonexistent/path-xyz", namespaces=["kr"])
        assert report.errors
        assert report.exit_code("low") == 2
