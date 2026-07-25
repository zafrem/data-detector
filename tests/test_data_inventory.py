"""Tests for DataInventoryGenerator."""

import json

import pytest

from datadetector.data_inventory import DataInventoryGenerator
from datadetector.models import Category, Severity
from datadetector.resource_models import (
    ConnectionConfig,
    ContainerInfo,
    ContainerScanResult,
    ContainerType,
    DataInventory,
    DataResource,
    FieldInfo,
    FieldScanResult,
    InventoryEntry,
    InventoryFormat,
    PIIConfidence,
    ResourceScanResult,
    ResourceType,
    ScanStrategy,
)


@pytest.fixture
def sample_scan_result():
    """Create a ResourceScanResult with known PII columns."""
    resource = DataResource(
        name="test-db",
        resource_type=ResourceType.DATABASE,
        connection=ConnectionConfig(uri="sqlite:///:memory:"),
        owner="data-team",
        tags=["production"],
    )

    return ResourceScanResult(
        resource=resource,
        container_results=[
            ContainerScanResult(
                container=ContainerInfo(name="users", container_type=ContainerType.TABLE),
                field_results=[
                    FieldScanResult(
                        field_info=FieldInfo(
                            name="id", container_name="users", data_type="INTEGER"
                        ),
                        pii_detected=False,
                    ),
                    FieldScanResult(
                        field_info=FieldInfo(
                            name="email", container_name="users", data_type="VARCHAR"
                        ),
                        pii_detected=True,
                        confidence=PIIConfidence.HIGH,
                        categories=[Category.EMAIL],
                        severities=[Severity.MEDIUM],
                        ns_ids=["common/email_01"],
                        sample_count=100,
                        match_count=95,
                    ),
                    FieldScanResult(
                        field_info=FieldInfo(
                            name="ssn", container_name="users", data_type="VARCHAR"
                        ),
                        pii_detected=True,
                        confidence=PIIConfidence.CONFIRMED,
                        categories=[Category.SSN],
                        severities=[Severity.CRITICAL],
                        ns_ids=["us/ssn_01"],
                        sample_count=100,
                        match_count=100,
                    ),
                ],
            ),
            ContainerScanResult(
                container=ContainerInfo(name="logs", container_type=ContainerType.TABLE),
                field_results=[
                    FieldScanResult(
                        field_info=FieldInfo(name="ip", container_name="logs", data_type="VARCHAR"),
                        pii_detected=True,
                        confidence=PIIConfidence.MEDIUM,
                        categories=[Category.IP],
                        severities=[Severity.LOW],
                        ns_ids=["common/ip_01"],
                        sample_count=50,
                        match_count=30,
                    ),
                ],
            ),
        ],
        strategy=ScanStrategy.SAMPLE,
        scanned_at="2024-01-01T00:00:00+00:00",
    )


@pytest.fixture
def second_scan_result():
    """A second scan result from a Kafka resource."""
    resource = DataResource(
        name="test-kafka",
        resource_type=ResourceType.KAFKA,
        connection=ConnectionConfig(uri="localhost:9092"),
        owner="streaming-team",
    )

    return ResourceScanResult(
        resource=resource,
        container_results=[
            ContainerScanResult(
                container=ContainerInfo(name="user-events", container_type=ContainerType.TOPIC),
                field_results=[
                    FieldScanResult(
                        field_info=FieldInfo(
                            name="email", container_name="user-events", data_type="string"
                        ),
                        pii_detected=True,
                        confidence=PIIConfidence.HIGH,
                        categories=[Category.EMAIL],
                        severities=[Severity.MEDIUM],
                        ns_ids=["common/email_01"],
                        sample_count=50,
                        match_count=48,
                    ),
                ],
            ),
        ],
        strategy=ScanStrategy.SAMPLE,
    )


class TestDataInventoryGenerator:
    def test_generate_from_single_scan(self, sample_scan_result):
        gen = DataInventoryGenerator()
        gen.add_scan_result(sample_scan_result)
        inventory = gen.generate()

        assert inventory.total_pii_fields == 3
        assert inventory.generated_at is not None

        # Check entries
        email_entry = next(e for e in inventory.entries if e.field_name == "email")
        assert email_entry.resource_name == "test-db"
        assert email_entry.container_name == "users"
        assert Category.EMAIL in email_entry.categories
        assert email_entry.confidence == PIIConfidence.HIGH
        assert email_entry.owner == "data-team"

    def test_generate_from_multiple_scans(self, sample_scan_result, second_scan_result):
        gen = DataInventoryGenerator()
        gen.add_scan_result(sample_scan_result)
        gen.add_scan_result(second_scan_result)
        inventory = gen.generate()

        assert inventory.total_pii_fields == 4  # 3 from DB + 1 from Kafka

        by_resource = inventory.by_resource()
        assert len(by_resource["test-db"]) == 3
        assert len(by_resource["test-kafka"]) == 1

    def test_non_pii_fields_excluded(self, sample_scan_result):
        gen = DataInventoryGenerator()
        gen.add_scan_result(sample_scan_result)
        inventory = gen.generate()

        field_names = [e.field_name for e in inventory.entries]
        assert "id" not in field_names  # Non-PII field


