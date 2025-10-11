# YAML Utilities Documentation

The `yaml_utils` module provides comprehensive YAML file read/write utilities for creating and managing pattern files.

## Table of Contents

- [Overview](#overview)
- [Basic YAML Operations](#basic-yaml-operations)
- [Pattern File Management](#pattern-file-management)
- [API Reference](#api-reference)
- [Examples](#examples)

## Overview

The YAML utilities provide two main classes:

1. **`YAMLHandler`** - General YAML read/write operations
2. **`PatternFileHandler`** - Specialized operations for pattern files

Additionally, convenience functions are provided for common operations.

## Basic YAML Operations

### Reading YAML Files

```python
from datadetector import read_yaml

# Read a YAML file
data = read_yaml("config.yml")
print(data)
```

Using the class directly:

```python
from datadetector.yaml_utils import YAMLHandler

data = YAMLHandler.read_yaml("config.yml")
```

### Writing YAML Files

```python
from datadetector import write_yaml

data = {
    "namespace": "custom",
    "description": "My custom patterns",
    "patterns": []
}

# Write new file (fails if exists)
write_yaml("my_patterns.yml", data)

# Overwrite existing file
write_yaml("my_patterns.yml", data, overwrite=True)

# Write with sorted keys
write_yaml("my_patterns.yml", data, sort_keys=True)
```

### Updating YAML Files

```python
from datadetector import update_yaml

# Merge with existing data (default)
updated_data = update_yaml("config.yml", {"new_key": "new_value"})

# Replace entire content
updated_data = update_yaml("config.yml", {"new_key": "new_value"}, merge=False)
```

## Pattern File Management

### Creating Pattern Files

```python
from datadetector import PatternFileHandler

# Create a new pattern file
PatternFileHandler.create_pattern_file(
    file_path="my_patterns.yml",
    namespace="custom",
    description="My custom patterns for emails and phones",
    patterns=[
        {
            "id": "custom_email_01",
            "location": "custom",
            "category": "email",
            "description": "Custom email pattern",
            "pattern": r"[a-zA-Z0-9._%+-]+@company\.com",
            "mask": "***@company.com",
            "policy": {
                "store_raw": False,
                "action_on_match": "redact",
                "severity": "high"
            }
        }
    ]
)
```

### Adding Patterns

```python
from datadetector import PatternFileHandler

# Define a new pattern
new_pattern = {
    "id": "custom_phone_01",
    "location": "custom",
    "category": "phone",
    "description": "Internal phone format",
    "pattern": r"\d{4}-\d{4}",
    "mask": "****-****",
    "examples": {
        "match": ["1234-5678", "9999-0000"],
        "nomatch": ["123-4567", "12345678"]
    },
    "policy": {
        "store_raw": False,
        "action_on_match": "redact",
        "severity": "medium"
    }
}

# Add to existing file
PatternFileHandler.add_pattern_to_file("my_patterns.yml", new_pattern)
```

### Updating Patterns

```python
from datadetector import PatternFileHandler

# Update specific fields in a pattern
PatternFileHandler.update_pattern_in_file(
    file_path="my_patterns.yml",
    pattern_id="custom_email_01",
    updates={
        "pattern": r"[a-zA-Z0-9._%+-]+@(company|enterprise)\.com",
        "description": "Updated email pattern with multiple domains"
    }
)
```

### Removing Patterns

```python
from datadetector import PatternFileHandler

# Remove a pattern by ID
success = PatternFileHandler.remove_pattern_from_file(
    file_path="my_patterns.yml",
    pattern_id="custom_email_01"
)

if success:
    print("Pattern removed successfully")
else:
    print("Pattern not found")
```

### Querying Patterns

```python
from datadetector import PatternFileHandler

# Get a specific pattern
pattern = PatternFileHandler.get_pattern_from_file(
    file_path="my_patterns.yml",
    pattern_id="custom_email_01"
)

if pattern:
    print(f"Pattern: {pattern['pattern']}")
    print(f"Category: {pattern['category']}")

# List all pattern IDs in a file
pattern_ids = PatternFileHandler.list_patterns_in_file("my_patterns.yml")
print(f"Found {len(pattern_ids)} patterns:")
for pid in pattern_ids:
    print(f"  - {pid}")
```

## API Reference

### YAMLHandler

#### `read_yaml(file_path: Union[str, Path]) -> Dict[str, Any]`

Read a YAML file and return its contents as a dictionary.

**Parameters:**
- `file_path`: Path to YAML file

**Returns:**
- Dictionary containing YAML contents

**Raises:**
- `FileNotFoundError`: If file doesn't exist
- `ValueError`: If YAML is invalid or not a dictionary

---

#### `write_yaml(file_path: Union[str, Path], data: Dict[str, Any], overwrite: bool = False, sort_keys: bool = False) -> None`

Write a dictionary to a YAML file.

**Parameters:**
- `file_path`: Path to output YAML file
- `data`: Dictionary to write
- `overwrite`: If True, overwrite existing file (default: False)
- `sort_keys`: If True, sort dictionary keys alphabetically (default: False)

**Raises:**
- `FileExistsError`: If file exists and overwrite=False
- `ValueError`: If data is not a dictionary

---

#### `update_yaml(file_path: Union[str, Path], updates: Dict[str, Any], merge: bool = True) -> Dict[str, Any]`

Update an existing YAML file with new data.

**Parameters:**
- `file_path`: Path to YAML file
- `updates`: Dictionary with updates to apply
- `merge`: If True, merge with existing data. If False, replace completely (default: True)

**Returns:**
- Updated dictionary

**Raises:**
- `FileNotFoundError`: If file doesn't exist

---

### PatternFileHandler

#### `create_pattern_file(file_path: Union[str, Path], namespace: str, description: str, patterns: Optional[List[Dict[str, Any]]] = None, overwrite: bool = False) -> None`

Create a new pattern YAML file.

**Parameters:**
- `file_path`: Path to output file
- `namespace`: Pattern namespace
- `description`: Description of the pattern file
- `patterns`: List of pattern definitions (optional)
- `overwrite`: If True, overwrite existing file (default: False)

---

#### `add_pattern_to_file(file_path: Union[str, Path], pattern: Dict[str, Any]) -> None`

Add a pattern to an existing pattern file.

**Parameters:**
- `file_path`: Path to pattern file
- `pattern`: Pattern definition to add (must include: id, location, category, pattern, policy)

**Raises:**
- `FileNotFoundError`: If file doesn't exist
- `ValueError`: If pattern is missing required fields

---

#### `remove_pattern_from_file(file_path: Union[str, Path], pattern_id: str) -> bool`

Remove a pattern from a pattern file.

**Parameters:**
- `file_path`: Path to pattern file
- `pattern_id`: ID of pattern to remove

**Returns:**
- `True` if pattern was removed, `False` if not found

---

#### `update_pattern_in_file(file_path: Union[str, Path], pattern_id: str, updates: Dict[str, Any]) -> bool`

Update a pattern in a pattern file.

**Parameters:**
- `file_path`: Path to pattern file
- `pattern_id`: ID of pattern to update
- `updates`: Dictionary of fields to update

**Returns:**
- `True` if pattern was updated, `False` if not found

---

#### `get_pattern_from_file(file_path: Union[str, Path], pattern_id: str) -> Optional[Dict[str, Any]]`

Get a specific pattern from a pattern file.

**Parameters:**
- `file_path`: Path to pattern file
- `pattern_id`: ID of pattern to retrieve

**Returns:**
- Pattern dictionary if found, `None` otherwise

---

#### `list_patterns_in_file(file_path: Union[str, Path]) -> List[str]`

List all pattern IDs in a pattern file.

**Parameters:**
- `file_path`: Path to pattern file

**Returns:**
- List of pattern IDs

---

### Convenience Functions

```python
from datadetector import read_yaml, write_yaml, update_yaml

# These are shortcuts to YAMLHandler methods
data = read_yaml("file.yml")
write_yaml("file.yml", data, overwrite=True)
updated = update_yaml("file.yml", {"key": "value"})
```

## Examples

### Example 1: Create a Complete Pattern File

```python
from datadetector import PatternFileHandler

# Define patterns
patterns = [
    {
        "id": "employee_id_01",
        "location": "company",
        "category": "identifier",
        "description": "Employee ID format",
        "pattern": r"EMP-\d{6}",
        "mask": "EMP-******",
        "examples": {
            "match": ["EMP-123456", "EMP-999999"],
            "nomatch": ["EMP-12345", "EMPLOYEE-123456"]
        },
        "policy": {
            "store_raw": False,
            "action_on_match": "redact",
            "severity": "medium"
        }
    },
    {
        "id": "department_code_01",
        "location": "company",
        "category": "identifier",
        "description": "Department code",
        "pattern": r"DEPT-[A-Z]{3}",
        "mask": "DEPT-***",
        "policy": {
            "store_raw": True,
            "action_on_match": "report",
            "severity": "low"
        }
    }
]

# Create file
PatternFileHandler.create_pattern_file(
    file_path="company_patterns.yml",
    namespace="company",
    description="Company-specific patterns for internal use",
    patterns=patterns
)
```

### Example 2: Batch Update Patterns

```python
from datadetector import PatternFileHandler

# Get all patterns
pattern_ids = PatternFileHandler.list_patterns_in_file("company_patterns.yml")

# Update severity for all patterns
for pattern_id in pattern_ids:
    PatternFileHandler.update_pattern_in_file(
        "company_patterns.yml",
        pattern_id,
        {"policy": {"severity": "high"}}
    )
```

### Example 3: Clone and Modify Pattern File

```python
from datadetector import read_yaml, write_yaml

# Read existing pattern file
original = read_yaml("patterns/kr.yml")

# Modify namespace and description
modified = {
    "namespace": "kr_extended",
    "description": f"{original['description']} - Extended version",
    "patterns": original["patterns"]
}

# Add a new pattern
new_pattern = {
    "id": "custom_kr_01",
    "location": "kr",
    "category": "other",
    "pattern": r"custom_pattern",
    "policy": {"store_raw": False, "action_on_match": "redact", "severity": "low"}
}
modified["patterns"].append(new_pattern)

# Write to new file
write_yaml("patterns/kr_extended.yml", modified)
```

### Example 4: Migrate Pattern Format

```python
from datadetector import read_yaml, write_yaml

# Read old format
old_patterns = read_yaml("old_patterns.yml")

# Convert to new format
new_patterns = {
    "namespace": old_patterns["namespace"],
    "description": old_patterns.get("description", "Migrated patterns"),
    "patterns": []
}

for old_pattern in old_patterns["patterns"]:
    new_pattern = {
        "id": old_pattern["id"],
        "location": old_pattern.get("location", old_patterns["namespace"]),
        "category": old_pattern["category"],
        "pattern": old_pattern["regex"],  # Field name changed
        "mask": old_pattern.get("mask", "***"),
        "policy": {
            "store_raw": old_pattern.get("store_raw", False),
            "action_on_match": old_pattern.get("action", "redact"),
            "severity": old_pattern.get("severity", "medium")
        }
    }
    new_patterns["patterns"].append(new_pattern)

# Write new format
write_yaml("new_patterns.yml", new_patterns)
```

### Example 5: Validate Pattern File

```python
from datadetector import PatternFileHandler, read_yaml

def validate_pattern_file(file_path):
    """Validate a pattern file structure."""
    try:
        data = read_yaml(file_path)

        # Check required top-level fields
        required_fields = ["namespace", "description", "patterns"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            print(f"❌ Missing required fields: {missing}")
            return False

        # Check each pattern
        pattern_fields = ["id", "location", "category", "pattern", "policy"]
        for i, pattern in enumerate(data["patterns"]):
            missing = [f for f in pattern_fields if f not in pattern]
            if missing:
                print(f"❌ Pattern {i}: Missing fields: {missing}")
                return False

        print(f"✅ Pattern file is valid!")
        print(f"   Namespace: {data['namespace']}")
        print(f"   Patterns: {len(data['patterns'])}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# Validate
validate_pattern_file("my_patterns.yml")
```

## Error Handling

All functions provide clear error messages:

```python
from datadetector import PatternFileHandler

try:
    # This will raise FileNotFoundError
    PatternFileHandler.add_pattern_to_file("nonexistent.yml", {...})
except FileNotFoundError as e:
    print(f"File not found: {e}")

try:
    # This will raise ValueError (missing required fields)
    PatternFileHandler.add_pattern_to_file("my_patterns.yml", {"id": "test"})
except ValueError as e:
    print(f"Invalid pattern: {e}")

try:
    # This will raise FileExistsError (overwrite=False by default)
    PatternFileHandler.create_pattern_file("existing.yml", "test", "Test")
except FileExistsError as e:
    print(f"File exists: {e}")
```

## Integration with Pattern Loading

Once you've created pattern files, load them with the engine:

```python
from datadetector import Engine, load_registry

# Load custom patterns
registry = load_registry(paths=["my_patterns.yml", "company_patterns.yml"])

# Create engine
engine = Engine(registry)

# Use patterns
result = engine.find("Check employee EMP-123456", namespaces=["company"])
print(f"Found {result.match_count} matches")
```

## Best Practices

1. **Always validate pattern files** after creation or modification
2. **Use descriptive pattern IDs** following the convention: `<type>_<number>` (e.g., `email_01`)
3. **Include examples** in patterns to validate regex correctness
4. **Set appropriate severity levels** based on data sensitivity
5. **Use `overwrite=False`** by default to prevent accidental data loss
6. **Keep backups** before batch updating patterns
7. **Test patterns** with the engine before deploying to production

## Logging

The YAML utilities use Python's logging module:

```python
import logging

# Enable debug logging for YAML operations
logging.basicConfig(level=logging.DEBUG)

from datadetector import PatternFileHandler

# This will log: "Successfully wrote YAML file: my_patterns.yml"
PatternFileHandler.create_pattern_file(...)
```

---

For more information, see:
- [Architecture](./ARCHITECTURE.md) - System architecture and design overview
- [Pattern Schema Documentation](../schemas/pattern-schema.json)
- [Engine API Documentation](./engine.md)
- [Testing Documentation](../TESTING.md)
