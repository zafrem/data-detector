"""Tests for VectorDBAdapter using the generic (dict-based) backend."""

import pytest

from datadetector.adapters.vector_db import VectorDBAdapter
from datadetector.resource_models import (
    ConnectionConfig,
    ContainerType,
    DataResource,
    ResourceType,
)


def _make_generic_data():
    """Create sample vector DB data with PII in documents and metadata."""
    return {
        "user_profiles": {
            "documents": [
                "John Doe lives at 123 Main St, Springfield. Phone: 010-1234-5678",
                "Jane Smith's email is jane@example.com. SSN: 123-45-6789",
                "Contact Bob Lee at bob@company.org for support inquiries",
                "Alice has passport number M12345678 and lives in Seoul",
            ],
            "metadatas": [
                {"source": "crm", "user_id": "u001", "email": "john@example.com"},
                {"source": "crm", "user_id": "u002", "email": "jane@example.com"},
                {"source": "support", "user_id": "u003", "email": "bob@company.org"},
                {"source": "crm", "user_id": "u004", "email": "alice@mail.com"},
            ],
        },
        "product_docs": {
            "documents": [
                "The API endpoint supports GET and POST methods",
                "Configure the database connection string in settings.yaml",
                "For billing inquiries, contact support@company.com",
            ],
            "metadatas": [
                {"source": "docs", "category": "api"},
                {"source": "docs", "category": "setup"},
                {"source": "docs", "category": "billing"},
            ],
        },
        "empty_collection": {
            "documents": [],
            "metadatas": [],
        },
    }


def _make_adapter(**params):
    """Create a VectorDBAdapter with generic backend."""
    data = params.pop("data", _make_generic_data())
    resource = DataResource(
        name="test-vectordb",
        resource_type=ResourceType.VECTOR_DB,
        connection=ConnectionConfig(
            uri=None,
            params={"backend": "generic", "data": data, **params},
        ),
    )
    adapter = VectorDBAdapter(resource)
    adapter.connect()
    return adapter


class TestVectorDBAdapterConnect:
    """Test connection behavior."""

    def test_connect_generic(self):
        adapter = _make_adapter()
        assert adapter._connected is True
        adapter.close()
        assert adapter._connected is False

    def test_connect_idempotent(self):
        adapter = _make_adapter()
        adapter.connect()  # Second connect should be no-op
        assert adapter._connected is True
        adapter.close()

    def test_connect_unsupported_backend(self):
        resource = DataResource(
            name="bad",
            resource_type=ResourceType.VECTOR_DB,
            connection=ConnectionConfig(params={"backend": "pinecone", "data": {}}),
        )
        adapter = VectorDBAdapter(resource)
        with pytest.raises(ValueError, match="Unsupported vector DB backend"):
            adapter.connect()

    def test_context_manager(self):
        data = _make_generic_data()
        resource = DataResource(
            name="test-ctx",
            resource_type=ResourceType.VECTOR_DB,
            connection=ConnectionConfig(params={"backend": "generic", "data": data}),
        )
        with VectorDBAdapter(resource) as adapter:
            assert adapter._connected is True
            containers = adapter.list_containers()
            assert len(containers) > 0
        assert adapter._connected is False


class TestVectorDBAdapterListContainers:
    """Test container listing."""

    def test_list_all_containers(self):
        adapter = _make_adapter()
        containers = adapter.list_containers()
        names = {c.name for c in containers}
        assert names == {"user_profiles", "product_docs", "empty_collection"}
        adapter.close()

    def test_container_type_is_collection(self):
        adapter = _make_adapter()
        containers = adapter.list_containers()
        for c in containers:
            assert c.container_type == ContainerType.COLLECTION
        adapter.close()

    def test_container_metadata(self):
        adapter = _make_adapter()
        containers = adapter.list_containers()
        by_name = {c.name: c for c in containers}

        assert by_name["user_profiles"].metadata["document_count"] == 4
        assert by_name["product_docs"].metadata["document_count"] == 3
        assert by_name["empty_collection"].metadata["document_count"] == 0
        adapter.close()

    def test_filter_by_pattern(self):
        adapter = _make_adapter()
        containers = adapter.list_containers(pattern="user_*")
        assert len(containers) == 1
        assert containers[0].name == "user_profiles"
        adapter.close()

    def test_not_connected_raises(self):
        resource = DataResource(
            name="test",
            resource_type=ResourceType.VECTOR_DB,
            connection=ConnectionConfig(params={"backend": "generic", "data": {}}),
        )
        adapter = VectorDBAdapter(resource)
        with pytest.raises(RuntimeError, match="not connected"):
            adapter.list_containers()


class TestVectorDBAdapterListFields:
    """Test field listing."""

    def test_document_field_always_present(self):
        adapter = _make_adapter()
        fields = adapter.list_fields("user_profiles")
        field_names = [f.name for f in fields]
        assert "document" in field_names
        adapter.close()

    def test_metadata_fields_discovered(self):
        adapter = _make_adapter()
        fields = adapter.list_fields("user_profiles")
        field_names = [f.name for f in fields]
        assert "metadata.source" in field_names
        assert "metadata.user_id" in field_names
        assert "metadata.email" in field_names
        adapter.close()

    def test_no_metadata_when_disabled(self):
        adapter = _make_adapter(include_metadata=False)
        fields = adapter.list_fields("user_profiles")
        field_names = [f.name for f in fields]
        assert field_names == ["document"]
        adapter.close()

    def test_empty_collection_fields(self):
        adapter = _make_adapter()
        fields = adapter.list_fields("empty_collection")
        # Should at least have the document field
        assert len(fields) >= 1
        assert fields[0].name == "document"
        adapter.close()

    def test_custom_text_field_name(self):
        adapter = _make_adapter(text_field="content")
        fields = adapter.list_fields("user_profiles")
        field_names = [f.name for f in fields]
        assert "content" in field_names
        assert "document" not in field_names
        adapter.close()


class TestVectorDBAdapterSampleValues:
    """Test value sampling."""

    def test_sample_documents(self):
        adapter = _make_adapter()
        adapter.list_containers()  # populate collections
        values = adapter.sample_values("user_profiles", "document")
        assert len(values) == 4
        assert any("John Doe" in v for v in values)
        adapter.close()

    def test_sample_metadata_field(self):
        adapter = _make_adapter()
        adapter.list_containers()
        values = adapter.sample_values("user_profiles", "metadata.email")
        assert len(values) == 4
        assert "john@example.com" in values
        adapter.close()

    def test_sample_with_limit(self):
        adapter = _make_adapter()
        adapter.list_containers()
        values = adapter.sample_values("user_profiles", "document", limit=2)
        assert len(values) == 2
        adapter.close()

    def test_sample_empty_collection(self):
        adapter = _make_adapter()
        adapter.list_containers()
        values = adapter.sample_values("empty_collection", "document")
        assert values == []
        adapter.close()

    def test_sample_nonexistent_metadata(self):
        adapter = _make_adapter()
        adapter.list_containers()
        values = adapter.sample_values("user_profiles", "metadata.nonexistent")
        assert values == []
        adapter.close()


class TestVectorDBAdapterRelationships:
    """Test relationship detection."""

    def test_shared_metadata_relationships(self):
        adapter = _make_adapter()
        # List containers and fields to populate schemas
        for container in adapter.list_containers():
            adapter.list_fields(container.name)

        relationships = adapter.get_relationships()
        # user_profiles and product_docs share metadata.source
        source_rels = [r for r in relationships if "metadata.source" in r.source_field]
        assert len(source_rels) > 0
        adapter.close()
