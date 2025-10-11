# Verification Functions

## Overview

Verification functions provide additional validation after regex matching. They're useful for patterns with checksums, validation algorithms, or complex business logic that can't be expressed in regex alone.

## How It Works

1. Regex pattern matches the text
2. If `verification` is specified, the matched value is passed to the verification function
3. Only if **both** regex and verification pass, the match is considered valid

## Built-in Verification Functions

### IBAN Mod-97

Validates International Bank Account Numbers using the Mod-97 algorithm.

```yaml
- id: iban_01
  location: co
  category: iban
  pattern: '[A-Z]{2}\d{2}[A-Z0-9]{11,30}'
  verification: iban_mod97
```

Example:
```python
from datadetector.verification import iban_mod97

print(iban_mod97("GB82WEST12345698765432"))  # True (valid)
print(iban_mod97("GB82WEST12345698765433"))  # False (invalid check digit)
```

### Luhn Algorithm

Validates numbers using the Luhn checksum algorithm (credit cards, some national IDs).

```yaml
- id: credit_card_visa_01
  location: co
  category: credit_card
  pattern: '4[0-9]{12}(?:[0-9]{3})?'
  verification: luhn
```

Example:
```python
from datadetector.verification import luhn

print(luhn("4532015112830366"))  # True (valid Visa)
print(luhn("4532015112830367"))  # False (invalid check digit)
```

## Creating Custom Verification Functions

### 1. Define Your Function

```python
def custom_checksum(value: str) -> bool:
    """
    Custom verification logic.

    Args:
        value: The matched string from regex

    Returns:
        True if valid, False otherwise
    """
    # Example: Sum of digits must be even
    digits = [int(c) for c in value if c.isdigit()]
    return sum(digits) % 2 == 0
```

### 2. Register the Function

```python
from datadetector.verification import register_verification_function

register_verification_function("custom_checksum", custom_checksum)
```

### 3. Reference in Pattern

```yaml
patterns:
  - id: custom_id_01
    location: myorg
    category: other
    pattern: 'CID-\d{4}'
    verification: custom_checksum  # Reference by name
```

### 4. Use in Code

```python
from datadetector import Engine, load_registry
from datadetector.verification import register_verification_function

# Register custom function
def custom_checksum(value: str) -> bool:
    digits = [int(c) for c in value if c.isdigit()]
    return sum(digits) % 2 == 0

register_verification_function("custom_checksum", custom_checksum)

# Load patterns (must be after registration)
registry = load_registry(paths=["patterns/custom.yml"])
engine = Engine(registry)

# Validate
result = engine.validate("CID-1234", "myorg/custom_id_01")  # True (1+2+3+4=10, even)
result = engine.validate("CID-1235", "myorg/custom_id_01")  # False (1+2+3+5=11, odd)
```

## Advanced Examples

### Example 1: ISBN-10 Validation

```python
def isbn10_check(value: str) -> bool:
    """Validate ISBN-10 check digit."""
    digits = [int(c) if c.isdigit() else 10 for c in value if c.isdigit() or c == 'X']
    if len(digits) != 10:
        return False
    checksum = sum((10 - i) * digit for i, digit in enumerate(digits))
    return checksum % 11 == 0

register_verification_function("isbn10", isbn10_check)
```

Pattern:
```yaml
- id: isbn10_01
  location: intl
  category: other
  description: ISBN-10 with check digit validation
  pattern: '(?:\d{9}[\dX]|\d-\d{3}-\d{5}-[\dX])'
  verification: isbn10
```

### Example 2: Custom Business Logic

```python
def valid_department_code(value: str) -> bool:
    """Validate department code against allowed departments."""
    allowed_depts = {'ENG', 'SLS', 'MKT', 'HR', 'FIN'}
    dept = value.split('-')[0]
    return dept in allowed_depts

register_verification_function("dept_code", valid_department_code)
```

Pattern:
```yaml
- id: dept_employee_id_01
  location: acme
  category: other
  pattern: '[A-Z]{3}-\d{6}'
  verification: dept_code
  examples:
    match: ["ENG-123456", "SLS-999999"]
    nomatch: ["XXX-123456", "ENG-12345"]
```

### Example 3: Date Range Validation

```python
from datetime import datetime

def valid_date_range(value: str) -> bool:
    """Check if date is within allowed range."""
    try:
        # Assuming format YYYY-MM-DD
        date = datetime.strptime(value, '%Y-%m-%d')
        start = datetime(2020, 1, 1)
        end = datetime(2030, 12, 31)
        return start <= date <= end
    except ValueError:
        return False

register_verification_function("date_range", valid_date_range)
```

## Management Functions

### Get Verification Function

```python
from datadetector.verification import get_verification_function

func = get_verification_function("iban_mod97")
if func:
    print(func("GB82WEST12345698765432"))
```

### Unregister Function

```python
from datadetector.verification import unregister_verification_function

result = unregister_verification_function("custom_checksum")
print(result)  # True if removed, False if not found
```

### List Available Functions

```python
from datadetector.verification import VERIFICATION_FUNCTIONS

print(list(VERIFICATION_FUNCTIONS.keys()))
# ['iban_mod97', 'luhn', ...]
```

## Best Practices

1. **Keep Functions Pure**: Verification functions should be stateless and deterministic
2. **Handle Errors Gracefully**: Return `False` for invalid input, don't raise exceptions
3. **Optimize Performance**: Verification runs on every match, so keep it fast
4. **Document Thoroughly**: Explain the validation logic in docstrings
5. **Test Extensively**: Write unit tests for your verification functions
6. **Register Early**: Register custom functions before loading patterns
7. **Use Meaningful Names**: Choose clear, descriptive function names

## Testing Verification

```python
# Test standalone
from datadetector.verification import iban_mod97

assert iban_mod97("GB82WEST12345698765432") == True
assert iban_mod97("GB82WEST12345698765433") == False

# Test with engine
from datadetector import Engine, load_registry

registry = load_registry(paths=["patterns/common.yml"])
engine = Engine(registry)

# Valid IBAN - passes both regex and verification
result = engine.validate("GB82WEST12345698765432", "co/iban_01")
assert result.is_valid == True

# Invalid IBAN - passes regex but fails verification
result = engine.validate("GB82WEST12345698765433", "co/iban_01")
assert result.is_valid == False
```

## Examples in Pattern Files

The verification is applied automatically when patterns are loaded:

```yaml
patterns:
  # IBAN with verification
  - id: iban_01
    pattern: '[A-Z]{2}\d{2}[A-Z0-9]{11,30}'
    verification: iban_mod97
    examples:
      match: ["GB82WEST12345698765432"]  # Valid IBAN
      nomatch:
        - "GB82WEST1234569876543"  # Too short
        - "ABCD1234567890123456"   # Invalid check digits

  # Credit card with Luhn
  - id: visa_card_01
    pattern: '4[0-9]{15}'
    verification: luhn
    examples:
      match: ["4532015112830366"]   # Valid Visa
      nomatch: ["4532015112830367"]  # Invalid check digit
```

The example validation automatically considers verification, so patterns that fail verification won't pass the `nomatch` test even if they match the regex.
