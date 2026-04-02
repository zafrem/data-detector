# Resource Scanning Guide

Data Detector can scan structured data resources for PII using a three-component system:

1. **Data Explorer** — Scan any resource (database, Kafka, API, files, vector DBs, AI training data) for PII
2. **Data Inventory Generator** — Create PII catalogs, export reports, compare changes
3. **Data Lineage Tracer** — Map PII flow within and across resources

## Installation

Install the adapter dependencies for your resource types:

```bash
pip install data-detector[database]       # SQLAlchemy (PostgreSQL, MySQL, SQLite, etc.)
pip install data-detector[kafka]          # Kafka + Schema Registry
pip install data-detector[file-storage]   # Parquet + Excel support
pip install data-detector[vector-db]      # ChromaDB for vector store scanning
pip install data-detector[training-data]  # HuggingFace datasets scanning
pip install data-detector[resources]      # All of the above
```

The API adapter requires no extra dependencies (uses stdlib `json` and `pyyaml`).
The Training Data adapter's JSONL backend also requires no extra dependencies (uses stdlib `json`).

## Supported Resource Types

| Resource Type | Adapter | Containers | Fields |
|--------------|---------|-----------|--------|
| Database (RDBMS) | `DatabaseAdapter` | Tables, Views | Columns |
| Kafka | `KafkaAdapter` | Topics | Schema fields (Avro/JSON) |
| REST API | `APIAdapter` | Endpoints (METHOD /path) | Parameters, body fields |
| File Storage | `FileStorageAdapter` | Files (CSV, JSON, Parquet, Excel) | Columns/keys |
| Vector DB | `VectorDBAdapter` | Collections | Document text, metadata fields |
| Training Data | `TrainingDataAdapter` | Datasets/files | Instruction, prompt, chat message fields |

## Quick Start

### 1. Scan a Database

```python
from datadetector import Engine, load_registry, DataExplorer
from datadetector import DataResource, ResourceType, ConnectionConfig
from datadetector.adapters.database import DatabaseAdapter

# Setup
registry = load_registry()
engine = Engine(registry)
explorer = DataExplorer(engine)

# Define the resource
resource = DataResource(
    name="production-db",
    resource_type=ResourceType.DATABASE,
    connection=ConnectionConfig(uri="postgresql://user:pass@localhost/mydb"),
    owner="data-team",
    tags=["production"],
)

# Scan
with DatabaseAdapter(resource) as adapter:
    result = explorer.scan(adapter)

print(f"Scanned {result.total_fields} fields across {len(result.container_results)} tables")
print(f"Found PII in {result.pii_fields} fields ({result.pii_containers} tables)")

for cr in result.container_results:
    for fr in cr.field_results:
        if fr.pii_detected:
            print(f"  {cr.container.name}.{fr.field_info.name}: "
                  f"{fr.categories} (confidence: {fr.confidence.value})")
```

### 2. Scan Kafka Topics

```python
from datadetector import DataResource, ResourceType, ConnectionConfig
from datadetector.adapters.kafka import KafkaAdapter

resource = DataResource(
    name="event-stream",
    resource_type=ResourceType.KAFKA,
    connection=ConnectionConfig(
        uri="localhost:9092",
        params={
            "schema_registry_url": "http://localhost:8081",
            "consumer_group": "pii-scanner",
        },
    ),
)

with KafkaAdapter(resource) as adapter:
    result = explorer.scan(adapter)
```

### 3. Scan an OpenAPI Spec

```python
from datadetector import DataResource, ResourceType, ConnectionConfig
from datadetector.adapters.api import APIAdapter

resource = DataResource(
    name="user-api",
    resource_type=ResourceType.API,
    connection=ConnectionConfig(uri="./openapi.yaml"),
)

with APIAdapter(resource) as adapter:
    result = explorer.scan(adapter)
    # Each endpoint becomes a container (e.g., "GET /users", "POST /orders")
```

### 4. Scan Files (CSV, JSON, Parquet, Excel)

```python
from datadetector import DataResource, ResourceType, ConnectionConfig
from datadetector.adapters.file_storage import FileStorageAdapter

resource = DataResource(
    name="data-lake",
    resource_type=ResourceType.FILE_STORAGE,
    connection=ConnectionConfig(
        uri="/data/exports",
        params={"glob_pattern": "**/*.csv"},
    ),
)

with FileStorageAdapter(resource) as adapter:
    result = explorer.scan(adapter)
```

Supported file formats: `.csv`, `.tsv`, `.json`, `.jsonl`, `.ndjson`, `.parquet`, `.xlsx`, `.xls`

### 5. Scan a Vector Database (ChromaDB)

Scan document chunks and metadata stored in vector databases for PII that may have been ingested during RAG pipelines:

