# API Reference

## Python API

### Loading Patterns

#### `load_registry(paths=None, validate_schema=True, validate_examples=True)`

Load patterns from YAML files into a registry.

**Parameters:**
- `paths` (List[str], optional): List of file or directory paths. If None, loads default patterns.
- `validate_schema` (bool): Whether to validate against JSON schema. Default: True.
- `validate_examples` (bool): Whether to validate examples against patterns. Default: True.

**Returns:** `PatternRegistry`

**Example:**
```python
from datadetector import load_registry

# Load from directory
registry = load_registry(paths=["patterns/"])

# Load specific files
registry = load_registry(paths=["patterns/common.yml", "patterns/kr.yml"])

# Load without validation
registry = load_registry(
    paths=["patterns/"],
    validate_schema=False,
    validate_examples=False
)
```

### Engine Class

#### `Engine(registry, default_mask_char='*', hash_algorithm='sha256')`

Core engine for PII detection, validation, and redaction.

**Parameters:**
- `registry` (PatternRegistry): Registry with loaded patterns
- `default_mask_char` (str): Default character for masking. Default: '*'
- `hash_algorithm` (str): Hash algorithm for hashing strategy. Default: 'sha256'

#### `Engine.find(text, namespaces=None, allow_overlaps=False, include_matched_text=False)`

Find all PII matches in text.

**Parameters:**
- `text` (str): Text to search
- `namespaces` (List[str], optional): List of namespaces to search. If None, searches all.
- `allow_overlaps` (bool): Whether to allow overlapping matches. Default: False.
- `include_matched_text` (bool): Whether to include matched text in results. Default: False.

**Returns:** `FindResult`

**Example:**
```python
result = engine.find("Phone: 010-1234-5678, Email: test@example.com")
for match in result.matches:
    print(f"{match.category} at {match.start}-{match.end}")
```

#### `Engine.validate(text, ns_id)`

Validate text against a specific pattern.

**Parameters:**
- `text` (str): Text to validate
- `ns_id` (str): Full namespace/id (e.g., "kr/mobile_01")

**Returns:** `ValidationResult`

**Example:**
```python
result = engine.validate("010-1234-5678", "kr/mobile_01")
print(result.is_valid)  # True or False
```

#### `Engine.redact(text, namespaces=None, strategy=None, allow_overlaps=False)`

Redact PII from text.

**Parameters:**
- `text` (str): Text to redact
- `namespaces` (List[str], optional): List of namespaces to search. If None, searches all.
- `strategy` (RedactionStrategy, optional): Redaction strategy (mask/hash/tokenize). Default: mask.
- `allow_overlaps` (bool): Whether to allow overlapping matches. Default: False.

**Returns:** `RedactionResult`

**Example:**
```python
result = engine.redact(
    "SSN: 900101-1234567",
    namespaces=["kr"],
    strategy="mask"
)
print(result.redacted_text)
```

### Data Models

#### `FindResult`

Result from find operation.

**Attributes:**
- `text` (str): Original text
- `matches` (List[Match]): List of matches found
- `namespaces_searched` (List[str]): Namespaces that were searched
- `has_matches` (bool): Property - True if any matches found
- `match_count` (int): Property - Number of matches

#### `Match`

Single pattern match result.

**Attributes:**
- `ns_id` (str): Full namespace/id (e.g., "kr/mobile_01")
- `pattern_id` (str): Pattern ID
- `namespace` (str): Namespace
- `category` (Category): PII category
- `start` (int): Start position in text
- `end` (int): End position in text
- `matched_text` (str, optional): Matched text (if policy allows)
- `mask` (str, optional): Mask template
- `severity` (Severity): Severity level

#### `ValidationResult`

Result from validate operation.

**Attributes:**
- `text` (str): Text that was validated
- `ns_id` (str): Pattern namespace/id used
- `is_valid` (bool): Whether text is valid
- `match` (Match, optional): Match details if valid

#### `RedactionResult`

Result from redact operation.

**Attributes:**
- `original_text` (str): Original text
- `redacted_text` (str): Text with PII redacted
- `strategy` (RedactionStrategy): Strategy used
- `matches` (List[Match]): Matches that were redacted
- `redaction_count` (int): Number of redactions

### Verification Functions

