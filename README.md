# Data Detector

**data-detector** is a general-purpose engine that detects and masks personal information (mobile phone numbers, social security numbers, email addresses, etc.) by **country and information type**, using a "pattern file-based + library + daemon (server)."

## Features

- 🌍 **Global Support**: Patterns organized by country (ISO2) and information type
- 🔍 **Detection**: Find PII in text using multiple patterns
- ✅ **Validation**: Validate text against specific patterns with optional verification functions
- 🔒 **Redaction**: Mask, hash, or tokenize sensitive information
- 🚀 **Multiple Interfaces**: Library API, CLI, and HTTP/gRPC server
- ⚡ **High Performance**: p95 < 10ms for 1KB text (single namespace)
- 🔄 **Hot Reload**: Non-disruptive pattern reloading
- 📊 **Observability**: Prometheus metrics and health checks

## Quick Start
### Clone repository
```bash
git clone https://github.com/data-detector.git
```

### Installation

```bash
pip install data-detector
```

See [Installation Guide](docs/installation.md) for more options.

### Library Usage

```python
from datadetector import Engine, load_registry

# Load patterns from directory
registry = load_registry(paths=["patterns/"])
engine = Engine(registry)

# Validate
is_valid = engine.validate("010-1234-5678", "kr/mobile_01")

# Find PII (searches all loaded patterns)
results = engine.find("My phone: 01012345678, email: test@example.com")

# Redact
redacted = engine.redact("SSN: 900101-1234567", namespaces=["kr"])
print(redacted.redacted_text)
```

### YAML Pattern Management

Create and manage pattern files programmatically:

```python
from datadetector import PatternFileHandler

# Create a new pattern file
PatternFileHandler.create_pattern_file(
    file_path="custom_patterns.yml",
    namespace="custom",
    description="My custom patterns",
    patterns=[{
        "id": "api_key_01",
        "location": "custom",
        "category": "token",
        "pattern": r"API-[A-Z0-9]{32}",
        "mask": "API-" + "*" * 32,
        "policy": {
            "store_raw": False,
            "action_on_match": "redact",
            "severity": "critical"
        }
    }]
)

# Add, update, or remove patterns
PatternFileHandler.add_pattern_to_file("custom_patterns.yml", new_pattern)
PatternFileHandler.update_pattern_in_file("custom_patterns.yml", "api_key_01", {...})
PatternFileHandler.remove_pattern_from_file("custom_patterns.yml", "api_key_01")
```

See [YAML Utilities Documentation](docs/yaml_utilities.md) for complete guide.

### Pattern Restoration Utility

The `tokens.yml` pattern file may use modified patterns (with `rk_` prefix) during development to avoid triggering GitHub's push protection. Use the restoration utility to convert these back to real-world Stripe API key patterns:

```bash
# After installing via pip
data-detector-restore-tokens

# Or run directly
python restore_tokens.py

# Or as a module
python -m datadetector.restore_tokens
```

**What it does:**
- Converts fake `rk_(live|test)_` patterns to real `[sp]k_(live|test)_` Stripe patterns
- Updates examples to use proper `sk_test_`, `sk_live_`, `pk_test_` prefixes
- Uses obviously fake example keys to avoid secret scanner detection

**Security Note:** All examples use FAKE keys like "EXAMPLEKEY" for security scanner compatibility. This is a defensive security tool - the patterns help detect real leaked credentials.

### CLI Usage

```bash
# Find PII
data-detector find --text "010-1234-5678" --ns kr

# Redact PII
data-detector redact --in input.log --out redacted.log --ns kr us

# Start server
data-detector serve --port 8080
```

### REST API

