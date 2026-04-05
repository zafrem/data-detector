"""Tests for resource_models.py — shared dataclasses and enums."""

from datadetector.models import Category, Severity
from datadetector.resource_models import (
    ConnectionConfig,
    ContainerInfo,
    ContainerScanResult,
    ContainerType,
    DataInventory,
    DataResource,
    FieldInfo,
    FieldScanResult,
    InventoryDiff,
    InventoryEntry,
    InventoryFormat,
    LineageEdge,
    LineageGraph,
    LineageNode,
    PIIConfidence,
    RelationshipType,
    ResourceScanResult,
    ResourceType,
    ScanStrategy,
)


class TestEnums:
    def test_resource_type_values(self):
        assert ResourceType.DATABASE.value == "database"
        assert ResourceType.KAFKA.value == "kafka"
        assert ResourceType.API.value == "api"
        assert ResourceType.FILE_STORAGE.value == "file_storage"

    def test_scan_strategy_values(self):
        assert ScanStrategy.METADATA_ONLY.value == "metadata_only"
        assert ScanStrategy.SAMPLE.value == "sample"
        assert ScanStrategy.FULL.value == "full"

    def test_pii_confidence_values(self):
        assert PIIConfidence.NONE.value == "none"
        assert PIIConfidence.LOW.value == "low"
        assert PIIConfidence.CONFIRMED.value == "confirmed"

    def test_container_type_values(self):
        assert ContainerType.TABLE.value == "table"
        assert ContainerType.TOPIC.value == "topic"
        assert ContainerType.ENDPOINT.value == "endpoint"
        assert ContainerType.FILE.value == "file"

    def test_inventory_format_values(self):
        assert InventoryFormat.JSON.value == "json"
        assert InventoryFormat.HTML.value == "html"


class TestConnectionConfig:
    def test_defaults(self):
        config = ConnectionConfig()
        assert config.uri is None
        assert config.params == {}

    def test_with_values(self):
        config = ConnectionConfig(uri="sqlite:///test.db", params={"schema": "public"})
        assert config.uri == "sqlite:///test.db"
        assert config.params["schema"] == "public"


class TestDataResource:
    def test_minimal(self):
        resource = DataResource(
            name="test-db",
            resource_type=ResourceType.DATABASE,
            connection=ConnectionConfig(uri="sqlite:///:memory:"),
        )
        assert resource.name == "test-db"
        assert resource.resource_type == ResourceType.DATABASE
        assert resource.description == ""
        assert resource.tags == []
        assert resource.owner is None

    def test_full(self):
        resource = DataResource(
            name="prod-db",
            resource_type=ResourceType.DATABASE,
            connection=ConnectionConfig(uri="postgresql://localhost/db"),
            description="Production database",
            tags=["production", "critical"],
            owner="data-team",
        )
        assert resource.owner == "data-team"
        assert len(resource.tags) == 2


class TestFieldInfo:
    def test_qualified_name(self):
        field = FieldInfo(name="email", container_name="users")
        assert field.qualified_name == "users.email"

    def test_defaults(self):
        field = FieldInfo(name="id", container_name="users")
        assert field.data_type == "unknown"
        assert field.nullable is True
        assert field.description == ""
        assert field.metadata == {}


class TestFieldScanResult:
    def test_max_severity_empty(self):
        result = FieldScanResult(field_info=FieldInfo(name="x", container_name="t"))
        assert result.max_severity is None

    def test_max_severity(self):
        result = FieldScanResult(
            field_info=FieldInfo(name="x", container_name="t"),
            severities=[Severity.LOW, Severity.HIGH, Severity.MEDIUM],
        )
        assert result.max_severity == Severity.HIGH

    def test_match_ratio_zero_samples(self):
        result = FieldScanResult(field_info=FieldInfo(name="x", container_name="t"))
        assert result.match_ratio == pytest.approx(0.0)

    def test_match_ratio(self):
        result = FieldScanResult(
            field_info=FieldInfo(name="x", container_name="t"),
            sample_count=100,
            match_count=75,
        )
        assert result.match_ratio == pytest.approx(0.75)


class TestContainerScanResult:
    def test_has_pii_false(self):
        result = ContainerScanResult(
            container=ContainerInfo(name="logs", container_type=ContainerType.TABLE),
            field_results=[
                FieldScanResult(
                    field_info=FieldInfo(name="id", container_name="logs"),
                    pii_detected=False,
                ),
            ],
        )
        assert result.has_pii is False
        assert result.pii_field_count == 0

    def test_has_pii_true(self):
        result = ContainerScanResult(
            container=ContainerInfo(name="users", container_type=ContainerType.TABLE),
            field_results=[
                FieldScanResult(
                    field_info=FieldInfo(name="id", container_name="users"),
                    pii_detected=False,
                ),
                FieldScanResult(
                    field_info=FieldInfo(name="email", container_name="users"),
                    pii_detected=True,
                ),
            ],
        )
        assert result.has_pii is True
        assert result.pii_field_count == 1


