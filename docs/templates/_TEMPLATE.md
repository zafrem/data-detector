# [Document Title]

> **Quick Summary**: One-sentence description of what this document covers.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [Examples](#examples)
- [API Reference](#api-reference)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Related Documentation](#related-documentation)

---

## Overview

### What is [Topic]?

Brief introduction to the topic (2-3 paragraphs).

**Key Features:**
- ✅ Feature 1
- ✅ Feature 2
- ✅ Feature 3

**Use Cases:**
- Use case 1
- Use case 2
- Use case 3

---

## Quick Start

### Installation

```bash
pip install data-detector
```

### Basic Example

```python
from datadetector import Engine, load_registry

# Initialize
registry = load_registry()
engine = Engine(registry)

# Use the feature
result = engine.method(input_data)
print(result)
```

**Expected Output:**
```
Result output here
```

---

## Core Concepts

### Concept 1

Explanation with diagram if applicable.

```
┌─────────────────────┐
│   Concept Diagram   │
└─────────────────────┘
```

**Example:**
```python
# Code example demonstrating concept
```

### Concept 2

Explanation.

**Example:**
```python
# Code example
```

---

## Examples

### Example 1: [Use Case Name]

**Scenario:** Description of what this example demonstrates.

```python
# Complete working example
from datadetector import Feature

# Step 1: Setup
feature = Feature()

# Step 2: Use
result = feature.process(data)

# Step 3: Handle result
if result.success:
    print(f"Success: {result.value}")
```

**Output:**
```
Success: value
```

### Example 2: [Use Case Name]

**Scenario:** Another use case.

```python
# Another complete example
```

---

## API Reference

### Class/Function Name

```python
def function_name(param1: str, param2: int = 0) -> Result:
    """
    Brief description.

    Args:
        param1: Description of param1
        param2: Description of param2 (default: 0)

    Returns:
        Result: Description of return value

    Raises:
        ValueError: When param1 is invalid

    Example:
        >>> result = function_name("test", 5)
        >>> print(result)
        Result(value='test', count=5)
    """
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `param1` | `str` | Yes | - | Parameter description |
| `param2` | `int` | No | `0` | Parameter description |

**Returns:**

| Field | Type | Description |
|-------|------|-------------|
| `value` | `str` | Result value |
| `count` | `int` | Count value |

---

## Best Practices

### 1. Practice Name

**Do this:**
```python
# ✅ Good example
correct_approach()
```

**Don't do this:**
```python
# ❌ Bad example
wrong_approach()
```

**Why:** Explanation of why the good approach is better.

### 2. Practice Name

Similar structure for other practices.

---

## Troubleshooting

### Issue: Common Problem

**Symptoms:**
- Symptom 1
- Symptom 2

**Solution:**
```python
# Code showing the fix
```

**Explanation:** Why this fixes the issue.

### Issue: Another Problem

Similar structure.

---

## Related Documentation

**Core Documentation:**
- [Installation Guide](installation.md) - Getting started
- [Architecture](ARCHITECTURE.md) - System design

**Related Features:**
- [Feature A](feature-a.md) - Related feature
- [Feature B](feature-b.md) - Another feature

**Advanced Topics:**
- [Advanced Guide](advanced.md) - Deep dive

---

## Support

- 📖 **Documentation**: [docs/](.)
- 💻 **Examples**: [examples/](../examples/)
- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/data-detector/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/data-detector/discussions)

---

**Last Updated:** YYYY-MM-DD | **Version:** 0.0.2
