"""Resource adapters for data scanning.

Adapters are imported directly to avoid requiring optional dependencies
at package level:

    from datadetector.adapters.database import DatabaseAdapter
    from datadetector.adapters.kafka import KafkaAdapter
    from datadetector.adapters.api import APIAdapter
    from datadetector.adapters.file_storage import FileStorageAdapter
    from datadetector.adapters.vector_db import VectorDBAdapter
    from datadetector.adapters.training_data import TrainingDataAdapter
"""

import importlib
import logging
from typing import Dict, Type

from datadetector.resource_adapter import ResourceAdapter
from datadetector.resource_models import ResourceType

logger = logging.getLogger(__name__)

# Maps resource type to (module_path, class_name) for lazy loading
_ADAPTER_REGISTRY: Dict[str, tuple] = {
    ResourceType.DATABASE.value: (
        "datadetector.adapters.database",
        "DatabaseAdapter",
    ),
    ResourceType.KAFKA.value: (
        "datadetector.adapters.kafka",
        "KafkaAdapter",
    ),
    ResourceType.API.value: (
        "datadetector.adapters.api",
        "APIAdapter",
    ),
    ResourceType.FILE_STORAGE.value: (
        "datadetector.adapters.file_storage",
        "FileStorageAdapter",
    ),
    ResourceType.VECTOR_DB.value: (
        "datadetector.adapters.vector_db",
        "VectorDBAdapter",
    ),
    ResourceType.TRAINING_DATA.value: (
        "datadetector.adapters.training_data",
        "TrainingDataAdapter",
    ),
}


def get_adapter_class(resource_type: str) -> Type[ResourceAdapter]:
    """Get adapter class by resource type string, with lazy import.

    Args:
        resource_type: Resource type value (e.g., "database", "kafka").

    Returns:
        The adapter class (not an instance).

    Raises:
        ValueError: If resource type is not supported.
        ImportError: If required dependency is not installed.
    """
    if resource_type not in _ADAPTER_REGISTRY:
        supported = ", ".join(sorted(_ADAPTER_REGISTRY.keys()))
        raise ValueError(
            f"Unsupported resource type: '{resource_type}'. " f"Supported types: {supported}"
        )

    module_path, class_name = _ADAPTER_REGISTRY[resource_type]

    try:
        module = importlib.import_module(module_path)
        return getattr(module, class_name)  # type: ignore[no-any-return]
    except ImportError as e:
        raise ImportError(
            f"Cannot load adapter for '{resource_type}': {e}. "
            f"Install the required dependencies with: "
            f"pip install data-detector[{resource_type}]"
        ) from e
