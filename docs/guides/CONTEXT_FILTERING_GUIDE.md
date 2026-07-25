# Context-Aware Pattern Filtering Guide

## Overview

Context-aware pattern filtering is a powerful feature that significantly improves performance and accuracy by only checking relevant regex patterns based on contextual hints like column names, field labels, or descriptions.

**Key Benefits:**
- **10-20x faster** for targeted scans (checking 2-5 patterns instead of all 61)
- **Fewer false positives** through context-based filtering
- **Better accuracy** with category hints
- **Backward compatible** - works alongside existing API

## Quick Start

```python
from datadetector import Engine, load_registry, ContextHint

engine = Engine(registry=load_registry())

# Traditional approach (checks all 61 patterns)
text = "SSN: 123-45-6789"
result = engine.find(text)

# Context-aware approach (checks only SSN patterns)
context = ContextHint(keywords=["ssn"], strategy='strict')
result = engine.find(text, context=context)
```

## Core Concepts

### ContextHint

The `ContextHint` class specifies what patterns to check:

```python
from datadetector import ContextHint

context = ContextHint(
    keywords=["ssn", "bank_account"],      # Keywords to match
    categories=["phone", "email"],          # Categories to include
    pattern_ids=["us/ssn_01"],             # Explicit pattern IDs
    exclude_patterns=["us/itin_01"],       # Patterns to exclude
    strategy='loose'                        # Filtering strategy
)
```

### Strategies

Three filtering strategies control how patterns are selected:

1. **`strict`** - Only use keyword-matched patterns. No fallback.
   ```python
   context = ContextHint(keywords=["email"], strategy='strict')
   # Only checks email patterns, nothing else
   ```

2. **`loose`** (default) - Use keyword-matched patterns, fall back to all if no matches.
   ```python
   context = ContextHint(keywords=["email"], strategy='loose')
   # Checks email patterns, or all patterns if no email keywords match
   ```

3. **`none`** - Disable filtering, check all patterns.
   ```python
   context = ContextHint(keywords=["email"], strategy='none')
   # Ignores keywords, checks all patterns
   ```

## Common Use Cases

### 1. Database Column Scanning

When scanning database columns, use column names as hints:

```python
from datadetector import Engine, load_registry, create_context_from_field_name

engine = Engine(registry=load_registry())

# Table schema
columns = {
    "user_ssn": ["123-45-6789", "987-65-4321"],
    "billing_zip": ["90210", "48201"],
    "contact_email": ["user@example.com"]
}

for column_name, values in columns.items():
    # Automatically extract keywords from column name
    context = create_context_from_field_name(column_name, strategy='strict')

    for value in values:
        result = engine.find(value, context=context)
        if result.has_matches:
            print(f"{column_name}: {value} -> {result.matches[0].ns_id}")
```

**Output:**
```
user_ssn: 123-45-6789 -> us/ssn_01
user_ssn: 987-65-4321 -> us/itin_01
billing_zip: 90210 -> us/zipcode_01
billing_zip: 48201 -> us/zipcode_01
contact_email: user@example.com -> comm/email_01
```

### 2. Form Field Processing

Use field labels as context hints:

```python
form_data = {
    "label": "Social Security Number",
    "description": "Enter your 9-digit SSN",
    "value": "123-45-6789"
}

context = ContextHint(keywords=["social", "security"], strategy='strict')
result = engine.find(form_data["value"], context=context)
```

### 3. Document Section Processing

Different document sections have different data types:

```python
document = [
    {
        "section": "Contact Information",
        "categories": ['email', 'phone'],
        "text": "Email: user@example.com, Phone: (555) 123-4567"
    },
    {
        "section": "Payment Details",
        "categories": ['credit_card', 'bank'],
        "text": "Card: 4532-1234-5678-9010"
    }
]

for section in document:
    context = ContextHint(categories=section['categories'], strategy='strict')
    result = engine.find(section['text'], context=context)

    print(f"{section['section']}: {len(result.matches)} matches")
```

### 4. API Response Scanning

Scan JSON responses using field names:

```python
import json

api_response = {
    "user_id": 12345,
    "ssn": "123-45-6789",
    "billing_zip": "90210",
    "phone_number": "(555) 123-4567"
}

for field_name, value in api_response.items():
    if not isinstance(value, str):
        continue

    context = create_context_from_field_name(field_name, strategy='loose')
    result = engine.find(str(value), context=context)

    if result.has_matches:
        print(f"{field_name}: CONTAINS PII ({result.matches[0].category.value})")
```

## Keyword Mappings

The system includes 100+ pre-configured keyword mappings in `patterns/keywords.yml`:

### English Keywords

