<p align="center">
  <img src="images/Data%20Detector.png" alt="Data Detector Logo" width="200">
</p>

# Data Detector

**Data Detector** is a high-performance engine for detecting, redacting, and generating sensitive data (PII).

## The purpose behind the development

"To be honest, data privacy wasn't exactly on my radar. But that changed when I started experimenting with RAG on a local LLM. I realized that using a personal AI agent could accidentally expose sensitive info. That 'aha' moment led me to build Data Detector. I really hope this tool helps keep people's data safe."

## Installation

```bash
pip install data-detector
```

For more options, see the [Installation Guide](docs/installation.md).

### Troubleshooting Submodules

If you cloned the repository without submodules or downloaded the auto-generated GitHub source zip, you may encounter errors like:
- `ModuleNotFoundError: No module named 'verification'`
- `FileNotFoundError: Pattern directory not found: .../pattern-engine/...`

**To fix this:**

1.  **If using Git**: Run the following command in the project root:
    ```bash
    git submodule update --init --recursive
    ```
2.  **If using GitHub Releases**: Do **not** use the default "Source code (zip/tar.gz)" files. Instead, download the **`data-detector-<version>-full.tar.gz`** asset which includes all submodule content.
3.  **If using Docker**: Ensure you have checked out submodules before building. The included `Dockerfile` is pre-configured to handle the necessary internal paths and symlinks.

## Quick Start

### Library Usage

```python
from datadetector import Engine, load_registry

# Load patterns and initialize engine
registry = load_registry()
engine = Engine(registry)

# Find PII
results = engine.find("My phone: 010-1234-5678")

# Redact text
redacted = engine.redact("Contact me at test@example.com")
print(redacted.redacted_text)
```

### NLP-Enhanced Detection (Korean, Chinese, Japanese)

For improved CJK PII detection with particle handling and word segmentation:

```python
from datadetector import Engine, load_registry, NLPConfig

# Configure NLP for CJK processing
nlp_config = NLPConfig(
    enable_language_detection=True,
    enable_korean_particles=True,
    enable_chinese_segmentation=True,
    enable_japanese_segmentation=True
)

registry = load_registry()
engine = Engine(registry, nlp_config=nlp_config)

# Detects PII even with particles or without spaces
text = "私の電話번호는 090-1234-5678입니다"
results = engine.find(text, namespaces=["jp", "kr"])
```

### Detection Process Steps

Here is how the engine processes text, illustrated with a Korean example:

1.  **Original Text**: `제 이름은 마크이고 전화번호는 010-1234-5678입니다.`
2.  **Tokenization**: `['제', '이름', '은', '마크', '이고', '전화번호', '는', '010-1234-5678', '입니다']`
    *   *The text is split into meaningful units (morphemes/words).*
3.  **No-word (Stopword Filtering)**: `이름 마크 전화번호 010-1234-5678`
    *   *Particles (은, 는, 이고, 입니다) are removed to isolate the data.*
4.  **Regex Matching**: `010-1234-5678`
    *   *The pattern is now clearly visible and matched.*
5.  **Verification**: `Data Check (Valid)`
    *   *The extracted number is verified against format rules.*

Install NLP dependencies:
```bash
pip install data-detector[nlp]
```

See [NLP Features Documentation](docs/nlp-features.md) for more details.

### Resource Scanning: Search > Inventory > Lineage

Data Detector provides a three-stage pipeline for securing structured data resources. Each stage can be used independently or linked together:

**Stage 1: Search for Security Information** → **Stage 2: Create Security Inventory** → **Stage 3: Security Data Lineage**

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Stage 1        │     │  Stage 2        │     │  Stage 3        │
│  Data Explorer  │────▶│  Inventory      │────▶│  Lineage        │
│                 │     │  Generator      │     │  Tracer         │
│  Scan DB, Kafka,│     │                 │     │                 │
│  API, Files,    │     │  Create PII     │     │  Trace how PII  │
│  VectorDB, AI   │     │                 │     │                 │
│  sensitive data │     │  catalog &      │     │  flows across   │
│                 │     │  export reports │     │  resources      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
   ResourceScanResult ──────▶ DataInventory ──────▶ LineageGraph
   (shared interface)
```

Each stage produces its own output and can be used alone:
- **Stage 1 only**: Just scan for sensitive data
- **Stage 1 + 2**: Scan and generate an inventory report
- **Stage 1 + 3**: Scan and trace data lineage
- **Stage 1 + 2 + 3**: Full pipeline

#### Stage 1: Search for Security Information

```python
from datadetector import Engine, load_registry, DataExplorer
from datadetector import DataResource, ResourceType, ConnectionConfig
from datadetector.adapters.database import DatabaseAdapter

registry = load_registry()
engine = Engine(registry)
explorer = DataExplorer(engine)

resource = DataResource(
    name="my-db",
    resource_type=ResourceType.DATABASE,
    connection=ConnectionConfig(uri="postgresql://user:pass@localhost/mydb"),
)

