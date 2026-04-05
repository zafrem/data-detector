"""Vector Database Adapter: scan vector stores for PII in stored documents.

Scans document chunks and metadata stored in vector databases to detect
PII that may have been embedded during RAG ingestion pipelines.

Supported backends:
- ChromaDB (local persistent or client mode)
- Generic dict-based (for custom integrations)

Connection parameters:
    uri: Path to ChromaDB persistent directory, or HTTP URL for client mode
    params:
        backend: "chromadb" (default) or "generic"
        collection_pattern: Optional glob pattern to filter collections
        include_metadata: bool (default: True) - scan metadata fields too
        text_field: str (default: "documents") - field name for document text
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

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

_chromadb: Optional[Any] = None


def _get_chromadb() -> Any:
    """Lazy-load chromadb with clear error message."""
    global _chromadb
    if _chromadb is None:
        try:
            import chromadb

            _chromadb = chromadb
        except ImportError:
            raise ImportError(
                "chromadb is required for vector database scanning. "
                "Install with: pip install data-detector[vector-db]"
            )
    return _chromadb


class VectorDBAdapter(ResourceAdapter):
    """Scan vector database collections for PII in stored documents and metadata.

    Example:
        >>> from datadetector.resource_models import ConnectionConfig, DataResource, ResourceType
        >>> resource = DataResource(
        ...     name="my-chromadb",
        ...     resource_type=ResourceType.VECTOR_DB,
        ...     connection=ConnectionConfig(
        ...         uri="/path/to/chroma_data",
        ...         params={"backend": "chromadb"},
        ...     ),
        ... )
        >>> with VectorDBAdapter(resource) as adapter:
        ...     containers = adapter.list_containers()
    """

    def __init__(self, resource: DataResource) -> None:
        super().__init__(resource)
        self._client: Any = None
        self._collections: Dict[str, Any] = {}
        self._collection_schemas: Dict[str, List[str]] = {}

    def connect(self) -> None:
        """Connect to vector database."""
        if self._connected:
            return

        backend = self.resource.connection.params.get("backend", "chromadb")

        if backend == "chromadb":
            self._connect_chromadb()
        elif backend == "generic":
            self._connect_generic()
        else:
            raise ValueError(
                f"Unsupported vector DB backend: '{backend}'. " f"Supported: chromadb, generic"
            )

        self._connected = True
        logger.info(f"Connected to vector DB '{self.resource.name}' ({backend})")

    def _connect_chromadb(self) -> None:
        """Connect to ChromaDB instance."""
        chromadb = _get_chromadb()
        uri = self.resource.connection.uri or ""

        if uri.startswith("https://") or uri.startswith("http://"):
            if uri.startswith("http://"):
                logger.warning(
                    "Insecure HTTP connection to ChromaDB at %s. "
                    "Use https:// in production.",
                    uri,
                )
            # Client mode
            host = uri.rstrip("/")
            port = self.resource.connection.params.get("port", 8000)
            self._client = chromadb.HttpClient(host=host, port=port)
        elif uri:
            # Persistent local mode
            path = Path(uri)
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(path))
        else:
            # Ephemeral (in-memory) mode
            self._client = chromadb.Client()

    def _connect_generic(self) -> None:
        """Connect using generic dict-based data provided in params."""
        data = self.resource.connection.params.get("data", {})
        if not isinstance(data, dict):
            raise ValueError("Generic backend requires 'data' dict in params")
        self._client = data

    def close(self) -> None:
        """Release vector DB connection."""
        self._client = None
        self._collections.clear()
        self._collection_schemas.clear()
        self._connected = False

    def list_containers(self, pattern: Optional[str] = None) -> List[ContainerInfo]:
        """List vector DB collections as containers."""
        self._ensure_connected()

        backend = self.resource.connection.params.get("backend", "chromadb")
        collection_pattern = pattern or self.resource.connection.params.get("collection_pattern")

        containers: List[ContainerInfo] = []

        if backend == "chromadb":
            collections = self._client.list_collections()
            for col in collections:
                name = col if isinstance(col, str) else col.name
                if collection_pattern and not self._match_pattern(name, collection_pattern):
                    continue

                # Get the collection object for later use
                col_obj = self._client.get_collection(name)
                self._collections[name] = col_obj

                count = col_obj.count()
                containers.append(
                    ContainerInfo(
                        name=name,
                        container_type=ContainerType.COLLECTION,
                        metadata={
                            "backend": "chromadb",
                            "document_count": count,
                        },
                    )
                )

        elif backend == "generic":
            for name, col_data in self._client.items():
                if collection_pattern and not self._match_pattern(name, collection_pattern):
                    continue
                docs = col_data.get("documents", [])
                containers.append(
                    ContainerInfo(
                        name=name,
                        container_type=ContainerType.COLLECTION,
                        metadata={
                            "backend": "generic",
                            "document_count": len(docs),
                        },
                    )
                )

        return containers

    def list_fields(self, container_name: str) -> List[FieldInfo]:
        """List scannable fields in a collection.

        Fields include:
        - 'document' (the stored text chunk)
        - Any metadata fields found in stored documents
        """
        self._ensure_connected()

        backend = self.resource.connection.params.get("backend", "chromadb")
        include_metadata = self.resource.connection.params.get("include_metadata", True)

        fields: List[FieldInfo] = []

        # Always include the document text field
        text_field = self.resource.connection.params.get("text_field", "document")
        fields.append(
            FieldInfo(
                name=text_field,
                container_name=container_name,
                data_type="text",
                nullable=False,
                description="Stored document text chunk",
            )
        )

        if not include_metadata:
            self._collection_schemas[container_name] = [text_field]
            return fields

        # Discover metadata fields by sampling
        metadata_keys = self._discover_metadata_fields(container_name, backend)

        for key in sorted(metadata_keys):
            fields.append(
                FieldInfo(
                    name=f"metadata.{key}",
                    container_name=container_name,
                    data_type="string",
                    nullable=True,
                    description=f"Document metadata field: {key}",
                    metadata={"source": "metadata"},
                )
            )

        self._collection_schemas[container_name] = [text_field] + [
            f"metadata.{k}" for k in sorted(metadata_keys)
        ]

        return fields

    def sample_values(self, container_name: str, field_name: str, limit: int = 100) -> List[str]:
        """Sample values from a collection field."""
        self._ensure_connected()

        backend = self.resource.connection.params.get("backend", "chromadb")
        text_field = self.resource.connection.params.get("text_field", "document")

        if backend == "chromadb":
            return self._sample_chromadb(container_name, field_name, text_field, limit)
        elif backend == "generic":
            return self._sample_generic(container_name, field_name, text_field, limit)
        return []

    def get_relationships(self) -> List[FieldRelationship]:
        """Detect relationships between collections with shared metadata fields."""
        self._ensure_connected()

        relationships: List[FieldRelationship] = []
        collection_names = list(self._collection_schemas.keys())

        for i, col_a in enumerate(collection_names):
            for col_b in collection_names[i + 1 :]:
                fields_a = set(self._collection_schemas.get(col_a, []))
                fields_b = set(self._collection_schemas.get(col_b, []))
                shared = fields_a & fields_b

                for field_name in shared:
                    if field_name.startswith("metadata."):
                        relationships.append(
                            FieldRelationship(
                                source_resource=self.resource.name,
                                source_field=f"{col_a}.{field_name}",
                                target_resource=self.resource.name,
                                target_field=f"{col_b}.{field_name}",
                                relationship_type=RelationshipType.EMBEDDING_SOURCE,
                                metadata={"shared_metadata_field": field_name},
                            )
                        )

        return relationships

    # ── Private helpers ──────────────────────────────────

    def _discover_metadata_fields(self, container_name: str, backend: str) -> set:
        """Discover metadata field names by sampling documents."""
        metadata_keys: set = set()
        sample_size = min(20, self.resource.connection.params.get("metadata_sample_size", 20))

        if backend == "chromadb":
            col = self._collections.get(container_name)
            if col is None:
                return metadata_keys
            try:
                result = col.peek(limit=sample_size)
                metadatas = result.get("metadatas", [])
                if metadatas:
                    for meta in metadatas:
                        if meta:
                            metadata_keys.update(meta.keys())
            except Exception as e:
                logger.warning(f"Could not discover metadata for '{container_name}': {e}")

        elif backend == "generic":
            col_data = self._client.get(container_name, {})
            metadatas = col_data.get("metadatas", [])
            for meta in metadatas[:sample_size]:
                if meta:
                    metadata_keys.update(meta.keys())

        return metadata_keys

    def _sample_chromadb(
        self,
        container_name: str,
        field_name: str,
        text_field: str,
        limit: int,
    ) -> List[str]:
        """Sample values from a ChromaDB collection."""
        col = self._collections.get(container_name)
        if col is None:
            # Try to get it
            try:
                col = self._client.get_collection(container_name)
                self._collections[container_name] = col
            except Exception:
                return []

        count = col.count()
        if count == 0:
            return []

        fetch_limit = min(limit, count)

        try:
            result = col.peek(limit=fetch_limit)
        except Exception as e:
            logger.warning(f"Could not sample '{container_name}': {e}")
            return []

        if field_name == text_field:
            docs = result.get("documents", [])
            return [str(d) for d in docs if d]

        # Metadata field: metadata.field_name
        if field_name.startswith("metadata."):
            meta_key = field_name[len("metadata.") :]
            metadatas = result.get("metadatas", [])
            values = []
            for meta in metadatas:
                if meta and meta_key in meta:
                    val = meta[meta_key]
                    if val is not None:
                        values.append(str(val))
            return values[:limit]

        return []

    def _sample_generic(
        self,
        container_name: str,
        field_name: str,
        text_field: str,
        limit: int,
    ) -> List[str]:
        """Sample values from generic dict-based collection."""
        col_data = self._client.get(container_name, {})

        if field_name == text_field:
            docs = col_data.get("documents", [])
            return [str(d) for d in docs[:limit] if d]

        if field_name.startswith("metadata."):
            meta_key = field_name[len("metadata.") :]
            metadatas = col_data.get("metadatas", [])
            values = []
            for meta in metadatas[:limit]:
                if meta and meta_key in meta:
                    val = meta[meta_key]
                    if val is not None:
                        values.append(str(val))
            return values

        return []

    @staticmethod
    def _match_pattern(name: str, pattern: str) -> bool:
        """Simple glob-like pattern matching for collection names."""
        import fnmatch

        return fnmatch.fnmatch(name, pattern)