| Keyword | Maps To | Example |
|---------|---------|---------|
| `ssn`, `social_security` | US SSN patterns | `user_ssn` → `us/ssn_01` |
| `bank_account`, `account_number` | Bank account patterns | `billing_account` → `kr/bank_account_*` |
| `zipcode`, `postal_code`, `zip` | Zipcode patterns | `billing_zip` → `us/zipcode_01` |
| `phone`, `telephone`, `mobile` | Phone patterns | `contact_phone` → `us/phone_01` |
| `email`, `email_address` | Email patterns | `user_email` → `comm/email_01` |
| `credit_card`, `card_number` | Credit card patterns | `payment_card` → `comm/credit_card_01` |
| `passport` | Passport patterns | `passport_number` → `us/passport_01` |

### Korean Keywords

| Keyword | Maps To | Example |
|---------|---------|---------|
| `주민등록번호`, `주민번호`, `rrn` | Korean RRN | `주민번호` → `kr/rrn_01` |
| `계좌번호`, `계좌` | Bank accounts | `은행계좌` → `kr/bank_account_*` |
| `우편번호` | Zipcode | `우편번호` → `kr/zipcode_01` |
| `전화번호`, `휴대폰`, `핸드폰` | Phone numbers | `휴대폰번호` → `kr/phone_02` |
| `사업자등록번호`, `사업자번호` | Business registration | `사업자번호` → `kr/business_registration_01` |
| `운전면허`, `운전면허번호` | Driver license | `운전면허` → `kr/driver_license_01` |

## Categories

Patterns are organized into 10 categories:

| Category | Description | Patterns |
|----------|-------------|----------|
| `ssn` | Social Security Numbers | US SSN, ITIN, Korean RRN |
| `bank` | Bank accounts | 16 Korean bank account patterns |
| `address` | Address information | US/Korean zipcodes |
| `phone` | Phone numbers | US/Korean phone patterns |
| `credit_card` | Credit cards | Visa, Mastercard, Amex, etc. |
| `email` | Email addresses | Email patterns |
| `passport` | Passport numbers | US/Korean passports |
| `other` | Other IDs | EIN, driver license, Medicare, business registration |
| `ip` | IP addresses | IPv4, IPv6 |
| `location` | Coordinates | Latitude, longitude, DMS |
| `token` | API keys/tokens | JWT, AWS, GitHub, Slack, OpenAI, etc. |

**Usage:**
```python
# Check only SSN-related patterns
context = ContextHint(categories=['ssn'], strategy='strict')

# Check multiple categories
context = ContextHint(categories=['phone', 'email', 'address'], strategy='strict')
```

## Advanced Features

### Wildcard Pattern Matching

Use wildcards to match multiple patterns:

```python
# Match all Korean bank account patterns (bank_account_01 through bank_account_16)
context = ContextHint(
    pattern_ids=['kr/bank_account_*'],
    strategy='strict'
)

result = engine.find("Account: 123-456789-01234", context=context)
```

### Pattern Exclusion

Exclude specific patterns even if they match keywords:

```python
# Check SSN category but exclude ITIN
context = ContextHint(
    categories=['ssn'],
    exclude_patterns=['us/itin_01'],
    strategy='strict'
)

# Will match us/ssn_01 but not us/itin_01
result = engine.find("123-45-6789", context=context)
```

### Combining Multiple Hints

Combine keywords, categories, and explicit pattern IDs:

```python
context = ContextHint(
    keywords=["account"],              # Match "account" keyword
    categories=['bank'],               # Include bank category
    pattern_ids=['us/ein_01'],        # Also check EIN pattern
    exclude_patterns=['kr/bank_account_13'],  # Exclude specific pattern
    strategy='strict'
)
```

### Redaction with Context

Context filtering works with all engine methods:

```python
text = "SSN: 123-45-6789, Email: user@example.com"

# Only redact SSN, leave email intact
context = ContextHint(keywords=["ssn"], strategy='strict')
result = engine.redact(text, context=context)

print(result.redacted_text)  # "SSN: ***-**-****, Email: user@example.com"
```

## Helper Functions

### create_context_from_field_name()

Automatically extract keywords from field names:

```python
from datadetector import create_context_from_field_name

# Extracts ["user", "ssn"] from field name
context = create_context_from_field_name("user_ssn", strategy='strict')

# Extracts ["billing", "address", "zip", "code"]
context = create_context_from_field_name("billing_address_zip_code")
```

**Features:**
- Splits on underscores, hyphens, spaces, and dots
- Filters out single-character keywords
- Converts to lowercase
- Supports strategy parameter

## Performance Optimization

### When to Use Context Filtering

✅ **Use when:**
- Scanning structured data (databases, JSON, CSV)
- Processing forms with field labels
- You have metadata about the data type
- Performance is critical

❌ **Don't use when:**
- Scanning unstructured text without hints
- You don't have reliable metadata
- You need to find any PII regardless of context

### Performance Comparison