class TestExportFormats:
    def test_export_json(self, sample_scan_result):
        gen = DataInventoryGenerator()
        gen.add_scan_result(sample_scan_result)
        inventory = gen.generate()

        result = gen.export(inventory, InventoryFormat.JSON)
        data = json.loads(result)
        assert data["total_pii_fields"] == 3
        assert len(data["entries"]) == 3
        assert data["entries"][0]["resource_name"] == "test-db"

    def test_export_csv(self, sample_scan_result):
        gen = DataInventoryGenerator()
        gen.add_scan_result(sample_scan_result)
        inventory = gen.generate()

        result = gen.export(inventory, InventoryFormat.CSV)
        lines = result.strip().split("\n")
        assert len(lines) == 4  # header + 3 entries
        assert "resource_name" in lines[0]
        assert "test-db" in lines[1]

    def test_export_yaml(self, sample_scan_result):
        gen = DataInventoryGenerator()
        gen.add_scan_result(sample_scan_result)
        inventory = gen.generate()

        result = gen.export(inventory, InventoryFormat.YAML)
        assert "total_pii_fields: 3" in result
        assert "resource_name: test-db" in result

    def test_export_html(self, sample_scan_result):
        gen = DataInventoryGenerator()
        gen.add_scan_result(sample_scan_result)
        inventory = gen.generate()

        result = gen.export(inventory, InventoryFormat.HTML)
        assert "<!DOCTYPE html>" in result
        assert "PII Data Inventory Report" in result
        assert "test-db" in result
        assert "email" in result

    def test_export_to_file(self, sample_scan_result, tmp_path):
        gen = DataInventoryGenerator()
        gen.add_scan_result(sample_scan_result)
        inventory = gen.generate()

        output_path = tmp_path / "inventory.json"
        with open(output_path, "w") as f:
            gen.export(inventory, InventoryFormat.JSON, output=f)

        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert data["total_pii_fields"] == 3


class TestJsonRoundTrip:
    def test_export_then_load(self, sample_scan_result, tmp_path):
        gen = DataInventoryGenerator()
        gen.add_scan_result(sample_scan_result)
        inventory = gen.generate()

        path = str(tmp_path / "inv.json")
        with open(path, "w") as f:
            gen.export(inventory, InventoryFormat.JSON, output=f)

        loaded = DataInventoryGenerator.load_json(path)
        assert loaded.total_pii_fields == inventory.total_pii_fields
        assert len(loaded.entries) == len(inventory.entries)

        for orig, loaded_e in zip(inventory.entries, loaded.entries):
            assert orig.resource_name == loaded_e.resource_name
            assert orig.field_name == loaded_e.field_name
            assert orig.confidence == loaded_e.confidence


class TestInventoryDiff:
    def test_diff_no_changes(self, sample_scan_result):
        gen = DataInventoryGenerator()
        gen.add_scan_result(sample_scan_result)
        inv = gen.generate()

        diff = DataInventoryGenerator.diff(inv, inv)
        assert diff.added == []
        assert diff.removed == []
        assert diff.changed == []
        assert diff.unchanged_count == 3

    def test_diff_new_entries(self, sample_scan_result, second_scan_result):
        gen1 = DataInventoryGenerator()
        gen1.add_scan_result(sample_scan_result)
        old_inv = gen1.generate()

        gen2 = DataInventoryGenerator()
        gen2.add_scan_result(sample_scan_result)
        gen2.add_scan_result(second_scan_result)
        new_inv = gen2.generate()

        diff = DataInventoryGenerator.diff(old_inv, new_inv)
        assert len(diff.added) == 1
        assert diff.added[0].resource_name == "test-kafka"

    def test_diff_removed_entries(self, sample_scan_result, second_scan_result):
        gen1 = DataInventoryGenerator()
        gen1.add_scan_result(sample_scan_result)
        gen1.add_scan_result(second_scan_result)
        old_inv = gen1.generate()

        gen2 = DataInventoryGenerator()
        gen2.add_scan_result(sample_scan_result)
        new_inv = gen2.generate()

        diff = DataInventoryGenerator.diff(old_inv, new_inv)
        assert len(diff.removed) == 1
        assert diff.removed[0].resource_name == "test-kafka"

    def test_diff_changed_entries(self, sample_scan_result):
        gen = DataInventoryGenerator()
        gen.add_scan_result(sample_scan_result)
        old_inv = gen.generate()

        # Create modified inventory
        new_inv = DataInventory(
            entries=[
                InventoryEntry(
                    resource_name="test-db",
                    resource_type=ResourceType.DATABASE,
                    container_name="users",
                    field_name="email",
                    categories=[Category.EMAIL],
                    max_severity=Severity.HIGH,  # Changed from MEDIUM
                    confidence=PIIConfidence.CONFIRMED,  # Changed from HIGH
                ),
                InventoryEntry(
                    resource_name="test-db",
                    resource_type=ResourceType.DATABASE,
                    container_name="users",
                    field_name="ssn",
                    categories=[Category.SSN],
                    max_severity=Severity.CRITICAL,
                    confidence=PIIConfidence.CONFIRMED,
                ),
                InventoryEntry(
                    resource_name="test-db",
                    resource_type=ResourceType.DATABASE,
                    container_name="logs",
                    field_name="ip",
                    categories=[Category.IP],
                    max_severity=Severity.LOW,
                    confidence=PIIConfidence.MEDIUM,
                ),
            ]
        )

        diff = DataInventoryGenerator.diff(old_inv, new_inv)
        assert len(diff.changed) == 1  # email entry changed
        old_email, new_email = diff.changed[0]
        assert old_email.max_severity == Severity.MEDIUM
        assert new_email.max_severity == Severity.HIGH


class TestSummary:
    def test_summary(self, sample_scan_result):
        gen = DataInventoryGenerator()
        gen.add_scan_result(sample_scan_result)
        inventory = gen.generate()

        summary = DataInventoryGenerator.summary(inventory)
        assert summary["total_pii_fields"] == 3
        assert summary["total_resources"] == 1
        assert "email" in summary["by_category"]
        assert "critical" in summary["by_severity"]
