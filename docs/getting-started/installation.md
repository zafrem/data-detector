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
git clone https://github.com/yourusername/data-detector.git
cd data-detector
pip install -e .
```
The `-e` flag installs the package in "editable" mode, which means that changes you make to the source code will be immediately available without needing to reinstall.

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