```python
import time

text = "SSN: 123-45-6789"

# Without context (checks all 61 patterns)
start = time.time()
for _ in range(1000):
    engine.find(text)
elapsed_no_context = time.time() - start

# With context (checks only 2-3 SSN patterns)
context = ContextHint(keywords=["ssn"], strategy='strict')
start = time.time()
for _ in range(1000):
    engine.find(text, context=context)
elapsed_with_context = time.time() - start

print(f"Speedup: {elapsed_no_context / elapsed_with_context:.2f}x")
# Typical output: Speedup: 10.5x
```

## Disabling Context Filtering

Disable the feature entirely if not needed:

```python
from datadetector import Engine, load_registry

# Disable context filtering (saves memory)
engine = Engine(
    registry=load_registry(),
    enable_context_filtering=False
)

# Context hints will be ignored
context = ContextHint(keywords=["ssn"])
result = engine.find(text, context=context)  # Checks all patterns
```

## Custom Keyword Mappings

Add custom keywords by editing `patterns/keywords.yml`:

```yaml
keywords:
  # Add custom keyword
  social_security_id:
    categories: [ssn]
    patterns: [us/ssn_01]
    priority: high

  # Add company-specific field name
  employee_tax_id:
    patterns: [us/ssn_01, us/ein_01]
    priority: high
```

Then reload the registry:

```python
from datadetector import Engine, load_registry, KeywordRegistry

keyword_registry = KeywordRegistry()  # Reloads keywords.yml
engine = Engine(
    registry=load_registry(),
    keyword_registry=keyword_registry
)
```

## Troubleshooting

### Context not filtering as expected

1. **Check strategy**: Use `strategy='strict'` for strict filtering
2. **Verify keywords**: Check if keywords exist in `patterns/keywords.yml`
3. **Enable logging**: Set logging level to DEBUG to see filtering decisions

```python
import logging
logging.basicConfig(level=logging.DEBUG)

context = ContextHint(keywords=["ssn"], strategy='strict')
result = engine.find(text, context=context)
# Debug logs will show: "Context filtering: 61 -> 2 patterns"
```

### Pattern not found with context

1. **Check pattern ID**: Verify pattern exists in registry
2. **Use loose strategy**: Fall back to all patterns if no match
3. **Check category**: Ensure pattern is in the specified category

```python
# List all patterns in a category
from datadetector import KeywordRegistry

registry = KeywordRegistry()
patterns = registry.get_patterns_for_category('ssn')
print(patterns)  # ['us/ssn_01', 'us/itin_01', 'kr/rrn_01']
```

## Best Practices

1. **Use `strict` for structured data**: When you have reliable metadata
2. **Use `loose` for semi-structured data**: When hints might be incomplete
3. **Combine with namespaces**: Further narrow down patterns
   ```python
   result = engine.find(
       text,
       namespaces=['us'],  # Only US patterns
       context=ContextHint(keywords=["ssn"], strategy='strict')
   )
   ```
4. **Cache ContextHint objects**: Reuse context objects for similar fields
5. **Profile performance**: Measure speedup in your specific use case

## Examples

See complete working examples in:
- `examples/context_filtering_examples.py` - 8 comprehensive examples
- `tests/test_context_filtering.py` - 29 test cases

Run examples:
```bash
python3 examples/context_filtering_examples.py
```

Run tests:
```bash
python3 -m pytest tests/test_context_filtering.py -v
```

## API Reference

### ContextHint

```python
@dataclass
class ContextHint:
    keywords: List[str] = []           # Keywords to match
    categories: List[str] = []         # Categories to include
    pattern_ids: List[str] = []        # Explicit pattern IDs
    exclude_patterns: List[str] = []   # Patterns to exclude
    strategy: str = 'loose'            # 'strict', 'loose', or 'none'
```

### Engine.find()

```python
def find(
    text: str,
    namespaces: Optional[List[str]] = None,
    allow_overlaps: bool = False,
    include_matched_text: bool = False,
    stop_on_first_match: bool = False,
    context: Optional[ContextHint] = None  # NEW: Context filtering
) -> FindResult
```

### Engine.redact()

```python
def redact(
    text: str,
    namespaces: Optional[List[str]] = None,
    strategy: Optional[RedactionStrategy] = None,
    allow_overlaps: bool = False,
    context: Optional[ContextHint] = None  # NEW: Context filtering
) -> RedactionResult
```

### create_context_from_field_name()

```python
def create_context_from_field_name(
    field_name: str,
    strategy: str = 'loose'
) -> ContextHint
```

## Migration Guide

Existing code continues to work without changes:

```python
# Old code (still works)
result = engine.find(text)

# New code (with context filtering)
context = ContextHint(keywords=["ssn"])
result = engine.find(text, context=context)
```

No breaking changes - context filtering is opt-in.
