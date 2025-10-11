# Token Pattern Detection

This guide covers the high-entropy token detection feature, which identifies API keys, secrets, and other sensitive tokens using entropy-based verification.

## Overview

Token patterns detect sensitive credentials and secrets by combining:
1. **Regex matching** - Initial pattern matching (fast)
2. **Entropy verification** - Shannon entropy calculation (precise)
3. **Priority-based search** - Vendor-specific patterns checked before generic ones

This approach provides:
- ✅ **High accuracy** - Filters out repetitive strings and low-entropy patterns
- ✅ **Low false positives** - Entropy threshold prevents "aaaa..." or "1234..." matches
- ✅ **Fast performance** - Regex narrows candidates before entropy check
- ✅ **Vendor-specific detection** - Recognizes AWS, GitHub, Stripe, etc.

## Quick Start

### Python API

```python
from datadetector import Engine, load_registry

# Load token patterns
registry = load_registry(paths=["patterns/tokens.yml"])
engine = Engine(registry)

# Detect tokens
text = "API Key: rk_test_4eC39HqLyjWDarjtT1zdp7dcEXAMPLE"
result = engine.find(text, namespaces=["comm"])

if result.has_matches:
    for match in result.matches:
        print(f"Found {match.pattern_id}: {match.category.value}")
```

### CLI

```bash
# Detect tokens in file
data-detector find --file secrets.log --patterns patterns/tokens.yml

# Fast detection check (stop on first match)
data-detector find --file data.txt --patterns patterns/tokens.yml --first-only
```

## Supported Token Types

### Vendor-Specific Tokens (Priority: 5-20)

| Pattern | Example | Priority | Verification |
|---------|---------|----------|--------------|
| AWS Access Key | `AKIAIOSFODNN7EXAMPLE` | 10 | Format only |
| AWS Secret Key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` | 15 | High entropy |
| GitHub Token | `ghp_EXAMPLE1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P` | 10 | High entropy |
| Stripe-like API Key | `rk_test_4eC39HqLyjWDarjtT1zdp7dcEXAMPLE` | 10 | High entropy |
| Google API Key | `AIzaSyD-EXAMPLE9tN3R6X5Q8W7E4R2T1Y9U6I5O3P` | 10 | Format only |
| Slack Token | `xoxb-123456789012-1234567890123-AbCdEfGh` | 10 | High entropy |
| JWT Token | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJz...` | 20 | Format only |
| Private Key | `-----BEGIN RSA PRIVATE KEY-----` | 5 | Header match |

### Generic Tokens (Priority: 90-95)

| Pattern | Description | Min Length | Entropy |
|---------|-------------|------------|---------|
| Generic Token | High-entropy alphanumeric | 20+ chars | 4.0+ bits/char |
| Generic API Key | High-entropy alphanumeric | 32+ chars | 4.0+ bits/char |

## How It Works

### 1. Pattern Matching (Regex)

First, regex patterns narrow down candidates:

```yaml
- id: generic_token_01
  pattern: '[A-Za-z0-9_\-+/=.]{20,}'  # 20+ chars, base64url charset
```

**Matches:** `aBcD3fGh1JkLmN0pQrStUvW2x` (25 chars)
**Skips:** `short` (too short)

### 2. Entropy Verification

Then, Shannon entropy filters low-randomness strings:

```python
def high_entropy_token(value: str) -> bool:
    """Validates token entropy >= 4.0 bits/char"""

    # Calculate Shannon entropy
    entropy = -sum((count/length) * log2(count/length)
                   for count in char_counts.values())

    return entropy >= 4.0
```

**Passes:** `aBcD3fGh1JkLmN0pQrStUvW2x` (entropy: 4.82)
**Fails:** `aaaaaaaaaaaaaaaaaaaaaaaa` (entropy: 0.0)

### 3. Priority-Based Matching

Vendor-specific patterns checked before generic ones:

```yaml
# Checked first (priority 10)
- id: stripe_key_01
  pattern: 'rk_(live|test)_[A-Za-z0-9]{24,}'
  priority: 10

# Checked last (priority 90)
- id: generic_token_01
  pattern: '[A-Za-z0-9_\-+/=.]{20,}'
  priority: 90
```

**Result:** Stripe keys match as `stripe_key_01` instead of `generic_token_01`

## Configuration

### Creating Custom Token Patterns

Add to `patterns/tokens.yml`:

```yaml
- id: my_api_token_01
  location: comm
  category: token
  description: My custom API token format
  pattern: 'myapp_[A-Za-z0-9]{40}'
  verification: high_entropy_token
  priority: 10
  mask: "[REDACTED_MY_TOKEN]"
  examples:
    match:
      - "myapp_aBcD3fGh1JkLmN0pQrStUvW2xY4zA5bC6dE7fG8hI9j"
    nomatch:
      - "myapp_short"
      - "myapp_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  policy:
    store_raw: false
    action_on_match: redact
    severity: critical
```