class TestResourceScanResult:
    def test_properties(self):
        resource = DataResource(
            name="test",
            resource_type=ResourceType.DATABASE,
            connection=ConnectionConfig(),
        )
        result = ResourceScanResult(
            resource=resource,
            container_results=[
                ContainerScanResult(
                    container=ContainerInfo(name="t1", container_type=ContainerType.TABLE),
                    field_results=[
                        FieldScanResult(
                            field_info=FieldInfo(name="f1", container_name="t1"),
                            pii_detected=True,
                        ),
                        FieldScanResult(
                            field_info=FieldInfo(name="f2", container_name="t1"),
                            pii_detected=False,
                        ),
                    ],
                ),
                ContainerScanResult(
                    container=ContainerInfo(name="t2", container_type=ContainerType.TABLE),
                    field_results=[
                        FieldScanResult(
                            field_info=FieldInfo(name="f3", container_name="t2"),
                            pii_detected=False,
                        ),
                    ],
                ),
            ],
        )
        assert result.total_fields == 3
        assert result.pii_fields == 1
        assert result.pii_containers == 1


class TestLineageNode:
    def test_full_path(self):
        node = LineageNode(resource_name="db", field_qualified_name="users.email")
        assert node.full_path == "db.users.email"

    def test_equality(self):
        a = LineageNode(resource_name="db", field_qualified_name="users.email")
        b = LineageNode(resource_name="db", field_qualified_name="users.email")
        c = LineageNode(resource_name="db", field_qualified_name="users.phone")
        assert a == b
        assert a != c

    def test_hash(self):
        a = LineageNode(resource_name="db", field_qualified_name="users.email")
        b = LineageNode(resource_name="db", field_qualified_name="users.email")
        assert hash(a) == hash(b)
        assert len({a, b}) == 1


class TestLineageGraph:
    def test_get_upstream_downstream(self):
        n1 = LineageNode(resource_name="db", field_qualified_name="users.id")
        n2 = LineageNode(resource_name="db", field_qualified_name="orders.user_id")
        edge = LineageEdge(source=n1, target=n2, relationship_type=RelationshipType.FOREIGN_KEY)
        graph = LineageGraph(nodes=[n1, n2], edges=[edge])

        assert len(graph.get_downstream(n1)) == 1
        assert len(graph.get_upstream(n1)) == 0
        assert len(graph.get_upstream(n2)) == 1
        assert len(graph.get_downstream(n2)) == 0

    def test_get_node(self):
        n1 = LineageNode(resource_name="db", field_qualified_name="users.email")
        graph = LineageGraph(nodes=[n1])
        assert graph.get_node("db", "users.email") == n1
        assert graph.get_node("db", "nonexistent") is None

    def test_get_pii_nodes(self):
        n1 = LineageNode(
            resource_name="db",
            field_qualified_name="users.email",
            categories=[Category.EMAIL],
        )
        n2 = LineageNode(resource_name="db", field_qualified_name="users.id")
        graph = LineageGraph(nodes=[n1, n2])
        pii_nodes = graph.get_pii_nodes()
        assert len(pii_nodes) == 1
        assert pii_nodes[0] == n1


class TestInventoryEntry:
    def test_key(self):
        entry = InventoryEntry(
            resource_name="db",
            resource_type=ResourceType.DATABASE,
            container_name="users",
            field_name="email",
        )
        assert entry.key == ("db", "users", "email")


class TestDataInventory:
    def _make_inventory(self):
        entries = [
            InventoryEntry(
                resource_name="db",
                resource_type=ResourceType.DATABASE,
                container_name="users",
                field_name="email",
                categories=[Category.EMAIL],
                max_severity=Severity.MEDIUM,
                confidence=PIIConfidence.HIGH,
            ),
            InventoryEntry(
                resource_name="db",
                resource_type=ResourceType.DATABASE,
                container_name="users",
                field_name="ssn",
                categories=[Category.SSN],
                max_severity=Severity.CRITICAL,
                confidence=PIIConfidence.CONFIRMED,
            ),
            InventoryEntry(
                resource_name="kafka",
                resource_type=ResourceType.KAFKA,
                container_name="events",
                field_name="email",
                categories=[Category.EMAIL],
                max_severity=Severity.MEDIUM,
                confidence=PIIConfidence.MEDIUM,
            ),
        ]
        return DataInventory(entries=entries)

    def test_total_pii_fields(self):
        inv = self._make_inventory()
        assert inv.total_pii_fields == 3

    def test_by_category(self):
        inv = self._make_inventory()
        by_cat = inv.by_category()
        assert len(by_cat[Category.EMAIL]) == 2
        assert len(by_cat[Category.SSN]) == 1

    def test_by_resource(self):
        inv = self._make_inventory()
        by_res = inv.by_resource()
        assert len(by_res["db"]) == 2
        assert len(by_res["kafka"]) == 1

    def test_by_severity(self):
        inv = self._make_inventory()
        by_sev = inv.by_severity()
        assert len(by_sev[Severity.CRITICAL]) == 1
        assert len(by_sev[Severity.MEDIUM]) == 2

    def test_filter_by_confidence(self):
        inv = self._make_inventory()
        high_plus = inv.filter_by_confidence(PIIConfidence.HIGH)
        assert len(high_plus) == 2  # HIGH + CONFIRMED


class TestInventoryDiff:
    def test_defaults(self):
        diff = InventoryDiff()
        assert diff.added == []
        assert diff.removed == []
        assert diff.changed == []
        assert diff.unchanged_count == 0
