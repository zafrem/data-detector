# Verification Functions Usage Guide

## Overview

The verification functions have been centralized in `regex-patterns/_verification/python/` to enable code reuse across different pattern detection implementations and languages.

## Directory Structure

```
regex-patterns/
├── _verification/
│   ├── README.md              # Full documentation
│   ├── USAGE.md               # This file - Quick usage guide
│   └── python/
│       ├── __init__.py        # Module exports
│       └── verification.py    # Core verification functions
├── hash/
│   └── tokens.yml             # Token pattern definitions
└── pii/
    └── *.yml                  # PII pattern definitions
```

## Quick Start (Python)

### Option 1: Import from centralized location (recommended for new code)

```python
# Direct import from verification module
from regex_patterns._verification.python import (
    high_entropy_token,
    luhn,
    iban_mod97,
    korean_bank_account_valid,
)

# Use in your code
if high_entropy_token("ghp_1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P"):
    print("High entropy token detected")
```

### Option 2: Import from datadetector (backward compatible)

```python
# Existing code continues to work
from datadetector.verification import (
    high_entropy_token,
    luhn,
    get_verification_function,
)

# The datadetector module now re-exports from centralized location
validator = get_verification_function("luhn")
is_valid = validator("4532015112830366")
```

## Available Verification Functions

| Function | Purpose | Example |
|----------|---------|---------|
| `iban_mod97` | IBAN validation | `iban_mod97("GB82WEST12345698765432")` |
| `luhn` | Luhn checksum (credit cards) | `luhn("4532015112830366")` |
| `high_entropy_token` | API keys, secrets | `high_entropy_token("ghp_...")` |
| `korean_bank_account_valid` | Korean bank accounts | `korean_bank_account_valid("110...")` |
| `korean_zipcode_valid` | Korean postal codes | `korean_zipcode_valid("06234")` |
| `us_zipcode_valid` | US ZIP codes | `us_zipcode_valid("90210")` |
| `us_ssn_valid` | US Social Security Numbers | `us_ssn_valid("123-45-6789")` |
| `not_timestamp` | Reject timestamps | `not_timestamp("1234567890")` |
| `generic_number_not_timestamp` | Generic timestamp check | `generic_number_not_timestamp(...)` |
| `contains_letter` | Has alphabetic chars | `contains_letter("ABC123")` |
| `dms_coordinate` | GPS coordinates | `dms_coordinate("37°46′29.7″N")` |

## Using in Pattern YAML Files

In your pattern definition files (e.g., `regex-patterns/hash/tokens.yml`):

```yaml
patterns:
  - id: github_token_01
    location: comm
    pattern: 'ghp_[A-Za-z0-9]{36,}'
    verification: high_entropy_token  # References the function name
    category: token
    severity: critical
```

## Implementing in Other Languages

To implement verification functions in other languages:

1. Create a directory: `regex-patterns/_verification/<language>/`
2. Implement the same functions with equivalent logic
3. Maintain consistent function signatures
4. Update the main README with usage examples

Example for Go:
```go
// regex-patterns/_verification/go/verification.go
package verification

func HighEntropyToken(value string) bool {
    // Implement same logic as Python version
    return entropy >= 4.0
}
```

## Testing

Test files are located in `tests/test_verification*.py`:

```bash
# Run verification tests
pytest tests/test_verification.py -v

# Run integration tests
pytest tests/test_verification_integration.py -v

# Run token pattern tests (uses verification)
pytest tests/test_token_patterns.py -v
```

## Benefits of Centralization

1. **Single source of truth** - One implementation used everywhere
2. **Consistency** - Same validation logic across all patterns
3. **Reusability** - Easy to use in different projects/languages
4. **Maintainability** - Update once, apply everywhere
5. **Testability** - Centralized tests cover all usage

## Migration Notes

- Existing code using `from datadetector.verification import ...` continues to work
- The `src/datadetector/verification.py` module now re-exports from centralized location
- No changes required to existing pattern YAML files
- Tests pass without modification

## See Also

- [Full Documentation](README.md) - Complete verification functions reference
- [Pattern Files](../hash/tokens.yml) - Example usage in patterns
- [Tests](../../tests/test_verification.py) - Comprehensive test suite
