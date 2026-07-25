"""Data models for universal resource scanning.

Provides shared dataclasses and enums used by DataExplorer, DataInventoryGenerator,
and DataLineageTracer for PII detection across databases, Kafka, APIs, and files.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from datadetector.models import Category, Match, Severity

# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────


class ResourceType(str, Enum):
    """Supported data resource types."""

    DATABASE = "database"
    KAFKA = "kafka"
    API = "api"
    FILE_STORAGE = "file_storage"
    VECTOR_DB = "vector_db"
    TRAINING_DATA = "training_data"


class ScanStrategy(str, Enum):
    """How aggressively to scan a resource."""

    METADATA_ONLY = "metadata_only"  # Field names/schema only
    SAMPLE = "sample"  # Metadata + sample values (default)
    FULL = "full"  # Scan all data (expensive)


class PIIConfidence(str, Enum):
    """Confidence level of PII detection for a field."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CONFIRMED = "confirmed"


class ContainerType(str, Enum):
    """What a 'container' represents in each resource type."""

    TABLE = "table"
    VIEW = "view"
    TOPIC = "topic"
    ENDPOINT = "endpoint"
    FILE = "file"
    DIRECTORY = "directory"
    COLLECTION = "collection"
    DATASET = "dataset"


class RelationshipType(str, Enum):
    """Types of relationships between containers/fields."""

    FOREIGN_KEY = "foreign_key"
    TOPIC_LINK = "topic_link"
    API_REFERENCE = "api_reference"
    FILE_DERIVATION = "file_derivation"
    EMBEDDING_SOURCE = "embedding_source"
    TRAINING_SOURCE = "training_source"
    MANUAL = "manual"


class InventoryFormat(str, Enum):
    """Export formats for inventory."""

    JSON = "json"
    CSV = "csv"
    YAML = "yaml"
    HTML = "html"


