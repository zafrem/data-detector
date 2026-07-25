"""Tests for KafkaAdapter with mocked Schema Registry and consumer."""

import json
from unittest.mock import MagicMock, patch

import pytest

from datadetector.resource_models import (
    ConnectionConfig,
    ContainerType,
    DataResource,
    ResourceType,
)


class TestKafkaAdapterSchemaRegistry:
    """Test Schema Registry interaction with mocked HTTP."""

    @pytest.fixture
    def mock_adapter(self):
        """Create a KafkaAdapter with mocked dependencies."""
        # We need to mock confluent_kafka before importing
        with patch.dict(
            "sys.modules",
            {
                "confluent_kafka": MagicMock(),
                "confluent_kafka.admin": MagicMock(),
            },
        ):
            from datadetector.adapters.kafka import KafkaAdapter

            resource = DataResource(
                name="test-kafka",
                resource_type=ResourceType.KAFKA,
                connection=ConnectionConfig(
                    uri="localhost:9092",
                    params={"schema_registry_url": "http://localhost:8081"},
                ),
            )
            adapter = KafkaAdapter(resource)

            # Mock the requests module
            mock_requests = MagicMock()
            adapter._requests = mock_requests
            adapter._schema_registry_url = "http://localhost:8081"
            adapter._connected = True

            # Mock consumer
            adapter._consumer = MagicMock()
            adapter._admin_client = MagicMock()

            yield adapter, mock_requests

    def test_list_containers_from_sr(self, mock_adapter):
        adapter, mock_requests = mock_adapter

        # Mock SR subjects response
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = [
            "user-events-value",
            "order-events-value",
            "user-events-key",
        ]
        resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = resp

        containers = adapter.list_containers()
        names = [c.name for c in containers]
        assert "user-events" in names
        assert "order-events" in names
        assert all(c.container_type == ContainerType.TOPIC for c in containers)

    def test_list_fields_avro_schema(self, mock_adapter):
        adapter, mock_requests = mock_adapter

        avro_schema = {
            "type": "record",
            "name": "UserEvent",
            "fields": [
                {"name": "user_id", "type": "string"},
                {"name": "email", "type": ["null", "string"], "doc": "User email"},
                {"name": "phone", "type": "string"},
            ],
        }

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"schema": json.dumps(avro_schema)}
        mock_requests.get.return_value = resp

        fields = adapter.list_fields("user-events")
        names = [f.name for f in fields]
        assert "user_id" in names
        assert "email" in names
        assert "phone" in names

    def test_list_fields_json_schema(self, mock_adapter):
        adapter, mock_requests = mock_adapter

        json_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "ssn": {"type": "string", "description": "Social Security Number"},
            },
            "required": ["name"],
        }

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"schema": json.dumps(json_schema)}
        mock_requests.get.return_value = resp

        fields = adapter.list_fields("user-data")
        names = [f.name for f in fields]
        assert "name" in names
        assert "ssn" in names

        ssn_field = next(f for f in fields if f.name == "ssn")
        assert ssn_field.nullable is True  # Not in required
        name_field = next(f for f in fields if f.name == "name")
        assert name_field.nullable is False  # In required

    def test_list_fields_no_schema(self, mock_adapter):
        adapter, mock_requests = mock_adapter

        resp = MagicMock()
        resp.status_code = 404
        mock_requests.get.return_value = resp

        fields = adapter.list_fields("no-schema-topic")
        assert fields == []

    def test_extract_nested_field(self, mock_adapter):
        adapter, _ = mock_adapter

        data = {"user": {"profile": {"email": "test@example.com"}}}
        assert adapter._extract_nested_field(data, "user.profile.email") == "test@example.com"
        assert adapter._extract_nested_field(data, "nonexistent") is None

    def test_flatten_nested_avro(self, mock_adapter):
        adapter, mock_requests = mock_adapter

        avro_schema = {
            "type": "record",
            "name": "Event",
            "fields": [
                {"name": "id", "type": "string"},
                {
                    "name": "address",
                    "type": {
                        "type": "record",
                        "name": "Address",
                        "fields": [
                            {"name": "street", "type": "string"},
                            {"name": "zipcode", "type": "string"},
                        ],
                    },
                },
            ],
        }

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"schema": json.dumps(avro_schema)}
        mock_requests.get.return_value = resp

        fields = adapter.list_fields("address-events")
        names = [f.name for f in fields]
        assert "id" in names
        assert "address.street" in names
        assert "address.zipcode" in names
