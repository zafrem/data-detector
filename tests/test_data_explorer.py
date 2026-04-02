"""Tests for DataExplorer with MockAdapter."""

import pytest

from datadetector import Engine, load_registry
from datadetector.data_explorer import DataExplorer
from datadetector.resource_adapter import ResourceAdapter
from datadetector.resource_models import (
    ConnectionConfig,
    ContainerInfo,
    ContainerType,
    DataResource,
    FieldInfo,
    PIIConfidence,
    ResourceType,
    ScanStrategy,
)


class MockAdapter(ResourceAdapter):
    """Test adapter that returns pre-configured data."""

    def __init__(self, resource, containers, fields_by_container, samples_by_field):
        super().__init__(resource)
        self._containers = containers
        self._fields = fields_by_container
        self._samples = samples_by_field

    def connect(self):
        self._connected = True

    def close(self):
        self._connected = False

    def list_containers(self, pattern=None):
        return self._containers

    def list_fields(self, container_name):
        return self._fields.get(container_name, [])

    def sample_values(self, container_name, field_name, limit=100):
        key = f"{container_name}.{field_name}"
        return self._samples.get(key, [])[:limit]


@pytest.fixture
def registry():
    """Load a subset of patterns that pass validation."""
    from pathlib import Path

    base = Path(__file__).parent.parent / "pattern-engine" / "regex" / "pii"
    safe_paths = [
        str(base / "common" / "email.yml"),
        str(base / "common" / "ip.yml"),
        str(base / "common" / "credit-cards.yml"),
        str(base / "us"),
        str(base / "kr" / "phone.yml"),
        str(base / "kr" / "rrn.yml"),
        str(base / "kr" / "banks.yml"),
    ]
    return load_registry(paths=safe_paths, validate_schema=False, validate_examples=False)


@pytest.fixture
def engine(registry):
    return Engine(registry, enable_context_filtering=False)


@pytest.fixture
def mock_resource():
    return DataResource(
        name="test-resource",
        resource_type=ResourceType.DATABASE,
        connection=ConnectionConfig(uri="mock://test"),
    )


@pytest.fixture
def pii_adapter(mock_resource):
    """Adapter with PII-containing fields."""
    containers = [
        ContainerInfo(name="users", container_type=ContainerType.TABLE),
        ContainerInfo(name="logs", container_type=ContainerType.TABLE),
    ]
    fields = {
        "users": [
            FieldInfo(name="id", container_name="users", data_type="INTEGER"),
            FieldInfo(name="email", container_name="users", data_type="VARCHAR"),
            FieldInfo(name="ssn", container_name="users", data_type="VARCHAR"),
            FieldInfo(name="phone", container_name="users", data_type="VARCHAR"),
            FieldInfo(name="age", container_name="users", data_type="INTEGER"),
        ],
        "logs": [
            FieldInfo(name="id", container_name="logs", data_type="INTEGER"),
            FieldInfo(name="message", container_name="logs", data_type="TEXT"),
            FieldInfo(name="timestamp", container_name="logs", data_type="TEXT"),
        ],
    }
    samples = {
        "users.id": ["1", "2", "3"],
        "users.email": ["john@example.com", "jane@test.org", "bob@mail.com"],
        "users.ssn": ["123-45-6789", "987-65-4321", "111-22-3333"],
        "users.phone": ["010-1234-5678", "010-9876-5432"],
        "users.age": ["30", "25", "40"],
        "logs.id": ["1", "2"],
        "logs.message": ["System started", "User logged in"],
        "logs.timestamp": ["2024-01-01 00:00:00", "2024-01-02 12:00:00"],
    }

    adapter = MockAdapter(mock_resource, containers, fields, samples)
    adapter.connect()
    return adapter


@pytest.fixture
def clean_adapter(mock_resource):
    """Adapter with no PII."""
    containers = [
        ContainerInfo(name="config", container_type=ContainerType.TABLE),
    ]
    fields = {
        "config": [
            FieldInfo(name="key", container_name="config", data_type="VARCHAR"),
            FieldInfo(name="value", container_name="config", data_type="VARCHAR"),
        ],
    }
    samples = {
        "config.key": ["theme", "language", "timezone"],
        "config.value": ["dark", "en", "UTC"],
    }

    adapter = MockAdapter(mock_resource, containers, fields, samples)
    adapter.connect()
    return adapter


