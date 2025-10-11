# Creating Custom Patterns

## Overview

You can add your own patterns to detect organization-specific or custom data formats.

## Steps

### 1. Create a YAML file

Create a file in the `patterns/` directory (any filename):

```yaml
namespace: custom
description: Custom organization patterns

patterns:
  - id: employee_id_01
    location: myorg     # Your organization/location code
    category: other
    description: Employee ID format
    pattern: 'EMP-\d{6}'
    mask: "EMP-******"
    examples:
      match: ["EMP-123456", "EMP-999999"]
      nomatch: ["EMP-12345", "TEMP-123456"]
    policy:
      store_raw: false
      action_on_match: redact
      severity: high
```

### 2. Load with your custom patterns

```python
from datadetector import load_registry, Engine

# Load specific file
registry = load_registry(paths=["patterns/custom.yml"])

# Or load entire directory (includes all .yml/.yaml files)
registry = load_registry(paths=["patterns/"])

engine = Engine(registry)

# Use the pattern
result = engine.validate("EMP-123456", "custom/employee_id_01")
print(result.is_valid)  # True
```

## Examples

### Example 1: Custom ID Format

```yaml
namespace: cp
description: Company-specific patterns

patterns:
  - id: project_code_01
    location: acme
    category: other
    description: ACME project code format (PROJ-YYYY-NNN)
    pattern: 'PROJ-\d{4}-\d{3}'
    mask: "PROJ-****-***"
    examples:
      match: ["PROJ-2024-001", "PROJ-2025-999"]
      nomatch: ["PROJ-24-001", "PROJECT-2024-001"]
    policy:
      store_raw: false
      action_on_match: redact
      severity: medium
```

### Example 2: Custom ID with Verification

```yaml
namespace: cp
description: Company patterns with verification

patterns:
  - id: custom_id_01
    location: acme
    category: other
    description: Custom ID with checksum
    pattern: 'CID-\d{4}'
    verification: custom_checksum  # Reference to custom function
    examples:
      match: ["CID-1234"]
      nomatch: ["CID-12345"]
    policy:
      store_raw: false
      action_on_match: redact
      severity: medium
```

Then register the verification function:

```python
from datadetector.verification import register_verification_function

def custom_checksum(value: str) -> bool:
    """Custom checksum: sum of digits must be even."""
    digits = [int(c) for c in value if c.isdigit()]
    return sum(digits) % 2 == 0

# Register before loading patterns
register_verification_function("custom_checksum", custom_checksum)

# Now load patterns
registry = load_registry(paths=["patterns/custom.yml"])
engine = Engine(registry)
```

### Example 3: Organization-Specific Email Domains

```yaml
namespace: cp
description: Company email patterns

patterns:
  - id: company_email_01
    location: acme
    category: email
    description: ACME company email addresses
    pattern: '[a-zA-Z0-9._%+-]+@acme\.(com|org|net)'
    flags: [IGNORECASE]
    mask: "***@acme.***"
    examples:
      match:
        - "john.doe@acme.com"
        - "employee@acme.org"
      nomatch:
        - "test@example.com"
        - "user@acme.co.uk"
    policy:
      store_raw: false
      action_on_match: redact
      severity: medium
```

## Best Practices

1. **Test Your Patterns**: Always include `examples` with both `match` and `nomatch` cases
2. **Use Specific Patterns**: Make patterns as specific as possible to avoid false positives
3. **Document Well**: Write clear descriptions for each pattern
4. **Choose Appropriate Severity**: Set severity based on data sensitivity
5. **Consider Verification**: For checksummed or validated IDs, add verification functions
6. **Use Consistent Naming**: Follow the `{name}_{NN}` format for pattern IDs
7. **Organize by Namespace**: Group related patterns in the same namespace

## Validation

Validate your patterns before deployment:

```bash
# This will validate all patterns and their examples
python -c "from datadetector import load_registry; load_registry(paths=['patterns/'], validate_examples=True)"
```

## Loading Patterns

### Load from specific files:
```python
registry = load_registry(paths=[
    "patterns/common.yml",
    "patterns/custom.yml"
])
```

### Load from directory:
```python
# Loads all .yml and .yaml files in the directory
registry = load_registry(paths=["patterns/"])
```

### Skip validation during development:
```python
registry = load_registry(
    paths=["patterns/"],
    validate_schema=False,      # Skip schema validation
    validate_examples=False     # Skip example validation
)
```
