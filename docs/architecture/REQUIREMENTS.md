# Requirements Files Guide

This project provides multiple requirements files for different use cases.

## Files Overview

### `requirements.txt`
Core dependencies needed to run data-detector.

**Use when:** You want to use data-detector as a library or run the application.

```bash
pip install -r requirements.txt
```

**Includes:**
- Core libraries (pyyaml, jsonschema, click)
- Web framework (fastapi, uvicorn)
- gRPC support (grpcio, grpcio-tools)
- Metrics (prometheus-client)
- Validation (pydantic)

### `requirements-test.txt`
Dependencies needed to run tests.

**Use when:** You want to run the test suite in CI/CD or locally.

```bash
pip install -r requirements-test.txt
```

**Includes:**
- All core dependencies (via `-r requirements.txt`)
- Testing frameworks (pytest, pytest-cov, pytest-asyncio)
- HTTP testing client (httpx)

### `requirements-dev.txt`
Full development environment dependencies.

**Use when:** You're developing data-detector and need all tools.

```bash
pip install -r requirements-dev.txt
```

**Includes:**
- All core dependencies (via `-r requirements.txt`)
- All testing dependencies
- Code quality tools (black, ruff, mypy)
- Type stubs (types-pyyaml, types-jsonschema)

## Alternative: Use pyproject.toml

You can also install directly from `pyproject.toml`:

```bash
# Install core package
pip install -e .

# Install with test dependencies
pip install -e ".[test]"

# Install with development dependencies
pip install -e ".[dev]"
```

## Recommended Workflow

### For Users
```bash
pip install data-detector
# or
pip install -r requirements.txt
```

### For Contributors
```bash
# Clone the repository
git clone https://github.com/yourusername/data-detector.git
cd data-detector

# Install in development mode with all dev tools
pip install -r requirements-dev.txt

# Or use pyproject.toml
pip install -e ".[dev]"
```

### For CI/CD

**Testing:**
```bash
pip install -r requirements-test.txt
pytest
```

**Linting:**
```bash
pip install -r requirements-dev.txt
ruff check src/ tests/
black --check src/ tests/
mypy src/
```

## Python Version Support

- **Minimum:** Python 3.8
- **Recommended:** Python 3.8+
- **Tested:** Python 3.8, 3.9, 3.10, 3.11, 3.12

## Notes

- All requirements files use minimum version specifications (`>=`) to allow flexibility
- The `-r` directive in requirements files includes other requirements files
- Type checking (mypy) requires Python 3.8+ but runtime supports Python 3.8+
