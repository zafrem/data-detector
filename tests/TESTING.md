# Testing Documentation

## Overview

This document describes the testing strategy, test coverage, and testing guidelines for the data-detector project.

## Test Coverage Summary

**Overall Coverage: 94%** (674 statements, 42 missed)

### Coverage by Module

| Module | Statements | Missed | Coverage |
|--------|-----------|--------|----------|
| `__init__.py` | 5 | 0 | 100% |
| `cli.py` | 132 | 16 | 88% |
| `engine.py` | 87 | 1 | 99% |
| `models.py` | 99 | 0 | 100% |
| `registry.py` | 144 | 9 | 94% |
| `server.py` | 130 | 16 | 88% |
| `verification.py` | 77 | 0 | 100% |

## Test Statistics

- **Total Tests:** 174
- **All Tests Passing:** ✅
- **Test Files:** 10
- **Test Execution Time:** ~60 seconds

## Test Structure

### Test Files

```
tests/
├── __init__.py
├── test_cli.py                          # CLI command tests (31 tests)
├── test_engine.py                       # Engine core functionality (18 tests)
├── test_engine_edge_cases.py           # Engine edge cases (4 tests)
├── test_location_field.py              # Location field validation (22 tests)
├── test_patterns.py                    # Pattern loading and validation (14 tests)
├── test_registry_edge_cases.py         # Registry edge cases (14 tests)
├── test_server.py                      # API endpoint tests (15 tests)
├── test_token_patterns.py              # Token detection tests (19 tests)
├── test_verification.py                # Verification functions (27 tests)
└── test_verification_integration.py    # Verification integration (10 tests)
```

## Test Categories

### 1. CLI Tests (`test_cli.py`)

Tests all CLI commands and options:

- **Version Command**
  - `test_version_flag` - Test --version flag

- **Find Command**
  - `test_find_with_text` - Find PII in text
  - `test_find_with_file` - Find PII in file
  - `test_find_with_namespace` - Filter by namespace
  - `test_find_with_multiple_namespaces` - Multiple namespace search
  - `test_find_json_output` - JSON output format
  - `test_find_with_include_text` - Include matched text
  - `test_find_with_first_only` - Stop on first match
  - `test_find_with_custom_patterns` - Custom pattern files
  - `test_find_without_input_error` - Error handling
  - `test_find_text_output_format` - Text output format

- **Validate Command**
  - `test_validate_valid_input` - Valid pattern validation
  - `test_validate_invalid_input` - Invalid input detection
  - `test_validate_pattern_not_found` - Non-existent pattern handling
  - `test_validate_with_custom_patterns` - Custom pattern validation

- **Redact Command**
  - `test_redact_with_text` - Redact from text
  - `test_redact_with_file` - Redact from file
  - `test_redact_to_file` - Output to file
  - `test_redact_with_namespace` - Namespace filtering
  - `test_redact_with_hash_strategy` - Hash redaction
  - `test_redact_with_tokenize_strategy` - Token redaction
  - `test_redact_with_stats` - Statistics output
  - `test_redact_with_stats_to_file` - Stats with file output
  - `test_redact_with_custom_patterns` - Custom patterns
  - `test_redact_without_input_error` - Error handling

- **List Patterns Command**
  - `test_list_patterns_default` - List default patterns
  - `test_list_patterns_with_custom` - List custom patterns

- **Serve Command**
  - `test_serve_import_error` - Dependency check
  - `test_serve_with_config` - Configuration file handling

- **Verbose Option**
  - `test_verbose_flag` - Short flag (-v)
  - `test_verbose_long_option` - Long option (--verbose)

### 2. Engine Tests (`test_engine.py`, `test_engine_edge_cases.py`)

Core detection and redaction engine:

- **Find Functionality**
  - Pattern matching across namespaces
  - Overlap handling
  - First match optimization
  - Include matched text with store_raw policy

- **Validate Functionality**
  - Pattern validation
  - Verification function integration
  - Store_raw policy handling

- **Redact Functionality**
  - Mask strategy (default and custom)
  - Hash strategy
  - Tokenize strategy
  - Multiple item redaction
  - Structure preservation

