"""Integration tests for the MLOps gate CLI (`data-detector gate ...`).

These drive the real Click CLI end-to-end via CliRunner: stdin/file input,
JSON report output, exit codes, and severity thresholds. Everything runs
offline. Also covers the `resource scan`/`inventory` round-trip (regression for
the previously-broken inventory command).

Note: the CLI builds its engine with default scoring (placeholder filtering ON),
so these tests use realistic, non-placeholder PII values.
"""

import json

import pytest
from click.testing import CliRunner

from datadetector.cli import main

# Non-placeholder PII so the default placeholder filter does not drop it.
PHONE = "010-9876-5432"
EMAIL = "alice.kim@gmail.com"


@pytest.fixture
def runner():
    return CliRunner()


def _json(result):
    """Parse the pure-stdout JSON report from a gate command."""
    return json.loads(result.output)


# ── gate text ────────────────────────────────────────────────────────────────


class TestGateText:
    def test_stdin_with_pii_exits_1(self, runner):
        result = runner.invoke(
            main, ["gate", "text", "--ns", "kr", "-q"], input=f"call me at {PHONE}"
        )
        assert result.exit_code == 1
        report = _json(result)
        assert report["target"] == "text"
        assert report["findings_count"] >= 1
        assert report["source"] == "stdin"

    def test_clean_stdin_exits_0(self, runner):
        result = runner.invoke(
            main, ["gate", "text", "--ns", "kr", "-q"], input="the quick brown fox"
        )
        assert result.exit_code == 0
        assert _json(result)["findings_count"] == 0

    def test_file_input(self, runner, tmp_path):
        f = tmp_path / "in.txt"
        f.write_text(f"phone {PHONE}", encoding="utf-8")
        result = runner.invoke(main, ["gate", "text", str(f), "--ns", "kr", "-q"])
        assert result.exit_code == 1
        assert _json(result)["source"] == str(f)

    def test_fail_on_critical_passes_high_severity(self, runner):
        """A 'high' phone finding should NOT trip a 'critical' gate (exit 0)."""
        result = runner.invoke(
            main,
            ["gate", "text", "--ns", "kr", "--fail-on", "critical", "-q"],
            input=f"call {PHONE}",
        )
        assert result.exit_code == 0
        assert _json(result)["findings_count"] >= 1  # detected, but below threshold

    def test_report_file_written(self, runner, tmp_path):
        out = tmp_path / "report.json"
        result = runner.invoke(
            main,
            ["gate", "text", "--ns", "kr", "-q", "--report", str(out)],
            input=f"call {PHONE}",
        )
        assert result.exit_code == 1
        assert out.exists()
        report = json.loads(out.read_text(encoding="utf-8"))
        assert report["findings_count"] >= 1

    def test_show_matches_includes_raw_value(self, runner):
        result = runner.invoke(
            main,
            ["gate", "text", "--ns", "kr", "-q", "--show-matches"],
            input=f"call {PHONE}",
        )
        report = _json(result)
        assert any(f.get("matched_text") == PHONE for f in report["findings"])

    def test_summary_printed_when_not_quiet(self, runner):
        result = runner.invoke(main, ["gate", "text", "--ns", "kr"], input=f"call {PHONE}")
        assert result.exit_code == 1
        # Human-readable summary line is emitted (alongside the JSON report).
        assert "[FAIL]" in result.output
        assert "max_severity=high" in result.output


# ── gate rag ─────────────────────────────────────────────────────────────────


class TestGateRag:
    def _write_jsonl(self, tmp_path, lines):
        f = tmp_path / "rag.jsonl"
        f.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return f

    def test_jsonl_with_pii(self, runner, tmp_path):
        f = self._write_jsonl(
            tmp_path,
            [
                json.dumps({"query": "hi", "response": f"your number is {PHONE}"}),
                json.dumps({"query": "clean", "response": "nothing here"}),
            ],
        )
        result = runner.invoke(main, ["gate", "rag", str(f), "--ns", "kr", "-q"])
        assert result.exit_code == 1
        report = _json(result)
        assert report["target"] == "rag"
        assert report["scanned_items"] == 2
        assert report["items_with_pii"] == 1

    def test_chat_format_via_stdin(self, runner):
        line = json.dumps({"messages": [{"role": "user", "content": f"call {PHONE}"}]})
        result = runner.invoke(main, ["gate", "rag", "--ns", "kr", "-q"], input=line + "\n")
        assert result.exit_code == 1
        report = _json(result)
        assert "messages[0].user" in report["findings"][0]["location"]

    def test_field_option_limits_scope(self, runner, tmp_path):
        f = self._write_jsonl(
            tmp_path, [json.dumps({"notes": f"phone {PHONE}", "response": "clean"})]
        )
        result = runner.invoke(
            main, ["gate", "rag", str(f), "--field", "response", "--ns", "kr", "-q"]
        )
        assert result.exit_code == 0
        assert _json(result)["findings_count"] == 0

    def test_malformed_line_is_an_error_exit_2(self, runner, tmp_path):
        f = self._write_jsonl(tmp_path, ["{not valid json}", json.dumps({"response": "ok"})])
        result = runner.invoke(main, ["gate", "rag", str(f), "--ns", "kr", "-q"])
        assert result.exit_code == 2
        assert _json(result)["errors"]


# ── gate training-data ───────────────────────────────────────────────────────


class TestGateTrainingData:
    def test_jsonl_dir_offline(self, runner, tmp_path):
        (tmp_path / "train.jsonl").write_text(
            json.dumps({"instruction": "x", "output": f"reach me at {EMAIL}"})
            + "\n"
            + json.dumps({"instruction": "y", "output": "nothing sensitive"})
            + "\n",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["gate", "training-data", str(tmp_path), "--ns", "comm", "-q"])
        assert result.exit_code == 1
        report = _json(result)
        assert report["target"] == "training-data"
        assert report["items_with_pii"] >= 1

    def test_missing_source_errors_exit_2(self, runner):
        result = runner.invoke(
            main, ["gate", "training-data", "/nope/missing-xyz", "--ns", "comm", "-q"]
        )
        assert result.exit_code == 2
        assert _json(result)["errors"]


# ── resource scan + inventory round-trip (regression) ────────────────────────


class TestResourceInventoryRoundTrip:
    def test_scan_then_inventory(self, runner, tmp_path):
        csv = tmp_path / "people.csv"
        csv.write_text(f"name,phone\nAlice,{PHONE}\nBob,010-1111-3333\n", encoding="utf-8")

        scan_out = tmp_path / "scan.json"
        scan = runner.invoke(
            main,
            [
                "resource",
                "scan",
                "--type",
                "file_storage",
                "--uri",
                str(csv),
                "--ns",
                "kr",
                "--out",
                str(scan_out),
            ],
        )
        assert scan.exit_code == 0, scan.output + getattr(scan, "stderr", "")
        assert scan_out.exists()

        inv = runner.invoke(
            main, ["resource", "inventory", "--in", str(scan_out), "--format", "json"]
        )
        # Regression: previously failed with "ResourceScanResult is not defined".
        assert inv.exit_code == 0
        combined = inv.output + getattr(inv, "stderr", "")
        assert "ResourceScanResult" not in combined
