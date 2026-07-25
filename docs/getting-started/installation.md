# Installation Guide

This guide covers the different ways to install Data Detector.

## Prerequisites

- Python 3.8 or higher
- `pip` package manager

## Install from PyPI (Recommended)

For most users, the recommended way to install Data Detector is from the Python Package Index (PyPI) using `pip`. This will install the latest stable version.

```bash
pip install data-detector
```

## Install from Source

If you want to get the latest, unreleased features or if you plan to contribute to the project, you can install it from the source code.

```bash
git clone https://github.com/yourusername/data-detector.git --recursive
cd data-detector
# Or if you already cloned without submodules:
git submodule update --init --recursive
pip install -e .
```
The `-e` flag installs the package in "editable" mode, which means that changes you make to the source code will be immediately available without needing to reinstall.

> **Note:** Data Detector relies on the `pii-pattern-engine` submodule for its PII detection logic. Ensure you have properly checked out submodules to avoid `ModuleNotFoundError` or `FileNotFoundError` during execution.

## Install with Optional Features

Data Detector supports optional feature groups for specialized use cases:

```bash
# Development tools (testing, linting, formatting)
pip install -e ".[dev]"

# NLP support for CJK languages (Korean, Chinese, Japanese)
pip install -e ".[nlp]"

# RE2 regex engine (ReDoS-safe, fast for large texts)
pip install -e ".[re2]"

# Resource scanning adapters
pip install -e ".[database]"       # Database scanning (SQLAlchemy)
pip install -e ".[kafka]"          # Kafka topic scanning (Schema Registry)
pip install -e ".[file-storage]"   # File scanning (Parquet, Excel)
pip install -e ".[vector-db]"      # Vector DB scanning (ChromaDB)
pip install -e ".[training-data]"  # AI training data scanning (HuggingFace)
pip install -e ".[resources]"      # All resource adapters combined
```

## Install with Development Dependencies

If you are a developer, you will need to install the development dependencies, which include tools for testing, formatting, and linting.

```bash
pip install -e ".[dev]"
```

## Docker Installation

For those who prefer containerized environments, you can build and run Data Detector using Docker. This is a great way to run the server as a standalone service.

```bash
# 1. Build the Docker image
docker build -t data-detector:latest .

# 2. Run the container
# This example maps port 8080 and mounts the local `patterns` directory.
docker run -p 8080:8080 -v ./patterns:/app/patterns data-detector:latest
```

## Verify the Installation

Once the installation is complete, you can verify that it was successful by checking the version number.

From your terminal:
```bash
data-detector --version
```

Or from within a Python script:
```python
import datadetector
print(datadetector.__version__)
```