with DatabaseAdapter(resource) as adapter:
    result = explorer.scan(adapter)
    print(f"Found {result.pii_fields} PII fields in {result.pii_containers} tables")
```

Supported resources: **Database** (SQLAlchemy), **Kafka** (Schema Registry), **REST API** (OpenAPI), **File Storage** (CSV/JSON/Parquet/Excel), **Vector DB** (ChromaDB), **Training Data** (JSONL/HuggingFace)

#### Stage 2: Create Security Inventory

```python
from datadetector import DataInventoryGenerator, InventoryFormat

gen = DataInventoryGenerator()
gen.add_scan_result(result)        # From Stage 1
inventory = gen.generate()

# Export as HTML report, JSON, CSV, or YAML
gen.export(inventory, InventoryFormat.HTML, output=open("report.html", "w"))

# Compare inventories over time
diff = DataInventoryGenerator.diff(old_inventory, inventory)
print(f"New PII: {len(diff.added)}, Removed: {len(diff.removed)}")
```

#### Stage 3: Security Data Lineage

```python
from datadetector import DataLineageTracer

tracer = DataLineageTracer()
tracer.add_scan_result(db_result, db_adapter)     # DB with FK discovery
tracer.add_scan_result(kafka_result)               # Kafka topics

# Link fields across resources
tracer.add_cross_resource_link(
    "my-db", "users.email",
    "my-kafka", "user-events.email",
)

graph = tracer.build_graph()
print(tracer.to_mermaid())         # Visualize PII flow as diagram
```

Install resource adapter dependencies:
```bash
pip install data-detector[database]       # SQLAlchemy for DB scanning
pip install data-detector[kafka]          # Kafka + Schema Registry
pip install data-detector[file-storage]   # Parquet, Excel support
pip install data-detector[vector-db]      # ChromaDB for vector store scanning
pip install data-detector[training-data]  # HuggingFace datasets scanning
pip install data-detector[resources]      # All resource adapters
```

See [Resource Scanning Guide](docs/guides/resource-scanning.md) for more details.

### CLI Usage

```bash
# Find PII in text
data-detector find --text "010-1234-5678" --ns kr

# Redact a file
data-detector redact --in input.log --out redacted.log

# Start a REST API server
data-detector serve --port 8080
```

## CLI Commands & Options

| Command | Description | Key Options |
| :--- | :--- | :--- |
| `find` | Search for PII in text or files. | `--text`, `--in`, `--ns` (namespace) |
| `redact` | Mask or tokenize sensitive data. | `--in`, `--out`, `--format` |
| `validate` | Validate text against a pattern. | `--text`, `--pattern-id` |
| `list-patterns`| Show all available PII patterns. | `--ns`, `--category` |
| `serve` | Run as an HTTP/gRPC server. | `--port`, `--host`, `--workers` |

Use `data-detector --help` for a full list of options.

## Chrome Extension

Monitor PII in real-time as you browse with the **PII Detector Chrome Extension**. It uses a hybrid approach combining fast client-side pattern matching with the Data-Detector API for accurate verification.

### Features

- **Multi-Source Monitoring**: Detect PII in form inputs, page content, and network requests
- **Real-Time Alerts**: Visual highlights and notifications when PII is detected
- **Privacy-Preserving**: Never stores actual PII values, only metadata
- **Hybrid Detection**: Fast client-side matching with API verification for accuracy
- **Offline Fallback**: Continues working even when API is unavailable

### Quick Setup

1. **Start the API Server**:
   ```bash
   data-detector serve --port 8080
   ```

2. **Load the Extension**:
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked" and select the `chrome-extension` directory

3. **Configure Settings**:
   - Click the extension icon
   - Go to Settings
   - Verify API endpoint is `http://localhost:8080`
   - Select namespaces (e.g., `comm`, `us`, `kr`)

For detailed instructions, architecture, and troubleshooting, see the [Chrome Extension README](chrome-extension/README.md).

## Documentation

For detailed guides and references, please see the following:

- **Guides**: [Quick Start](docs/quickstart.md) | [Architecture](docs/ARCHITECTURE.md) | [Configuration](docs/configuration.md)
- **Patterns**: [Supported Patterns](docs/supported-patterns.md) | [Custom Patterns](docs/custom-patterns.md) | [Pattern Structure](docs/patterns.md)
- **Features**: [NLP Processing](docs/nlp-features.md) | [Resource Scanning](docs/guides/resource-scanning.md) | [Fake Data Generation](docs/yaml_utilities.md) | [RAG Security](docs/rag-integration.md) | [Verification Functions](docs/verification.md)
- **API**: [API Reference](docs/api-reference.md)

## CI/CD Integration

Data Detector can be integrated into your CI/CD pipeline to automatically block PII leaks.

- **Guide**: [CI/CD Integration Guide](docs/guides/cicd-integration.md)
- **Example Script**: [examples/cicd_scan.sh](examples/cicd_scan.sh)

```bash
# Example: Fail build if PII is found in changed files
data-detector find --file "changed_file.py" --on-match exit
```

## License

Apache License 2.0 - see [LICENSE](LICENSE) file for details.