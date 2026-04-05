"""API adapter for scanning REST APIs via OpenAPI/Swagger specifications.

Parses OpenAPI 3.x and Swagger 2.0 specs to extract endpoint fields
for PII detection. No additional dependencies required beyond pyyaml
(already a core dependency).

Example:
    >>> resource = DataResource(
    ...     name="my-api",
    ...     resource_type=ResourceType.API,
    ...     connection=ConnectionConfig(uri="./openapi.yaml"),
    ... )
    >>> with APIAdapter(resource) as adapter:
    ...     endpoints = adapter.list_containers()
"""

import fnmatch
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from datadetector.resource_adapter import ResourceAdapter
from datadetector.resource_models import (
    ContainerInfo,
    ContainerType,
    DataResource,
    FieldInfo,
    FieldRelationship,
    RelationshipType,
)

logger = logging.getLogger(__name__)

# HTTP methods recognized in OpenAPI specs
_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


class APIAdapter(ResourceAdapter):
    """OpenAPI/Swagger specification adapter.

    ConnectionConfig usage:
        uri: Path to OpenAPI spec file (YAML/JSON) or URL
        params:
            spec: Inline spec dict (alternative to uri)
            base_url: API base URL for reference
    """

    def __init__(self, resource: DataResource) -> None:
        super().__init__(resource)
        self._spec: Optional[Dict[str, Any]] = None
        self._resolved_spec: Optional[Dict[str, Any]] = None

    def connect(self) -> None:
        """Load and parse OpenAPI specification."""
        params = self.resource.connection.params
        spec = params.get("spec")

        if spec and isinstance(spec, dict):
            self._spec = spec
        elif self.resource.connection.uri:
            self._spec = self._load_spec_from_path(self.resource.connection.uri)
        else:
            raise ConnectionError(
                "API adapter requires either connection.uri (spec file path) "
                "or connection.params['spec'] (inline dict)."
            )

        # Resolve $ref pointers
        assert self._spec is not None
        self._resolved_spec = self._resolve_refs(self._spec)
        self._connected = True
        logger.info(f"Loaded API spec: {self.resource.name}")

    def close(self) -> None:
        """Release spec data."""
        self._spec = None
        self._resolved_spec = None
        self._connected = False

    def list_containers(
        self,
        pattern: Optional[str] = None,
    ) -> List[ContainerInfo]:
        """List API endpoints as containers.

        Each path + method combination is one container.
        Container name format: "METHOD /path" (e.g., "GET /users/{id}").

        Args:
            pattern: Optional glob pattern for endpoint names.

        Returns:
            List of ContainerInfo for each endpoint.
        """
        self._ensure_connected()
        assert self._resolved_spec is not None

        containers: List[ContainerInfo] = []
        paths = self._resolved_spec.get("paths", {})

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            for method in _HTTP_METHODS:
                if method not in path_item:
                    continue

                operation = path_item[method]
                name = f"{method.upper()} {path}"

                if pattern and not fnmatch.fnmatch(name, pattern):
                    continue

                containers.append(
                    ContainerInfo(
                        name=name,
                        container_type=ContainerType.ENDPOINT,
                        metadata={
                            "method": method.upper(),
                            "path": path,
                            "summary": operation.get("summary", ""),
                            "operation_id": operation.get("operationId", ""),
                            "tags": operation.get("tags", []),
                        },
                    )
                )

        return containers

    def list_fields(self, container_name: str) -> List[FieldInfo]:
        """List parameters and body fields for an endpoint.

        Extracts fields from:
        - Path parameters
        - Query parameters
        - Header parameters
        - Request body schema (flattened)
        - Response body schema (flattened, 200/201 response)

        Args:
            container_name: Endpoint name in "METHOD /path" format.

        Returns:
            List of FieldInfo objects.
        """
        self._ensure_connected()
        assert self._resolved_spec is not None

        # Parse container name
        parts = container_name.split(" ", 1)
        if len(parts) != 2:
            return []
        method, path = parts[0].lower(), parts[1]

        paths = self._resolved_spec.get("paths", {})
        path_item = paths.get(path, {})
        operation = path_item.get(method, {})

        if not operation:
            return []

        fields: List[FieldInfo] = []

        # Parameters (path, query, header)
        parameters = operation.get("parameters", [])
        # Include path-level parameters
        parameters = path_item.get("parameters", []) + parameters
        for param in parameters:
            if not isinstance(param, dict):
                continue
            location = param.get("in", "query")
            schema = param.get("schema", {})
            fields.append(
                FieldInfo(
                    name=param.get("name", ""),
                    container_name=container_name,
                    data_type=schema.get("type", "string"),
                    nullable=not param.get("required", False),
                    description=param.get("description", ""),
                    metadata={"location": location},
                )
            )

        # Request body
        request_body = operation.get("requestBody", {})
        if request_body:
            body_fields = self._extract_body_fields(request_body, container_name, "request")
            fields.extend(body_fields)

        # Response body (200 or 201)
        responses = operation.get("responses", {})
        for status_code in ("200", "201", 200, 201):
            response = responses.get(status_code)
            if response:
                resp_fields = self._extract_body_fields(response, container_name, "response")
                fields.extend(resp_fields)
                break

        return fields

    def sample_values(
        self,
        container_name: str,
        field_name: str,
        limit: int = 100,
    ) -> List[str]:
        """Extract example values from the spec.

        Checks schema 'example', 'examples', and 'default' fields.

        Args:
            container_name: Endpoint name.
            field_name: Field name.
            limit: Maximum values.

        Returns:
            List of example values as strings.
        """
        self._ensure_connected()
        assert self._resolved_spec is not None

        values: List[str] = []

        # Search for examples in the spec
        parts = container_name.split(" ", 1)
        if len(parts) != 2:
            return values
        method, path = parts[0].lower(), parts[1]

        paths = self._resolved_spec.get("paths", {})
        path_item = paths.get(path, {})
        operation = path_item.get(method, {})

        # Check parameters
        for param in operation.get("parameters", []):
            if not isinstance(param, dict):
                continue
            if param.get("name") == field_name:
                example = param.get("example") or param.get("schema", {}).get("example")
                if example is not None:
                    values.append(str(example))
                examples = param.get("examples", {})
                for ex_val in examples.values():
                    if isinstance(ex_val, dict) and "value" in ex_val:
                        values.append(str(ex_val["value"]))

        # Check request body schema
        self._collect_schema_examples(operation.get("requestBody", {}), field_name, values)

        # Check response schemas
        for status_code in ("200", "201", 200, 201):
            response = operation.get("responses", {}).get(status_code)
            if response:
                self._collect_schema_examples(response, field_name, values)

        return values[:limit]

    def get_relationships(self) -> List[FieldRelationship]:
        """Detect shared schema references across endpoints.

        When multiple endpoints reference the same schema component,
        it indicates shared data structures.

        Returns:
            List of FieldRelationship objects.
        """
        self._ensure_connected()
        assert self._spec is not None

        # Track which endpoints use which $ref schemas
        ref_usage: Dict[str, List[str]] = {}  # $ref -> [endpoint_names]
        paths = self._spec.get("paths", {})

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            for method in _HTTP_METHODS:
                if method not in path_item:
                    continue
                endpoint_name = f"{method.upper()} {path}"
                refs = self._collect_refs(path_item[method])
                for ref in refs:
                    ref_usage.setdefault(ref, []).append(endpoint_name)

        relationships: List[FieldRelationship] = []
        for ref, endpoints in ref_usage.items():
            if len(endpoints) < 2:
                continue
            schema_name = ref.split("/")[-1]
            for i in range(len(endpoints)):
                for j in range(i + 1, len(endpoints)):
                    relationships.append(
                        FieldRelationship(
                            source_resource=self.resource.name,
                            source_field=endpoints[i],
                            target_resource=self.resource.name,
                            target_field=endpoints[j],
                            relationship_type=RelationshipType.API_REFERENCE,
                            metadata={"shared_schema": schema_name, "ref": ref},
                        )
                    )

        return relationships

    # ── Internal helpers ──

    def _load_spec_from_path(self, path_str: str) -> Dict[str, Any]:
        """Load spec from file path."""
        path = Path(path_str)
        if not path.exists():
            raise ConnectionError(f"Spec file not found: {path}")

        with open(path, encoding="utf-8") as f:
            content = f.read()

        if path.suffix in (".yaml", ".yml"):
            return yaml.safe_load(content)
        elif path.suffix == ".json":
            return json.loads(content)
        else:
            # Try YAML first, then JSON
            try:
                return yaml.safe_load(content)
            except yaml.YAMLError:
                return json.loads(content)

    def _resolve_refs(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve $ref pointers in the spec (single-level)."""
        import copy

        resolved = copy.deepcopy(spec)
        self._resolve_refs_recursive(resolved, spec)
        return resolved

    def _resolve_refs_recursive(
        self,
        obj: Any,
        root: Dict[str, Any],
        depth: int = 0,
    ) -> Any:
        """Recursively resolve $ref pointers."""
        if depth > 20:
            return obj

        if isinstance(obj, dict):
            if "$ref" in obj:
                ref_path = obj["$ref"]
                resolved = self._follow_ref(ref_path, root)
                if resolved is not None:
                    obj.clear()
                    obj.update(resolved)
                    self._resolve_refs_recursive(obj, root, depth + 1)
            else:
                for value in obj.values():
                    self._resolve_refs_recursive(value, root, depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                self._resolve_refs_recursive(item, root, depth + 1)

        return obj

    @staticmethod
    def _follow_ref(ref: str, root: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Follow a $ref pointer like '#/components/schemas/User'."""
        if not ref.startswith("#/"):
            return None

        parts = ref[2:].split("/")
        current: Any = root
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current if isinstance(current, dict) else None

    def _extract_body_fields(
        self,
        body: Dict[str, Any],
        container_name: str,
        location: str,
        prefix: str = "",
    ) -> List[FieldInfo]:
        """Extract fields from request/response body schema."""
        fields: List[FieldInfo] = []

        # OpenAPI 3.x content
        content = body.get("content", {})
        for media_type, media_obj in content.items():
            schema = media_obj.get("schema", {})
            fields.extend(self._flatten_schema(schema, container_name, location, prefix))

        # Swagger 2.x schema directly on body
        if "schema" in body and "content" not in body:
            schema = body["schema"]
            fields.extend(self._flatten_schema(schema, container_name, location, prefix))

        return fields

    def _flatten_schema(
        self,
        schema: Dict[str, Any],
        container_name: str,
        location: str,
        prefix: str = "",
    ) -> List[FieldInfo]:
        """Flatten a JSON Schema into FieldInfo list."""
        fields: List[FieldInfo] = []

        if not isinstance(schema, dict):
            return fields

        schema_type = schema.get("type", "object")
        required = set(schema.get("required", []))

        # Object with properties
        if "properties" in schema:
            for prop_name, prop_schema in schema["properties"].items():
                full_name = f"{prefix}.{prop_name}" if prefix else prop_name
                prop_type = prop_schema.get("type", "string")

                if prop_type == "object" and "properties" in prop_schema:
                    fields.extend(
                        self._flatten_schema(prop_schema, container_name, location, full_name)
                    )
                elif prop_type == "array" and "items" in prop_schema:
                    items = prop_schema["items"]
                    if isinstance(items, dict) and items.get("type") == "object":
                        fields.extend(
                            self._flatten_schema(items, container_name, location, f"{full_name}[]")
                        )
                    else:
                        fields.append(
                            FieldInfo(
                                name=full_name,
                                container_name=container_name,
                                data_type=f"array<{items.get('type', 'string')}>",
                                nullable=prop_name not in required,
                                description=prop_schema.get("description", ""),
                                metadata={"location": location},
                            )
                        )
                else:
                    fields.append(
                        FieldInfo(
                            name=full_name,
                            container_name=container_name,
                            data_type=str(prop_type),
                            nullable=prop_name not in required,
                            description=prop_schema.get("description", ""),
                            metadata={"location": location},
                        )
                    )

        # Array at top level
        elif schema_type == "array" and "items" in schema:
            items = schema["items"]
            if isinstance(items, dict):
                fields.extend(self._flatten_schema(items, container_name, location, prefix))

        return fields

    def _collect_schema_examples(
        self,
        obj: Dict[str, Any],
        field_name: str,
        values: List[str],
    ) -> None:
        """Recursively collect example values for a field from schema."""
        if not isinstance(obj, dict):
            return

        content = obj.get("content", {})
        for media_obj in content.values():
            schema = media_obj.get("schema", {})
            self._find_field_examples(schema, field_name, values)
            # Check media-level examples
            example = media_obj.get("example")
            if isinstance(example, dict) and field_name in example:
                values.append(str(example[field_name]))

    def _find_field_examples(
        self,
        schema: Dict[str, Any],
        field_name: str,
        values: List[str],
    ) -> None:
        """Find example values for a specific field in a schema."""
        if not isinstance(schema, dict):
            return

        properties = schema.get("properties", {})
        # Check simple field name (last part for nested)
        simple_name = field_name.split(".")[-1] if "." in field_name else field_name

        if simple_name in properties:
            prop = properties[simple_name]
            if "example" in prop:
                values.append(str(prop["example"]))
            if "default" in prop:
                values.append(str(prop["default"]))
            if "enum" in prop:
                for e in prop["enum"][:3]:
                    values.append(str(e))

        # Check top-level example
        if "example" in schema and isinstance(schema["example"], dict):
            if simple_name in schema["example"]:
                values.append(str(schema["example"][simple_name]))

    @staticmethod
    def _collect_refs(obj: Any) -> List[str]:
        """Collect all $ref strings from a nested structure."""
        refs: List[str] = []
        if isinstance(obj, dict):
            if "$ref" in obj:
                refs.append(obj["$ref"])
            for value in obj.values():
                refs.extend(APIAdapter._collect_refs(value))
        elif isinstance(obj, list):
            for item in obj:
                refs.extend(APIAdapter._collect_refs(item))
        return refs
