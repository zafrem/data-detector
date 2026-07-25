"""Tests for FileStorageAdapter using tmp_path fixtures."""

import json

import pytest

from datadetector.adapters.file_storage import FileStorageAdapter
from datadetector.resource_models import (
    ConnectionConfig,
    ContainerType,
    DataResource,
    ResourceType,
)


@pytest.fixture
def csv_dir(tmp_path):
    """Create a directory with CSV test files."""
    # users.csv
    users = tmp_path / "users.csv"
    users.write_text(
        "name,email,phone,ssn\n"
        "John Doe,john@example.com,010-1234-5678,123-45-6789\n"
        "Jane Smith,jane@test.org,010-9876-5432,987-65-4321\n"
        "Bob Lee,bob@mail.com,010-1111-2222,111-22-3333\n"
    )

    # orders.csv
    orders = tmp_path / "orders.csv"
    orders.write_text(
        "order_id,user_name,credit_card,amount\n"
        "1,John Doe,4111-1111-1111-1111,99.99\n"
        "2,Jane Smith,5500-0000-0000-0004,149.99\n"
    )

    # empty.csv
    empty = tmp_path / "empty.csv"
    empty.write_text("col_a,col_b\n")

    return tmp_path


@pytest.fixture
def json_dir(tmp_path):
    """Create a directory with JSON test files."""
    # users.json (array)
    data = [
        {"name": "John", "email": "john@example.com", "age": 30},
        {"name": "Jane", "email": "jane@test.org", "age": 25},
    ]
    (tmp_path / "users.json").write_text(json.dumps(data))

    # config.json (object)
    config = {"db_host": "localhost", "api_key": "sk-12345", "debug": True}
    (tmp_path / "config.json").write_text(json.dumps(config))

    return tmp_path


@pytest.fixture
def jsonl_dir(tmp_path):
    """Create a directory with JSONL test files."""
    lines = [
        json.dumps({"user_id": "1", "email": "john@example.com", "ssn": "123-45-6789"}),
        json.dumps({"user_id": "2", "email": "jane@test.org", "ssn": "987-65-4321"}),
    ]
    (tmp_path / "events.jsonl").write_text("\n".join(lines) + "\n")
    return tmp_path


def _make_adapter(path, **params):
    """Create a FileStorageAdapter for a path."""
    resource = DataResource(
        name="test-files",
        resource_type=ResourceType.FILE_STORAGE,
        connection=ConnectionConfig(uri=str(path), params=params),
    )
    adapter = FileStorageAdapter(resource)
    adapter.connect()
    return adapter


class TestFileStorageAdapterConnection:
    def test_connect_directory(self, csv_dir):
        adapter = _make_adapter(csv_dir)
        assert adapter._connected is True
        assert len(adapter._files) >= 2
        adapter.close()

    def test_connect_single_file(self, csv_dir):
        adapter = _make_adapter(csv_dir / "users.csv")
        assert adapter._connected is True
        assert len(adapter._files) == 1
        adapter.close()

    def test_connect_nonexistent_raises(self, tmp_path):
        with pytest.raises(ConnectionError):
            _make_adapter(tmp_path / "nonexistent")

    def test_context_manager(self, csv_dir):
        resource = DataResource(
            name="test",
            resource_type=ResourceType.FILE_STORAGE,
            connection=ConnectionConfig(uri=str(csv_dir)),
        )
        with FileStorageAdapter(resource) as adapter:
            assert adapter._connected is True

    def test_glob_filter(self, csv_dir):
        adapter = _make_adapter(csv_dir, glob="users.*")
        containers = adapter.list_containers()
        assert len(containers) == 1
        assert containers[0].name == "users.csv"
        adapter.close()


class TestFileStorageCSV:
    def test_list_containers(self, csv_dir):
        adapter = _make_adapter(csv_dir)
        containers = adapter.list_containers()
        names = [c.name for c in containers]
        assert "users.csv" in names
        assert "orders.csv" in names
        assert all(c.container_type == ContainerType.FILE for c in containers)

    def test_list_fields(self, csv_dir):
        adapter = _make_adapter(csv_dir)
        fields = adapter.list_fields("users.csv")
        names = [f.name for f in fields]
        assert "name" in names
        assert "email" in names
        assert "phone" in names
        assert "ssn" in names

    def test_sample_values(self, csv_dir):
        adapter = _make_adapter(csv_dir)
        values = adapter.sample_values("users.csv", "email", limit=10)
        assert len(values) == 3
        assert "john@example.com" in values

    def test_sample_empty_file(self, csv_dir):
        adapter = _make_adapter(csv_dir)
        values = adapter.sample_values("empty.csv", "col_a", limit=10)
        assert values == []

    def test_list_fields_empty_file(self, csv_dir):
        adapter = _make_adapter(csv_dir)
        fields = adapter.list_fields("empty.csv")
        names = [f.name for f in fields]
        assert "col_a" in names
        assert "col_b" in names


class TestFileStorageJSON:
    def test_list_fields_array(self, json_dir):
        adapter = _make_adapter(json_dir)
        fields = adapter.list_fields("users.json")
        names = [f.name for f in fields]
        assert "name" in names
        assert "email" in names
        assert "age" in names

    def test_list_fields_object(self, json_dir):
        adapter = _make_adapter(json_dir)
        fields = adapter.list_fields("config.json")
        names = [f.name for f in fields]
        assert "db_host" in names
        assert "api_key" in names

    def test_sample_values_array(self, json_dir):
        adapter = _make_adapter(json_dir)
        values = adapter.sample_values("users.json", "email", limit=10)
        assert len(values) == 2
        assert "john@example.com" in values

    def test_sample_values_object(self, json_dir):
        adapter = _make_adapter(json_dir)
        values = adapter.sample_values("config.json", "api_key", limit=10)
        assert "sk-12345" in values


class TestFileStorageJSONL:
    def test_list_fields(self, jsonl_dir):
        adapter = _make_adapter(jsonl_dir)
        fields = adapter.list_fields("events.jsonl")
        names = [f.name for f in fields]
        assert "user_id" in names
        assert "email" in names
        assert "ssn" in names

    def test_sample_values(self, jsonl_dir):
        adapter = _make_adapter(jsonl_dir)
        values = adapter.sample_values("events.jsonl", "email", limit=10)
        assert len(values) == 2
        assert "john@example.com" in values


class TestFileStorageContainerFilter:
    def test_pattern_filter(self, csv_dir):
        adapter = _make_adapter(csv_dir)
        containers = adapter.list_containers(pattern="user*")
        assert len(containers) == 1
        assert containers[0].name == "users.csv"