### Adjusting Entropy Threshold

Modify `verification.py` to adjust sensitivity:

```python
def high_entropy_token(value: str) -> bool:
    # Higher threshold = fewer matches (more strict)
    min_entropy = 4.5  # Default: 4.0

    return entropy >= min_entropy
```

**Threshold guidelines:**
- `3.5`: Lenient (may include some patterned strings)
- `4.0`: Balanced (default, recommended)
- `4.5`: Strict (only highly random strings)
- `5.0`: Very strict (may miss some valid tokens)

## Performance

### Benchmark Results

Test: 100 iterations, text with 4 tokens

| Mode | Time | Speedup |
|------|------|---------|
| Find all matches | 489ms | 1x |
| Stop on first match | 1.3ms | **377x faster** |

### Optimization Tips

1. **Use `stop_on_first_match=True` for detection:**
   ```python
   has_tokens = engine.find(text, stop_on_first_match=True).has_matches
   ```

2. **Set appropriate priorities:**
   - High priority (0-10): Vendor-specific tokens
   - Low priority (90-95): Generic fallbacks

3. **Load only needed patterns:**
   ```python
   registry = load_registry(paths=["patterns/tokens.yml"])
   # Don't load all patterns if you only need tokens
   ```

4. **Use specific namespaces:**
   ```python
   result = engine.find(text, namespaces=["comm"])  # Only token patterns
   ```

## Common Use Cases

### 1. Secret Scanning in CI/CD

```python
def scan_for_secrets(file_path: str) -> bool:
    """Quickly check if file contains secrets"""
    registry = load_registry(paths=["patterns/tokens.yml"])
    engine = Engine(registry)

    text = open(file_path).read()
    result = engine.find(text, stop_on_first_match=True)

    if result.has_matches:
        print(f"⚠️  Secret detected in {file_path}")
        return True
    return False
```

### 2. Log Redaction

```python
def redact_logs(log_text: str) -> str:
    """Redact tokens from logs"""
    registry = load_registry(paths=["patterns/tokens.yml"])
    engine = Engine(registry)

    result = engine.redact(log_text, namespaces=["comm"])
    return result.redacted_text
```

### 3. Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Scan staged files for tokens
for file in $(git diff --cached --name-only); do
    if data-detector find --file "$file" --patterns patterns/tokens.yml --first-only; then
        echo "❌ Secret detected in $file - commit blocked"
        exit 1
    fi
done

echo "✅ No secrets detected"
```

## API Reference

### Engine.find() Parameters

```python
def find(
    text: str,
    namespaces: Optional[List[str]] = None,
    allow_overlaps: bool = False,
    include_matched_text: bool = False,
    stop_on_first_match: bool = False,  # NEW: Early termination
) -> FindResult:
```

**Parameters:**
- `stop_on_first_match` (bool): Stop after finding first match
  - Use for quick detection checks
  - 100-400x faster than finding all matches
  - Patterns checked in priority order

### CLI Options

```bash
data-detector find [OPTIONS]

Options:
  --text TEXT              Text to search
  --file PATH              File to search
  --patterns PATH          Pattern files to load
  --ns NAMESPACE           Namespaces to search
  --first-only             Stop on first match (fast detection)
  --include-text           Include matched text in output
  --output [json|text]     Output format
```

## Troubleshooting

### False Positives

**Problem:** Generic tokens matching non-secrets

**Solution:** Increase entropy threshold or use vendor-specific patterns

```python
# In verification.py
min_entropy = 4.5  # Increase from 4.0
```

### False Negatives

**Problem:** Real tokens not being detected

**Solution:** Lower entropy threshold or check pattern regex

```python
# In verification.py
min_entropy = 3.5  # Decrease from 4.0
```

### Performance Issues

**Problem:** Slow detection on large files

**Solutions:**
1. Use `stop_on_first_match=True` for detection checks
2. Load only token patterns, not all patterns
3. Set appropriate priorities to check common tokens first

## Security Best Practices

1. **Never log matched tokens:**
   ```python
   result = engine.find(text, include_matched_text=False)  # Don't include raw text
   ```

2. **Use redaction for logs:**
   ```python
   redacted = engine.redact(log_text)
   logger.info(redacted.redacted_text)
   ```

3. **Block commits with secrets:**
   ```bash
   # Pre-commit hook
   data-detector find --file "$file" --first-only && exit 1
   ```

4. **Scan regularly:**
   ```python
   # Periodic secret scanning
   for file in repository.files():
       if has_secrets(file):
           alert_security_team(file)
   ```

## See Also

- [Verification Functions](verification.md) - Custom entropy thresholds
- [Pattern Priority](patterns.md#priority) - Pattern search order
- [Performance Optimization](performance.md) - Speed tips
- [API Reference](api-reference.md) - Complete API docs
