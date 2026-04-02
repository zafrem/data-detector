"""Data Lineage Tracer: trace PII flow within and across resources.

Builds a directed graph of data flow between fields, annotated with PII
categories. Supports tracing upstream/downstream, finding PII sources/sinks,
and exporting as JSON or Mermaid diagrams.
"""

import logging
from collections import deque
from typing import Any, Dict, List, Optional, Set

from datadetector.resource_adapter import ResourceAdapter
from datadetector.resource_models import (
    DataInventory,
    FieldRelationship,
    LineageEdge,
    LineageGraph,
    LineageNode,
    RelationshipType,
    ResourceScanResult,
)

logger = logging.getLogger(__name__)


class DataLineageTracer:
    """Builds and queries a PII lineage graph across multiple resources.

    Example:
        >>> tracer = DataLineageTracer()
        >>> tracer.add_scan_result(db_result, db_adapter)
        >>> tracer.add_scan_result(kafka_result, kafka_adapter)
        >>> tracer.add_cross_resource_link(
        ...     "my-db", "users.email",
        ...     "my-kafka", "user-events.email",
        ... )
        >>> graph = tracer.build_graph()
        >>> paths = tracer.trace("my-db.users.email")
    """

    def __init__(self) -> None:
        self._scan_results: List[ResourceScanResult] = []
        self._relationships: List[FieldRelationship] = []
        self._graph: Optional[LineageGraph] = None

    def add_scan_result(
        self,
        result: ResourceScanResult,
        adapter: Optional[ResourceAdapter] = None,
    ) -> None:
        """Add scan result and optionally extract relationships from adapter.

        Args:
            result: ResourceScanResult from DataExplorer.scan().
            adapter: Optional connected adapter to extract relationships
                    (e.g., foreign keys from DatabaseAdapter).
        """
        self._scan_results.append(result)
        self._graph = None  # Invalidate cached graph

        if adapter is not None:
            try:
                relationships = adapter.get_relationships()
                self._relationships.extend(relationships)
                logger.info(
                    f"Extracted {len(relationships)} relationships from "
                    f"'{result.resource.name}'"
                )
            except Exception as e:
                logger.warning(
                    f"Could not extract relationships from " f"'{result.resource.name}': {e}"
                )

    def add_relationship(self, relationship: FieldRelationship) -> None:
        """Add a manual relationship.

        Args:
            relationship: FieldRelationship to add.
        """
        self._relationships.append(relationship)
        self._graph = None

    def add_cross_resource_link(
        self,
        source_resource: str,
        source_field: str,
        target_resource: str,
        target_field: str,
        relationship_type: RelationshipType = RelationshipType.MANUAL,
    ) -> None:
        """Convenience method for adding cross-resource links.

        Args:
            source_resource: Source resource name.
            source_field: Qualified field name (container.field).
            target_resource: Target resource name.
            target_field: Qualified field name (container.field).
            relationship_type: Type of relationship.
        """
        self._relationships.append(
            FieldRelationship(
                source_resource=source_resource,
                source_field=source_field,
                target_resource=target_resource,
                target_field=target_field,
                relationship_type=relationship_type,
            )
        )
        self._graph = None

    def build_graph(self) -> LineageGraph:
        """Build the lineage graph from scan results and relationships.

        Creates nodes from all scanned fields (PII and non-PII involved
        in relationships), and edges from discovered + manual relationships.

        Returns:
            LineageGraph with nodes and edges.
        """
        node_map: Dict[str, LineageNode] = {}  # full_path -> node

        # Step 1: Create nodes from scan results
        for scan_result in self._scan_results:
            resource_name = scan_result.resource.name
            for container_result in scan_result.container_results:
                for field_result in container_result.field_results:
                    qualified = field_result.field_info.qualified_name
                    full_path = f"{resource_name}.{qualified}"
                    node = LineageNode(
                        resource_name=resource_name,
                        field_qualified_name=qualified,
                        categories=list(field_result.categories),
                        confidence=field_result.confidence,
                    )
                    node_map[full_path] = node

        # Step 2: Create edges from relationships
        edges: List[LineageEdge] = []
        for rel in self._relationships:
            src_path = f"{rel.source_resource}.{rel.source_field}"
            tgt_path = f"{rel.target_resource}.{rel.target_field}"

            # Ensure nodes exist (create placeholders if needed)
            if src_path not in node_map:
                node_map[src_path] = LineageNode(
                    resource_name=rel.source_resource,
                    field_qualified_name=rel.source_field,
                )
            if tgt_path not in node_map:
                node_map[tgt_path] = LineageNode(
                    resource_name=rel.target_resource,
                    field_qualified_name=rel.target_field,
                )

            edges.append(
                LineageEdge(
                    source=node_map[src_path],
                    target=node_map[tgt_path],
                    relationship_type=rel.relationship_type,
                    metadata=dict(rel.metadata),
                )
            )

        # Step 3: Infer implicit cross-resource links
        inferred_edges = self._infer_cross_resource_links(node_map, edges)
        edges.extend(inferred_edges)

        self._graph = LineageGraph(
            nodes=list(node_map.values()),
            edges=edges,
        )
        return self._graph

    def get_graph(self) -> LineageGraph:
        """Get the current lineage graph, building if needed.

        Returns:
            LineageGraph.
        """
        if self._graph is None:
            return self.build_graph()
        return self._graph

    def trace(
        self,
        field_full_path: str,
        direction: str = "both",
        max_depth: int = 10,
    ) -> LineageGraph:
        """Trace lineage for a specific field.

        Args:
            field_full_path: Full path "resource.container.field".
            direction: "upstream", "downstream", or "both".
            max_depth: Maximum traversal depth.

        Returns:
            Subgraph containing only reachable nodes and edges.
        """
        graph = self.get_graph()

        # Find the starting node
        start_node = None
        for node in graph.nodes:
            if node.full_path == field_full_path:
                start_node = node
                break

        if start_node is None:
            return LineageGraph()

        visited_nodes: Set[str] = set()
        collected_edges: List[LineageEdge] = []

        if direction in ("upstream", "both"):
            self._bfs_traverse(
                graph, start_node, "upstream", max_depth, visited_nodes, collected_edges
            )

        if direction in ("downstream", "both"):
            self._bfs_traverse(
                graph, start_node, "downstream", max_depth, visited_nodes, collected_edges
            )

        visited_nodes.add(start_node.full_path)

        # Collect nodes
        node_map = {n.full_path: n for n in graph.nodes}
        result_nodes = [node_map[p] for p in visited_nodes if p in node_map]

        return LineageGraph(nodes=result_nodes, edges=collected_edges)

    def get_pii_flow_summary(self) -> Dict[str, List[str]]:
        """High-level summary of PII flow by category.

        Returns:
            Dict mapping category name to list of field full paths.
            Example: {"email": ["db.users.email", "kafka.events.email"]}
        """
        graph = self.get_graph()
        summary: Dict[str, List[str]] = {}

        for node in graph.nodes:
            for cat in node.categories:
                cat_name = cat.value
                summary.setdefault(cat_name, []).append(node.full_path)

        return summary

    def find_pii_sources(self) -> List[LineageNode]:
        """Find origin nodes (no upstream edges) that contain PII.

        Returns:
            List of PII nodes with no incoming edges.
        """
        graph = self.get_graph()
        has_incoming = {e.target.full_path for e in graph.edges}

        return [n for n in graph.nodes if n.categories and n.full_path not in has_incoming]

    def find_pii_sinks(self) -> List[LineageNode]:
        """Find terminal nodes (no downstream edges) that contain PII.

        Returns:
            List of PII nodes with no outgoing edges.
        """
        graph = self.get_graph()
        has_outgoing = {e.source.full_path for e in graph.edges}

        return [n for n in graph.nodes if n.categories and n.full_path not in has_outgoing]

    def annotate_with_inventory(self, inventory: DataInventory) -> None:
        """Update graph nodes with PII categories from inventory.

        Args:
            inventory: DataInventory to annotate from.
        """
        graph = self.get_graph()
        inv_map: Dict[str, Any] = {}

        for entry in inventory.entries:
            key = f"{entry.resource_name}.{entry.container_name}.{entry.field_name}"
            inv_map[key] = entry

        for node in graph.nodes:
            entry = inv_map.get(node.full_path)
            if entry is not None:
                node.categories = list(entry.categories)
                node.confidence = entry.confidence

    def to_dict(self) -> Dict[str, Any]:
        """Export graph as JSON-serializable dict.

        Format compatible with D3.js force-directed graph visualization.

        Returns:
            Dict with "nodes" and "edges" lists.
        """
        graph = self.get_graph()

        nodes = []
        for node in graph.nodes:
            nodes.append(
                {
                    "id": node.full_path,
                    "resource": node.resource_name,
                    "field": node.field_qualified_name,
                    "categories": [c.value for c in node.categories],
                    "confidence": node.confidence.value,
                    "has_pii": bool(node.categories),
                }
            )

        edges = []
        for edge in graph.edges:
            edges.append(
                {
                    "source": edge.source.full_path,
                    "target": edge.target.full_path,
                    "type": edge.relationship_type.value,
                    "metadata": edge.metadata,
                }
            )

        return {"nodes": nodes, "edges": edges}

    def to_mermaid(self) -> str:
        """Export graph as Mermaid diagram text.

        Returns:
            Mermaid flowchart string.
        """
        graph = self.get_graph()
        lines = ["graph LR"]

        # Define nodes
        node_ids: Dict[str, str] = {}
        for i, node in enumerate(graph.nodes):
            node_id = f"N{i}"
            node_ids[node.full_path] = node_id
            label = node.full_path.replace('"', "'")
            if node.categories:
                cats = ",".join(c.value for c in node.categories)
                lines.append(f'    {node_id}["{label}<br/>[{cats}]"]')
            else:
                lines.append(f'    {node_id}["{label}"]')

        # Define edges
        for edge in graph.edges:
            src_id = node_ids.get(edge.source.full_path, "?")
            tgt_id = node_ids.get(edge.target.full_path, "?")
            edge_label = edge.relationship_type.value
            lines.append(f"    {src_id} -->|{edge_label}| {tgt_id}")

        # Style PII nodes
        pii_node_ids = [
            node_ids[n.full_path] for n in graph.nodes if n.categories and n.full_path in node_ids
        ]
        if pii_node_ids:
            ids_str = ",".join(pii_node_ids)
            lines.append(f"    style {ids_str} fill:#ffcccc,stroke:#cc0000")

        return "\n".join(lines)

    # ── Internal helpers ──

    def _bfs_traverse(
        self,
        graph: LineageGraph,
        start: LineageNode,
        direction: str,
        max_depth: int,
        visited: Set[str],
        collected_edges: List[LineageEdge],
    ) -> None:
        """BFS traversal in the specified direction."""
        queue: deque = deque()
        queue.append((start, 0))
        seen: Set[str] = {start.full_path}

        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue

            if direction == "upstream":
                edges = graph.get_upstream(current)
                next_nodes = [e.source for e in edges]
            else:
                edges = graph.get_downstream(current)
                next_nodes = [e.target for e in edges]

            for edge in edges:
                collected_edges.append(edge)

            for next_node in next_nodes:
                if next_node.full_path not in seen:
                    seen.add(next_node.full_path)
                    visited.add(next_node.full_path)
                    queue.append((next_node, depth + 1))

    def _infer_cross_resource_links(
        self,
        node_map: Dict[str, LineageNode],
        existing_edges: List[LineageEdge],
    ) -> List[LineageEdge]:
        """Infer implicit cross-resource links.

        When two fields in different resources share the same field name
        AND the same detected PII category, create a tentative edge.

        Returns:
            List of inferred edges.
        """
        # Build index: field_base_name -> [nodes with PII]
        field_index: Dict[str, List[LineageNode]] = {}
        for node in node_map.values():
            if not node.categories:
                continue
            # Extract just the field name (last part of qualified name)
            parts = node.field_qualified_name.split(".")
            field_name = parts[-1] if parts else ""
            if field_name:
                field_index.setdefault(field_name, []).append(node)

        # Track existing edges to avoid duplicates
        existing_pairs: Set[tuple] = set()
        for edge in existing_edges:
            existing_pairs.add((edge.source.full_path, edge.target.full_path))
            existing_pairs.add((edge.target.full_path, edge.source.full_path))

        inferred: List[LineageEdge] = []
        for field_name, nodes in field_index.items():
            if len(nodes) < 2:
                continue

            # Check pairs across different resources
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    node_a = nodes[i]
                    node_b = nodes[j]

                    # Only infer across different resources
                    if node_a.resource_name == node_b.resource_name:
                        continue

                    # Check for shared PII categories
                    cats_a = set(c.value for c in node_a.categories)
                    cats_b = set(c.value for c in node_b.categories)
                    shared_cats = cats_a & cats_b

                    if not shared_cats:
                        continue

                    # Skip if edge already exists
                    pair = (node_a.full_path, node_b.full_path)
                    if pair in existing_pairs:
                        continue
                    existing_pairs.add(pair)
                    existing_pairs.add((node_b.full_path, node_a.full_path))

                    inferred.append(
                        LineageEdge(
                            source=node_a,
                            target=node_b,
                            relationship_type=RelationshipType.MANUAL,
                            metadata={
                                "inferred": True,
                                "shared_field": field_name,
                                "shared_categories": sorted(shared_cats),
                            },
                        )
                    )

        if inferred:
            logger.info(f"Inferred {len(inferred)} cross-resource links")

        return inferred
