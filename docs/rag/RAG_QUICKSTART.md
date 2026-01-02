# RAG Security - Quick Start Guide

> **Quick Summary**: Get started with three-layer PII protection for RAG systems in 5 minutes.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [Examples](#examples)
- [Redaction Strategies](#redaction-strategies)
- [Configuration](#configuration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Related Documentation](#related-documentation)

---

## Overview

### What is RAG Security?

RAG Security provides **three-layer PII protection** for Retrieval-Augmented Generation systems. It scans and sanitizes sensitive information at every stage of your RAG pipeline: user queries, document storage, and LLM responses.

**Key Features:**
- ✅ Three-layer protection (Input → Storage → Output)
- ✅ Multiple redaction strategies (MASK, FAKE, TOKENIZE, HASH)
- ✅ YAML-based configuration
- ✅ Fast performance (< 15ms per document)
- ✅ Reversible tokenization for authorized access
- ✅ REST API ready

**Use Cases:**
- Customer support chatbots
- Internal knowledge bases
- Public documentation search
- Compliance-driven RAG systems

---

## Quick Start

### Installation

```bash
pip install data-detector
```

### Basic Example (3 Lines)

```python
from datadetector import Engine, load_registry
from datadetector.rag_middleware import RAGSecurityMiddleware

# Initialize
registry = load_registry()
engine = Engine(registry)
security = RAGSecurityMiddleware(engine)

# Scan query (Layer 1)
result = await security.scan_query("Email john@example.com about order")
print(f"Safe query: {result.sanitized_text}")
# Output: "Safe query: Email [EMAIL] about order"
```

### Complete Example (All 3 Layers)

```python
import asyncio
from datadetector import Engine, load_registry
from datadetector.rag_middleware import RAGSecurityMiddleware

async def main():
    # Initialize
    registry = load_registry()
    engine = Engine(registry)
    security = RAGSecurityMiddleware(engine)

    # Layer 1: Input scanning
    query = "Status for customer john@example.com?"
    input_result = await security.scan_query(query, namespaces=["comm"])

    if input_result.blocked:
        return "Query blocked"

    print(f"✓ Safe query: {input_result.sanitized_text}")

    # Layer 2: Storage scanning
    document = "Customer: john@example.com, Phone: 555-0123"
    doc_result = await security.scan_document(document, namespaces=["comm"])

    print(f"✓ Safe for vector DB: {doc_result.sanitized_text}")

    # Store in vector DB
    # vector_db.add(doc_result.sanitized_text)

    # Layer 3: Output scanning
    llm_response = "The email is john@example.com"
    output_result = await security.scan_response(llm_response, namespaces=["comm"])

    if output_result.blocked:
        print("⚠ Response blocked due to PII leak")
    else:
        print(f"✓ Safe response: {output_result.sanitized_text}")

asyncio.run(main())
```

**Expected Output:**
```
✓ Safe query: Status for customer [EMAIL]?
✓ Safe for vector DB: Customer: [EMAIL], Phone: [PHONE]
⚠ Response blocked due to PII leak
```

---

## Core Concepts

### Three-Layer Architecture

```
User Query
    ↓
┌─────────────────────────┐
│ Layer 1: INPUT          │  ← Scan queries before RAG
│ Action: SANITIZE        │
└─────────────────────────┘
    ↓ (safe query)
┌─────────────────────────┐
│ Vector DB Search        │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│ Layer 2: STORAGE        │  ← Scan docs before indexing
│ Action: TOKENIZE        │
└─────────────────────────┘
    ↓ (sanitized docs)
┌─────────────────────────┐
│ LLM Processing          │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│ Layer 3: OUTPUT         │  ← Scan responses before return
│ Action: BLOCK           │
└─────────────────────────┘
    ↓
Safe Response
```

### Security Policies

Each layer has configurable security policies:

```python
from datadetector.rag_models import SecurityPolicy, SecurityAction, SecurityLayer

policy = SecurityPolicy(
    layer=SecurityLayer.INPUT,
    action=SecurityAction.SANITIZE,  # block | sanitize | warn | allow
    severity_threshold=SeverityLevel.MEDIUM,
    redaction_strategy=RedactionStrategy.FAKE
)
```

---

## Examples

### Example 1: Block Sensitive Queries

**Scenario:** Reject queries containing high-severity PII (e.g., SSN).

```python
from datadetector.rag_models import SecurityPolicy, SecurityAction, SecurityLayer, SeverityLevel

# Create strict blocking policy
strict_policy = SecurityPolicy(
    layer=SecurityLayer.INPUT,
    action=SecurityAction.BLOCK,
    severity_threshold=SeverityLevel.HIGH
)

# Apply policy
security.update_policy(SecurityLayer.INPUT, strict_policy)

# Test with sensitive query
result = await security.scan_query("Process SSN 123-45-6789", namespaces=["us"])

print(f"Blocked: {result.blocked}")
print(f"Reason: {result.reason}")
```

**Output:**
```
Blocked: True
Reason: Query contains 1 high-severity PII matches
```

### Example 2: Sanitize Documents for Vector DB

**Scenario:** Remove PII from documents before indexing with FAKE data.

```python
from datadetector.models import RedactionStrategy
from datadetector.rag_models import SecurityPolicy, SecurityLayer

# Policy with FAKE strategy (better for embeddings)
storage_policy = SecurityPolicy(
    layer=SecurityLayer.STORAGE,
    action=SecurityAction.SANITIZE,
    redaction_strategy=RedactionStrategy.FAKE
)

security.update_policy(SecurityLayer.STORAGE, storage_policy)

# Scan document
document = """
Customer: John Doe
Email: john@example.com
Phone: 555-0123
"""

result = await security.scan_document(document, namespaces=["comm"])

print(f"Original:\n{document}")
print(f"\nSanitized:\n{result.sanitized_text}")

# Store in vector DB
# vector_db.add(result.sanitized_text)
```

**Output:**
```
Original:
Customer: John Doe
Email: john@example.com
Phone: 555-0123

Sanitized:
Customer: John Doe
Email: fake123@example.com
Phone: 555-9876
```

### Example 3: Tokenize with Reversal

**Scenario:** Use reversible tokens for internal systems.

```python
from datadetector.tokenization import SecureTokenizer

tokenizer = SecureTokenizer(engine)

# Tokenize document
document = "Email: john@example.com, SSN: 123-45-6789"
sanitized, token_map = tokenizer.tokenize_with_map(document, namespaces=["comm", "us"])

print(f"Tokenized: {sanitized}")
print(f"Token map: {token_map.tokens}")

# Store sanitized in vector DB
# vector_db.add(sanitized)

# Store token map securely (encrypted)
# secure_db.save(token_map, encrypted=True)

# Later, reverse if authorized
detokenized = tokenizer.detokenize(sanitized, token_map)
print(f"Detokenized: {detokenized}")
```

**Output:**
```
Tokenized: Email: [TOKEN:comm:email:0], SSN: [TOKEN:us:ssn:1]
Token map: {'[TOKEN:comm:email:0]': 'john@example.com', '[TOKEN:us:ssn:1]': '123-45-6789'}
Detokenized: Email: john@example.com, SSN: 123-45-6789
```

---

## Redaction Strategies

### Strategy Comparison

| Strategy | Speed | Reversible | Best For | Example |
|----------|-------|------------|----------|---------|
| **MASK** | ⚡ Fastest | ❌ No | Output blocking | `***@***.com` |
| **FAKE** | ⚡ Fast | ❌ No | Storage (RAG) | `fake@example.com` |
| **TOKENIZE** | ⚡ Fast | ✅ Yes | Compliance | `[TOKEN:0]` |
| **HASH** | ⚡ Fast | ❌ No | Analytics | `[HASH:a1b2c3]` |

### MASK Strategy

```python
from datadetector.models import RedactionStrategy

result = engine.redact(
    "Email: john@example.com",
    strategy=RedactionStrategy.MASK
)
print(result.redacted_text)
# Output: "Email: ***@***.com"
```

**Pros:** Simple, fast
**Cons:** Poor for embeddings, unnatural

### FAKE Strategy

```python
result = engine.redact(
    "Email: john@example.com",
    strategy=RedactionStrategy.FAKE
)
print(result.redacted_text)
# Output: "Email: fake123@example.com"
```

**Pros:** Natural, better embeddings
**Cons:** Slightly slower, requires faker library

### TOKENIZE Strategy

```python
from datadetector.tokenization import SecureTokenizer

tokenizer = SecureTokenizer(engine)
sanitized, token_map = tokenizer.tokenize_with_map("Email: john@example.com")
print(sanitized)
# Output: "Email: [TOKEN:comm:email:0]"

# Can reverse
original = tokenizer.detokenize(sanitized, token_map)
print(original)
# Output: "Email: john@example.com"
```

**Pros:** Reversible, secure
**Cons:** Requires token map storage

### HASH Strategy

```python
result = engine.redact(
    "Email: john@example.com",
    strategy=RedactionStrategy.HASH
)
print(result.redacted_text)
# Output: "Email: [HASH:a1b2c3d4e5f6]"
```

**Pros:** Maximum security, one-way
**Cons:** Irreversible, poor UX

---

## Configuration

### YAML Configuration

Edit `config/rag_security_policy.yml`:

```yaml
# Input Layer
input_layer:
  enabled: true
  action: sanitize
  redaction_strategy: fake  # ← CHOOSE: mask | fake | tokenize | hash
  namespaces:
    - comm
    - us

# Storage Layer
storage_layer:
  enabled: true
  action: sanitize
  redaction_strategy: tokenize  # ← CHOOSE: mask | fake | tokenize | hash
  preserve_format: true

# Output Layer
output_layer:
  enabled: true
  action: block
  redaction_strategy: mask  # ← CHOOSE: mask | fake | tokenize | hash
  severity_threshold: high
```

### Load Configuration

```python
from datadetector import load_rag_policy

# Load from YAML
policy_config = load_rag_policy("config/rag_security_policy.yml")

# Create middleware with loaded policies
security = RAGSecurityMiddleware(
    engine,
    input_policy=policy_config.get_input_policy(),
    storage_policy=policy_config.get_storage_policy(),
    output_policy=policy_config.get_output_policy()
)
```

### REST API Configuration

```bash
# Start server
data-detector serve --port 8080

# Use API
curl -X POST http://localhost:8080/rag/scan-query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Email john@example.com",
    "action": "sanitize",
    "namespaces": ["comm"]
  }'
```

---

## Best Practices

### 1. Use Different Strategies per Layer

**Do this:**
```python
# ✅ Optimized configuration
input_policy = SecurityPolicy(
    layer=SecurityLayer.INPUT,
    redaction_strategy=RedactionStrategy.FAKE  # Natural queries
)

storage_policy = SecurityPolicy(
    layer=SecurityLayer.STORAGE,
    redaction_strategy=RedactionStrategy.TOKENIZE  # Reversible
)

output_policy = SecurityPolicy(
    layer=SecurityLayer.OUTPUT,
    redaction_strategy=RedactionStrategy.MASK  # Fast blocking
)
```

**Why:** Each layer has different requirements. Input/storage benefit from natural text, output needs fast blocking.

### 2. Limit Namespaces for Performance

**Do this:**
```python
# ✅ Only scan relevant patterns
result = await security.scan_query(
    query,
    namespaces=["comm"]  # Just email/phone
)
```

**Don't do this:**
```python
# ❌ Scanning all patterns unnecessarily
result = await security.scan_query(query)  # All namespaces
```

**Why:** Scanning only relevant namespaces is 2-3x faster.

### 3. Store Token Maps Securely

**Do this:**
```python
# ✅ Encrypt and separate storage
from cryptography.fernet import Fernet

cipher = Fernet(encryption_key)
encrypted = cipher.encrypt(json.dumps(token_map.tokens).encode())

# Store in separate secure database
secure_db.save(doc_id, encrypted, access_level="admin_only")
```

**Don't do this:**
```python
# ❌ Storing unencrypted in vector DB
vector_db.add({
    'text': sanitized,
    'token_map': token_map.tokens  # DON'T!
})
```

**Why:** Token maps contain original PII and must be encrypted and access-controlled.

---

## Troubleshooting

### Issue: "FakeDataGenerator not available"

**Symptoms:**
- Warning when using FAKE strategy
- Falls back to MASK strategy

**Solution:**
```bash
pip install faker
```

**Explanation:** FAKE strategy requires the `faker` library for realistic data generation.

### Issue: Slow Performance

**Symptoms:**
- Response time > 50ms
- High CPU usage

**Solution:**
```python
# Use stop_on_first_match for detection only
result = await security.scan_query(
    query,
    namespaces=["comm"],  # Limit namespaces
    stop_on_first_match=True  # 2-3x faster
)
```

**Explanation:** Scanning all patterns in all namespaces is slower. Limit to relevant patterns.

### Issue: Token Map Storage

**Symptoms:**
- "Token map not found" errors
- Cannot detokenize

**Solution:**
```python
# Ensure token map is saved before detokenizing
sanitized, token_map = tokenizer.tokenize_with_map(text)

# Save token map
secure_db.save(doc_id, encrypt(token_map.tokens))

# Later, retrieve before detokenizing
retrieved_map = decrypt(secure_db.get(doc_id))
detokenized = tokenizer.detokenize(sanitized, TokenMap(tokens=retrieved_map))
```

**Explanation:** Token maps must be explicitly saved and retrieved for detokenization.

---

## Related Documentation

**Core Documentation:**
- [Installation Guide](installation.md) - Getting started with data-detector
- [Architecture](RAG_SECURITY_ARCHITECTURE.md) - Detailed system architecture

**RAG Security:**
- [RAG Security Architecture](RAG_SECURITY_ARCHITECTURE.md) - Complete architecture guide
- [RAG Integration](rag-integration.md) - Framework integration guide
- [Token Map Storage](TOKEN_MAP_STORAGE.md) - Secure token storage guide

**Advanced Topics:**
- [Custom Patterns](custom-patterns.md) - Create custom PII patterns
- [Verification Functions](verification.md) - Add validation logic

---

## Support

- 📖 **Full Documentation**: [RAG Security Architecture](RAG_SECURITY_ARCHITECTURE.md)
- 💻 **Examples**: Run `examples/rag_quickstart.py`
- ⚙️ **Configuration**: Edit `config/rag_security_policy.yml`
- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/data-detector/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/data-detector/discussions)

---

**Last Updated:** 2025-11-29 | **Version:** 0.0.2
