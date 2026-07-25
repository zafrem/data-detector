"""Integration tests for the `data-detector resource lineage` CLI command.

Builds a PII lineage graph from inventory JSON artifacts (the distributed MLOps
flow: scan/inventory elsewhere, combine here). Runs fully offline.
"""

import json

import pytest
from click.testing import CliRunner

from datadetector.cli import main
from datadetector.data_inventory import DataInventoryGenerator
from datadetector.models import Category, Severity
from datadetector.resource_models import (
    DataInventory,
    InventoryEntry,
    InventoryFormat,
    PIIConfidence,
    ResourceType,
)


@pytest.fixture
def runner():
    return CliRunner()


def _write_inventory(path, resource, container, field_name, category=Category.EMAIL):
    inv = DataInventory(
        entries=[
            InventoryEntry(
                resource_name=resource,
                resource_type=ResourceType.TRAINING_DATA,
                container_name=container,
                field_name=field_name,
                data_type="text",
                categories=[category],
                max_severity=Severity.HIGH,
                confidence=PIIConfidence.HIGH,
            )
        ],
        generated_at="t",
    )
    path.write_text(DataInventoryGenerator().export(inv, InventoryFormat.JSON), encoding="utf-8")
    return path


class TestResourceLineageCLI:
    def test_mermaid_from_two_inventories(self, runner, tmp_path):
        a = _write_inventory(tmp_path / "a.json", "team-a", "users", "email")
        b = _write_inventory(tmp_path / "b.json", "team-b", "events", "email")

        result = runner.invoke(
            main, ["resource", "lineage", "--in", str(a), "--in", str(b), "--format", "mermaid"]
        )
        assert result.exit_code == 0, result.output
        assert "graph LR" in result.output
        # both email nodes present
        assert "team-a.users.email" in result.output
        assert "team-b.events.email" in result.output

    def test_json_output_has_graph_and_flow_summary(self, runner, tmp_path):
        a = _write_inventory(tmp_path / "a.json", "team-a", "users", "email")
        b = _write_inventory(tmp_path / "b.json", "team-b", "events", "email")

        result = runner.invoke(
            main, ["resource", "lineage", "--in", str(a), "--in", str(b), "--format", "json"]
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) >= 1  # inferred cross-resource link
        assert set(data["pii_flow_summary"]["email"]) == {
            "team-a.users.email",
            "team-b.events.email",
        }
        assert "sources" in data and "sinks" in data

    def test_output_written_to_file(self, runner, tmp_path):
        a = _write_inventory(tmp_path / "a.json", "team-a", "users", "email")
        out = tmp_path / "lineage.mmd"
        result = runner.invoke(main, ["resource", "lineage", "--in", str(a), "--out", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        assert "graph LR" in out.read_text(encoding="utf-8")

    def test_explicit_link_option(self, runner, tmp_path):
        a = _write_inventory(tmp_path / "a.json", "team-a", "users", "email")
        b = _write_inventory(tmp_path / "b.json", "team-b", "events", "contact", Category.EMAIL)
        result = runner.invoke(
            main,
            [
                "resource",
                "lineage",
                "--in",
                str(a),
                "--in",
                str(b),
                "--link",
                "team-a:users.email=team-b:events.contact",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0, result.output
        edges = json.loads(result.output)["edges"]
        pairs = {(e["source"], e["target"]) for e in edges}
        assert ("team-a.users.email", "team-b.events.contact") in pairs

    def test_malformed_link_is_warned_not_fatal(self, runner, tmp_path):
        a = _write_inventory(tmp_path / "a.json", "team-a", "users", "email")
        result = runner.invoke(
            main,
            ["resource", "lineage", "--in", str(a), "--link", "garbage", "--format", "json"],
        )
        assert result.exit_code == 0
        assert "malformed --link" in result.output  # warning surfaced

    def test_unreadable_inventory_errors(self, runner, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not json}", encoding="utf-8")
        result = runner.invoke(main, ["resource", "lineage", "--in", str(bad)])
        assert result.exit_code == 1
        assert "no inventories" in result.output