```python
from datadetector import DataResource, ResourceType, ConnectionConfig
from datadetector.adapters.vector_db import VectorDBAdapter

resource = DataResource(
    name="rag-store",
    resource_type=ResourceType.VECTOR_DB,
    connection=ConnectionConfig(
        uri="/path/to/chroma_data",  # Or "http://localhost:8000" for client mode
        params={"backend": "chromadb"},
    ),
)

with VectorDBAdapter(resource) as adapter:
    result = explorer.scan(adapter)
    # Each collection is a container; fields include "document" (text) and metadata.*
```

The adapter scans:
- **Document text** — the stored text chunks in each collection
- **Metadata fields** — auto-discovered from stored document metadata (e.g., `metadata.source`, `metadata.email`)

Connection parameters:
- `backend`: `"chromadb"` (default) or `"generic"` (dict-based for testing)
- `collection_pattern`: Optional glob to filter collections (e.g., `"user_*"`)
- `include_metadata`: Whether to scan metadata fields (default: `True`)
- `text_field`: Custom name for the document text field (default: `"document"`)

### 6. Scan AI Training Data

Scan instruction-tuning datasets, fine-tuning data, and prompt/completion logs for PII:

```python
from datadetector import DataResource, ResourceType, ConnectionConfig
from datadetector.adapters.training_data import TrainingDataAdapter

# Scan JSONL files (instruction-tuning, chat, prompt/completion formats)
resource = DataResource(
    name="finetune-data",
    resource_type=ResourceType.TRAINING_DATA,
    connection=ConnectionConfig(
        uri="/data/training/",
        params={"backend": "jsonl"},
    ),
)

with TrainingDataAdapter(resource) as adapter:
    result = explorer.scan(adapter)
    # Each .jsonl file is a container; fields are auto-detected from the data format
```

**Auto-detected formats:**

| Format | Detected Fields | Example Keys |
|--------|----------------|-------------|
| Instruction-tuning | `instruction`, `input`, `output` | Alpaca, Dolly |
| Prompt/Completion | `prompt`, `completion` | OpenAI fine-tuning |
| Chat (messages) | `messages.system.content`, `messages.user.content`, `messages.assistant.content` | ChatML, ShareGPT |
| Plain text | `text` | Pre-training data |

**HuggingFace datasets** (requires `pip install data-detector[training-data]`):

```python
resource = DataResource(
    name="hf-dataset",
    resource_type=ResourceType.TRAINING_DATA,
    connection=ConnectionConfig(
        uri="tatsu-lab/alpaca",  # HuggingFace dataset identifier
        params={
            "backend": "huggingface",
            "split": "train",
            "streaming": False,  # Set True for large datasets
        },
    ),
)

with TrainingDataAdapter(resource) as adapter:
    result = explorer.scan(adapter)
```

Connection parameters:
- `backend`: `"jsonl"` (default) or `"huggingface"`
- `glob`: File pattern for JSONL discovery (default: `"*.jsonl"`)
- `split`: HuggingFace dataset split (default: `"train"`)
- `max_file_size_mb`: Skip files larger than this (default: `500`)
- `streaming`: Use HuggingFace streaming mode for large datasets (default: `False`)

## Scan Strategies

Control how much work the scanner does:

```python
from datadetector import ScanStrategy

# Metadata only — fast, uses field names/types (no data access)
result = explorer.scan(adapter, strategy=ScanStrategy.METADATA_ONLY)

# Sample — default, metadata + sample values from each field
result = explorer.scan(adapter, strategy=ScanStrategy.SAMPLE)

# Full — comprehensive scan (adapter-specific)
result = explorer.scan(adapter, strategy=ScanStrategy.FULL)
```

## Scan Specific Containers

```python
# Only scan specific tables/topics/files
result = explorer.scan(adapter, containers=["users", "payments"])
```

## Tuning Detection

```python
explorer = DataExplorer(
    engine,
    sample_limit=200,           # Sample more values per field (default: 100)
    metadata_weight=0.3,        # Weight for field name analysis (default: 0.3)
    sample_weight=0.7,          # Weight for sample value analysis (default: 0.7)
    confidence_threshold=0.3,   # Minimum score to flag as PII (default: 0.3)
    namespaces=["us", "common"],# Only check US and common patterns
)
```

## Confidence Levels

The combined metadata + sample score maps to confidence levels:

| Score Range | Confidence | Meaning |
|------------|-----------|---------|
| >= 0.9 | `CONFIRMED` | Very high certainty — strong metadata + sample match |
| >= 0.7 | `HIGH` | High certainty |
| >= 0.5 | `MEDIUM` | Moderate certainty — review recommended |
| >= 0.2 | `LOW` | Low certainty — possible false positive |
| < 0.2 | `NONE` | Not PII |

## Progress Callbacks

Monitor scan progress in real-time:

```python
def on_scanned(container_result):
    name = container_result.container.name
    pii = container_result.pii_field_count
    print(f"Scanned {name}: {pii} PII fields found")

explorer = DataExplorer(engine, on_container_scanned=on_scanned)
result = explorer.scan(adapter)
```

## Data Inventory

Generate PII catalogs from scan results:

