# YAML Utilities Guide

The `datadetector.utils.yaml_utils` module provides a powerful set of tools for programmatically creating, reading, updating, and managing YAML files, with a special focus on Data Detector's pattern files.

## Overview

This module is designed to make it easy to automate the management of your detection patterns. It is built around two main classes:

1.  **`YAMLHandler`**: A general-purpose class for safe and reliable reading and writing of any YAML file.
2.  **`PatternFileHandler`**: A specialized subclass of `YAMLHandler` that understands the structure of Data Detector pattern files. It provides high-level methods like `add_pattern_to_file` and `update_pattern_in_file`.

For common operations, there are also top-level convenience functions like `read_yaml` and `write_yaml`.

## Basic YAML Operations

These functions are for working with any generic YAML file.

### Reading a YAML File
```python
from datadetector.utils.yaml_utils import read_yaml

try:
    config_data = read_yaml("config.yml")
    print("Successfully read config:")
    print(config_data)
except FileNotFoundError:
    print("Config file not found.")
```

### Writing a YAML File
```python
from datadetector.utils.yaml_utils import write_yaml

new_data = {
    "setting": "value",
    "enabled": True,
}

# This will create a new file or fail if it already exists.
try:
    write_yaml("new_config.yml", new_data, sort_keys=True)
    print("Successfully wrote new_config.yml")
except FileExistsError:
    print("File already exists. Use overwrite=True to replace it.")

# To overwrite an existing file:
write_yaml("new_config.yml", new_data, overwrite=True)
```

## Managing Pattern Files

This is the primary use case for the YAML utilities. The `PatternFileHandler` provides a safe and structured way to manage your pattern files without having to manually parse the YAML.

### Creating a New Pattern File
This is the recommended way to create a new, well-structured pattern file from scratch.
```python
from datadetector.utils.yaml_utils import PatternFileHandler

# Define a simple pattern to start with
initial_pattern = {
    "id": "employee_id_01",
    "location": "myorg",
    "category": "identifier",
    "pattern": r"EMP-\d{6}",
    "policy": {"action_on_match": "redact", "severity": "medium"}
}

# Create the file
PatternFileHandler.create_pattern_file(
    file_path="company_patterns.yml",
    namespace="myorg",
    description="Patterns for My Organization",
    patterns=[initial_pattern],
    overwrite=True # Use overwrite=True if you are re-running the script
)
print("Created company_patterns.yml")
```

### Adding a Pattern to an Existing File
```python
from datadetector.utils.yaml_utils import PatternFileHandler

new_pattern = {
    "id": "project_code_01",
    "location": "myorg",
    "category": "identifier",
    "pattern": r"PROJ-\d{4}",
    "policy": {"action_on_match": "redact", "severity": "low"}
}

try:
    PatternFileHandler.add_pattern_to_file(
        "company_patterns.yml",
        new_pattern
    )
    print(f"Added pattern '{new_pattern['id']}' to company_patterns.yml")
except ValueError as e:
    print(f"Error adding pattern: {e}") # e.g., if the pattern ID already exists
```

### Updating a Pattern in a File
You can update one or more fields of a specific pattern without having to read and rewrite the whole file manually.
```python
from datadetector.utils.yaml_utils import PatternFileHandler

updates = {
    "description": "Updated Employee ID with new format",
    "pattern": r"EMP-[A-Z]-\d{6}",
    "policy": {"severity": "high"}
}

was_updated = PatternFileHandler.update_pattern_in_file(
    "company_patterns.yml",
    "employee_id_01",
    updates
)

if was_updated:
    print("Successfully updated pattern 'employee_id_01'")
```

### Reading and Removing Patterns from a File
```python
from datadetector.utils.yaml_utils import PatternFileHandler

# Get a specific pattern
pattern = PatternFileHandler.get_pattern_from_file("company_patterns.yml", "project_code_01")
if pattern:
    print(f"Read pattern 'project_code_01': {pattern}")

# List all pattern IDs in the file
all_ids = PatternFileHandler.list_patterns_in_file("company_patterns.yml")
print(f"All pattern IDs: {all_ids}")

# Remove a pattern
was_removed = PatternFileHandler.remove_pattern_from_file("company_patterns.yml", "project_code_01")
if was_removed:
    print("Successfully removed pattern 'project_code_01'")
```

## Best Practices

-   **Use `PatternFileHandler` for Pattern Files**: While you can use the basic `YAMLHandler`, the `PatternFileHandler` provides validation and structure that helps prevent common errors.
-   **Check for Existence**: When writing scripts, always check if a file exists or if a pattern was successfully found before proceeding. The handler functions return booleans or `None` to make this easy.
-   **Handle Exceptions**: Wrap file operations in `try...except` blocks to gracefully handle `FileNotFoundError`, `FileExistsError`, and `ValueError`.
-   **Keep Backups**: Before running a script that performs batch updates on your pattern files, it's always a good idea to have a backup.

## API Reference (Abridged)

This is a summary of the most important methods. For full details, please refer to the source code or the full API documentation.

### `PatternFileHandler`
- `create_pattern_file(file_path, namespace, description, patterns, ...)`: Creates a new pattern file.
- `add_pattern_to_file(file_path, pattern)`: Adds a new pattern dictionary to an existing file.
- `update_pattern_in_file(file_path, pattern_id, updates)`: Updates fields of an existing pattern. Returns `True` if successful.
- `remove_pattern_from_file(file_path, pattern_id)`: Removes a pattern by its ID. Returns `True` if successful.
- `get_pattern_from_file(file_path, pattern_id)`: Retrieves a single pattern by its ID. Returns the pattern dict or `None`.
- `list_patterns_in_file(file_path)`: Returns a list of all pattern IDs in a file.

### Convenience Functions
- `read_yaml(file_path)`: Reads any YAML file and returns its content.
- `write_yaml(file_path, data, ...)`: Writes a dictionary to a YAML file.
- `update_yaml(file_path, updates, ...)`: Updates a YAML file.