- **Edge Cases**
  - Empty text handling
  - Very long text (100KB+)
  - Unicode text support
  - Patterns without masks
  - Unknown strategy fallback

### 3. Registry Tests (`test_patterns.py`, `test_registry_edge_cases.py`)

Pattern loading and registry management:

- **Pattern Loading**
  - YAML file loading
  - Directory scanning
  - Default patterns
  - Custom patterns
  - Schema validation
  - Example validation

- **Pattern Metadata**
  - Required fields validation
  - Policy configuration
  - Critical pattern security
  - Location field consistency

- **Edge Cases**
  - Duplicate pattern warnings
  - Missing files warnings
  - Empty directories
  - Invalid YAML format
  - Missing schema handling
  - Regex compilation errors
  - Verification function not found
  - All regex flag support
  - Priority handling

### 4. Server Tests (`test_server.py`)

API endpoint testing:

- **Health Endpoint**
  - `/health` - System health check

- **Find Endpoint**
  - `/find` - PII detection
  - Multiple namespaces
  - Allow overlaps option
  - Include matched text option

- **Validate Endpoint**
  - `/validate` - Pattern validation
  - Invalid input handling
  - Pattern not found errors

- **Redact Endpoint**
  - `/redact` - PII redaction
  - Hash strategy
  - Default strategy
  - No matches handling

- **Reload Endpoint**
  - `/reload` - Pattern reload

- **Metrics Endpoint**
  - `/metrics` - Prometheus metrics

### 5. Verification Tests (`test_verification.py`, `test_verification_integration.py`)

Verification function testing:

- **IBAN Mod-97**
  - Valid IBAN numbers (multiple countries)
  - Invalid check digits
  - Format validation
  - Case insensitivity
  - Space handling

- **Luhn Algorithm**
  - Valid credit card numbers
  - Invalid check digits
  - Format validation
  - Space/dash handling

- **High Entropy Token**
  - API keys and secrets detection
  - Length validation (20+ chars)
  - Entropy calculation
  - Invalid character handling
  - Whitespace rejection

- **DMS Coordinates**
  - Degrees Minutes Seconds format
  - Latitude range validation (0-90°)
  - Longitude range validation (0-180°)
  - Minutes/seconds validation
  - Direction validation (N/S/E/W)

- **Registry Functions**
  - Built-in function retrieval
  - Custom function registration
  - Function unregistration
  - Function overwriting

- **Integration**
  - IBAN validation with patterns
  - Find with verification
  - Redact with verification
  - Multiple IBAN detection
  - Country-specific patterns
  - Custom verification functions

### 6. Location Field Tests (`test_location_field.py`)

Location-based pattern filtering:

- Pattern location attributes
- Namespace-location consistency
- Location-based filtering
- Custom pattern locations
- Documentation validation

### 7. Token Pattern Tests (`test_token_patterns.py`)

Token and credential detection:

- GitHub tokens
- AWS access/secret keys
- JWT tokens
- Private keys
- Generic API keys
- Priority ordering
- First-match optimization

## Uncovered Code (6%)

The following code remains uncovered, which is acceptable:

### CLI Module (12% uncovered)
- **Lines 314-343**: `serve` command execution
  - Runs `uvicorn.run()` which is a blocking server
  - Difficult to test in unit tests
  - Would require integration tests or mocking the entire uvicorn framework

### Server Module (12% uncovered)
- **Lines 136-138, 179**: Error handling edge cases
- **Lines 215-217, 223, 233-235, 241**: Exception paths rarely triggered
- **Lines 256-258, 264**: Specific error conditions

### Registry Module (6% uncovered)
- **Lines 159-160**: Schema file missing path
  - Only triggered when schema file is deleted from package
  - Edge case that shouldn't occur in normal operation

### Engine Module (1% uncovered)
- **Line 266**: Fallback redaction logic
  - Defensive code path for unknown strategies

## Running Tests

### Run All Tests
```bash
pytest
```

### Run with Coverage
```bash
pytest --cov=datadetector --cov-report=term --cov-report=html
```

### Run Specific Test File
```bash
pytest tests/test_cli.py
```

