"""Abstract base class for resource adapters.

All concrete adapters (Database, Kafka, API, FileStorage) implement this
interface. The DataExplorer works with any ResourceAdapter to scan for PII.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, List, Optional

from datadetector.resource_models import (
    ContainerInfo,
    DataResource,
    FieldInfo,
    FieldRelationship,
)

logger = logging.getLogger(__name__)


class ResourceAdapter(ABC):
    """Abstract interface that all resource adapters implement.

    Lifecycle: __init__(resource) -> connect() -> [operations] -> close()
    Supports context manager protocol for automatic cleanup.

    Example:
        >>> with DatabaseAdapter(resource) as adapter:
        ...     containers = adapter.list_containers()
        ...     for c in containers:
        ...         fields = adapter.list_fields(c.name)
    """

    def __init__(self, resource: DataResource) -> None:
        self.resource = resource
        self._connected = False

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the resource.

        Raises:
            ConnectionError: If connection fails.
            ImportError: If required adapter dependency is not installed.
        """
        ...

    @abstractmethod
    def close(self) -> None:
        """Release connection resources."""
        ...

    @abstractmethod
    def list_containers(
        self,
        pattern: Optional[str] = None,
    ) -> List[ContainerInfo]:
        """List all scannable containers in the resource.

        What a 'container' means depends on resource type:
        - Database: tables and views
        - Kafka: topics
        - API: endpoints (path + method)
        - File Storage: files matching pattern

        Args:
            pattern: Optional glob/regex filter for container names.

        Returns:
            List of ContainerInfo objects.
        """
        ...

    @abstractmethod
    def list_fields(self, container_name: str) -> List[FieldInfo]:
        """List all scannable fields within a container.

        What a 'field' means depends on resource type:
        - Database: columns of a table
        - Kafka: fields from Schema Registry schema
        - API: request/response parameters
        - File Storage: columns/keys in a file

        Args:
            container_name: Name of the container.

        Returns:
            List of FieldInfo objects.
        """
        ...

    @abstractmethod
    def sample_values(
        self,
        container_name: str,
        field_name: str,
        limit: int = 100,
    ) -> List[str]:
        """Get sample values for a specific field, coerced to strings.

        Null values are excluded from results.

        Args:
            container_name: Container name.
            field_name: Field name within the container.
            limit: Maximum number of sample values.

        Returns:
            List of string-coerced non-null sample values.
        """
        ...

    def get_relationships(self) -> List[FieldRelationship]:
        """Get known relationships between fields/containers.

        Default implementation returns empty list. Adapters that support
        relationship discovery (e.g., database foreign keys) override this.

        Returns:
            List of FieldRelationship objects.
        """
        return []

    def __enter__(self) -> "ResourceAdapter":
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> None:
        self.close()

    def _ensure_connected(self) -> None:
        """Raise RuntimeError if not connected."""
        if not self._connected:
            raise RuntimeError(
                f"Adapter for '{self.resource.name}' is not connected. "
                f"Call connect() first or use as context manager."
            )
