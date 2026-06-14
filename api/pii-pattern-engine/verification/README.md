# Verification Functions

This directory contains reusable verification functions for pattern validation across different implementations.

## Structure

```
verification/
├── README.md           # This file
├── python/             # Python implementation
│   ├── __init__.py     # Module exports
│   └── verification.py # Verification functions
├── javascript/         # JavaScript implementation
│   └── verification.js # Verification functions
├── golang/             # Go implementation
│   └── verification.go # Verification functions
└── java/               # Java implementation
    └── src/main/java/com/piipatternengine/verification/Verification.java
```

## Python Verification Functions

The Python verification module provides functions for validating matched patterns beyond simple regex matching.

### Available Functions

#### Financial Validators
- `iban_mod97(value)` - IBAN Mod-97 checksum validation
- `luhn(value)` - Luhn algorithm (credit cards, etc.)
- `korean_bank_account_valid(value)` - Korean bank account validation

#### Geographic Validators
- `dms_coordinate(value)` - DMS coordinate format validation
- `korean_zipcode_valid(value)` - Korean postal code validation
- `us_zipcode_valid(value)` - US ZIP code validation

#### Token/Secret Validators
- `high_entropy_token(value)` - High-entropy token detection (API keys, secrets)

#### Identity Validators
- `us_ssn_valid(value)` - US Social Security Number validation

#### Generic Validators
- `not_timestamp(value)` - Reject timestamp-like numeric strings
- `generic_number_not_timestamp(value)` - Generic timestamp rejection
- `contains_letter(value)` - Check if string contains letters

### Usage in Python

```python
# Import from the verification module
from pii_pattern_engine.verification.python import high_entropy_token, luhn

# Use in pattern validation
if high_entropy_token("ghp_1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P7q8R9s0T"):
    print("Valid high-entropy token")

if luhn("4532015112830366"):
    print("Valid credit card number")
```

### Adding Custom Verification Functions

```python
from pii_pattern_engine.verification.python import register_verification_function

def custom_verify(value: str) -> bool:
    # Your custom validation logic
    return len(value) > 10

register_verification_function("custom", custom_verify)
```

## Using in Other Languages

The following language implementations are currently supported:

### JavaScript

```javascript
const { high_entropy_token, luhn } = require("./javascript/verification");

if (high_entropy_token("ghp_1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P7q8R9s0T")) {
    console.log("Valid high-entropy token");
}
```

### Go

```go
import "verification/golang/verification"

if verification.HighEntropyToken("ghp_1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P7q8R9s0T") {
    fmt.Println("Valid high-entropy token")
}
```

### Java

```java
import com.piipatternengine.verification.Verification;

if (Verification.highEntropyToken("ghp_1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P7q8R9s0T")) {
    System.out.println("Valid high-entropy token");
}
```

## Function Signature

All verification functions should follow this signature:

- **Input**: A string value to validate
- **Output**: Boolean (true if valid, false otherwise)
- **Side effects**: None (pure functions)

## Testing

Each verification function should have corresponding tests that verify:
- Valid inputs return true
- Invalid inputs return false
- Edge cases are handled correctly
- Performance is acceptable for large-scale validation

## Contributing

When adding new verification functions:

1. Add the function to the appropriate language directory
2. Document the function with clear docstrings/comments
3. Add the function to the registry (VERIFICATION_FUNCTIONS dict in Python)
4. Update this README with the new function
5. Add comprehensive tests
