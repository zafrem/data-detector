"""Tests for DataLineageTracer."""

import pytest

from datadetector.data_lineage import DataLineageTracer
from datadetector.models import Category
from datadetector.resource_models import (
    ConnectionConfig,
    ContainerInfo,
    ContainerScanResult,
    ContainerType,
    DataInventory,
    DataResource,
    FieldInfo,
    FieldRelationship,
    FieldScanResult,
    InventoryEntry,
    PIIConfidence,
    RelationshipType,
    ResourceScanResult,
    ResourceType,
    ScanStrategy,
)


@pytest.fixture
def db_scan_result():
    """Database scan result with users and orders tables."""
    resource = DataResource(
        name="my-db",
        resource_type=ResourceType.DATABASE,
        connection=ConnectionConfig(uri="sqlite:///:memory:"),
    )
    return ResourceScanResult(
        resource=resource,
        container_results=[
            ContainerScanResult(
                container=ContainerInfo(name="users", container_type=ContainerType.TABLE),
                field_results=[
                    FieldScanResult(
                        field_info=FieldInfo(name="id", container_name="users"),
                        pii_detected=False,
                    ),
                    FieldScanResult(
                        field_info=FieldInfo(name="email", container_name="users"),
                        pii_detected=True,
                        categories=[Category.EMAIL],
                        confidence=PIIConfidence.HIGH,
                    ),
                    FieldScanResult(
                        field_info=FieldInfo(name="ssn", container_name="users"),
                        pii_detected=True,
                        categories=[Category.SSN],
                        confidence=PIIConfidence.CONFIRMED,
                    ),
                ],
            ),
            ContainerScanResult(
                container=ContainerInfo(name="orders", container_type=ContainerType.TABLE),
                field_results=[
                    FieldScanResult(
                        field_info=FieldInfo(name="id", container_name="orders"),
                        pii_detected=False,
                    ),
                    FieldScanResult(
                        field_info=FieldInfo(name="user_id", container_name="orders"),
                        pii_detected=False,
                    ),
                    FieldScanResult(
                        field_info=FieldInfo(name="billing_email", container_name="orders"),
                        pii_detected=True,
                        categories=[Category.EMAIL],
                        confidence=PIIConfidence.HIGH,
                    ),
                ],
            ),
        ],
        strategy=ScanStrategy.SAMPLE,
    )


@pytest.fixture
def kafka_scan_result():
    """Kafka scan result with user-events topic."""
    resource = DataResource(
        name="my-kafka",
        resource_type=ResourceType.KAFKA,
        connection=ConnectionConfig(uri="localhost:9092"),
    )
    return ResourceScanResult(
        resource=resource,
        container_results=[
            ContainerScanResult(
                container=ContainerInfo(name="user-events", container_type=ContainerType.TOPIC),
                field_results=[
                    FieldScanResult(
                        field_info=FieldInfo(name="user_id", container_name="user-events"),
                        pii_detected=False,
                    ),
                    FieldScanResult(
                        field_info=FieldInfo(name="email", container_name="user-events"),
                        pii_detected=True,
                        categories=[Category.EMAIL],
                        confidence=PIIConfidence.HIGH,
                    ),
                ],
            ),
        ],
        strategy=ScanStrategy.SAMPLE,
    )


@pytest.fixture
def db_relationships():
    """Foreign key relationships for the database."""
    return [
        FieldRelationship(
            source_resource="my-db",
            source_field="orders.user_id",
            target_resource="my-db",
            target_field="users.id",
            relationship_type=RelationshipType.FOREIGN_KEY,
        ),
    ]


class TestDataLineageTracerBuild:
    def test_build_graph_from_single_scan(self, db_scan_result):
        tracer = DataLineageTracer()
        tracer.add_scan_result(db_scan_result)
        graph = tracer.build_graph()

        assert len(graph.nodes) == 6  # 3 users + 3 orders fields
        pii_nodes = graph.get_pii_nodes()
        assert len(pii_nodes) == 3  # email, ssn, billing_email

    def test_build_graph_with_relationships(self, db_scan_result, db_relationships):
        tracer = DataLineageTracer()
        tracer.add_scan_result(db_scan_result)
        for rel in db_relationships:
            tracer.add_relationship(rel)
        graph = tracer.build_graph()

        assert len(graph.edges) >= 1
        fk_edges = [e for e in graph.edges if e.relationship_type == RelationshipType.FOREIGN_KEY]
        assert len(fk_edges) == 1

    def test_build_graph_cross_resource(self, db_scan_result, kafka_scan_result):
        tracer = DataLineageTracer()
        tracer.add_scan_result(db_scan_result)
        tracer.add_scan_result(kafka_scan_result)
        graph = tracer.build_graph()

        # Should have nodes from both resources
        db_nodes = [n for n in graph.nodes if n.resource_name == "my-db"]
        kafka_nodes = [n for n in graph.nodes if n.resource_name == "my-kafka"]
        assert len(db_nodes) >= 1
        assert len(kafka_nodes) >= 1

    def test_inferred_cross_resource_links(self, db_scan_result, kafka_scan_result):
        tracer = DataLineageTracer()
        tracer.add_scan_result(db_scan_result)
        tracer.add_scan_result(kafka_scan_result)
        graph = tracer.build_graph()

        # Should infer link between users.email (db) and user-events.email (kafka)
        # since they share the same field name "email" and same category EMAIL
        inferred = [e for e in graph.edges if e.metadata.get("inferred")]
        assert len(inferred) >= 1

    def test_manual_cross_resource_link(self, db_scan_result, kafka_scan_result):
        tracer = DataLineageTracer()
        tracer.add_scan_result(db_scan_result)
        tracer.add_scan_result(kafka_scan_result)
        tracer.add_cross_resource_link(
            "my-db",
            "users.email",
            "my-kafka",
            "user-events.email",
        )
        graph = tracer.build_graph()

        manual_edges = [e for e in graph.edges if e.relationship_type == RelationshipType.MANUAL]
        assert len(manual_edges) >= 1