class TestDataExplorerScan:
    def test_scan_detects_email(self, engine, pii_adapter):
        explorer = DataExplorer(engine)
        result = explorer.scan(pii_adapter)

        # Find email field result
        email_result = None
        for cr in result.container_results:
            for fr in cr.field_results:
                if fr.field_info.name == "email":
                    email_result = fr
                    break

        assert email_result is not None
        assert email_result.pii_detected is True
        assert email_result.confidence != PIIConfidence.NONE

    def test_scan_detects_ssn(self, engine, pii_adapter):
        explorer = DataExplorer(engine, namespaces=["us", "common"])
        result = explorer.scan(pii_adapter)

        ssn_result = None
        for cr in result.container_results:
            for fr in cr.field_results:
                if fr.field_info.name == "ssn":
                    ssn_result = fr
                    break

        assert ssn_result is not None
        assert ssn_result.pii_detected is True

    def test_scan_clean_data(self, engine, clean_adapter):
        explorer = DataExplorer(engine)
        result = explorer.scan(clean_adapter)

        assert result.pii_fields == 0
        assert result.pii_containers == 0

    def test_scan_counts(self, engine, pii_adapter):
        explorer = DataExplorer(engine)
        result = explorer.scan(pii_adapter)

        assert result.total_fields == 8  # 5 users + 3 logs
        assert result.pii_fields >= 1
        assert len(result.container_results) == 2

    def test_scan_specific_containers(self, engine, pii_adapter):
        explorer = DataExplorer(engine)
        result = explorer.scan(pii_adapter, containers=["users"])

        assert len(result.container_results) == 1
        assert result.container_results[0].container.name == "users"

    def test_scan_has_timing(self, engine, pii_adapter):
        explorer = DataExplorer(engine)
        result = explorer.scan(pii_adapter)

        assert result.scan_duration_ms > 0
        assert result.scanned_at is not None

    def test_scan_errors_non_fatal(self, engine, mock_resource):
        """Adapter that raises on list_fields for one container."""

        class FailingAdapter(MockAdapter):
            def list_fields(self, container_name):
                if container_name == "bad_table":
                    raise RuntimeError("Permission denied")
                return super().list_fields(container_name)

        containers = [
            ContainerInfo(name="bad_table", container_type=ContainerType.TABLE),
            ContainerInfo(name="good_table", container_type=ContainerType.TABLE),
        ]
        fields = {
            "good_table": [
                FieldInfo(name="id", container_name="good_table", data_type="INTEGER"),
            ],
        }
        adapter = FailingAdapter(mock_resource, containers, fields, {})
        adapter.connect()

        explorer = DataExplorer(engine)
        result = explorer.scan(adapter)
        assert len(result.errors) >= 1
        # good_table should still be scanned
        good_results = [cr for cr in result.container_results if cr.container.name == "good_table"]
        assert len(good_results) == 1


class TestDataExplorerMetadata:
    def test_metadata_only_strategy(self, engine, pii_adapter):
        explorer = DataExplorer(engine)
        result = explorer.scan(pii_adapter, strategy=ScanStrategy.METADATA_ONLY)

        # Should still detect based on field names
        for cr in result.container_results:
            for fr in cr.field_results:
                assert fr.sample_count == 0  # No sampling done

    def test_high_metadata_score_for_known_fields(self, engine):
        """Fields named 'email', 'ssn', etc. should get high metadata scores."""
        explorer = DataExplorer(engine)
        field = FieldInfo(name="user_email", container_name="t", data_type="VARCHAR")
        score, hint = explorer._analyze_metadata(field)
        assert score > 0.4

    def test_low_metadata_score_for_generic_fields(self, engine):
        explorer = DataExplorer(engine)
        field = FieldInfo(name="count", container_name="t", data_type="INTEGER")
        score, hint = explorer._analyze_metadata(field)
        assert score < 0.3


class TestDataExplorerConfidence:
    def test_score_to_confidence(self):
        assert DataExplorer._score_to_confidence(0.95) == PIIConfidence.CONFIRMED
        assert DataExplorer._score_to_confidence(0.75) == PIIConfidence.HIGH
        assert DataExplorer._score_to_confidence(0.55) == PIIConfidence.MEDIUM
        assert DataExplorer._score_to_confidence(0.25) == PIIConfidence.LOW
        assert DataExplorer._score_to_confidence(0.05) == PIIConfidence.NONE

    def test_skip_binary_types(self, engine, mock_resource):
        """Binary/blob fields should be skipped."""
        containers = [
            ContainerInfo(name="t", container_type=ContainerType.TABLE),
        ]
        fields = {
            "t": [
                FieldInfo(name="photo", container_name="t", data_type="BLOB"),
                FieldInfo(name="data", container_name="t", data_type="BINARY"),
            ],
        }
        adapter = MockAdapter(mock_resource, containers, fields, {})
        adapter.connect()

        explorer = DataExplorer(engine)
        result = explorer.scan(adapter)
        for cr in result.container_results:
            for fr in cr.field_results:
                assert fr.pii_detected is False


class TestDataExplorerCallback:
    def test_on_container_scanned_callback(self, engine, pii_adapter):
        scanned = []
        explorer = DataExplorer(
            engine,
            on_container_scanned=lambda cr: scanned.append(cr.container.name),
        )
        explorer.scan(pii_adapter)
        assert "users" in scanned
        assert "logs" in scanned
