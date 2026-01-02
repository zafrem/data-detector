# Verification Functions Guide

## Overview

Verification functions are a powerful feature that allows you to add an extra layer of validation on top of a regular expression match. While a regex can check the *format* of a piece of data (e.g., "is it a 16-digit number?"), a verification function can check its *semantic validity* (e.g., "does this 16-digit number pass the Luhn checksum algorithm for credit cards?").

This is essential for accurately detecting complex data types like credit card numbers, bank account numbers, and many national ID numbers, which have built-in validation rules.

## How Verification Works

The validation process happens in two stages:

1.  **Regex Match**: First, the engine uses the pattern's regular expression to find a potential match in the text.
2.  **Verification Function**: If a match is found AND the pattern has a `verification` field, the matched text is passed to the specified verification function.

A piece of data is only considered a valid match if it passes **both** the regex and the verification function.

## Built-in Verification Functions

Data Detector comes with several common verification functions built-in.

### `iban_mod97`

Validates an International Bank Account Number (IBAN) using the MOD-97 checksum algorithm.

**Pattern Usage:**
```yaml
- id: iban_01
  location: comm
  category: iban
  pattern: '[A-Z]{2}\d{2}[A-Z0-9]{11,30}'
  verification: iban_mod97
```

### `luhn`

Validates a number using the Luhn algorithm. This is widely used for credit card numbers and some national ID numbers.

**Pattern Usage:**
```yaml
- id: credit_card_01
  location: comm
  category: credit_card
  pattern: '\d{13,19}'
  verification: luhn
```

## Creating Custom Verification Functions

You can easily create and register your own verification functions to handle any custom validation logic your organization needs.

### Step 1: Define the Function

A verification function is a simple Python function that takes one argument (the matched string) and returns `True` if it's valid or `False` if it's not.

```python
# A simple custom checksum: returns True if the sum of the digits is even.
def checksum_is_even(value: str) -> bool:
    """
    Checks if the sum of the digits in the string is an even number.

    Args:
        value: The matched string from the regex.

    Returns:
        True if the sum of digits is even, False otherwise.
    """
    try:
        digits = [int(c) for c in value if c.isdigit()]
        return sum(digits) % 2 == 0
    except (ValueError, TypeError):
        # Always return False if the input is malformed.
        return False
```

### Step 2: Register the Function

Before you can use your function in a pattern, you must register it with a unique name. This must be done *before* you load the patterns that use it.

```python
from datadetector.verification import register_verification_function

register_verification_function("checksum_is_even", checksum_is_even)
```

### Step 3: Reference it in a Pattern

In your YAML pattern file, use the registered name in the `verification` field.

```yaml
# In custom_patterns.yml
namespace: myorg
patterns:
  - id: custom_id_01
    location: myorg
    category: other
    pattern: 'CID-\d{4}'
    verification: checksum_is_even  # Use the registered name
```

### Step 4: Putting it all together

Here is a complete example of how to register and use a custom verification function.

```python
from datadetector import Engine, load_registry
from datadetector.verification import register_verification_function

# 1. Define the custom function
def checksum_is_even(value: str) -> bool:
    digits = [int(c) for c in value if c.isdigit()]
    return sum(digits) % 2 == 0

# 2. Register it with a unique name
register_verification_function("checksum_is_even", checksum_is_even)

# 3. Load the registry (Data Detector will link the function to the pattern)
registry = load_registry(paths=["patterns/custom_patterns.yml"])
engine = Engine(registry)

# 4. Validate data
# Passes: 1+2+3+4 = 10 (even)
result1 = engine.validate("CID-1234", "myorg/custom_id_01")
print(f"CID-1234 is valid: {result1.is_valid}")  # True

# Fails: 1+2+3+5 = 11 (odd)
result2 = engine.validate("CID-1235", "myorg/custom_id_01")
print(f"CID-1235 is valid: {result2.is_valid}")  # False
```

## Best Practices

1.  **Keep Functions Pure and Stateless**: A verification function should always return the same output for the same input. It should not rely on global state or external services, as this can lead to unpredictable behavior.
2.  **Handle Errors Gracefully**: The function should never raise an exception for invalid input. Always wrap your logic in a `try...except` block and return `False` if an error occurs.
3.  **Optimize for Performance**: Verification functions are executed for every potential match, so they need to be fast. Avoid slow operations like network requests or complex computations if possible.
4.  **Document and Test Thoroughly**: Write clear docstrings explaining what your function does and write unit tests to ensure it works correctly for both valid and invalid inputs.
5.  **Register Early**: Always register your custom functions before you call `load_registry`. The registry needs to know about the function when it's compiling the patterns.
6.  **Use Meaningful Names**: Choose a clear and descriptive name for your function when you register it. This makes your pattern files easier to understand.

## Managing Verification Functions

You can programmatically manage the registered functions.

-   **Get a function**: `get_verification_function(name)`
-   **Unregister a function**: `unregister_verification_function(name)`
-   **List all functions**: `list(VERIFICATION_FUNCTIONS.keys())`

```python
from datadetector.verification import get_verification_function, unregister_verification_function, VERIFICATION_FUNCTIONS

# Get a built-in function
luhn_func = get_verification_function("luhn")
if luhn_func:
    print(luhn_func("4532015112830366")) # True

# Unregister a custom function
unregister_verification_function("checksum_is_even")

# See what's available
print(list(VERIFICATION_FUNCTIONS.keys()))
# ['iban_mod97', 'luhn']
```