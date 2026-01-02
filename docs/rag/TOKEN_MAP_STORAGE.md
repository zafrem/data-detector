# Token Map Storage Guide

> **Quick Summary**: Learn how to securely store and manage reversible token maps for PII protection in RAG systems.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [Examples](#examples)
- [Storage Solutions](#storage-solutions)
- [Best Practices](#best-practices)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)
- [Related Documentation](#related-documentation)

---

## Overview

### What are Token Maps?

Token maps enable **reversible PII masking** - the ability to replace sensitive data with tokens and later retrieve the original values when authorized. This is critical for compliance, auditing, and authorized access scenarios in RAG systems.

**Key Features:**
- ✅ Reversible masking (can unmask if authorized)
- ✅ Secure token mapping storage
- ✅ Encryption at rest
- ✅ Access control integration
- ✅ GDPR compliance support

**Use Cases:**
- Compliance audits (need to prove what was masked)
- Customer support (authorized access to PII)
- Debugging and troubleshooting
- Internal knowledge bases

**Important:** Token maps are **NOT saved automatically**. You must explicitly store them in a secure location separate from your vector database.

---

## Quick Start

### Basic Tokenization

```python
from datadetector import Engine, load_registry
from datadetector.tokenization import SecureTokenizer

# Initialize
registry = load_registry()
engine = Engine(registry)
tokenizer = SecureTokenizer(engine)

# Tokenize text
text = "Email: john@example.com, Phone: 555-0123"
sanitized, token_map = tokenizer.tokenize_with_map(text, namespaces=["comm"])

print(f"Sanitized: {sanitized}")
print(f"Token map: {token_map.tokens}")

# ⚠️ Token map exists only in memory!
# You MUST save it explicitly
```

**Output:**
```
Sanitized: Email: [TOKEN:comm:email:0], Phone: [TOKEN:comm:phone:1]
Token map: {'[TOKEN:comm:email:0]': 'john@example.com', '[TOKEN:comm:phone:1]': '555-0123'}
```

### Complete Example with Storage

```python
from cryptography.fernet import Fernet
import json

# 1. Tokenize
sanitized, token_map = tokenizer.tokenize_with_map(text)

# 2. Store sanitized text in Vector DB (public, fast)
doc_id = vector_db.add(sanitized)

# 3. Encrypt token map
encryption_key = Fernet.generate_key()  # Store this in secrets manager!
cipher = Fernet(encryption_key)
encrypted = cipher.encrypt(json.dumps(token_map.tokens).encode())

# 4. Store encrypted map in SEPARATE secure database
secure_db.save(doc_id, encrypted, access_level="admin_only")

# Later: Retrieve and detokenize (if authorized)
encrypted_map = secure_db.get(doc_id)
decrypted = cipher.decrypt(encrypted_map)
original_tokens = json.loads(decrypted)

from datadetector.rag_models import TokenMap
retrieved_map = TokenMap(tokens=original_tokens)
original_text = tokenizer.detokenize(sanitized, retrieved_map)

print(f"Original: {original_text}")
```

**Output:**
```
Original: Email: john@example.com, Phone: 555-0123
```

---

## Core Concepts

### Storage Architecture

```
┌─────────────────────────────────────────────────────┐
│              SEPARATION OF STORAGE                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────────┐    ┌──────────────────────┐  │
│  │  Vector Database │    │ Secure Token Store   │  │
│  │  (Public/Fast)   │    │ (Encrypted/Private)  │  │
│  ├──────────────────┤    ├──────────────────────┤  │
│  │ Sanitized Docs   │    │ Token Maps           │  │
│  │                  │    │                      │  │
│  │ "Customer:       │    │ {                    │  │
│  │  [TOKEN:0]       │    │   "[TOKEN:0]":       │  │
│  │  needs help"     │    │   "john@example.com" │  │
│  │                  │    │ }                    │  │
│  │                  │    │ (ENCRYPTED!)         │  │
│  └──────────────────┘    └──────────────────────┘  │
│         │                          │                │
│    Fast Search             Restricted Access       │
│    Anyone can query        Only authorized users   │
└─────────────────────────────────────────────────────┘
```

### TOKENIZE vs HASH

```python
# TOKENIZE - Reversible
text = "Email: john@example.com"
sanitized, token_map = tokenizer.tokenize_with_map(text)
# → "Email: [TOKEN:comm:email:0]"
# Can reverse: token_map stored separately

original = tokenizer.detokenize(sanitized, token_map)
# → "Email: john@example.com" ✅ Got it back!

# HASH - Irreversible
result = engine.redact(text, strategy=RedactionStrategy.HASH)
# → "Email: [HASH:a1b2c3d4e5f6]"
# Cannot reverse! ❌ Data permanently lost
```

| Feature | TOKENIZE | HASH |
|---------|----------|------|
| **Reversible** | ✅ Yes (with map) | ❌ Never |
| **Storage needed** | 💾 Yes (encrypted map) | ✅ No |
| **Get original** | ✅ If authorized | ❌ Impossible |
| **Use case** | Audits, support | Analytics |

---

## Examples

### Example 1: PostgreSQL with Encryption

**Scenario:** Production RAG system with PostgreSQL token storage.

```python
import psycopg2
from cryptography.fernet import Fernet
import json
import os

# Connect to SEPARATE secure database
conn = psycopg2.connect(
    host="secure-db.internal",
    database="token_store",
    user="token_admin",
    password=os.getenv("TOKEN_DB_PASSWORD")
)

# Create table (one time)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS token_maps (
        doc_id VARCHAR(255) PRIMARY KEY,
        encrypted_data BYTEA NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        access_level VARCHAR(50) DEFAULT 'admin_only'
    )
""")
conn.commit()

# Function: Store token map
def store_token_map(doc_id: str, token_map: dict, encryption_key: bytes):
    """Store encrypted token map."""
    cipher = Fernet(encryption_key)

    # Encrypt
    token_json = json.dumps(token_map).encode()
    encrypted = cipher.encrypt(token_json)

    # Store with access control
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO token_maps (doc_id, encrypted_data, access_level)
        VALUES (%s, %s, 'admin_only')
        ON CONFLICT (doc_id) DO UPDATE
        SET encrypted_data = EXCLUDED.encrypted_data
    """, (doc_id, encrypted))
    conn.commit()

# Function: Retrieve token map (only if authorized)
def get_token_map(doc_id: str, user_role: str, encryption_key: bytes):
    """Retrieve and decrypt token map (authorized only)."""
    # Check authorization
    if user_role not in ["admin", "support_lead"]:
        raise PermissionError("Unauthorized access to token map")

    cursor = conn.cursor()
    cursor.execute("""
        SELECT encrypted_data FROM token_maps
        WHERE doc_id = %s
    """, (doc_id,))

    result = cursor.fetchone()
    if not result:
        raise KeyError("Token map not found")

    encrypted = result[0]

    # Decrypt
    cipher = Fernet(encryption_key)
    decrypted = cipher.decrypt(encrypted)
    return json.loads(decrypted)

# Usage
encryption_key = Fernet.generate_key()  # Store in secrets manager!

# Store
doc = "Customer: john@example.com"
sanitized, token_map = tokenizer.tokenize_with_map(doc)
doc_id = vector_db.add(sanitized)
store_token_map(doc_id, token_map.tokens, encryption_key)

# Retrieve (authorized)
retrieved_map = get_token_map(doc_id, user_role="admin", encryption_key=encryption_key)
print(f"Retrieved: {retrieved_map}")
```

**Output:**
```
Retrieved: {'[TOKEN:comm:email:0]': 'john@example.com'}
```

### Example 2: Redis with Auto-Expiration

**Scenario:** Fast token storage with automatic expiration (TTL).

```python
import redis
from cryptography.fernet import Fernet
import json
import os

# Connect to secure Redis instance
redis_client = redis.Redis(
    host='secure-redis.internal',
    port=6379,
    password=os.getenv("REDIS_PASSWORD"),
    ssl=True,  # Use TLS
    db=0
)

def store_token_map(doc_id: str, token_map: dict, encryption_key: bytes):
    """Store with 90-day auto-expiration."""
    cipher = Fernet(encryption_key)

    # Encrypt
    token_json = json.dumps(token_map).encode()
    encrypted = cipher.encrypt(token_json)

    # Store with TTL (90 days)
    redis_client.setex(
        name=f"tokenmap:{doc_id}",
        time=90 * 24 * 60 * 60,  # 90 days in seconds
        value=encrypted
    )

def get_token_map(doc_id: str, encryption_key: bytes):
    """Retrieve token map."""
    encrypted = redis_client.get(f"tokenmap:{doc_id}")
    if not encrypted:
        raise KeyError("Token map not found or expired")

    cipher = Fernet(encryption_key)
    decrypted = cipher.decrypt(encrypted)
    return json.loads(decrypted)

# Usage
encryption_key = Fernet.generate_key()

# Store
store_token_map("doc123", {"[TOKEN:0]": "john@example.com"}, encryption_key)

# Retrieve
retrieved = get_token_map("doc123", encryption_key)
print(f"Retrieved: {retrieved}")
```

**Output:**
```
Retrieved: {'[TOKEN:0]': 'john@example.com'}
```

### Example 3: AWS KMS + DynamoDB (Production)

**Scenario:** Enterprise-grade storage with managed encryption.

```python
import boto3
import json
from datetime import datetime
import time

# AWS services
kms = boto3.client('kms')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('token-maps')

def store_token_map(doc_id: str, token_map: dict):
    """Store with AWS KMS encryption."""
    # Encrypt using AWS KMS (managed keys)
    token_json = json.dumps(token_map)

    response = kms.encrypt(
        KeyId='alias/token-map-key',  # Create in AWS KMS
        Plaintext=token_json.encode()
    )
    encrypted = response['CiphertextBlob']

    # Store in DynamoDB
    table.put_item(
        Item={
            'doc_id': doc_id,
            'encrypted_data': encrypted,
            'created_at': datetime.now().isoformat(),
            'access_policy': 'admin_only',
            'ttl': int(time.time()) + (90 * 24 * 60 * 60)  # Auto-delete
        }
    )

def get_token_map(doc_id: str, user_role: str):
    """Retrieve with authorization check."""
    # Check authorization
    if user_role not in ["admin", "compliance"]:
        raise PermissionError("Unauthorized")

    # Retrieve from DynamoDB
    response = table.get_item(Key={'doc_id': doc_id})
    if 'Item' not in response:
        raise KeyError("Token map not found")

    encrypted = response['Item']['encrypted_data']

    # Decrypt using KMS
    response = kms.decrypt(CiphertextBlob=encrypted)
    decrypted = response['Plaintext'].decode()

    return json.loads(decrypted)

# Usage
store_token_map("doc123", {"[TOKEN:0]": "john@example.com"})
retrieved = get_token_map("doc123", user_role="admin")
print(f"Retrieved: {retrieved}")
```

**Output:**
```
Retrieved: {'[TOKEN:0]': 'john@example.com'}
```

### Example 4: Complete RAG System

**Scenario:** End-to-end RAG system with secure token management.

```python
from datadetector import Engine, load_registry
from datadetector.tokenization import SecureTokenizer
import psycopg2
from cryptography.fernet import Fernet
import os

class SecureRAGSystem:
    """RAG system with secure token map storage."""

    def __init__(self):
        # PII detector
        registry = load_registry()
        self.engine = Engine(registry)
        self.tokenizer = SecureTokenizer(self.engine)

        # Vector DB (public, fast)
        self.vector_db = self.connect_vector_db()

        # Token store (secure, encrypted)
        self.token_store = psycopg2.connect(
            host="secure-db.internal",
            database="token_maps",
            password=os.getenv("TOKEN_DB_PASSWORD")
        )

        # Encryption
        self.encryption_key = os.getenv("TOKEN_MAP_KEY").encode()
        self.cipher = Fernet(self.encryption_key)

    def index_document(self, doc: str) -> str:
        """Index document with PII protection."""
        # 1. Tokenize
        sanitized, token_map = self.tokenizer.tokenize_with_map(
            doc, namespaces=["comm", "us"]
        )

        # 2. Store in Vector DB
        doc_id = self.vector_db.add(sanitized)

        # 3. Encrypt and store token map
        if token_map.tokens:
            token_json = json.dumps(token_map.tokens).encode()
            encrypted = self.cipher.encrypt(token_json)

            cursor = self.token_store.cursor()
            cursor.execute("""
                INSERT INTO token_maps (doc_id, encrypted_data)
                VALUES (%s, %s)
            """, (doc_id, encrypted))
            self.token_store.commit()

        return doc_id

    def query(self, user_query: str, user_role: str) -> str:
        """Query with authorization-based detokenization."""
        # Search vector DB
        results = self.vector_db.search(user_query)
        doc_id = results[0]['id']
        tokenized_text = results[0]['text']

        # Detokenize if authorized
        if user_role in ["admin", "support_lead"]:
            cursor = self.token_store.cursor()
            cursor.execute(
                "SELECT encrypted_data FROM token_maps WHERE doc_id = %s",
                (doc_id,)
            )
            result = cursor.fetchone()

            if result:
                decrypted = self.cipher.decrypt(result[0])
                token_map_dict = json.loads(decrypted)

                from datadetector.rag_models import TokenMap
                token_map = TokenMap(tokens=token_map_dict)
                return self.tokenizer.detokenize(tokenized_text, token_map)

        # Regular users see tokenized version
        return tokenized_text

# Usage
rag = SecureRAGSystem()

# Index
doc = "Customer: john@example.com, SSN: 123-45-6789"
doc_id = rag.index_document(doc)
print(f"Indexed: {doc_id}")

# Query as regular user
result = rag.query("customer info", user_role="user")
print(f"User sees: {result}")

# Query as admin
result = rag.query("customer info", user_role="admin")
print(f"Admin sees: {result}")
```

**Output:**
```
Indexed: doc_001
User sees: Customer: [TOKEN:comm:email:0], SSN: [TOKEN:us:ssn:1]
Admin sees: Customer: john@example.com, SSN: 123-45-6789
```

---

## Storage Solutions

### ❌ BAD: Local Files (Unencrypted)

```python
# ❌ DON'T DO THIS!
with open('token_map.json', 'w') as f:
    json.dump(token_map.tokens, f)
```

**Problems:**
- Anyone with file access sees PII
- Not encrypted
- Not backed up
- Lost if server dies

### ❌ BAD: In Vector Database

```python
# ❌ DON'T DO THIS!
vector_db.add({
    'text': sanitized,
    'token_map': token_map.tokens  # Defeats the purpose!
})
```

**Problems:**
- Defeats purpose of tokenization
- No access control separation
- Anyone querying vector DB sees PII

### ✅ GOOD: Separate Encrypted Database

```python
# ✅ CORRECT APPROACH
# 1. Sanitized in vector DB
vector_db.add(sanitized)

# 2. Token map in separate, encrypted storage
secure_db.save(doc_id, encrypt(token_map.tokens))
```

**Benefits:**
- ✅ Separation of concerns
- ✅ Encryption at rest
- ✅ Access control
- ✅ Vector DB breach doesn't leak PII

---

## Best Practices

### 1. Always Encrypt

**Do this:**
```python
# ✅ Encrypt before storing
from cryptography.fernet import Fernet

cipher = Fernet(encryption_key)
encrypted = cipher.encrypt(json.dumps(token_map.tokens).encode())
secure_db.save(doc_id, encrypted)
```

**Why:** Token maps contain original PII and must be encrypted at rest.

### 2. Use Separate Storage

**Do this:**
```python
# ✅ Different databases
vector_db.add(sanitized)  # Fast, public
token_store.save(doc_id, encrypted_map)  # Secure, restricted
```

**Why:** Separation prevents vector DB compromise from leaking PII.

### 3. Implement Access Control

**Do this:**
```python
# ✅ Role-based access
def get_token_map(doc_id: str, user_role: str):
    if user_role not in ["admin", "compliance"]:
        raise PermissionError("Unauthorized")

    # Log access for audit
    audit_log.log(f"{user_role} accessed token map {doc_id}")

    return retrieve_and_decrypt(doc_id)
```

**Why:** Only authorized users should access original PII.

### 4. Use Secrets Manager for Keys

**Do this:**
```python
# ✅ Never hardcode keys
import os

encryption_key = os.getenv("TOKEN_MAP_ENCRYPTION_KEY")

# Or AWS Secrets Manager
import boto3
secrets = boto3.client('secretsmanager')
response = secrets.get_secret_value(SecretId='token-map-key')
encryption_key = response['SecretString']
```

**Why:** Hardcoded keys in code are a security vulnerability.

### 5. Implement Auto-Expiration

**Do this:**
```python
# ✅ Set TTL on token maps
redis_client.setex(
    name=f"tokenmap:{doc_id}",
    time=90 * 24 * 60 * 60,  # 90 days
    value=encrypted
)
```

**Why:** Comply with data retention policies and reduce risk over time.

### 6. Audit All Access

**Do this:**
```python
# ✅ Log all token map access
import logging

audit_logger = logging.getLogger('token_access')

def get_token_map(doc_id: str, user_id: str):
    audit_logger.info(f"Token access: doc={doc_id}, user={user_id}")
    return retrieve_and_decrypt(doc_id)
```

**Why:** Audit trail for compliance and security monitoring.

---

## Security Considerations

### Key Rotation

```python
def rotate_encryption_keys(old_key: bytes, new_key: bytes):
    """Rotate encryption keys for all token maps."""
    old_cipher = Fernet(old_key)
    new_cipher = Fernet(new_key)

    cursor = conn.cursor()
    cursor.execute("SELECT doc_id, encrypted_data FROM token_maps")

    for doc_id, encrypted in cursor.fetchall():
        # Decrypt with old key
        decrypted = old_cipher.decrypt(encrypted)

        # Re-encrypt with new key
        re_encrypted = new_cipher.encrypt(decrypted)

        # Update
        cursor.execute(
            "UPDATE token_maps SET encrypted_data = %s WHERE doc_id = %s",
            (re_encrypted, doc_id)
        )

    conn.commit()
```

### GDPR Compliance

```python
def delete_personal_data(doc_id: str):
    """Delete all personal data (GDPR right to erasure)."""
    # Delete from vector DB
    vector_db.delete(doc_id)

    # Delete token map
    cursor = conn.cursor()
    cursor.execute("DELETE FROM token_maps WHERE doc_id = %s", (doc_id,))
    conn.commit()

    # Clear caches
    cache.delete(f"doc:{doc_id}")

    # Audit log
    audit_log(f"Deleted all data for {doc_id}")
```

---

## Troubleshooting

### Issue: Token map not found

**Symptoms:**
- `KeyError: "Token map not found"`
- Cannot detokenize documents

**Solution:**
```python
# Ensure token map is saved after tokenization
sanitized, token_map = tokenizer.tokenize_with_map(text)

# MUST save explicitly
if token_map.tokens:
    store_token_map(doc_id, token_map.tokens, encryption_key)
```

### Issue: Decryption fails

**Symptoms:**
- `cryptography.fernet.InvalidToken` error

**Solution:**
```python
# Use the SAME encryption key for decrypt as encrypt
# Store key in environment variable, not code
encryption_key = os.getenv("TOKEN_MAP_ENCRYPTION_KEY")

# Verify key is the same
assert encryption_key == original_encryption_key
```

### Issue: Unauthorized access

**Symptoms:**
- Users can't access token maps
- Permission errors

**Solution:**
```python
# Check user role is in authorized list
AUTHORIZED_ROLES = ["admin", "support_lead", "compliance"]

def get_token_map(doc_id: str, user_role: str):
    if user_role not in AUTHORIZED_ROLES:
        raise PermissionError(f"Role '{user_role}' not authorized")

    return retrieve_and_decrypt(doc_id)
```

---

## Related Documentation

**Core Documentation:**
- [RAG Quick Start](RAG_QUICKSTART.md) - Getting started with RAG security
- [RAG Security Architecture](RAG_SECURITY_ARCHITECTURE.md) - Complete architecture

**Related Topics:**
- [RAG Integration](rag-integration.md) - Framework integration guide
- [Configuration](configuration.md) - System configuration

**Security:**
- [Verification Functions](verification.md) - PII validation
- [Custom Patterns](custom-patterns.md) - Define custom PII patterns

---

## Support

- 📖 **Documentation**: [docs/](.)
- 💻 **Examples**: Run `examples/rag_quickstart.py`
- 🔐 **Security**: Report security issues privately
- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/data-detector/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/data-detector/discussions)

---

**Last Updated:** 2025-11-29 | **Version:** 0.0.2