#### `iban_mod97(value)`

Verify IBAN using Mod-97 check algorithm.

**Parameters:**
- `value` (str): IBAN string

**Returns:** `bool`

#### `luhn(value)`

Verify using Luhn algorithm (mod-10 checksum).

**Parameters:**
- `value` (str): Numeric string

**Returns:** `bool`

#### `register_verification_function(name, func)`

Register a custom verification function.

**Parameters:**
- `name` (str): Name to register under
- `func` (Callable[[str], bool]): Verification function

#### `get_verification_function(name)`

Get verification function by name.

**Parameters:**
- `name` (str): Function name

**Returns:** `Callable[[str], bool]` or `None`

#### `unregister_verification_function(name)`

Unregister a verification function.

**Parameters:**
- `name` (str): Function name

**Returns:** `bool` - True if removed, False if not found

## REST API

### POST /find

Find PII matches in text.

**Request:**
```json
{
  "text": "My phone is 010-1234-5678",
  "namespaces": ["kr"],
  "allow_overlaps": false,
  "include_matched_text": false
}
```

**Response:**
```json
{
  "text": "My phone is 010-1234-5678",
  "matches": [
    {
      "ns_id": "kr/mobile_01",
      "pattern_id": "mobile_01",
      "namespace": "kr",
      "category": "phone",
      "start": 12,
      "end": 25,
      "matched_text": null,
      "severity": "high"
    }
  ],
  "namespaces_searched": ["kr"],
  "match_count": 1
}
```

### POST /validate

Validate text against a pattern.

**Request:**
```json
{
  "text": "010-1234-5678",
  "ns_id": "kr/mobile_01"
}
```

**Response:**
```json
{
  "text": "010-1234-5678",
  "ns_id": "kr/mobile_01",
  "is_valid": true,
  "match": {
    "ns_id": "kr/mobile_01",
    "category": "phone",
    "start": 0,
    "end": 13
  }
}
```

### POST /redact

Redact PII from text.

**Request:**
```json
{
  "text": "My SSN is 900101-1234567",
  "namespaces": ["kr"],
  "strategy": "mask",
  "allow_overlaps": false
}
```

**Response:**
```json
{
  "original_text": "My SSN is 900101-1234567",
  "redacted_text": "My SSN is ***-****-****",
  "strategy": "mask",
  "matches": [...],
  "redaction_count": 1
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.0.1",
  "patterns_loaded": 150,
  "namespaces": ["kr", "us", "co"]
}
```

### GET /metrics

Prometheus metrics endpoint.

**Response:** (Prometheus format)
```
# HELP data_detector_requests_total Total requests
# TYPE data_detector_requests_total counter
data_detector_requests_total{method="find"} 1234
...
```

## CLI Reference

### data-detector find

Find PII in text.

```bash
data-detector find [OPTIONS]
```

**Options:**
- `--text TEXT`: Text to search
- `--file PATH`: File to search
- `--ns NAMESPACE`: Namespace(s) to search (can specify multiple)
- `--output FORMAT`: Output format (json/text)

**Examples:**
```bash
data-detector find --text "010-1234-5678" --ns kr
data-detector find --file input.txt --ns kr us --output json
```

### data-detector validate

Validate text against a pattern.

```bash
data-detector validate [OPTIONS]
```

**Options:**
- `--text TEXT`: Text to validate
- `--ns-id NS_ID`: Pattern namespace/id

**Example:**
```bash
data-detector validate --text "010-1234-5678" --ns-id kr/mobile_01
```

### data-detector redact

Redact PII from text.

```bash
data-detector redact [OPTIONS]
```

**Options:**
- `--in PATH`: Input file
- `--out PATH`: Output file
- `--ns NAMESPACE`: Namespace(s) to search
- `--strategy STRATEGY`: Redaction strategy (mask/hash/tokenize)

**Example:**
```bash
data-detector redact --in input.log --out redacted.log --ns kr us
```

### data-detector serve

Start the server.

```bash
data-detector serve [OPTIONS]
```

**Options:**
- `--port PORT`: Server port (default: 8080)
- `--host HOST`: Server host (default: 0.0.0.0)
- `--config PATH`: Configuration file path

**Example:**
```bash
data-detector serve --port 8080 --config config.yml
```
