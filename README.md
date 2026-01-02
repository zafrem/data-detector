<p align="center">
  <img src="images/Data%20Detector.png" alt="Data Detector Logo" width="200">
</p>

# Data Detector

**Data Detector** is a high-performance engine for detecting, redacting, and generating sensitive data (PII).

## Installation

```bash
pip install data-detector
```

For more options, see the [Installation Guide](docs/installation.md).

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

### NLP-Enhanced Detection (Korean)

For improved Korean PII detection with grammatical particle handling:

```python
from datadetector import Engine, load_registry, NLPConfig

# Configure NLP for Korean particle processing
nlp_config = NLPConfig(
    enable_language_detection=True,
    enable_korean_particles=True
)

registry = load_registry()
engine = Engine(registry, nlp_config=nlp_config)

# Detects PII even with Korean particles attached
text = "전화번호는 010-1234-5678은 입니다"
results = engine.find(text, namespaces=["kr"])
```

Install NLP dependencies:
```bash
pip install data-detector[nlp]
```

See [NLP Features Documentation](docs/nlp-features.md) for more details.

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

## Documentation

For detailed guides and references, please see the following:

- **Guides**: [Quick Start](docs/quickstart.md) | [Architecture](docs/ARCHITECTURE.md) | [Configuration](docs/configuration.md)
- **Patterns**: [Supported Patterns](docs/supported-patterns.md) | [Custom Patterns](docs/custom-patterns.md) | [Pattern Structure](docs/patterns.md)
- **Features**: [NLP Processing](docs/nlp-features.md) | [Fake Data Generation](docs/yaml_utilities.md) | [RAG Security](docs/rag-integration.md) | [Verification Functions](docs/verification.md)
- **API**: [API Reference](docs/api-reference.md)

## License

MIT License - see [LICENSE](LICENSE) file for details.