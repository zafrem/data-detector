"""Unit tests for building lineage directly from DataInventory artifacts.

Covers DataLineageTracer.add_inventory(): seeding nodes from inventory entries,
automatic cross-resource link inference across inventories from different
sources, mixed scan-result + inventory graphs, and JSON round-tripping.
"""

from datadetector.data_inventory import DataInventoryGenerator
from datadetector.data_lineage import DataLineageTracer
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
    InventoryEntry,
    InventoryFormat,
    PIIConfidence,
    ResourceScanResult,
    ResourceType,
)


def _entry(resource, container, field_name, category=Category.EMAIL, confidence=PIIConfidence.HIGH):
    return InventoryEntry(
        resource_name=resource,
        resource_type=ResourceType.TRAINING_DATA,
        container_name=container,
        field_name=field_name,
        data_type="text",
        categories=[category],
        max_severity=Severity.HIGH,
        confidence=confidence,
    )


def _inv(resource, entries):
    return DataInventory(entries=entries, generated_at="t")


class TestAddInventory:
    def test_seeds_one_node_per_entry(self):
        inv = _inv(
            "team-a",
            [
                _entry("team-a", "users", "email"),
                _entry("team-a", "users", "phone", category=Category.PHONE),
            ],
        )
        tracer = DataLineageTracer()
        tracer.add_inventory(inv)
        graph = tracer.build_graph()

        paths = {n.full_path for n in graph.nodes}
        assert paths == {"team-a.users.email", "team-a.users.phone"}

    def test_node_carries_categories_and_confidence(self):
        tracer = DataLineageTracer()
        tracer.add_inventory(_inv("team-a", [_entry("team-a", "users", "email")]))
        node = tracer.build_graph().nodes[0]
        assert node.categories == [Category.EMAIL]
        assert node.confidence == PIIConfidence.HIGH

    def test_cross_resource_link_inferred_across_inventories(self):
        """Two inventories from different sources sharing field+category → edge."""
        tracer = DataLineageTracer()
        tracer.add_inventory(_inv("team-a", [_entry("team-a", "users", "email")]))
        tracer.add_inventory(_inv("team-b", [_entry("team-b", "events", "email")]))
        graph = tracer.build_graph()

        assert len(graph.nodes) == 2
        assert len(graph.edges) >= 1
        edge = graph.edges[0]
        assert edge.metadata.get("inferred") is True

        summary = tracer.get_pii_flow_summary()
        assert set(summary["email"]) == {"team-a.users.email", "team-b.events.email"}

    def test_explicit_cross_resource_link(self):
        tracer = DataLineageTracer()
        tracer.add_inventory(_inv("team-a", [_entry("team-a", "users", "email")]))
        tracer.add_inventory(
            _inv("team-b", [_entry("team-b", "events", "user_email", category=Category.EMAIL)])
        )
        tracer.add_cross_resource_link("team-a", "users.email", "team-b", "events.user_email")
        graph = tracer.build_graph()
        edge_pairs = {(e.source.full_path, e.target.full_path) for e in graph.edges}
        assert ("team-a.users.email", "team-b.events.user_email") in edge_pairs

    def test_mixed_scan_result_and_inventory_no_overwrite(self):
        """A scan-result node is not overwritten by an inventory for the same field."""
        resource = DataResource(
            name="my-db",
            resource_type=ResourceType.DATABASE,
            connection=ConnectionConfig(uri="sqlite:///:memory:"),
        )
        scan = ResourceScanResult(
            resource=resource,
            container_results=[
                ContainerScanResult(
                    container=ContainerInfo(name="users", container_type=ContainerType.TABLE),
                    field_results=[
                        FieldScanResult(
                            field_info=FieldInfo(name="email", container_name="users"),
                            pii_detected=True,
                            categories=[Category.EMAIL],
                            confidence=PIIConfidence.CONFIRMED,
                        )
                    ],
                )
            ],
        )
        tracer = DataLineageTracer()
        tracer.add_scan_result(scan)
        # Inventory references the same field but with weaker confidence.
        tracer.add_inventory(
            _inv("my-db", [_entry("my-db", "users", "email", confidence=PIIConfidence.LOW)])
        )
        graph = tracer.build_graph()

        nodes = [n for n in graph.nodes if n.full_path == "my-db.users.email"]
        assert len(nodes) == 1  # not duplicated
        assert nodes[0].confidence == PIIConfidence.CONFIRMED  # scan node kept

    def test_json_roundtrip_export_load_build(self):
        inv = _inv("team-a", [_entry("team-a", "users", "email")])
        json_str = DataInventoryGenerator().export(inv, InventoryFormat.JSON)
        loaded = DataInventoryGenerator.load_json_str(json_str)

        tracer = DataLineageTracer()
        tracer.add_inventory(loaded)
        graph = tracer.build_graph()

        assert {n.full_path for n in graph.nodes} == {"team-a.users.email"}
        assert graph.nodes[0].categories == [Category.EMAIL]

    def test_to_dict_and_mermaid_render(self):
        tracer = DataLineageTracer()
        tracer.add_inventory(_inv("team-a", [_entry("team-a", "users", "email")]))
        tracer.add_inventory(_inv("team-b", [_entry("team-b", "events", "email")]))
        tracer.build_graph()

        data = tracer.to_dict()
        assert len(data["nodes"]) == 2
        assert all(n["has_pii"] for n in data["nodes"])
        assert "graph LR" in tracer.to_mermaid()
