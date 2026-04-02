"""Training Data Adapter: scan AI training datasets for PII.

Scans instruction-tuning datasets, fine-tuning data, prompt/completion logs,
and HuggingFace datasets to detect PII that could leak into trained models.

Supported formats:
- JSONL instruction-tuning files (instruction/input/output, prompt/completion)
- HuggingFace datasets (via ``datasets`` library)
- Chat format JSONL (messages array with role/content)

Connection parameters:
    uri: Path to directory or file, or HuggingFace dataset identifier
    params:
        backend: "jsonl" (default) or "huggingface"
        glob: File glob pattern (default: "*.jsonl")
        split: HuggingFace dataset split (default: "train")
        max_file_size_mb: Maximum file size to scan (default: 500)
        streaming: bool (default: False) - use HuggingFace streaming mode
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

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

_datasets_lib: Optional[Any] = None

# Common field names in training data formats
_INSTRUCTION_FIELDS = {
    "instruction",
    "input",
    "output",
    "prompt",
    "completion",
    "response",
    "question",
    "answer",
    "context",
    "text",
    "content",
    "system",
    "human",
    "assistant",
    "user",
}

# Chat message format fields
_CHAT_FIELDS = {"role", "content", "name", "function_call", "tool_calls"}


def _get_datasets() -> Any:
    """Lazy-load HuggingFace datasets with clear error message."""
    global _datasets_lib
    if _datasets_lib is None:
        try:
            import datasets

            _datasets_lib = datasets
        except ImportError:
            raise ImportError(
                "datasets is required for HuggingFace dataset scanning. "
                "Install with: pip install data-detector[training-data]"
            )
    return _datasets_lib


class TrainingDataAdapter(ResourceAdapter):
    """Scan AI training datasets for PII in text fields.

    Example:
        >>> from datadetector.resource_models import ConnectionConfig, DataResource, ResourceType
        >>> resource = DataResource(
        ...     name="finetune-data",
        ...     resource_type=ResourceType.TRAINING_DATA,
        ...     connection=ConnectionConfig(
        ...         uri="/data/training/",
        ...         params={"backend": "jsonl"},
        ...     ),
        ... )
        >>> with TrainingDataAdapter(resource) as adapter:
        ...     containers = adapter.list_containers()
    """

    def __init__(self, resource: DataResource) -> None:
        super().__init__(resource)
        self._files: List[Path] = []
        self._hf_dataset: Any = None
        self._field_cache: Dict[str, List[str]] = {}
        self._row_counts: Dict[str, int] = {}

    def connect(self) -> None:
        """Connect to training data source."""
        if self._connected:
            return

        backend = self.resource.connection.params.get("backend", "jsonl")

        if backend == "jsonl":
            self._connect_jsonl()
        elif backend == "huggingface":
            self._connect_huggingface()
        else:
            raise ValueError(
                f"Unsupported training data backend: '{backend}'. " f"Supported: jsonl, huggingface"
            )

        self._connected = True
        logger.info(f"Connected to training data '{self.resource.name}' ({backend})")

    def _connect_jsonl(self) -> None:
        """Discover JSONL training data files."""
        uri = self.resource.connection.uri or ""
        base_path = Path(uri)

        if not base_path.exists():
            raise ConnectionError(f"Path does not exist: {uri}")

        glob_pattern = self.resource.connection.params.get("glob", "*.jsonl")
        max_size_mb = self.resource.connection.params.get("max_file_size_mb", 500)
        max_size_bytes = max_size_mb * 1024 * 1024

        if base_path.is_file():
            if base_path.stat().st_size <= max_size_bytes:
                self._files = [base_path]
            else:
                logger.warning(
                    f"File too large: {base_path} "
                    f"({base_path.stat().st_size / 1024 / 1024:.1f}MB > {max_size_mb}MB)"
                )
        else:
            recursive = self.resource.connection.params.get("recursive", True)
            pattern = f"**/{glob_pattern}" if recursive else glob_pattern
            self._files = sorted(
                f
                for f in base_path.glob(pattern)
                if f.is_file() and f.stat().st_size <= max_size_bytes
            )

        if not self._files:
            logger.warning(f"No training data files found at '{uri}'")

    def _connect_huggingface(self) -> None:
        """Connect to a HuggingFace dataset."""
        datasets = _get_datasets()
        dataset_id = self.resource.connection.uri or ""
        split = self.resource.connection.params.get("split", "train")
        streaming = self.resource.connection.params.get("streaming", False)

        if not dataset_id:
            raise ValueError("HuggingFace backend requires dataset identifier in uri")

        try:
            self._hf_dataset = datasets.load_dataset(
                dataset_id,
                split=split,
                streaming=streaming,
            )
        except Exception as e:
            raise ConnectionError(f"Failed to load HuggingFace dataset '{dataset_id}': {e}") from e

    def close(self) -> None:
        """Release resources."""
        self._files.clear()
        self._hf_dataset = None
        self._field_cache.clear()
        self._row_counts.clear()
        self._connected = False

    def list_containers(self, pattern: Optional[str] = None) -> List[ContainerInfo]:
        """List training data files/datasets as containers."""
        self._ensure_connected()

        backend = self.resource.connection.params.get("backend", "jsonl")
        containers: List[ContainerInfo] = []

        if backend == "jsonl":
            for f in self._files:
                name = f.name
                if pattern and not self._match_pattern(name, pattern):
                    continue

                # Count lines for row estimate
                row_count = self._count_lines(f)
                self._row_counts[name] = row_count

                containers.append(
                    ContainerInfo(
                        name=name,
                        container_type=ContainerType.DATASET,
                        metadata={
                            "backend": "jsonl",
                            "file_path": str(f),
                            "size_bytes": f.stat().st_size,
                            "row_count": row_count,
                            "format": self._detect_format(f),
                        },
                    )
                )

        elif backend == "huggingface":
            dataset_id = self.resource.connection.uri or "unknown"
            split = self.resource.connection.params.get("split", "train")
            name = f"{dataset_id.replace('/', '_')}_{split}"

            if pattern and not self._match_pattern(name, pattern):
                return containers

            num_rows = 0
            if hasattr(self._hf_dataset, "num_rows"):
                num_rows = self._hf_dataset.num_rows
            self._row_counts[name] = num_rows

            containers.append(
                ContainerInfo(
                    name=name,
                    container_type=ContainerType.DATASET,
                    metadata={
                        "backend": "huggingface",
                        "dataset_id": dataset_id,
                        "split": split,
                        "num_rows": num_rows,
                    },
                )
            )

        return containers

    def list_fields(self, container_name: str) -> List[FieldInfo]:
        """List fields in a training data container.

        Discovers fields by reading the first few rows and extracting keys.
        For chat-format data, flattens messages into role-based fields.
        """
        self._ensure_connected()

        backend = self.resource.connection.params.get("backend", "jsonl")

        if backend == "jsonl":
            fields = self._list_jsonl_fields(container_name)
        elif backend == "huggingface":
            fields = self._list_hf_fields(container_name)
        else:
            fields = []

        self._field_cache[container_name] = [f.name for f in fields]
        return fields

    def sample_values(self, container_name: str, field_name: str, limit: int = 100) -> List[str]:
        """Sample values from a training data field."""
        self._ensure_connected()

        backend = self.resource.connection.params.get("backend", "jsonl")

        if backend == "jsonl":
            return self._sample_jsonl(container_name, field_name, limit)
        elif backend == "huggingface":
            return self._sample_hf(container_name, field_name, limit)
        return []

    def get_relationships(self) -> List[FieldRelationship]:
        """Detect relationships between training data containers.

        Identifies shared field schemas across files (e.g., multiple JSONL
        files with the same instruction/output format).
        """
        self._ensure_connected()

        relationships: List[FieldRelationship] = []
        container_names = list(self._field_cache.keys())

        for i, name_a in enumerate(container_names):
            for name_b in container_names[i + 1 :]:
                fields_a = set(self._field_cache.get(name_a, []))
                fields_b = set(self._field_cache.get(name_b, []))
                shared = fields_a & fields_b - {"id"}

                if len(shared) >= 2:
                    for field_name in shared:
                        relationships.append(
                            FieldRelationship(
                                source_resource=self.resource.name,
                                source_field=f"{name_a}.{field_name}",
                                target_resource=self.resource.name,
                                target_field=f"{name_b}.{field_name}",
                                relationship_type=RelationshipType.TRAINING_SOURCE,
                                metadata={"shared_schema": True},
                            )
                        )

        return relationships

    # ── JSONL helpers ────────────────────────────────────

    def _list_jsonl_fields(self, container_name: str) -> List[FieldInfo]:
        """Discover fields from a JSONL file by reading first N rows."""
        file_path = self._resolve_file(container_name)
        if file_path is None:
            return []

        keys: Set[str] = set()
        has_messages = False
        message_roles: Set[str] = set()
        sample_rows = 20

        try:
            with open(file_path, encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if i >= sample_rows:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                        if isinstance(row, dict):
                            keys.update(row.keys())
                            # Detect chat format
                            if "messages" in row and isinstance(row["messages"], list):
                                has_messages = True
                                for msg in row["messages"]:
                                    if isinstance(msg, dict) and "role" in msg:
                                        message_roles.add(msg["role"])
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning(f"Could not read fields from '{container_name}': {e}")
            return []

        fields: List[FieldInfo] = []

        for key in sorted(keys):
            if key == "messages" and has_messages:
                # Expand chat messages into role-based content fields
                for role in sorted(message_roles):
                    fields.append(
                        FieldInfo(
                            name=f"messages.{role}.content",
                            container_name=container_name,
                            data_type="text",
                            nullable=True,
                            description=f"Chat message content for role '{role}'",
                            metadata={"format": "chat", "role": role},
                        )
                    )
                continue

            # Determine if this is a text field likely to contain PII
            data_type = "text" if key in _INSTRUCTION_FIELDS else "string"

            fields.append(
                FieldInfo(
                    name=key,
                    container_name=container_name,
                    data_type=data_type,
                    nullable=True,
                    description=f"Training data field: {key}",
                )
            )

        return fields

    def _sample_jsonl(self, container_name: str, field_name: str, limit: int) -> List[str]:
        """Sample values from a JSONL file field."""
        file_path = self._resolve_file(container_name)
        if file_path is None:
            return []

        values: List[str] = []

        try:
            with open(file_path, encoding="utf-8") as f:
                for line in f:
                    if len(values) >= limit:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                        if not isinstance(row, dict):
                            continue

                        val = self._extract_field_value(row, field_name)
                        if val is not None:
                            text = str(val).strip()
                            if text:
                                values.append(text)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning(f"Could not sample '{field_name}' from '{container_name}': {e}")

        return values

    def _extract_field_value(self, row: dict, field_name: str) -> Optional[str]:
        """Extract a value from a row, supporting nested chat message fields."""
        # Chat format: messages.role.content
        if field_name.startswith("messages.") and "messages" in row:
            parts = field_name.split(".", 2)
            if len(parts) == 3:
                _, role, attr = parts
                messages = row.get("messages", [])
                if isinstance(messages, list):
                    for msg in messages:
                        if isinstance(msg, dict) and msg.get("role") == role and attr in msg:
                            return str(msg[attr])
            return None

        # Direct field access
        if field_name in row:
            val = row[field_name]
            if val is not None:
                return str(val)

        return None

    def _resolve_file(self, container_name: str) -> Optional[Path]:
        """Find the file matching a container name."""
        for f in self._files:
            if f.name == container_name:
                return f
        return None

    def _count_lines(self, file_path: Path) -> int:
        """Count non-empty lines in a file (fast)."""
        count = 0
        try:
            with open(file_path, "rb") as f:
                for line in f:
                    if line.strip():
                        count += 1
        except Exception:
            pass
        return count

    def _detect_format(self, file_path: Path) -> str:
        """Detect the training data format by reading the first line."""
        try:
            with open(file_path, encoding="utf-8") as f:
                line = f.readline().strip()
                if not line:
                    return "unknown"
                row = json.loads(line)
                if isinstance(row, dict):
                    keys = set(row.keys())
                    if "messages" in keys:
                        return "chat"
                    if {"instruction", "output"} & keys:
                        return "instruction"
                    if {"prompt", "completion"} & keys:
                        return "completion"
                    if "text" in keys:
                        return "text"
                    return "custom"
        except Exception:
            return "unknown"

    # ── HuggingFace helpers ──────────────────────────────

    def _list_hf_fields(self, container_name: str) -> List[FieldInfo]:
        """List fields from a HuggingFace dataset."""
        if self._hf_dataset is None:
            return []

        fields: List[FieldInfo] = []

        try:
            if hasattr(self._hf_dataset, "column_names"):
                columns = self._hf_dataset.column_names
            elif hasattr(self._hf_dataset, "features"):
                columns = list(self._hf_dataset.features.keys())
            else:
                # Streaming mode: peek at first item
                first = next(iter(self._hf_dataset))
                columns = list(first.keys()) if isinstance(first, dict) else []
        except Exception as e:
            logger.warning(f"Could not list HF fields: {e}")
            return []

        for col in columns:
            data_type = "text" if col.lower() in _INSTRUCTION_FIELDS else "string"
            fields.append(
                FieldInfo(
                    name=col,
                    container_name=container_name,
                    data_type=data_type,
                    nullable=True,
                    description=f"HuggingFace dataset column: {col}",
                )
            )

        return fields

    def _sample_hf(self, container_name: str, field_name: str, limit: int) -> List[str]:
        """Sample values from a HuggingFace dataset column."""
        if self._hf_dataset is None:
            return []

        values: List[str] = []

        try:
            if hasattr(self._hf_dataset, "select"):
                # Non-streaming: use select for efficiency
                num_rows = min(limit, len(self._hf_dataset))
                subset = self._hf_dataset.select(range(num_rows))
                for row in subset:
                    if field_name in row and row[field_name] is not None:
                        text = str(row[field_name]).strip()
                        if text:
                            values.append(text)
            else:
                # Streaming mode: iterate
                for i, row in enumerate(self._hf_dataset):
                    if i >= limit:
                        break
                    if field_name in row and row[field_name] is not None:
                        text = str(row[field_name]).strip()
                        if text:
                            values.append(text)
        except Exception as e:
            logger.warning(f"Could not sample HF field '{field_name}': {e}")

        return values

    @staticmethod
    def _match_pattern(name: str, pattern: str) -> bool:
        """Simple glob-like pattern matching."""
        import fnmatch

        return fnmatch.fnmatch(name, pattern)
