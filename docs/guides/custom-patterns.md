# Creating Custom Patterns

## Overview

While Data Detector comes with a wide range of built-in patterns, one of its most powerful features is the ability to define your own. This allows you to detect proprietary or organization-specific data formats, such as employee IDs, project codes, or internal case numbers.

This guide will walk you through the process of creating, validating, and using your own custom patterns.

## How to Create a Custom Pattern

The process involves two main steps: creating a YAML file with your pattern definitions and then loading it into the `PatternRegistry`.

### Step 1: Create a Pattern YAML File

First, create a new `.yml` file. You can place it anywhere, but we recommend keeping it in the `patterns/` directory for organizational purposes.

In this file, you'll define your patterns. Each pattern needs a unique `id`, a `location` (a code for your organization), a `category`, the `pattern` (a regex), and a `policy`.

**Example: `custom_patterns.yml`**
```yaml
# A namespace for your custom patterns
namespace: myorg
description: "Custom patterns for My Organization"

patterns:
  # A pattern for detecting employee IDs in the format EMP-######
  - id: employee_id_01
    location: myorg      # A unique code for your organization or location
    category: other      # Use 'other' for non-standard categories
    description: "Detects MyOrg employee IDs"
    pattern: 'EMP-\d{6}'
    mask: "EMP-******"
    # Provide examples for testing and validation
    examples:
      match: ["EMP-123456", "EMP-999999"]
      nomatch: ["EMP-12345", "TEMP-123456"]
    # Define how to handle matches
    policy:
      store_raw: false
      action_on_match: redact
      severity: high
```

### Step 2: Load Your Custom Patterns

When you initialize the `PatternRegistry`, simply include the path to your new file. You can load it by itself or along with the built-in patterns.

```python
from datadetector import load_registry, Engine

# Option 1: Load only your custom pattern file
registry = load_registry(paths=["patterns/custom_patterns.yml"])

# Option 2: Load an entire directory (which includes your file and others)
registry = load_registry(paths=["patterns/"])

engine = Engine(registry)

# Now you can use your custom pattern
result = engine.validate("EMP-123456", "myorg/employee_id_01")
print(result.is_valid)  # True

# It will also be used in general 'find' and 'redact' operations
redacted = engine.redact("The user is EMP-123456.")
print(redacted.redacted_text) # "The user is EMP-******."
```

## Advanced Examples

### Example 1: Custom ID with Verification Function

For patterns that require more than just a regex (e.g., a checksum validation), you can link a `verification` function.

**Pattern Definition (`custom_verify.yml`):**
```yaml
namespace: verify_co
patterns:
  - id: custom_id_01
    location: acme
    category: other
    description: "Custom ID with a checksum"
    pattern: 'CID-\d{4}'
    verification: custom_checksum  # The name of the function to call
    policy:
      store_raw: false
      action_on_match: redact
      severity: critical
```

**Function Registration (in your Python code):**
You must register the function *before* loading the patterns that use it.

```python
from datadetector.verification import register_verification_function

def is_sum_even(value: str) -> bool:
    """A simple custom checksum: returns True if the sum of digits is even."""
    digits = [int(c) for c in value if c.isdigit()]
    return sum(digits) % 2 == 0

# Register the function with the name used in the YAML file
register_verification_function("custom_checksum", is_sum_even)

# Now, when you load the registry, the 'custom_checksum' verification will be linked.
registry = load_registry(paths=["patterns/custom_verify.yml"])
engine = Engine(registry)

# This will now fail the checksum validation
engine.validate("CID-1234", "verify_co/custom_id_01") # sum is 10 (even) -> True
engine.validate("CID-1235", "verify_co/custom_id_01") # sum is 11 (odd) -> False
```

### Example 2: Organization-Specific Email Domains

You can create patterns that are more specific versions of common types, like an email address, but restricted to your own domains.

```yaml
namespace: acme_corp
patterns:
  - id: company_email_01
    location: acme
    category: email
    description: "ACME Corporation internal and external email addresses"
    pattern: '[a-zA-Z0-9._%+-]+@acme\.(com|org|net)'
    flags: [IGNORECASE]
    mask: "[EMAIL]"
    policy:
      store_raw: false
      action_on_match: redact
      severity: medium
```

## Best Practices for Creating Patterns

Following these best practices will help you create patterns that are accurate, performant, and easy to maintain.

1.  **Test Your Patterns Thoroughly**: Always include `examples` with both `match` and `nomatch` cases. This is crucial for validation and preventing regressions.
2.  **Be Specific to Avoid False Positives**: A generic pattern like `\d{6}` is fast but might incorrectly match any six-digit number. A more specific pattern like `EMP-\d{6}` is safer.
3.  **Document Clearly**: Write a clear `description` for each pattern. This helps other developers (and your future self) understand what the pattern is for.
4.  **Choose the Right Severity**: The `severity` level helps with prioritizing findings. Use `critical` for highly sensitive data like credentials and `low` for less sensitive information.
5.  **Use Verification for Complex Rules**: If a format includes a checksum or other algorithmic rule, use a `verification` function. A regex can't validate everything.
6.  **Use a Consistent Naming Convention**: A consistent naming scheme like `{name}_{NN}` for pattern IDs (e.g., `employee_id_01`, `employee_id_02`) makes patterns easier to manage.
7.  **Organize with Namespaces**: Group related patterns under a common `namespace`. This makes them easier to find and manage.

## Validating Your Custom Patterns

After creating your pattern file, you can validate it to ensure it is syntactically correct and that your examples work as expected.

The `load_registry` function can be used as a validation tool from the command line.
```bash
# This command will load all patterns and raise an error if any are invalid.
python -c "from datadetector import load_registry; load_registry(paths=['patterns/'], validate_schema=True, validate_examples=True)"
```

You can also turn off validation, for example, to speed up loading during development, though this is not recommended.
```python
registry = load_registry(
    paths=["patterns/"],
    validate_schema=False,      # Skip JSON schema validation
    validate_examples=False     # Skip testing of examples
)
```