# Installation Guide

## Prerequisites

- Python 3.8 or higher
- pip package manager

## Install from PyPI

```bash
pip install data-detector
```

## Install from Source

```bash
git clone https://github.com/yourusername/data-detector.git
cd data-detector
pip install -e .
```

## Install with Development Dependencies

```bash
pip install -e ".[dev]"
```

## Docker Installation

```bash
# Build
docker build -t data-detector:latest .

# Run
docker run -p 8080:8080 -v ./patterns:/app/patterns data-detector:latest
```

## Verify Installation

```bash
data-detector --version
```

Or in Python:

```python
import datadetector
print(datadetector.__version__)
```
