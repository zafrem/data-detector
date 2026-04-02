"""Kafka adapter using Schema Registry for metadata and consumer for sampling.

Supports Avro and JSON Schema via Schema Registry, with fallback to
raw message sampling when Schema Registry is not available.

Install: pip install data-detector[kafka]
"""

import json
import logging
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


def _get_confluent_kafka() -> Any:
    """Lazy-load confluent_kafka."""
    try:
        import confluent_kafka

        return confluent_kafka
    except ImportError:
        raise ImportError(
            "confluent-kafka is required for Kafka scanning. "
            "Install with: pip install data-detector[kafka]"
        )


def _get_requests() -> Any:
    """Lazy-load requests."""
    try:
        import requests

        return requests
    except ImportError:
        raise ImportError(
            "requests is required for Kafka Schema Registry access. "
            "Install with: pip install data-detector[kafka]"
        )


class KafkaAdapter(ResourceAdapter):
    """Kafka adapter with Schema Registry + consumer support.

    ConnectionConfig usage:
        uri: Kafka bootstrap servers (e.g., "localhost:9092")
        params:
            schema_registry_url: Schema Registry URL (e.g., "http://localhost:8081")
            consumer_group: Consumer group ID (default: "datadetector-scanner")
            timeout_ms: Consumer poll timeout in ms (default: 5000)
            security_protocol: e.g., "SASL_SSL"
            sasl_mechanism: e.g., "PLAIN"
            sasl_username: SASL username
            sasl_password: SASL password

    Example:
        >>> resource = DataResource(
        ...     name="my-kafka",
        ...     resource_type=ResourceType.KAFKA,
        ...     connection=ConnectionConfig(
        ...         uri="localhost:9092",
        ...         params={"schema_registry_url": "http://localhost:8081"},
        ...     ),
        ... )
        >>> with KafkaAdapter(resource) as adapter:
        ...     topics = adapter.list_containers()
    """

    def __init__(self, resource: DataResource) -> None:
        super().__init__(resource)
        self._consumer: Optional[Any] = None
        self._admin_client: Optional[Any] = None
        self._schema_registry_url: Optional[str] = None
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._requests: Optional[Any] = None

    def connect(self) -> None:
        """Connect to Kafka and Schema Registry."""
        ck = _get_confluent_kafka()
        self._requests = _get_requests()

        bootstrap_servers = self.resource.connection.uri
        if not bootstrap_servers:
            raise ConnectionError("Kafka bootstrap servers URI is required.")

        params = self.resource.connection.params
        self._schema_registry_url = params.get("schema_registry_url")

        # Build consumer config
        consumer_config: Dict[str, Any] = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": params.get("consumer_group", "datadetector-scanner"),
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
        }

        # Security settings
        if params.get("security_protocol"):
            consumer_config["security.protocol"] = params["security_protocol"]
        if params.get("sasl_mechanism"):
            consumer_config["sasl.mechanism"] = params["sasl_mechanism"]
        if params.get("sasl_username"):
            consumer_config["sasl.username"] = params["sasl_username"]
        if params.get("sasl_password"):
            consumer_config["sasl.password"] = params["sasl_password"]

        try:
            self._consumer = ck.Consumer(consumer_config)
            self._admin_client = ck.admin.AdminClient({"bootstrap.servers": bootstrap_servers})
            self._connected = True
            logger.info(f"Connected to Kafka: {self.resource.name}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Kafka '{self.resource.name}': {e}") from e

    def close(self) -> None:
        """Close consumer connection."""
        if self._consumer is not None:
            self._consumer.close()
            self._consumer = None
        self._admin_client = None
        self._connected = False
        logger.info(f"Disconnected from Kafka: {self.resource.name}")

    def list_containers(
        self,
        pattern: Optional[str] = None,
    ) -> List[ContainerInfo]:
        """List Kafka topics.

        Uses Schema Registry subjects if available, otherwise lists
        topics from the admin client.

        Args:
            pattern: Optional glob pattern to filter topic names.

        Returns:
            List of ContainerInfo for each topic.
        """
        self._ensure_connected()
        import fnmatch

        topics: List[ContainerInfo] = []

        # Try Schema Registry first
        if self._schema_registry_url:
            try:
                subjects = self._get_sr_subjects()
                # Extract topic names from subjects (format: "topic-value" or "topic-key")
                seen_topics: set = set()
                for subject in subjects:
                    topic = subject
                    for suffix in ("-value", "-key"):
                        if subject.endswith(suffix):
                            topic = subject[: -len(suffix)]
                            break
                    if topic not in seen_topics:
                        seen_topics.add(topic)
                        if pattern and not fnmatch.fnmatch(topic, pattern):
                            continue
                        topics.append(
                            ContainerInfo(
                                name=topic,
                                container_type=ContainerType.TOPIC,
                                metadata={"has_schema": True},
                            )
                        )
                return topics
            except Exception as e:
                logger.warning(f"Schema Registry unavailable, falling back to admin: {e}")

        # Fallback: list topics from admin client
        if self._admin_client:
            metadata = self._admin_client.list_topics(timeout=10)
            for topic_name in metadata.topics:
                if topic_name.startswith("_"):
                    continue  # Skip internal topics
                if pattern and not fnmatch.fnmatch(topic_name, pattern):
                    continue
                partitions = metadata.topics[topic_name].partitions
                topics.append(
                    ContainerInfo(
                        name=topic_name,
                        container_type=ContainerType.TOPIC,
                        metadata={
                            "has_schema": False,
                            "partition_count": len(partitions),
                        },
                    )
                )

        return topics

    def list_fields(self, container_name: str) -> List[FieldInfo]:
        """List fields from the topic's schema.

        Fetches schema from Schema Registry and flattens to field list.
        If no schema is available, returns empty list.

        Args:
            container_name: Topic name.

        Returns:
            List of FieldInfo objects.
        """
        self._ensure_connected()

        schema = self._get_topic_schema(container_name)
        if schema is None:
            logger.warning(f"No schema found for topic '{container_name}'")
            return []

        return self._flatten_schema(schema, container_name)

    def sample_values(
        self,
        container_name: str,
        field_name: str,
        limit: int = 100,
    ) -> List[str]:
        """Consume messages and extract field values.

        Args:
            container_name: Topic name.
            field_name: Field name (supports dot notation for nested fields).
            limit: Maximum number of values to sample.

        Returns:
            List of string-coerced values.
        """
        self._ensure_connected()

        timeout_ms = self.resource.connection.params.get("timeout_ms", 5000)
        timeout_s = timeout_ms / 1000.0

        ck = _get_confluent_kafka()

        # Assign partition(s) and seek to recent offsets
        topic_partitions = self._consumer.list_topics(container_name).topics
        if container_name not in topic_partitions:
            return []

        partitions = topic_partitions[container_name].partitions
        tp_list = [ck.TopicPartition(container_name, p, ck.OFFSET_END) for p in partitions]

        # Seek back by `limit` messages per partition
        offsets = self._consumer.offsets_for_times(tp_list, timeout=timeout_s)
        for tp in offsets:
            if tp.offset > limit:
                tp.offset = tp.offset - limit
            else:
                tp.offset = 0

        self._consumer.assign(offsets)

        values: List[str] = []
        empty_polls = 0
        max_empty_polls = 3

        while len(values) < limit and empty_polls < max_empty_polls:
            msg = self._consumer.poll(timeout=timeout_s)
            if msg is None or msg.error():
                empty_polls += 1
                continue
            empty_polls = 0

            try:
                payload = json.loads(msg.value().decode("utf-8"))
                val = self._extract_nested_field(payload, field_name)
                if val is not None:
                    values.append(str(val))
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                continue

        self._consumer.unassign()
        return values

    def get_relationships(self) -> List[FieldRelationship]:
        """Detect shared schema fields across topics.

        Two topics sharing a field with the same name and compatible type
        suggests a data flow relationship.

        Returns:
            List of FieldRelationship objects.
        """
        self._ensure_connected()

        # Build field map: field_name -> [(topic, field_info)]
        field_map: Dict[str, List[tuple]] = {}
        containers = self.list_containers()

        for container in containers:
            fields = self.list_fields(container.name)
            for f in fields:
                field_map.setdefault(f.name, []).append((container.name, f))

        relationships: List[FieldRelationship] = []
        for field_name, field_list in field_map.items():
            if len(field_list) < 2:
                continue
            # Create relationships between topics sharing the same field
            for i in range(len(field_list)):
                for j in range(i + 1, len(field_list)):
                    topic_a, field_a = field_list[i]
                    topic_b, field_b = field_list[j]
                    if field_a.data_type == field_b.data_type:
                        relationships.append(
                            FieldRelationship(
                                source_resource=self.resource.name,
                                source_field=f"{topic_a}.{field_name}",
                                target_resource=self.resource.name,
                                target_field=f"{topic_b}.{field_name}",
                                relationship_type=RelationshipType.TOPIC_LINK,
                                metadata={"shared_field": field_name},
                            )
                        )

        return relationships

    # ── Schema Registry helpers ──

    def _get_sr_subjects(self) -> List[str]:
        """Get all subjects from Schema Registry."""
        if not self._schema_registry_url or not self._requests:
            return []
        resp = self._requests.get(f"{self._schema_registry_url}/subjects", timeout=10)
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    def _get_topic_schema(self, topic: str) -> Optional[Dict[str, Any]]:
        """Fetch and cache schema for a topic from Schema Registry."""
        if topic in self._schemas:
            return self._schemas[topic]

        if not self._schema_registry_url or not self._requests:
            return None

        # Try value schema first, then key schema
        for suffix in ("-value", "-key"):
            subject = f"{topic}{suffix}"
            try:
                resp = self._requests.get(
                    f"{self._schema_registry_url}/subjects/{subject}/versions/latest",
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    schema_str = data.get("schema", "{}")
                    schema = json.loads(schema_str)
                    self._schemas[topic] = schema
                    return schema
            except Exception as e:
                logger.debug(f"Could not fetch schema for {subject}: {e}")

        return None

    def _flatten_schema(
        self,
        schema: Dict[str, Any],
        container_name: str,
        prefix: str = "",
    ) -> List[FieldInfo]:
        """Flatten an Avro or JSON schema into FieldInfo list."""
        fields: List[FieldInfo] = []

        # Avro schema format
        if schema.get("type") == "record" and "fields" in schema:
            for f in schema["fields"]:
                field_name = f"{prefix}{f['name']}" if not prefix else f"{prefix}.{f['name']}"
                avro_type = f.get("type", "unknown")
                if isinstance(avro_type, list):
                    # Union type: pick the non-null type
                    avro_type = [t for t in avro_type if t != "null"]
                    avro_type = avro_type[0] if avro_type else "unknown"
                if isinstance(avro_type, dict) and avro_type.get("type") == "record":
                    # Nested record: recurse
                    fields.extend(self._flatten_schema(avro_type, container_name, field_name))
                else:
                    fields.append(
                        FieldInfo(
                            name=field_name,
                            container_name=container_name,
                            data_type=str(avro_type),
                            nullable="null"
                            in (f.get("type") if isinstance(f.get("type"), list) else []),
                            description=f.get("doc", ""),
                        )
                    )

        # JSON Schema format
        elif "properties" in schema:
            required = set(schema.get("required", []))
            for prop_name, prop_schema in schema["properties"].items():
                field_name = f"{prefix}{prop_name}" if not prefix else f"{prefix}.{prop_name}"
                prop_type = prop_schema.get("type", "unknown")
                if prop_type == "object" and "properties" in prop_schema:
                    fields.extend(self._flatten_schema(prop_schema, container_name, field_name))
                else:
                    fields.append(
                        FieldInfo(
                            name=field_name,
                            container_name=container_name,
                            data_type=str(prop_type),
                            nullable=prop_name not in required,
                            description=prop_schema.get("description", ""),
                        )
                    )

        return fields

    @staticmethod
    def _extract_nested_field(data: Dict[str, Any], field_name: str) -> Any:
        """Extract a field value using dot notation."""
        parts = field_name.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current