class ScanStatus(str, Enum):
    """Status of a scan operation."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MaskingStrategy(str, Enum):
    """Recommended masking strategy for a PII field."""

    MASK = "mask"  # Replace with mask characters (e.g., ***-****-****)
    HASH = "hash"  # Replace with hash value
    TOKENIZE = "tokenize"  # Replace with reversible token
    FAKE = "fake"  # Replace with realistic fake data
    ENCRYPT = "encrypt"  # Encrypt in place
    SUPPRESS = "suppress"  # Remove entirely


# ──────────────────────────────────────────────
# Resource Registration
# ──────────────────────────────────────────────


@dataclass
class ConnectionConfig:
    """Connection details for a resource.

    Args:
        uri: Connection string, URL, or file path.
        params: Adapter-specific parameters (e.g., schema, consumer_group).
    """

    uri: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataResource:
    """A registered data resource to scan.

    Args:
        name: Human-readable name for identification.
        resource_type: Type of resource (database, kafka, api, file_storage).
        connection: Connection configuration.
        description: Optional description of the resource.
        tags: Tags for categorization.
        owner: Owner or team responsible.
    """

    name: str
    resource_type: ResourceType
    connection: ConnectionConfig
    description: str = ""
    tags: List[str] = field(default_factory=list)
    owner: Optional[str] = None


# ──────────────────────────────────────────────
# Container and Field Models
# ──────────────────────────────────────────────


@dataclass
class ContainerInfo:
    """A scannable container: table, topic, endpoint, or file.

    Args:
        name: Container name (table name, topic name, etc.).
        container_type: Type of container.
        metadata: Adapter-specific metadata (row_count, partitions, etc.).
    """

    name: str
    container_type: ContainerType
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FieldInfo:
    """Universal representation of a scannable field.

    Covers database columns, Kafka schema fields, API parameters,
    and file columns/keys.

    Args:
        name: Field name (column name, JSON key, parameter name).
        container_name: Name of the parent container.
        data_type: Data type as string (SQL type, JSON type, etc.).
        nullable: Whether the field can be null.
        description: Optional description or comment.
        metadata: Adapter-specific extra info.
    """

    name: str
    container_name: str
    data_type: str = "unknown"
    nullable: bool = True
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def qualified_name(self) -> str:
        """Return container.field qualified name."""
        return f"{self.container_name}.{self.name}"


# ──────────────────────────────────────────────
# Scan Results
# ──────────────────────────────────────────────


@dataclass
class FieldScanResult:
    """PII detection result for one field.

    Args:
        field_info: The scanned field.
        pii_detected: Whether PII was found.
        confidence: Detection confidence level.
        categories: PII categories detected.
        severities: Severity levels of detected PII.
        matches: Representative Match objects from Engine.
        metadata_score: Score from field name/metadata analysis (0.0-1.0).
        sample_score: Score from sample value analysis (0.0-1.0).
        combined_score: Weighted combination of metadata and sample scores.
        sample_count: Number of values sampled.
        match_count: Number of values that had PII matches.
        ns_ids: Pattern IDs that matched (e.g., "kr/mobile_01").
    """

    field_info: FieldInfo
    pii_detected: bool = False
    confidence: PIIConfidence = PIIConfidence.NONE
    categories: List[Category] = field(default_factory=list)
    severities: List[Severity] = field(default_factory=list)
    matches: List[Match] = field(default_factory=list)
    metadata_score: float = 0.0
    sample_score: float = 0.0
    combined_score: float = 0.0
    sample_count: int = 0
    match_count: int = 0
    ns_ids: List[str] = field(default_factory=list)

    @property
    def max_severity(self) -> Optional[Severity]:
        """Return highest severity found, or None."""
        if not self.severities:
            return None
        order = {
            Severity.LOW: 0,
            Severity.MEDIUM: 1,
            Severity.HIGH: 2,
            Severity.CRITICAL: 3,
        }
        return max(self.severities, key=lambda s: order.get(s, 0))

    @property
    def match_ratio(self) -> float:
        """Return ratio of matched samples to total samples."""
        if self.sample_count == 0:
            return 0.0
        return self.match_count / self.sample_count


@dataclass
class ContainerScanResult:
    """Scan result for one container (table/topic/endpoint/file).

    Args:
        container: The scanned container info.
        field_results: Results for each field in the container.
        scan_duration_ms: Time taken to scan this container.
    """

    container: ContainerInfo
    field_results: List[FieldScanResult] = field(default_factory=list)
    scan_duration_ms: float = 0.0

    @property
    def pii_field_count(self) -> int:
        """Number of fields with PII detected."""
        return sum(1 for f in self.field_results if f.pii_detected)

    @property
    def has_pii(self) -> bool:
        """Whether any field has PII."""
        return any(f.pii_detected for f in self.field_results)


@dataclass
class ResourceScanResult:
    """Scan result for an entire resource.

    Args:
        resource: The scanned resource.
        container_results: Results for each container.
        strategy: Scan strategy used.
        scanned_at: ISO format timestamp of scan start (alias for scan_started_at).
        scan_started_at: ISO format timestamp when the scan began.
        scan_finished_at: ISO format timestamp when the scan completed.
        scan_duration_ms: Total scan time in milliseconds.
        status: Current status of the scan.
        errors: Errors encountered during scanning.
    """

    resource: DataResource
    container_results: List[ContainerScanResult] = field(default_factory=list)
    strategy: ScanStrategy = ScanStrategy.SAMPLE
    scanned_at: Optional[str] = None
    scan_started_at: Optional[str] = None
    scan_finished_at: Optional[str] = None
    scan_duration_ms: float = 0.0
    status: ScanStatus = ScanStatus.COMPLETED
    errors: List[str] = field(default_factory=list)

    @property
    def total_fields(self) -> int:
        """Total number of fields scanned."""
        return sum(len(c.field_results) for c in self.container_results)

    @property
    def pii_fields(self) -> int:
        """Number of fields with PII detected."""
        return sum(c.pii_field_count for c in self.container_results)

    @property
    def pii_containers(self) -> int:
        """Number of containers with at least one PII field."""
        return sum(1 for c in self.container_results if c.has_pii)


# ──────────────────────────────────────────────
# Relationship / Lineage Models
# ──────────────────────────────────────────────


@dataclass
class FieldRelationship:
    """A relationship between two fields (possibly across resources).

    Args:
        source_resource: Source resource name.
        source_field: Qualified field name (container.field).
        target_resource: Target resource name.
        target_field: Qualified field name (container.field).
        relationship_type: Type of relationship.
        metadata: Additional relationship info.
    """

    source_resource: str
    source_field: str
    target_resource: str
    target_field: str
    relationship_type: RelationshipType
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LineageNode:
    """A node in the lineage graph.

    Args:
        resource_name: Which resource this field belongs to.
        field_qualified_name: container.field qualified name.
        categories: PII categories detected at this node.
        confidence: Detection confidence.
    """

    resource_name: str
    field_qualified_name: str
    categories: List[Category] = field(default_factory=list)
    confidence: PIIConfidence = PIIConfidence.NONE

    @property
    def full_path(self) -> str:
        """Return resource.container.field full path."""
        return f"{self.resource_name}.{self.field_qualified_name}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LineageNode):
            return NotImplemented
        return (
            self.resource_name == other.resource_name
            and self.field_qualified_name == other.field_qualified_name
        )

    def __hash__(self) -> int:
        return hash((self.resource_name, self.field_qualified_name))


@dataclass
class LineageEdge:
    """An edge in the lineage graph.

    Args:
        source: Source node.
        target: Target node.
        relationship_type: Type of relationship.
        metadata: Additional edge info.
    """

    source: LineageNode
    target: LineageNode
    relationship_type: RelationshipType
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LineageGraph:
    """The full PII lineage graph.

    Args:
        nodes: All nodes in the graph.
        edges: All edges in the graph.
    """

    nodes: List[LineageNode] = field(default_factory=list)
    edges: List[LineageEdge] = field(default_factory=list)

    def get_upstream(self, node: LineageNode) -> List[LineageEdge]:
        """Get all edges flowing into this node."""
        return [e for e in self.edges if e.target == node]

    def get_downstream(self, node: LineageNode) -> List[LineageEdge]:
        """Get all edges flowing out of this node."""
        return [e for e in self.edges if e.source == node]

    def get_node(self, resource_name: str, field_qualified_name: str) -> Optional[LineageNode]:
        """Find a node by resource and field name."""
        for n in self.nodes:
            if n.resource_name == resource_name and n.field_qualified_name == field_qualified_name:
                return n
        return None

    def get_pii_nodes(self) -> List[LineageNode]:
        """Get all nodes that have PII categories."""
        return [n for n in self.nodes if n.categories]


# ──────────────────────────────────────────────
# Inventory Models
# ──────────────────────────────────────────────


@dataclass
class MaskingPolicy:
    """Recommended masking configuration for a PII field.

    Args:
        strategy: Recommended masking strategy.
        mask_pattern: Custom mask pattern (e.g., "***-****-****").
        preserve_format: Whether to preserve the original format during masking.
        notes: Additional notes or rationale.
    """

    strategy: MaskingStrategy = MaskingStrategy.MASK
    mask_pattern: Optional[str] = None
    preserve_format: bool = False
    notes: str = ""


@dataclass
class InventoryEntry:
    """One entry in the data inventory (one field with PII).

    Args:
        resource_name: Name of the resource.
        resource_type: Type of resource.
        container_name: Name of the container.
        field_name: Name of the field.
        data_type: Field data type.
        categories: PII categories detected.
        max_severity: Highest severity found.
        confidence: Detection confidence.
        ns_ids: Pattern IDs that matched.
        match_ratio: Ratio of sampled values with PII.
        sample_count: Number of values sampled.
        match_count: Number of values that matched PII.
        owner: Resource owner.
        tags: Resource tags.
        scan_started_at: When the scan that found this entry started.
        scan_finished_at: When the scan that found this entry completed.
        masking_policy: Recommended masking configuration for this field.
    """

    resource_name: str
    resource_type: ResourceType
    container_name: str
    field_name: str
    data_type: str = "unknown"
    categories: List[Category] = field(default_factory=list)
    max_severity: Optional[Severity] = None
    confidence: PIIConfidence = PIIConfidence.NONE
    ns_ids: List[str] = field(default_factory=list)
    match_ratio: float = 0.0
    sample_count: int = 0
    match_count: int = 0
    owner: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    scan_started_at: Optional[str] = None
    scan_finished_at: Optional[str] = None
    masking_policy: Optional[MaskingPolicy] = None

    @property
    def key(self) -> Tuple[str, str, str]:
        """Unique key for diff comparison: (resource, container, field)."""
        return (self.resource_name, self.container_name, self.field_name)


@dataclass
class ScanMetadata:
    """Summary of scan execution for inventory context.

    Args:
        resource_name: Name of the scanned resource.
        resource_type: Type of resource.
        strategy: Scan strategy used.
        scan_started_at: When the scan began.
        scan_finished_at: When the scan completed.
        scan_duration_ms: How long the scan took.
        total_containers: Number of containers scanned.
        total_fields: Total fields scanned.
        pii_fields: Number of fields with PII detected.
        status: Final status of the scan.
        errors: Errors encountered during scanning.
    """

    resource_name: str
    resource_type: ResourceType
    strategy: ScanStrategy = ScanStrategy.SAMPLE
    scan_started_at: Optional[str] = None
    scan_finished_at: Optional[str] = None
    scan_duration_ms: float = 0.0
    total_containers: int = 0
    total_fields: int = 0
    pii_fields: int = 0
    status: ScanStatus = ScanStatus.COMPLETED
    errors: List[str] = field(default_factory=list)


@dataclass
class DataInventory:
    """Aggregated PII inventory across all scanned resources.

    Args:
        entries: All PII inventory entries.
        generated_at: ISO format timestamp of inventory generation.
        scan_metadata: Scan execution summaries for each resource.
    """

    entries: List[InventoryEntry] = field(default_factory=list)
    generated_at: Optional[str] = None
    scan_metadata: List[ScanMetadata] = field(default_factory=list)

    @property
    def total_pii_fields(self) -> int:
        """Total number of PII fields in inventory."""
        return len(self.entries)

    def by_category(self) -> Dict[Category, List[InventoryEntry]]:
        """Group entries by PII category."""
        result: Dict[Category, List[InventoryEntry]] = {}
        for entry in self.entries:
            for cat in entry.categories:
                result.setdefault(cat, []).append(entry)
        return result

    def by_resource(self) -> Dict[str, List[InventoryEntry]]:
        """Group entries by resource name."""
        result: Dict[str, List[InventoryEntry]] = {}
        for entry in self.entries:
            result.setdefault(entry.resource_name, []).append(entry)
        return result

    def by_severity(self) -> Dict[Severity, List[InventoryEntry]]:
        """Group entries by max severity."""
        result: Dict[Severity, List[InventoryEntry]] = {}
        for entry in self.entries:
            if entry.max_severity:
                result.setdefault(entry.max_severity, []).append(entry)
        return result

    def filter_by_confidence(self, min_confidence: PIIConfidence) -> List[InventoryEntry]:
        """Filter entries by minimum confidence level."""
        order = {
            PIIConfidence.NONE: 0,
            PIIConfidence.LOW: 1,
            PIIConfidence.MEDIUM: 2,
            PIIConfidence.HIGH: 3,
            PIIConfidence.CONFIRMED: 4,
        }
        min_level = order.get(min_confidence, 0)
        return [e for e in self.entries if order.get(e.confidence, 0) >= min_level]


@dataclass
class InventoryDiff:
    """Difference between two inventory snapshots.

    Args:
        added: New PII fields found.
        removed: PII fields no longer detected.
        changed: Fields where categories/severity/confidence changed (old, new).
        unchanged_count: Number of unchanged entries.
        timestamp: When the diff was computed.
    """

    added: List[InventoryEntry] = field(default_factory=list)
    removed: List[InventoryEntry] = field(default_factory=list)
    changed: List[Tuple[InventoryEntry, InventoryEntry]] = field(default_factory=list)
    unchanged_count: int = 0
    timestamp: Optional[str] = None
