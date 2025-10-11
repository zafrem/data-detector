# Quick Start Guide

## Basic Usage

### Library API

```python
from datadetector import Engine, load_registry

# Load patterns from specific files
registry = load_registry(paths=["patterns/common.yml", "patterns/kr.yml"])
# Or load all patterns from a directory
registry = load_registry(paths=["patterns/"])

engine = Engine(registry)

# Validate
is_valid = engine.validate("010-1234-5678", "kr/mobile_01")
print(is_valid)  # True

# Find PII (searches all loaded patterns)
results = engine.find("My phone: 01012345678, email: test@example.com")
for match in results.matches:
    print(f"Found {match.category} at position {match.start}-{match.end}")

# Redact
redacted = engine.redact(
    "SSN: 900101-1234567",
    namespaces=["kr"],
    strategy="mask"
)
print(redacted.redacted_text)
```

### CLI Usage

```bash
# Find PII in text
data-detector find --ns kr/mobile --file sample.txt

# Redact PII
data-detector redact --in input.log --out redacted.log --ns kr us

# Start server
data-detector serve --port 8080 --config config.yml
```

### REST API

Start the server:
```bash
data-detector serve --port 8080
```

Use the API:
```bash
# Find PII
curl -X POST http://localhost:8080/find \
  -H "Content-Type: application/json" \
  -d '{"text": "010-1234-5678", "namespaces": ["kr"]}'

# Validate
curl -X POST http://localhost:8080/validate \
  -H "Content-Type: application/json" \
  -d '{"text": "010-1234-5678", "ns_id": "kr/mobile"}'

# Redact
curl -X POST http://localhost:8080/redact \
  -H "Content-Type: application/json" \
  -d '{"text": "My SSN is 900101-1234567", "namespaces": ["kr"]}'

# Health check
curl http://localhost:8080/health
```

## Next Steps

- [Pattern Structure](patterns.md) - Learn how to define patterns
- [Configuration](configuration.md) - Configure the server and registry
- [Custom Patterns](custom-patterns.md) - Create your own patterns
- [Verification Functions](verification.md) - Add custom validation logic