### Run Specific Test
```bash
pytest tests/test_cli.py::TestFindCommand::test_find_with_text
```

### Run with Verbose Output
```bash
pytest -v
```

### Run in Quiet Mode
```bash
pytest -q
```

## Test Fixtures

Common fixtures used across tests:

- `engine` - Engine instance with default patterns
- `registry` - Empty PatternRegistry
- `client` - FastAPI TestClient for server tests
- `runner` - Click CLI test runner
- `tmp_path` - Temporary directory for file operations
- `sample_text` - Sample text with PII for testing

## Testing Best Practices

### 1. Test Naming
- Use descriptive test names: `test_<what>_<condition>_<expected>`
- Example: `test_find_with_multiple_namespaces`

### 2. Test Organization
- Group related tests in classes
- Use clear class names: `Test<Feature>`
- One assertion per logical test when possible

### 3. Coverage Goals
- Maintain >90% overall coverage
- 100% coverage for critical modules (models, verification)
- >95% for core functionality (engine)
- >85% for CLI and server (harder to test completely)

### 4. Test Data
- Use realistic test data
- Include edge cases (empty, very long, unicode)
- Test both valid and invalid inputs

### 5. Isolation
- Each test should be independent
- Use fixtures for common setup
- Clean up resources (use `finally` or context managers)

### 6. Documentation
- Add docstrings to test classes and methods
- Document edge cases being tested
- Explain complex test scenarios

## Continuous Integration

The CI workflow (`.github/workflows/ci.yml`) runs:

1. **Linting**
   - ruff (code quality)
   - black (formatting)
   - mypy (type checking)

2. **Testing**
   - Run tests on multiple OS (Ubuntu, macOS, Windows)
   - Test Python versions: 3.8, 3.9, 3.10, 3.11, 3.12
   - Generate coverage reports
   - Upload to Codecov

3. **Build Verification**
   - Package building
   - Package validation
   - Docker image building

## Adding New Tests

When adding new features:

1. Write tests first (TDD approach recommended)
2. Ensure new code has >90% coverage
3. Include edge cases and error conditions
4. Update this document if adding new test categories
5. Run full test suite before committing

## Test Coverage Reports

Coverage reports are generated in multiple formats:

- **Terminal**: Quick overview in console
- **XML**: For CI/CD integration (coverage.xml)
- **HTML**: Detailed browsable report (htmlcov/index.html)

View HTML report:
```bash
pytest --cov=datadetector --cov-report=html
open htmlcov/index.html
```

## Troubleshooting

### Tests Failing Locally
1. Ensure all dependencies are installed: `pip install -e ".[test]"`
2. Check Python version compatibility (3.8+)
3. Clear pytest cache: `pytest --cache-clear`

### Coverage Not Updating
1. Delete coverage files: `rm -rf .coverage htmlcov/`
2. Run tests with coverage flag
3. Check source paths in `pyproject.toml`

### Import Errors
1. Install package in editable mode: `pip install -e .`
2. Check PYTHONPATH includes project root
3. Verify test file imports are correct

## Future Improvements

Potential testing enhancements:

1. **Integration Tests**
   - Full server integration tests
   - Database integration (if added)
   - External service mocking

2. **Performance Tests**
   - Benchmark pattern matching speed
   - Large file processing tests
   - Concurrent request handling

3. **Security Tests**
   - Fuzzing for pattern matching
   - Security vulnerability scanning
   - Input validation edge cases

4. **Load Tests**
   - Server load testing
   - Stress testing with concurrent users
   - Memory usage profiling

## Contributing

When contributing tests:

1. Follow existing test structure and naming
2. Ensure tests are deterministic
3. Mock external dependencies
4. Keep tests fast (avoid sleep/delays)
5. Document complex test scenarios
6. Update coverage goals if needed

## See Also

- [Architecture](docs/ARCHITECTURE.md) - System architecture and design overview
- [YAML Utilities](docs/yaml_utilities.md) - Pattern file management
- [API Reference](docs/api-reference.md) - Complete API documentation
- [Custom Patterns](docs/custom-patterns.md) - Creating custom patterns

---

Last Updated: 2025-10-11
Coverage: 94% (674/674 statements)