```bash
# Start server
data-detector serve --port 8080

# Find PII
curl -X POST http://localhost:8080/find \
  -H "Content-Type: application/json" \
  -d '{"text": "010-1234-5678", "namespaces": ["kr"]}'
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System architecture and design overview
- [Quick Start Guide](docs/quickstart.md) - Get started quickly
- [Pattern Structure](docs/patterns.md) - Learn about pattern definitions
- [Custom Patterns](docs/custom-patterns.md) - Create your own patterns
- [YAML Utilities](docs/yaml_utilities.md) - **NEW!** Programmatically create and manage pattern files
- [Verification Functions](docs/verification.md) - Add custom validation logic
- [Configuration](docs/configuration.md) - Server and registry configuration
- [API Reference](docs/api-reference.md) - Complete API documentation
- [Supported Patterns](docs/supported-patterns.md) - Built-in pattern catalog
- [Testing](TESTING.md) - Test suite documentation and coverage

## Supported Pattern Types

- 📱 Phone numbers (KR, US, TW, JP, CN, IN)
- 🆔 National IDs (SSN, RRN, Aadhaar, etc.)
- 📧 Email addresses
- 🏦 Bank accounts & IBANs (with Mod-97 verification)
- 💳 Credit cards (Visa, MasterCard, Amex, etc.)
- 🛂 Passport numbers
- 📍 Physical addresses
- 🌐 IP addresses & URLs

**Total**: 60+ patterns across 7 locations (Common, KR, US, TW, JP, CN, IN)

See [Supported Patterns](docs/supported-patterns.md) for the complete list.

## Verification Functions

Patterns can include verification functions for additional validation beyond regex:

```yaml
- id: iban_01
  category: iban
  pattern: '[A-Z]{2}\d{2}[A-Z0-9]{11,30}'
  verification: iban_mod97  # Validates IBAN checksum
```

Built-in verification functions:
- `iban_mod97` - IBAN Mod-97 checksum validation
- `luhn` - Luhn algorithm for credit cards

You can also register custom verification functions. See [Verification Functions](docs/verification.md) for details.

## Performance

- **Latency**: p95 < 10ms for 1KB text with single namespace
- **Throughput**: 500+ RPS on 1 vCPU, 512MB RAM
- **Scalability**: Handles 1k+ patterns and 1k+ concurrent requests

## Security & Privacy

- No raw PII is logged (only hashes/metadata)
- TLS support for server
- Configurable rate limiting
- GDPR/CCPA compliant operations

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ tests/
ruff check src/ tests/

# Validate patterns
python -c "from datadetector import load_registry; load_registry(validate_examples=True)"
```

## Docker

```bash
# Build
docker build -t data-detector:latest .

# Run
docker run -p 8080:8080 -v ./patterns:/app/patterns data-detector:latest
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

## Support

- 📖 [Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/yourusername/data-detector/issues)
- 💬 [Discussions](https://github.com/yourusername/data-detector/discussions)


# Next Step
- Pattern Expansion: Support for additional countries like the EU, the UK, Canada, and Australia, as well as new PII types like Social Security Numbers, Vehicle Numbers, and Driver's License Numbers, will expand the usability of the pattern. Enhance the contribution guidelines to facilitate pattern additions by the community.

- Web UI/Test Tool: Currently, text must be submitted via the CLI or gRPC. Providing a UI that allows users to directly input patterns and view results, such as a web-based demo or a VS Code extension, will improve the user experience.

- Asynchronous/Streaming API: Adding an asyncio-based asynchronous API for high-speed log processing or data pipeline integration, or providing Kafka/Flink connectors, will facilitate application to large-scale systems.

- Automated Pattern Management: Maintaining the pattern catalog in a remote repository and implementing version control to automatically deploy pattern updates will improve operational convenience. Strictly defining the pattern format as a JSON schema will help prevent errors.

- Other Language Bindings: While gRPC allows calls from various languages, providing wrapper libraries for Node.js and Java would increase developer adoption.

- Monitoring and Deployment: In addition to the performance metrics presented in the README, adding benchmarks measuring memory usage and parallel processing performance in real environments, along with Kubernetes/Helm deployment examples and CI processes, would facilitate adoption by operations teams.
