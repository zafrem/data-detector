# RAG Security Architecture

> **Quick Summary**: Comprehensive guide to the three-layer PII protection system for RAG applications with detailed architecture, redaction strategies, and configuration.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture Overview](#architecture-overview)
- [Core Concepts](#core-concepts)
- [Redaction Strategies](#redaction-strategies)
- [Configuration](#configuration)
- [API Integration](#api-integration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Related Documentation](#related-documentation)

---

## Overview

### What is RAG Security Architecture?

The RAG Security Architecture provides comprehensive PII protection for Retrieval-Augmented Generation systems through a three-layer defense strategy. Each layer addresses specific security risks in the RAG pipeline: user input, document storage, and LLM output.

**Key Features:**
- ✅ Three-layer security (Input → Storage → Output)
- ✅ Four redaction strategies (MASK, FAKE, TOKENIZE, HASH)
- ✅ YAML-based configuration
- ✅ High performance (< 15ms per document)
- ✅ Framework integrations (LangChain, LlamaIndex)
- ✅ REST API ready

**Use Cases:**
- Customer support chatbots with PII protection
- Internal knowledge bases requiring compliance
- Public documentation search with strict security
- Multi-tenant RAG systems

---

## Architecture Overview

### System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                  RAG SECURITY ARCHITECTURE                      │
└─────────────────────────────────────────────────────────────────┘

                         User Query
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  LAYER 1: INPUT SECURITY                │
        │  ─────────────────────────               │
        │  • Scan user queries                    │
        │  • Block/sanitize sensitive queries     │
        │  • Strategy: FAKE or MASK               │
        │  • Fast response: < 5ms                 │
        └──────────────┬──────────────────────────┘
                       │ (sanitized query)
                       ▼
        ┌─────────────────────────────────────────┐
        │  Vector DB Query                        │
        │  • Uses sanitized query                 │
        │  • Retrieves sanitized documents        │
        └──────────────┬──────────────────────────┘
                       │
                       ▼
        ┌─────────────────────────────────────────┐
        │  LAYER 2: STORAGE SECURITY              │
        │  ──────────────────────────             │
        │  • Scan before indexing                 │
        │  • Tokenize for reversibility           │
        │  • Or use FAKE for embeddings           │
        │  • Performance: < 10ms per 1KB          │
        └──────────────┬──────────────────────────┘
                       │ (sanitized docs)
                       ▼
        ┌─────────────────────────────────────────┐
        │  LLM Processing                         │
        │  • Processes sanitized context          │
        │  • Generates response                   │
        └──────────────┬──────────────────────────┘
                       │
                       ▼
        ┌─────────────────────────────────────────┐
        │  LAYER 3: OUTPUT SECURITY               │
        │  ─────────────────────────              │
        │  • Scan LLM responses                   │
        │  • Block leaked PII strictly            │
        │  • Strategy: BLOCK or MASK              │
        │  • Critical protection layer            │
        └──────────────┬──────────────────────────┘
                       │
                       ▼
                  Safe Response
```

### Component Architecture

```
┌──────────────────────────────────────────────────────────┐
│              RAGSecurityMiddleware                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌───────────┐ │
│  │ Input Policy   │  │ Storage Policy │  │Output     │ │
│  │                │  │                │  │Policy     │ │
│  │ action:        │  │ action:        │  │           │ │
│  │   sanitize     │  │   sanitize     │  │action:    │ │
│  │ strategy:      │  │ strategy:      │  │  block    │ │
│  │   fake         │  │   tokenize     │  │strategy:  │ │
│  │ threshold:     │  │ threshold:     │  │  mask     │ │
│  │   medium       │  │   low          │  │threshold: │ │
│  └────────┬───────┘  └────────┬───────┘  │  high     │ │
│           │                   │          └─────┬─────┘ │
│           └───────────────────┴────────────────┘       │
│                              │                         │
└──────────────────────────────┼─────────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Engine             │
                    │                      │
                    │  • Pattern Registry  │
                    │  • Redaction Logic   │
                    │  • Fake Generator    │
                    │  • Tokenizer         │
                    └──────────────────────┘
```

---

## Core Concepts

### Three Security Layers

### Layer 1: Input Security

**Purpose**: Protect against sensitive queries entering the RAG system

**When**: Before query is processed or sent to vector DB

**Strategy Options**:
- **SANITIZE** (recommended): Remove PII, continue with safe query
- **BLOCK**: Reject queries containing PII
- **WARN**: Log but allow (for internal tools)

**Example**:
```python
# Original query
"What's the order status for customer john@example.com?"

# After INPUT layer (FAKE strategy)
"What's the order status for customer fake123@example.com?"

# Result: Safe to process, maintains query structure
```

**Performance**: < 5ms per query

### Layer 2: Storage Security

**Purpose**: Protect PII in indexed documents

**When**: Before documents are embedded and stored in vector DB

**Strategy Options**:
- **TOKENIZE** (reversible): Replace with tokens, store mapping securely
- **FAKE** (semantic): Replace with realistic data for better embeddings
- **MASK**: Simple masking (not recommended for RAG)

**Example - Tokenization**:
```python
# Original document
"Customer: john@example.com, SSN: 123-45-6789"

# After STORAGE layer (TOKENIZE strategy)
"Customer: [TOKEN:comm:email:0], SSN: [TOKEN:us:ssn:1]"

# Token map (stored separately, encrypted)
{
  "[TOKEN:comm:email:0]": "john@example.com",
  "[TOKEN:us:ssn:1]": "123-45-6789"
}
```

**Example - Fake Data**:
```python
# Original document
"Customer: john@example.com, Phone: 555-0123"

# After STORAGE layer (FAKE strategy)
"Customer: fake456@example.com, Phone: 555-9876"

# Better for embeddings: preserves semantic structure
```

**Performance**: < 10ms per 1KB document

### Layer 3: Output Security

**Purpose**: Final defense against PII leakage in responses

**When**: After LLM generates response, before returning to user

**Strategy Options**:
- **BLOCK** (recommended): Reject responses containing PII
- **SANITIZE**: Remove PII from response
- **WARN**: Log leaked PII but allow

**Example**:
```python
# LLM generated (leaked PII)
"The customer's email is john@example.com"

# After OUTPUT layer (BLOCK)
"[RESPONSE BLOCKED: Contains sensitive information]"

# User receives safe error message
```

**Performance**: < 8ms per response

---

## Redaction Strategies

### 1. MASK Strategy

**Description**: Replace PII with asterisks or pattern-specific masks

**Pros**:
- ⚡ Fastest (< 2ms overhead)
- 🔒 Simple and secure
- 📝 Easy to understand

**Cons**:
- ❌ Breaks semantic structure
- ❌ Poor for embeddings
- ❌ Unnatural for LLMs

**Example**:
```python
"Email: john@example.com"
→ "Email: ***@***.***"

"SSN: 123-45-6789"
→ "SSN: ***-**-****"
```

**Best For**:
- Output layer (blocking)
- Simple logging
- Non-RAG use cases

### 2. FAKE Strategy

**Description**: Replace PII with realistic fake data

**Pros**:
- ✅ Preserves semantic structure
- ✅ Better embeddings for RAG
- ✅ Natural for LLM processing
- ✅ Maintains text flow

**Cons**:
- ⏱️ Slightly slower (3-5ms overhead)
- 🔀 Non-deterministic (different each time)
- 📦 Requires faker library

**Example**:
```python
"Email: john@example.com"
→ "Email: fake123@example.com"

"Phone: 555-0123"
→ "Phone: 555-9876"

"SSN: 123-45-6789"
→ "SSN: 987-65-4321"
```

**Best For**:
- Storage layer (document indexing)
- Input layer (query sanitization)
- RAG systems (embeddings)

### 3. TOKENIZE Strategy

**Description**: Replace with reversible tokens

**Pros**:
- 🔄 Reversible (can unmask if authorized)
- 🔒 Secure (tokens meaningless without map)
- 📊 Audit trail possible

**Cons**:
- 💾 Requires secure token map storage
- 🔐 Key management complexity
- 📝 Unnatural tokens in text

**Example**:
```python
"Email: john@example.com, SSN: 123-45-6789"
→ "Email: [TOKEN:comm:email:0], SSN: [TOKEN:us:ssn:1]"

# Token map stored securely
{
  "[TOKEN:comm:email:0]": "john@example.com",
  "[TOKEN:us:ssn:1]": "123-45-6789"
}
```

**Best For**:
- Storage layer (when reversal needed)
- Audit requirements
- Compliance needs

### 4. HASH Strategy

**Description**: Replace with cryptographic hash

**Pros**:
- 🔒 Irreversible (maximum security)
- 🔑 Same input → same hash
- ✅ Verifiable without revealing

**Cons**:
- ❌ Irreversible (data loss)
- ❌ Unnatural for embeddings
- ❌ Poor UX

**Example**:
```python
"Email: john@example.com"
→ "Email: [HASH:a1b2c3d4e5f6g7h8]"
```

**Best For**:
- Maximum security scenarios
- Logging/analytics
- One-way anonymization

---

## Configuration

### YAML Configuration File

**Location**: `config/rag_security_policy.yml`

### Basic Configuration

```yaml
# Input Layer - User Queries
input_layer:
  enabled: true
  action: sanitize  # block | sanitize | warn | allow
  severity_threshold: medium
  redaction_strategy: fake  # CHOOSE: mask | fake | tokenize | hash
  namespaces:
    - comm  # Email, phone, URL
    - us    # SSN, credit cards
  log_matches: true

# Storage Layer - Document Indexing
storage_layer:
  enabled: true
  action: sanitize
  severity_threshold: low
  redaction_strategy: fake  # CHOOSE: mask | fake | tokenize | hash
  namespaces:
    - comm
    - us
  preserve_format: true
  log_matches: true

# Output Layer - LLM Responses
output_layer:
  enabled: true
  action: block
  severity_threshold: high
  redaction_strategy: mask  # CHOOSE: mask | fake | tokenize | hash
  namespaces:
    - comm
    - us
  log_matches: true
```

### Loading Configuration

```python
from datadetector import Engine, load_registry, load_rag_policy
from datadetector.rag_middleware import RAGSecurityMiddleware

# Load patterns and create engine
registry = load_registry()
engine = Engine(registry)

# Load RAG security policies from YAML
policy_config = load_rag_policy("config/rag_security_policy.yml")

# Create middleware with loaded policies
middleware = RAGSecurityMiddleware(
    engine,
    input_policy=policy_config.get_input_policy(),
    storage_policy=policy_config.get_storage_policy(),
    output_policy=policy_config.get_output_policy(),
)

# Use middleware
result = await middleware.scan_query("What's john@example.com's status?")
```

### Preset Configurations

#### Public Chatbot (Strict)
```yaml
input_layer:
  action: sanitize
  redaction_strategy: fake  # Preserve query structure
storage_layer:
  action: sanitize
  redaction_strategy: fake  # Better embeddings
output_layer:
  action: block  # Strict blocking
  severity_threshold: medium
```

#### Internal Tool (Lenient)
```yaml
input_layer:
  action: warn  # Allow but log
  redaction_strategy: mask
storage_layer:
  action: sanitize
  redaction_strategy: tokenize  # Reversible
output_layer:
  action: sanitize
  severity_threshold: high
```

#### Maximum Security
```yaml
input_layer:
  action: block
  severity_threshold: low
storage_layer:
  action: block
  severity_threshold: low
output_layer:
  action: block
  severity_threshold: low
```

---

## API Integration

### REST API

**Start Server**:
```bash
data-detector serve --port 8080
```

**Layer 1: Scan Query**
```bash
curl -X POST http://localhost:8080/rag/scan-query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Email john@example.com about order",
    "action": "sanitize",
    "namespaces": ["comm"]
  }'
```

**Response**:
```json
{
  "sanitized_text": "Email fake123@example.com about order",
  "blocked": false,
  "pii_detected": true,
  "match_count": 1,
  "action_taken": "sanitize"
}
```

### Python Library

```python
import asyncio
from datadetector import Engine, load_registry
from datadetector.rag_middleware import RAGSecurityMiddleware

async def secure_rag_pipeline(query: str, documents: list):
    # Initialize
    registry = load_registry()
    engine = Engine(registry)
    security = RAGSecurityMiddleware(engine)

    # Layer 1: Input
    input_result = await security.scan_query(query)
    if input_result.blocked:
        return "Query blocked"

    # Layer 2: Storage (during indexing)
    sanitized_docs = []
    for doc in documents:
        doc_result = await security.scan_document(doc)
        if not doc_result.blocked:
            sanitized_docs.append(doc_result.sanitized_text)

    # ... RAG processing ...

    # Layer 3: Output
    llm_response = "..."  # From LLM
    output_result = await security.scan_response(llm_response)

    if output_result.blocked:
        return "[RESPONSE BLOCKED]"

    return output_result.sanitized_text
```

---

## Best Practices

### Performance Optimization

### Benchmarks

| Operation | Text Size | Strategy | Latency (p95) |
|-----------|-----------|----------|---------------|
| Input Scan | 256 chars | FAKE | < 5ms |
| Input Scan | 256 chars | MASK | < 3ms |
| Document Scan | 1KB | FAKE | < 15ms |
| Document Scan | 1KB | TOKENIZE | < 10ms |
| Response Scan | 512 chars | BLOCK | < 8ms |

### Optimization Tips

**1. Use Appropriate Strategy per Layer**
```python
# Optimize for speed where needed
input_policy = SecurityPolicy(
    layer=SecurityLayer.INPUT,
    redaction_strategy=RedactionStrategy.FAKE  # Slight overhead OK
)

output_policy = SecurityPolicy(
    layer=SecurityLayer.OUTPUT,
    redaction_strategy=RedactionStrategy.MASK  # Fastest
)
```

**2. Limit Namespaces**
```python
# Only scan relevant PII types
await security.scan_query(
    query,
    namespaces=["comm"]  # Just email/phone, not all patterns
)
```

**3. Use Streaming for Bulk**
```python
from datadetector import StreamEngine

stream_engine = StreamEngine(engine, max_concurrent=10)

# Process many documents concurrently
results = await stream_engine.scan_batch(documents)
```

**4. Stop on First Match**
```python
# For binary detection (has PII yes/no)
result = await security.scan_query(
    query,
    stop_on_first_match=True  # Faster
)
```

### Use Case Examples

#### 1. Customer Support Chatbot

**Requirements**:
- Users query with customer emails/phones
- Knowledge base has PII
- Must not leak PII in responses

**Configuration**:
```yaml
input_layer:
  action: sanitize
  redaction_strategy: fake  # Preserve query semantics

storage_layer:
  action: sanitize
  redaction_strategy: tokenize  # Can reverse if needed

output_layer:
  action: block  # Strict
  severity_threshold: medium
```

#### 2. Internal Knowledge Base

**Requirements**:
- Internal users need access
- Documents contain PII
- Some PII may be needed for work

**Configuration**:
```yaml
input_layer:
  action: warn  # Allow but log

storage_layer:
  action: sanitize
  redaction_strategy: tokenize  # Reversible

output_layer:
  action: sanitize
  severity_threshold: high
  allow_detokenization: true  # For authorized users
```

#### 3. Public Documentation Search

**Requirements**:
- Public access
- Maximum security
- No PII should exist

**Configuration**:
```yaml
input_layer:
  action: block
  severity_threshold: low

storage_layer:
  action: block  # Don't index PII docs
  severity_threshold: low

output_layer:
  action: block
  severity_threshold: low
```

---

## Troubleshooting

### Issue: Slow Performance

**Symptoms:**
- High latency (> 50ms)
- Slow document processing
- CPU bottlenecks

**Solution:**
```python
# Limit to relevant namespaces
result = await security.scan_query(
    query,
    namespaces=["comm"],  # Only email/phone
    stop_on_first_match=True  # Faster
)

# Use streaming for batch processing
from datadetector import StreamEngine
stream = StreamEngine(engine, max_concurrent=10)
results = await stream.scan_batch(documents)
```

**Explanation:** Limiting namespaces and using concurrent processing significantly improves performance.

### Issue: Configuration Not Loading

**Symptoms:**
- YAML configuration not applied
- Using default policies
- Configuration errors

**Solution:**
```python
from datadetector import load_rag_policy

# Load configuration explicitly
policy_config = load_rag_policy("config/rag_security_policy.yml")

# Verify policies loaded
print(f"Input policy: {policy_config.get_input_policy()}")
print(f"Storage policy: {policy_config.get_storage_policy()}")
print(f"Output policy: {policy_config.get_output_policy()}")
```

**Explanation:** Ensure YAML file path is correct and configuration is explicitly loaded before creating middleware.

### Issue: PII Leakage in Responses

**Symptoms:**
- LLM responses contain original PII
- Output layer not blocking
- Token detokenization happening incorrectly

**Solution:**
```python
# Use strict output policy
output_policy = SecurityPolicy(
    layer=SecurityLayer.OUTPUT,
    action=SecurityAction.BLOCK,  # Strict blocking
    severity_threshold=SeverityLevel.MEDIUM
)

security.update_policy(SecurityLayer.OUTPUT, output_policy)

# Scan all responses
output_result = await security.scan_response(llm_response)
if output_result.blocked:
    return "[RESPONSE BLOCKED]"  # Never return original
```

**Explanation:** Output layer must use BLOCK action with appropriate severity threshold to prevent PII leakage.

---

## Related Documentation

**Core Documentation:**
- [Installation Guide](installation.md) - Getting started with data-detector
- [Architecture](ARCHITECTURE.md) - System design overview

**RAG Security:**
- [RAG Quick Start](RAG_QUICKSTART.md) - 5-minute quick start guide
- [RAG Integration](rag-integration.md) - Complete integration guide
- [Token Map Storage](TOKEN_MAP_STORAGE.md) - Secure token storage guide

**Advanced Topics:**
- [Custom Patterns](custom-patterns.md) - Create custom PII patterns
- [Verification Functions](verification.md) - Add validation logic
- [Performance Optimization](performance.md) - Advanced optimization

---

## Support

- 📖 **Documentation**: [RAG Integration Guide](rag-integration.md)
- 💻 **Examples**: Run `examples/rag_quickstart.py`
- ⚙️ **Configuration**: Edit `config/rag_security_policy.yml`
- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/data-detector/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/data-detector/discussions)
- 🔒 **Security**: Report privately to security@example.com

---

**Last Updated:** 2025-11-29 | **Version:** 0.0.2