```python
from datadetector import DataInventoryGenerator, InventoryFormat

gen = DataInventoryGenerator()
gen.add_scan_result(db_result)
gen.add_scan_result(kafka_result)

inventory = gen.generate()
print(f"Total PII fields: {inventory.total_pii_fields}")

# Group by resource, category, or severity
by_resource = inventory.by_resource()
by_category = inventory.by_category()
by_severity = inventory.by_severity()
```

### Export Formats

```python
# JSON
json_str = gen.export(inventory, InventoryFormat.JSON)

# CSV
csv_str = gen.export(inventory, InventoryFormat.CSV)

# YAML
yaml_str = gen.export(inventory, InventoryFormat.YAML)

# HTML (self-contained report with severity-colored badges)
html_str = gen.export(inventory, InventoryFormat.HTML)

# Export to file
with open("inventory.html", "w") as f:
    gen.export(inventory, InventoryFormat.HTML, output=f)
```

### Inventory Diff

Compare inventories over time to detect changes:

```python
old_inventory = DataInventoryGenerator.load_json("inventory_v1.json")
new_inventory = gen.generate()

diff = DataInventoryGenerator.diff(old_inventory, new_inventory)
print(f"New PII fields: {len(diff.added)}")
print(f"Removed: {len(diff.removed)}")
print(f"Changed: {len(diff.changed)}")
```

### Summary

```python
summary = DataInventoryGenerator.summary(inventory)
# {
#   "total_pii_fields": 12,
#   "total_resources": 3,
#   "by_category": {"email": 4, "ssn": 2, ...},
#   "by_severity": {"critical": 2, "high": 5, ...},
#   "by_resource_type": {"database": 8, "kafka": 4},
# }
```

## Data Lineage

Trace how PII flows between fields and across resources:

```python
from datadetector import DataLineageTracer

tracer = DataLineageTracer()

# Add scan results (with adapter for automatic FK discovery)
tracer.add_scan_result(db_result, db_adapter)
tracer.add_scan_result(kafka_result)

# Add manual cross-resource links
tracer.add_cross_resource_link(
    "production-db", "users.email",
    "event-stream", "user-events.email",
)

# Build the graph
graph = tracer.build_graph()
print(f"Nodes: {len(graph.nodes)}, Edges: {len(graph.edges)}")
```

### PII Flow Summary

```python
summary = tracer.get_pii_flow_summary()
# {"email": ["production-db.users.email", "event-stream.user-events.email", ...]}
```

### Trace from a Field

```python
# Trace downstream — where does this PII go?
downstream = tracer.trace("production-db.users.email", direction="downstream")

# Trace upstream — where does this PII come from?
upstream = tracer.trace("event-stream.user-events.email", direction="upstream")

# Trace both directions
full = tracer.trace("production-db.users.email", direction="both", max_depth=5)
```

### Find Sources and Sinks

```python
sources = tracer.find_pii_sources()   # PII nodes with no incoming edges
sinks = tracer.find_pii_sinks()       # PII nodes with no outgoing edges
```

### Visualization

```python
# Mermaid diagram (paste into GitHub markdown, Notion, etc.)
mermaid = tracer.to_mermaid()
print(mermaid)
# graph LR
#   n0["production-db<br>users.email"]
#   n1["event-stream<br>user-events.email"]
#   n0 -->|manual| n1
#   style n0 fill:#ffcccc
#   style n1 fill:#ffcccc

# D3.js-compatible JSON
data = tracer.to_dict()
# {"nodes": [...], "edges": [...]}
```

### Annotate with Inventory

Enrich the lineage graph with inventory data:

```python
tracer.annotate_with_inventory(inventory)
graph = tracer.get_graph()
node = graph.get_node("production-db", "users.email")
print(node.categories)  # Updated from inventory
```

## Writing a Custom Adapter

Implement the `ResourceAdapter` interface to support new resource types:

```python
from datadetector.resource_adapter import ResourceAdapter
from datadetector.resource_models import ContainerInfo, FieldInfo, FieldRelationship

class MyCustomAdapter(ResourceAdapter):
    def connect(self):
        # Initialize connection
        self._connected = True

    def close(self):
        # Cleanup
        self._connected = False

    def list_containers(self, pattern=None):
        # Return list of ContainerInfo
        return [ContainerInfo(name="my_table", container_type=ContainerType.TABLE)]

    def list_fields(self, container_name):
        # Return list of FieldInfo for a container
        return [FieldInfo(name="email", container_name=container_name, data_type="VARCHAR")]

    def sample_values(self, container_name, field_name, limit=100):
        # Return sample string values for a field
        return ["user@example.com", "admin@test.org"]

    def get_relationships(self):
        # Optional: return foreign key / link relationships
        return []
```

## Error Handling

Scan errors are non-fatal by default. If a container or field fails, the error is recorded and scanning continues:

```python
result = explorer.scan(adapter)
if result.errors:
    for error in result.errors:
        print(f"Warning: {error}")
```
