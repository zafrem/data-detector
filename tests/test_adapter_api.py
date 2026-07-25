"""Tests for APIAdapter with inline OpenAPI specs."""

import pytest

from datadetector.adapters.api import APIAdapter
from datadetector.resource_models import (
    ConnectionConfig,
    ContainerType,
    DataResource,
    ResourceType,
)


@pytest.fixture
def simple_spec():
    """Simple OpenAPI 3.0 spec."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "operationId": "listUsers",
                    "tags": ["users"],
                    "parameters": [
                        {
                            "name": "email",
                            "in": "query",
                            "schema": {"type": "string"},
                            "description": "Filter by email",
                            "example": "test@example.com",
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "required": ["id", "name"],
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "name": {"type": "string"},
                                                "email": {
                                                    "type": "string",
                                                    "example": "user@example.com",
                                                },
                                                "phone": {"type": "string"},
                                            },
                                        },
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "summary": "Create user",
                    "operationId": "createUser",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["name", "email"],
                                    "properties": {
                                        "name": {"type": "string"},
                                        "email": {"type": "string"},
                                        "ssn": {
                                            "type": "string",
                                            "description": "Social Security Number",
                                        },
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "Created",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "name": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                },
            },
            "/users/{id}": {
                "get": {
                    "summary": "Get user",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {"200": {"description": "Success"}},
                }
            },
        },
    }


@pytest.fixture
def ref_spec():
    """Spec with $ref references."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Ref API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            }
                        }
                    }
                },
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/User"}}
                        }
                    },
                    "responses": {"201": {"description": "Created"}},
                },
            },
            "/orders": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Order"}
                                }
                            }
                        }
                    }
                }
            },
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                    },
                },
                "Order": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "total": {"type": "number"},
                    },
                },
            }
        },
    }


def _make_adapter(spec):
    """Create an APIAdapter with inline spec."""
    resource = DataResource(
        name="test-api",
        resource_type=ResourceType.API,
        connection=ConnectionConfig(params={"spec": spec}),
    )
    adapter = APIAdapter(resource)
    adapter.connect()
    return adapter


class TestAPIAdapterConnection:
    def test_connect_with_inline_spec(self, simple_spec):
        adapter = _make_adapter(simple_spec)
        assert adapter._connected is True
        adapter.close()
        assert adapter._connected is False

    def test_context_manager(self, simple_spec):
        resource = DataResource(
            name="test",
            resource_type=ResourceType.API,
            connection=ConnectionConfig(params={"spec": simple_spec}),
        )
        with APIAdapter(resource) as adapter:
            assert adapter._connected is True

    def test_missing_spec_raises(self):
        resource = DataResource(
            name="test",
            resource_type=ResourceType.API,
            connection=ConnectionConfig(),
        )
        adapter = APIAdapter(resource)
        with pytest.raises(ConnectionError):
            adapter.connect()


class TestAPIAdapterContainers:
    def test_list_containers(self, simple_spec):
        adapter = _make_adapter(simple_spec)
        containers = adapter.list_containers()
        names = [c.name for c in containers]
        assert "GET /users" in names
        assert "POST /users" in names
        assert "GET /users/{id}" in names
        assert all(c.container_type == ContainerType.ENDPOINT for c in containers)

    def test_list_containers_with_pattern(self, simple_spec):
        adapter = _make_adapter(simple_spec)
        containers = adapter.list_containers(pattern="GET*")
        names = [c.name for c in containers]
        assert "GET /users" in names
        assert "POST /users" not in names

    def test_container_metadata(self, simple_spec):
        adapter = _make_adapter(simple_spec)
        containers = adapter.list_containers()
        get_users = next(c for c in containers if c.name == "GET /users")
        assert get_users.metadata["method"] == "GET"
        assert get_users.metadata["path"] == "/users"
        assert get_users.metadata["operation_id"] == "listUsers"


class TestAPIAdapterFields:
    def test_list_fields_get_endpoint(self, simple_spec):
        adapter = _make_adapter(simple_spec)
        fields = adapter.list_fields("GET /users")
        names = [f.name for f in fields]
        # Should have query param + response fields
        assert "email" in names  # query param
        assert "id" in names  # response
        assert "name" in names  # response
        assert "phone" in names  # response

    def test_list_fields_post_endpoint(self, simple_spec):
        adapter = _make_adapter(simple_spec)
        fields = adapter.list_fields("POST /users")
        names = [f.name for f in fields]
        assert "name" in names
        assert "email" in names
        assert "ssn" in names

    def test_field_nullable(self, simple_spec):
        adapter = _make_adapter(simple_spec)
        fields = adapter.list_fields("POST /users")
        name_field = next(
            f for f in fields if f.name == "name" and f.metadata.get("location") == "request"
        )
        ssn_field = next(f for f in fields if f.name == "ssn")
        assert name_field.nullable is False  # required
        assert ssn_field.nullable is True  # not required

    def test_list_fields_path_params(self, simple_spec):
        adapter = _make_adapter(simple_spec)
        fields = adapter.list_fields("GET /users/{id}")
        names = [f.name for f in fields]
        assert "id" in names
        id_field = next(f for f in fields if f.name == "id")
        assert id_field.metadata["location"] == "path"

    def test_list_fields_nonexistent(self, simple_spec):
        adapter = _make_adapter(simple_spec)
        fields = adapter.list_fields("DELETE /nonexistent")
        assert fields == []


class TestAPIAdapterRefResolution:
    def test_ref_resolved_in_fields(self, ref_spec):
        adapter = _make_adapter(ref_spec)
        fields = adapter.list_fields("GET /users")
        names = [f.name for f in fields]
        assert "name" in names
        assert "email" in names

    def test_shared_ref_relationships(self, ref_spec):
        adapter = _make_adapter(ref_spec)
        rels = adapter.get_relationships()
        # GET /users and POST /users share User schema
        assert len(rels) >= 1
        shared = [r for r in rels if "User" in r.metadata.get("shared_schema", "")]
        assert len(shared) >= 1


class TestAPIAdapterSamples:
    def test_sample_from_example(self, simple_spec):
        adapter = _make_adapter(simple_spec)
        values = adapter.sample_values("GET /users", "email")
        assert any("example.com" in v for v in values)

    def test_sample_no_examples(self, simple_spec):
        adapter = _make_adapter(simple_spec)
        values = adapter.sample_values("GET /users", "nonexistent_field")
        assert values == []