class TestDataLineageTracerTrace:
    def test_trace_downstream(self, db_scan_result, db_relationships):
        tracer = DataLineageTracer()
        tracer.add_scan_result(db_scan_result)
        for rel in db_relationships:
            tracer.add_relationship(rel)

        subgraph = tracer.trace("my-db.users.id", direction="downstream")
        # users.id -> orders.user_id via FK
        assert len(subgraph.nodes) >= 1

    def test_trace_upstream(self, db_scan_result, db_relationships):
        tracer = DataLineageTracer()
        tracer.add_scan_result(db_scan_result)
        for rel in db_relationships:
            tracer.add_relationship(rel)

        subgraph = tracer.trace("my-db.orders.user_id", direction="upstream")
        assert len(subgraph.nodes) >= 1

    def test_trace_nonexistent_field(self, db_scan_result):
        tracer = DataLineageTracer()
        tracer.add_scan_result(db_scan_result)
        subgraph = tracer.trace("nonexistent.field.path")
        assert len(subgraph.nodes) == 0
        assert len(subgraph.edges) == 0

    def test_trace_both_directions(self, db_scan_result, db_relationships, kafka_scan_result):
        tracer = DataLineageTracer()
        tracer.add_scan_result(db_scan_result)
        tracer.add_scan_result(kafka_scan_result)
        for rel in db_relationships:
            tracer.add_relationship(rel)
        tracer.add_cross_resource_link(
            "my-db",
            "users.email",
            "my-kafka",
            "user-events.email",
        )

        subgraph = tracer.trace("my-db.users.email", direction="both")
        assert len(subgraph.nodes) >= 1


class TestDataLineageTracerAnalysis:
    def test_pii_flow_summary(self, db_scan_result, kafka_scan_result):
        tracer = DataLineageTracer()
        tracer.add_scan_result(db_scan_result)
        tracer.add_scan_result(kafka_scan_result)

        summary = tracer.get_pii_flow_summary()
        assert "email" in summary
        assert (
            len(summary["email"]) >= 2
        )  # db.users.email + kafka.user-events.email + possibly billing

    def test_find_pii_sources(self, db_scan_result, db_relationships):
        tracer = DataLineageTracer()
        tracer.add_scan_result(db_scan_result)
        for rel in db_relationships:
            tracer.add_relationship(rel)

        sources = tracer.find_pii_sources()
        # PII nodes with no incoming edges
        assert len(sources) >= 1

    def test_find_pii_sinks(self, db_scan_result, db_relationships):
        tracer = DataLineageTracer()
        tracer.add_scan_result(db_scan_result)
        for rel in db_relationships:
            tracer.add_relationship(rel)

        sinks = tracer.find_pii_sinks()
        assert len(sinks) >= 1

    def test_annotate_with_inventory(self, db_scan_result):
        tracer = DataLineageTracer()
        tracer.add_scan_result(db_scan_result)
        tracer.build_graph()

        inventory = DataInventory(
            entries=[
                InventoryEntry(
                    resource_name="my-db",
                    resource_type=ResourceType.DATABASE,
                    container_name="users",
                    field_name="email",
                    categories=[Category.EMAIL, Category.NAME],  # Added NAME
                    confidence=PIIConfidence.CONFIRMED,
                ),
            ]
        )

        tracer.annotate_with_inventory(inventory)
        graph = tracer.get_graph()
        node = graph.get_node("my-db", "users.email")
        assert node is not None
        assert Category.NAME in node.categories


class TestDataLineageExport:
    def test_to_dict(self, db_scan_result, db_relationships):
        tracer = DataLineageTracer()
        tracer.add_scan_result(db_scan_result)
        for rel in db_relationships:
            tracer.add_relationship(rel)

        data = tracer.to_dict()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) >= 1

        # Nodes should have expected fields
        node = data["nodes"][0]
        assert "id" in node
        assert "resource" in node
        assert "categories" in node
        assert "has_pii" in node

    def test_to_mermaid(self, db_scan_result, db_relationships):
        tracer = DataLineageTracer()
        tracer.add_scan_result(db_scan_result)
        for rel in db_relationships:
            tracer.add_relationship(rel)

        mermaid = tracer.to_mermaid()
        assert mermaid.startswith("graph LR")
        assert "-->|" in mermaid  # Has edges
        assert "foreign_key" in mermaid

    def test_to_mermaid_pii_styling(self, db_scan_result):
        tracer = DataLineageTracer()
        tracer.add_scan_result(db_scan_result)

        mermaid = tracer.to_mermaid()
        assert "fill:#ffcccc" in mermaid  # PII nodes styled


class TestEmptyGraph:
    def test_empty_tracer(self):
        tracer = DataLineageTracer()
        graph = tracer.build_graph()
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_empty_summary(self):
        tracer = DataLineageTracer()
        assert tracer.get_pii_flow_summary() == {}

    def test_empty_sources_sinks(self):
        tracer = DataLineageTracer()
        assert tracer.find_pii_sources() == []
        assert tracer.find_pii_sinks() == []

    def test_empty_export(self):
        tracer = DataLineageTracer()
        data = tracer.to_dict()
        assert data == {"nodes": [], "edges": []}

        mermaid = tracer.to_mermaid()
        assert "graph LR" in mermaid
