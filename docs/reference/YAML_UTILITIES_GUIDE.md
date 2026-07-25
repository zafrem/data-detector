# YAML Utilities - Complete Guide

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [API Reference](#api-reference)
5. [Usage Examples](#usage-examples)
6. [Best Practices](#best-practices)
7. [Error Handling](#error-handling)
8. [Advanced Topics](#advanced-topics)

---

## Overview

The YAML utilities module (`datadetector.utils.yaml_utils`) provides a comprehensive set of tools for reading, writing, and managing YAML pattern files. It offers two main classes:

- **`YAMLHandler`** - General-purpose YAML file operations
- **`PatternFileHandler`** - Specialized pattern file management

### Why Use YAML Utilities?

- ✅ **Type-safe** - Validates data types and structure
- ✅ **Error-resistant** - Prevents accidental overwrites
- ✅ **Convenient** - Simple API for common operations
- ✅ **Pattern-aware** - Understands pattern file structure
- ✅ **Well-tested** - 100% test coverage

---

## Installation

The YAML utilities are included with the data-detector package:

```bash
pip install data-detector
```

Or install from source:

```bash
git clone https://github.com/yourusername/data-detector.git
cd data-detector
pip install -e .
```

---

## Quick Start

### Basic YAML Operations

```python
from datadetector import read_yaml, write_yaml

# Read a YAML file
data = read_yaml("config.yml")

# Write a YAML file
write_yaml("output.yml", {"key": "value"})

# Overwrite existing file
write_yaml("output.yml", {"key": "new_value"}, overwrite=True)
```

### Pattern File Operations

```python
from datadetector import PatternFileHandler

# Create a new pattern file
PatternFileHandler.create_pattern_file(
    file_path="my_patterns.yml",
    namespace="custom",
    description="My custom patterns"
)

# Add a pattern
PatternFileHandler.add_pattern_to_file("my_patterns.yml", {
    "id": "email_01",
    "location": "custom",
    "category": "email",
    "pattern": r"[a-z]+@example\.com",
    "mask": "***@example.com",
    "policy": {
        "store_raw": False,
        "action_on_match": "redact",
        "severity": "medium"
    }
})

# List all patterns
pattern_ids = PatternFileHandler.list_patterns_in_file("my_patterns.yml")
print(pattern_ids)  # ['email_01']
```

---

## API Reference

### YAMLHandler Class

#### `read_yaml(file_path: Union[str, Path]) -> Dict[str, Any]`

Reads a YAML file and returns its contents as a dictionary.

**Parameters:**
- `file_path` - Path to YAML file (string or Path object)

**Returns:**
- Dictionary containing YAML contents

**Raises:**
- `FileNotFoundError` - If file doesn't exist
- `ValueError` - If YAML is invalid or not a dictionary

**Example:**
```python
from datadetector.utils.yaml_utils import YAMLHandler

data = YAMLHandler.read_yaml("patterns/kr.yml")
print(f"Namespace: {data['namespace']}")
print(f"Patterns: {len(data['patterns'])}")
```

---

#### `write_yaml(file_path: Union[str, Path], data: Dict[str, Any], overwrite: bool = False, sort_keys: bool = False) -> None`

Writes a dictionary to a YAML file.

**Parameters:**
- `file_path` - Path to output YAML file
- `data` - Dictionary to write
- `overwrite` - If True, overwrites existing file (default: False)
- `sort_keys` - If True, sorts dictionary keys alphabetically (default: False)

**Raises:**
- `FileExistsError` - If file exists and overwrite=False
- `ValueError` - If data is not a dictionary

**Example:**
```python
from datadetector.utils.yaml_utils import YAMLHandler

# Create directory structure automatically
YAMLHandler.write_yaml(
    "output/subdir/config.yml",
    {"namespace": "test", "patterns": []},
    overwrite=True
)
```

---

#### `update_yaml(file_path: Union[str, Path], updates: Dict[str, Any], merge: bool = True) -> Dict[str, Any]`

Updates an existing YAML file with new data.

**Parameters:**
- `file_path` - Path to YAML file
- `updates` - Dictionary with updates to apply
- `merge` - If True, merges with existing data. If False, replaces completely (default: True)

**Returns:**
- Updated dictionary

**Raises:**
- `FileNotFoundError` - If file doesn't exist

**Example:**
```python
from datadetector.utils.yaml_utils import YAMLHandler

# Merge with existing content
updated = YAMLHandler.update_yaml(
    "config.yml",
    {"new_field": "new_value"},
    merge=True
)

# Replace entire content
replaced = YAMLHandler.update_yaml(
    "config.yml",
    {"completely": "new"},
    merge=False
)
```

---

### PatternFileHandler Class

#### `create_pattern_file(file_path, namespace, description, patterns=None, overwrite=False)`

Creates a new pattern YAML file.

**Parameters:**
- `file_path` - Path to output file
- `namespace` - Pattern namespace (e.g., "custom", "company")
- `description` - Description of the pattern file
- `patterns` - List of pattern definitions (optional, default: empty list)
- `overwrite` - If True, overwrites existing file (default: False)

**Example:**
```python
from datadetector import PatternFileHandler

PatternFileHandler.create_pattern_file(
    file_path="company_patterns.yml",
    namespace="company",
    description="Company-specific patterns",
    patterns=[
        {
            "id": "employee_id_01",
            "location": "company",
            "category": "other",
            "description": "Employee ID format",
            "pattern": r"EMP-\d{6}",
            "mask": "EMP-******",
            "policy": {
                "store_raw": False,
                "action_on_match": "redact",
                "severity": "medium"
            }
        }
    ]
)
```

---

#### `add_pattern_to_file(file_path, pattern)`

Adds a pattern to an existing pattern file.

**Parameters:**
- `file_path` - Path to pattern file
- `pattern` - Pattern definition dictionary

**Required Pattern Fields:**
- `id` - Pattern identifier (must match: `[a-z_][a-z0-9_]*_\d{2}`)
- `location` - Location/country code
- `category` - Category (email, phone, ssn, etc.)
- `pattern` - Regular expression pattern
- `policy` - Policy configuration with store_raw, action_on_match, severity

**Raises:**
- `FileNotFoundError` - If file doesn't exist
- `ValueError` - If pattern is missing required fields

**Example:**
```python
from datadetector import PatternFileHandler

new_pattern = {
    "id": "api_token_01",
    "location": "company",
    "category": "token",
    "description": "Internal API token",
    "pattern": r"TOK_[A-Z0-9]{40}",
    "mask": "TOK_" + "*" * 40,
    "examples": {
        "match": ["TOK_ABC123DEF456GHI789JKL012MNO345PQR678"],
        "nomatch": ["TOKEN_SHORT", "TOK-ABC123"]
    },
    "policy": {
        "store_raw": False,
        "action_on_match": "redact",
        "severity": "critical"
    }
}

PatternFileHandler.add_pattern_to_file("company_patterns.yml", new_pattern)
```

---

#### `remove_pattern_from_file(file_path, pattern_id) -> bool`

Removes a pattern from a pattern file.

**Parameters:**
- `file_path` - Path to pattern file
- `pattern_id` - ID of pattern to remove

**Returns:**
- `True` if pattern was removed, `False` if not found

**Example:**
```python
from datadetector import PatternFileHandler

# Remove pattern
success = PatternFileHandler.remove_pattern_from_file(
    "company_patterns.yml",
    "employee_id_01"
)

if success:
    print("Pattern removed successfully")
else:
    print("Pattern not found")
```

---

#### `update_pattern_in_file(file_path, pattern_id, updates) -> bool`

Updates specific fields in a pattern.

**Parameters:**
- `file_path` - Path to pattern file
- `pattern_id` - ID of pattern to update
- `updates` - Dictionary of fields to update

**Returns:**
- `True` if pattern was updated, `False` if not found

**Example:**
```python
from datadetector import PatternFileHandler

# Update pattern severity and description
success = PatternFileHandler.update_pattern_in_file(
    "company_patterns.yml",
    "api_token_01",
    {
        "description": "Updated description",
        "policy": {
            "severity": "critical",
            "action_on_match": "tokenize"
        }
    }
)
```

---

#### `get_pattern_from_file(file_path, pattern_id) -> Optional[Dict[str, Any]]`

Retrieves a specific pattern from a pattern file.

**Parameters:**
- `file_path` - Path to pattern file
- `pattern_id` - ID of pattern to retrieve

**Returns:**
- Pattern dictionary if found, `None` otherwise

**Example:**
```python
from datadetector import PatternFileHandler

pattern = PatternFileHandler.get_pattern_from_file(
    "company_patterns.yml",
    "api_token_01"
)

if pattern:
    print(f"Pattern: {pattern['pattern']}")
    print(f"Category: {pattern['category']}")
    print(f"Severity: {pattern['policy']['severity']}")
else:
    print("Pattern not found")
```

---

#### `list_patterns_in_file(file_path) -> List[str]`

Lists all pattern IDs in a pattern file.

**Parameters:**
- `file_path` - Path to pattern file

**Returns:**
- List of pattern IDs

**Example:**
```python
from datadetector import PatternFileHandler

pattern_ids = PatternFileHandler.list_patterns_in_file("company_patterns.yml")

print(f"Found {len(pattern_ids)} patterns:")
for pid in pattern_ids:
    print(f"  - {pid}")
```

---

### Convenience Functions

For quick access, you can use these module-level functions:

```python
from datadetector import read_yaml, write_yaml, update_yaml

# Read
data = read_yaml("file.yml")

# Write
write_yaml("file.yml", data, overwrite=True)

# Update
updated = update_yaml("file.yml", {"key": "value"})
```

These are shortcuts to `YAMLHandler.read_yaml()`, `YAMLHandler.write_yaml()`, and `YAMLHandler.update_yaml()`.

---

## Usage Examples

### Example 1: Create a Complete Pattern File

```python
from datadetector import PatternFileHandler

# Define multiple patterns
patterns = [
    {
        "id": "credit_card_01",
        "location": "custom",
        "category": "credit_card",
        "description": "Credit card number",
        "pattern": r"\d{4}-\d{4}-\d{4}-\d{4}",
        "mask": "****-****-****-****",
        "verification": "luhn",  # Use Luhn algorithm
        "policy": {
            "store_raw": False,
            "action_on_match": "redact",
            "severity": "critical"
        }
    },
    {
        "id": "phone_01",
        "location": "custom",
        "category": "phone",
        "description": "Phone number",
        "pattern": r"\d{3}-\d{3}-\d{4}",
        "mask": "***-***-****",
        "policy": {
            "store_raw": False,
            "action_on_match": "redact",
            "severity": "high"
        }
    }
]

# Create file
PatternFileHandler.create_pattern_file(
    file_path="sensitive_data_patterns.yml",
    namespace="sensitive",
    description="Patterns for sensitive personal data",
    patterns=patterns
)

print("✅ Created pattern file with 2 patterns")
```

---

### Example 2: Batch Update Pattern Severity

```python
from datadetector import PatternFileHandler

# Get all patterns
pattern_ids = PatternFileHandler.list_patterns_in_file("company_patterns.yml")

# Update severity for all patterns
for pattern_id in pattern_ids:
    # Get current pattern
    pattern = PatternFileHandler.get_pattern_from_file(
        "company_patterns.yml",
        pattern_id
    )

    # Update based on category
    if pattern["category"] in ["credit_card", "ssn", "token"]:
        new_severity = "critical"
    else:
        new_severity = "high"

    # Apply update
    PatternFileHandler.update_pattern_in_file(
        "company_patterns.yml",
        pattern_id,
        {"policy": {"severity": new_severity}}
    )

    print(f"Updated {pattern_id} to {new_severity}")
```

---

### Example 3: Clone and Modify Pattern File

```python
from datadetector import read_yaml, write_yaml

# Read original
original = read_yaml("patterns/kr.yml")

# Create modified version
modified = {
    "namespace": "kr_extended",
    "description": f"{original['description']} - Extended version",
    "patterns": original["patterns"].copy()
}

# Add custom patterns
custom_patterns = [
    {
        "id": "custom_kr_phone_01",
        "location": "kr",
        "category": "phone",
        "pattern": r"070-\d{4}-\d{4}",
        "mask": "070-****-****",
        "policy": {
            "store_raw": False,
            "action_on_match": "redact",
            "severity": "medium"
        }
    }
]

modified["patterns"].extend(custom_patterns)

# Write to new file
write_yaml("patterns/kr_extended.yml", modified)

print(f"✅ Created extended pattern file with {len(modified['patterns'])} patterns")
```

---

### Example 4: Pattern File Validation

```python
from datadetector import read_yaml, PatternFileHandler

def validate_pattern_file(file_path):
    """Comprehensive pattern file validation."""
    errors = []
    warnings = []

    try:
        # Read file
        data = read_yaml(file_path)

        # Check required top-level fields
        required_fields = ["namespace", "description", "patterns"]
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Check namespace format
        if "namespace" in data:
            if not data["namespace"].islower():
                warnings.append("Namespace should be lowercase")

        # Validate each pattern
        if "patterns" in data:
            pattern_fields = ["id", "location", "category", "pattern", "policy"]

            for i, pattern in enumerate(data["patterns"]):
                # Check required fields
                for field in pattern_fields:
                    if field not in pattern:
                        errors.append(f"Pattern {i}: Missing field '{field}'")

                # Check ID format
                if "id" in pattern:
                    import re
                    if not re.match(r'^[a-z_][a-z0-9_]*_\d{2}$', pattern["id"]):
                        errors.append(
                            f"Pattern {i}: ID '{pattern['id']}' doesn't match "
                            "required format (e.g., 'email_01')"
                        )

                # Check policy structure
                if "policy" in pattern:
                    policy_fields = ["store_raw", "action_on_match", "severity"]
                    for field in policy_fields:
                        if field not in pattern["policy"]:
                            errors.append(
                                f"Pattern {i}: Policy missing field '{field}'"
                            )

        # Print results
        if errors:
            print("❌ Validation failed:")
            for error in errors:
                print(f"   ERROR: {error}")

        if warnings:
            print("⚠️  Warnings:")
            for warning in warnings:
                print(f"   WARNING: {warning}")

        if not errors and not warnings:
            print("✅ Pattern file is valid!")
            print(f"   Namespace: {data['namespace']}")
            print(f"   Patterns: {len(data.get('patterns', []))}")
            return True

        return len(errors) == 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# Use validation
validate_pattern_file("my_patterns.yml")
```

---

### Example 5: Migrate Pattern Format

```python
from datadetector import read_yaml, write_yaml

def migrate_old_format(old_file, new_file):
    """Migrate from old pattern format to new format."""

    # Read old format
    old = read_yaml(old_file)

    # Convert to new format
    new = {
        "namespace": old["namespace"],
        "description": old.get("description", "Migrated patterns"),
        "patterns": []
    }

    for old_pattern in old["patterns"]:
        new_pattern = {
            "id": old_pattern["id"],
            "location": old_pattern.get("location", old["namespace"]),
            "category": old_pattern["category"],
            "pattern": old_pattern.get("regex", old_pattern.get("pattern")),
            "mask": old_pattern.get("mask", "***"),
            "policy": {
                "store_raw": old_pattern.get("store_raw", False),
                "action_on_match": old_pattern.get("action", "redact"),
                "severity": old_pattern.get("severity", "medium")
            }
        }

        # Migrate optional fields
        if "examples" in old_pattern:
            new_pattern["examples"] = old_pattern["examples"]

        if "verification" in old_pattern:
            new_pattern["verification"] = old_pattern["verification"]

        if "metadata" in old_pattern:
            new_pattern["metadata"] = old_pattern["metadata"]

        new["patterns"].append(new_pattern)

    # Write new format
    write_yaml(new_file, new)

    print(f"✅ Migrated {len(new['patterns'])} patterns")
    print(f"   From: {old_file}")
    print(f"   To: {new_file}")

# Run migration
migrate_old_format("old_patterns.yml", "new_patterns.yml")
```

---

### Example 6: Dynamic Pattern Generation

```python
from datadetector import PatternFileHandler

def generate_ip_range_patterns(namespace="network", start_range=0, end_range=255):
    """Generate patterns for IP address ranges."""

    patterns = []

    # Generate pattern for each range
    for i in range(start_range, end_range + 1, 10):
        pattern_id = f"ip_range_{i:03d}"

        pattern = {
            "id": pattern_id,
            "location": namespace,
            "category": "ip",
            "description": f"IP range {i}.x.x.x",
            "pattern": rf"{i}\.\d{{1,3}}\.\d{{1,3}}\.\d{{1,3}}",
            "mask": f"{i}.*.*.*",
            "policy": {
                "store_raw": False,
                "action_on_match": "report",
                "severity": "low"
            }
        }

        patterns.append(pattern)

    # Create pattern file
    PatternFileHandler.create_pattern_file(
        file_path=f"{namespace}_ip_patterns.yml",
        namespace=namespace,
        description=f"Auto-generated IP range patterns",
        patterns=patterns,
        overwrite=True
    )

    print(f"✅ Generated {len(patterns)} IP range patterns")

# Generate patterns
generate_ip_range_patterns()
```

---

### Example 7: Backup and Restore

```python
from datadetector import read_yaml, write_yaml
import shutil
from datetime import datetime

def backup_pattern_file(file_path):
    """Create timestamped backup of pattern file."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_{timestamp}"

    # Read and write (preserves YAML formatting)
    data = read_yaml(file_path)
    write_yaml(backup_path, data)

    print(f"✅ Backup created: {backup_path}")
    return backup_path

def restore_pattern_file(backup_path, target_path):
    """Restore pattern file from backup."""

    data = read_yaml(backup_path)
    write_yaml(target_path, data, overwrite=True)

    print(f"✅ Restored from: {backup_path}")
    print(f"   To: {target_path}")

# Usage
backup = backup_pattern_file("important_patterns.yml")

# Later... restore if needed
# restore_pattern_file(backup, "important_patterns.yml")
```

---

## Best Practices

### 1. **Always Backup Before Modifications**

```python
from datadetector import read_yaml, write_yaml

# Create backup before modifying
backup_data = read_yaml("patterns.yml")
write_yaml("patterns.yml.backup", backup_data)

# Now safe to modify
# ...
```

### 2. **Use Validation**

```python
from datadetector import load_registry

# Validate patterns after creation
try:
    registry = load_registry(
        paths=["my_patterns.yml"],
        validate_schema=True,
        validate_examples=True
    )
    print("✅ Patterns are valid")
except ValueError as e:
    print(f"❌ Validation failed: {e}")
```

### 3. **Follow Naming Conventions**

```python
# Good pattern IDs
"email_01"
"phone_01"
"credit_card_visa_01"

# Bad pattern IDs
"Email01"          # Should be lowercase
"phone"            # Missing number suffix
"credit-card-01"   # Use underscores, not hyphens
```

### 4. **Include Examples**

```python
pattern = {
    "id": "custom_id_01",
    "location": "custom",
    "category": "other",
    "pattern": r"ID-\d{8}",
    "mask": "ID-********",
    "examples": {  # Always include examples
        "match": ["ID-12345678", "ID-00000001"],
        "nomatch": ["ID-123", "ID12345678"]
    },
    "policy": {...}
}
```

### 5. **Set Appropriate Severity**

```python
# Critical - Immediate security risk
"severity": "critical"  # Credit cards, SSN, passwords

# High - Significant privacy concern
"severity": "high"      # Phone numbers, email, addresses

# Medium - Moderate sensitivity
"severity": "medium"    # Internal IDs, non-critical PII

# Low - Low sensitivity
"severity": "low"       # Public information, metadata
```

### 6. **Use Descriptive Descriptions**

```python
# Good
"description": "Employee ID in format EMP-NNNNNN where N is digit"

# Bad
"description": "Employee ID"
```

### 7. **Test Patterns Before Deployment**

```python
from datadetector import Engine, load_registry

# Load and test
registry = load_registry(paths=["my_patterns.yml"], validate_examples=False)
engine = Engine(registry)

# Test with sample data
test_cases = [
    "Employee EMP-123456 called",
    "Contact: 010-1234-5678",
    "Email: test@example.com"
]

for text in test_cases:
    result = engine.find(text, namespaces=["custom"])
    print(f"Text: {text}")
    print(f"Matches: {result.match_count}")
```

---

## Error Handling

### Common Errors and Solutions

#### FileNotFoundError

```python
from datadetector import read_yaml

try:
    data = read_yaml("nonexistent.yml")
except FileNotFoundError as e:
    print(f"File not found: {e}")
    # Create default file
    write_yaml("nonexistent.yml", {"namespace": "default", "patterns": []})
```

#### FileExistsError

```python
from datadetector import write_yaml

try:
    write_yaml("existing.yml", data)
except FileExistsError:
    print("File exists. Use overwrite=True to replace")
    write_yaml("existing.yml", data, overwrite=True)
```

#### ValueError (Invalid YAML)

```python
from datadetector import read_yaml

try:
    data = read_yaml("invalid.yml")
except ValueError as e:
    print(f"Invalid YAML: {e}")
    # Fix the file manually or create new one
```

#### ValueError (Missing Required Fields)

```python
from datadetector import PatternFileHandler

try:
    PatternFileHandler.add_pattern_to_file("file.yml", {"id": "test"})
except ValueError as e:
    print(f"Invalid pattern: {e}")
    # Add required fields: location, category, pattern, policy
```

---

## Advanced Topics

### Working with Large Pattern Files

```python
from datadetector import read_yaml, write_yaml

# Read large file
data = read_yaml("large_patterns.yml")

# Process in chunks
chunk_size = 100
patterns = data["patterns"]

for i in range(0, len(patterns), chunk_size):
    chunk = patterns[i:i + chunk_size]

    # Process chunk
    for pattern in chunk:
        # Modify pattern
        pass

    # Write progress
    if i % 500 == 0:
        print(f"Processed {i}/{len(patterns)} patterns")

# Write back
write_yaml("large_patterns.yml", data, overwrite=True)
```

### Custom Validation Functions

```python
from datadetector import read_yaml

def validate_custom_requirements(file_path):
    """Custom validation logic."""
    data = read_yaml(file_path)

    # Company-specific requirements
    for pattern in data["patterns"]:
        # Must have description
        if "description" not in pattern or len(pattern["description"]) < 10:
            raise ValueError(f"Pattern {pattern['id']}: Description too short")

        # Must have examples
        if "examples" not in pattern:
            raise ValueError(f"Pattern {pattern['id']}: Missing examples")

        # Critical patterns must not store raw
        if pattern["policy"]["severity"] == "critical":
            if pattern["policy"]["store_raw"]:
                raise ValueError(f"Pattern {pattern['id']}: Critical patterns cannot store raw data")

    print("✅ Custom validation passed")

validate_custom_requirements("company_patterns.yml")
```

### Integration with CI/CD

```python
#!/usr/bin/env python3
"""CI/CD validation script for pattern files."""

import sys
from pathlib import Path
from datadetector import load_registry, read_yaml

def validate_all_patterns(pattern_dir="patterns"):
    """Validate all pattern files in directory."""

    pattern_files = list(Path(pattern_dir).glob("*.yml"))

    if not pattern_files:
        print(f"❌ No pattern files found in {pattern_dir}")
        return False

    print(f"Validating {len(pattern_files)} pattern files...")

    errors = []

    for file in pattern_files:
        try:
            # Schema validation
            data = read_yaml(file)

            # Load with validation
            registry = load_registry(
                paths=[str(file)],
                validate_schema=True,
                validate_examples=True
            )

            print(f"✅ {file.name}: {len(registry)} patterns")

        except Exception as e:
            errors.append(f"{file.name}: {str(e)}")
            print(f"❌ {file.name}: {str(e)}")

    if errors:
        print(f"\n❌ Validation failed with {len(errors)} errors")
        return False

    print(f"\n✅ All {len(pattern_files)} files validated successfully")
    return True

if __name__ == "__main__":
    success = validate_all_patterns()
    sys.exit(0 if success else 1)
```

---

## See Also

- [Architecture](./ARCHITECTURE.md) - System architecture and design overview
- [Pattern Schema](../schemas/pattern-schema.json) - JSON schema for pattern files
- [Engine API](./engine.md) - Using patterns with the detection engine
- [Verification Functions](./verification.md) - Custom validation logic
- [Testing Guide](../TESTING.md) - Testing your patterns

---

## Contributing

Found a bug or have a feature request? Please open an issue on GitHub!

---

**Last Updated:** 2025-10-11
**Version:** 1.0.0
