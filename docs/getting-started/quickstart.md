# Quick Start Guide

This guide provides a brief overview of how to use Data Detector through its main interfaces: the Python library, the Command-Line Interface (CLI), and the REST API.

## Library API

The library is the most flexible way to integrate Data Detector into your Python applications.

```python
from datadetector import Engine, load_registry

# You can load patterns from specific files or an entire directory.
# Load patterns from specific files:
registry = load_registry(paths=["patterns/common.yml", "patterns/kr.yml"])
# Or load all patterns from a directory:
registry = load_registry(paths=["patterns/"])

engine = Engine(registry)

# Validate if a string matches a specific pattern
is_valid = engine.validate("010-1234-5678", "kr/mobile_01")
print(is_valid)  # True

# Find all PII in a text (searches all loaded patterns)
results = engine.find("My phone: 01012345678, email: test@example.com")
for match in results.matches:
    print(f"Found {match.category} ('{match.text}') at position {match.start}-{match.end}")

# Redact PII within a text using a specific strategy
redacted = engine.redact(
    "SSN: 900101-1234567",
    namespaces=["kr"],
    strategy="mask"  # Other strategies: "hash", "replace"
)
print(redacted.redacted_text)
```

## CLI Usage

The CLI is useful for quick scans, scripting, and managing the server.

```bash
# Find PII in a file, filtering by the 'kr/mobile' namespace
data-detector find --ns kr/mobile --file sample.txt

# Redact PII from a log file and write the output to a new file
data-detector redact --in input.log --out redacted.log --ns kr us

# Start the Data Detector server with a specific configuration
data-detector serve --port 8080 --config config.yml
```

## REST API

Once the server is running, you can interact with it via simple HTTP requests.

First, start the server:
```bash
data-detector serve --port 8080
```

Then, use the API endpoints:
```bash
# Find PII in a string of text
curl -X POST http://localhost:8080/find \
  -H "Content-Type: application/json" \
  -d '{"text": "My phone is 010-1234-5678", "namespaces": ["kr"]}'

# Validate a string against a specific pattern ID
curl -X POST http://localhost:8080/validate \
  -H "Content-Type: application/json" \
  -d '{"text": "010-1234-5678", "ns_id": "kr/mobile"}'

# Redact PII from a string of text
curl -X POST http://localhost:8080/redact \
  -H "Content-Type: application/json" \
  -d '{"text": "My SSN is 900101-1234567", "namespaces": ["kr"]}'

# Check the health of the server
curl http://localhost:8080/health
```

## Next Steps

Now that you have a basic understanding of Data Detector, you can explore more advanced topics:

- [Pattern Structure](patterns.md) - Learn how to define detection patterns.
- [Configuration](configuration.md) - Configure the server and pattern registry.
- [Custom Patterns](custom-patterns.md) - Create your own patterns for custom data types.
- [Verification Functions](verification.md) - Add custom logic to validate pattern matches.