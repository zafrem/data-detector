# Changelog

All notable changes to this project will be documented in this file.

## [0.0.1] - 2025-10-10

### Changed
- **Repository Renamed**: Complete rebrand from `regex-vault` to `data-detector`
  - Package name: `regex-vault` → `data-detector`
  - Python module: `regexvault` → `datadetector`
  - CLI command: `regex-vault` → `data-detector`
  - Environment variables: `REGEX_VAULT_*` → `DATA_DETECTOR_*`
  - All documentation and references updated
  - Version reset to 0.0.1 for fresh start

## [Unreleased]

### Fixed
- **CI/CD Pipeline**: Updated GitHub Actions workflows
  - Updated `actions/upload-artifact` from v3 to v4 (deprecated v3 was causing build failures)
  - Added `load: true` to Docker build step to properly load image for testing

### Added
- **Verification Functions System**: Added extensible verification function system for additional validation beyond regex matching
  - Built-in `iban_mod97()` function for IBAN Mod-97 checksum validation
  - Built-in `luhn()` function for Luhn algorithm validation (credit cards, etc.)
  - Built-in `dms_coordinate()` function for DMS coordinate validation
  - Support for custom verification functions via registration API
  - `verification` field in pattern schema to reference verification functions

- **New Pattern Categories**:
  - Added `IBAN` category for International Bank Account Numbers
  - Added `LOCATION` category for geographic coordinates

- **New Pattern Files**:
  - `patterns/iban.yml` - IBAN patterns with Mod-97 verification for multiple countries
  - Location coordinate patterns in `patterns/common.yml` (latitude, longitude, DMS format)

- **Enhanced Directory Loading**: `load_registry()` now supports loading all YAML files from a directory
  - Pass a directory path to load all `.yml` and `.yaml` files
  - Maintains backward compatibility with individual file paths

- **Comprehensive Documentation**:
  - Created `/docs` folder with 8 detailed documentation files:
    - `installation.md` - Installation guide
    - `quickstart.md` - Quick start guide
    - `patterns.md` - Pattern structure reference
    - `custom-patterns.md` - Custom pattern creation guide
    - `verification.md` - Verification functions guide
    - `configuration.md` - Configuration reference
    - `api-reference.md` - Complete API documentation
    - `supported-patterns.md` - Catalog of built-in patterns
  - Restructured README.md to be concise with links to detailed docs

- **Credit Card Patterns**: Added additional credit card patterns in `common.yml`
  - American Express
  - Discover
  - JCB
  - Diners Club

### Changed
- **Python 3.8 Compatibility**: Fixed all type annotations for Python 3.8 compatibility
  - Changed `list[str]` to `List[str]`
  - Changed `dict[str, Any]` to `Dict[str, Any]`
  - Changed `tuple[int, int]` to `Tuple[int, int]`
  - Updated files: `models.py`, `registry.py`, `engine.py`, `server.py`, `verification.py`

- **Pattern Model**: Enhanced `Pattern` model with verification support
  - Added `verification` field (str) - name of verification function
  - Added `verification_func` field (Callable) - compiled verification function

- **Engine Behavior**: Updated `find()` and `validate()` methods to apply verification
  - Matches must pass both regex AND verification (if specified)
  - Failed verification matches are filtered out automatically

- **Example Validation**: Updated pattern example validation to consider verification functions
  - `nomatch` examples that match regex but fail verification are now valid
  - `match` examples must pass both regex and verification

- **Import Organization**: Reorganized imports to follow PEP 8 standards (alphabetical ordering)

### Fixed
- **Pattern Schema**: Added missing categories to schema enum (`iban`, `location`)
- **Example Validation Logic**: Fixed validation to properly handle patterns with verification
- **Test Configuration**: Removed pytest coverage options that require additional packages

### Deprecated
- None

### Removed
- Temporarily commented out Korean address patterns (`kr/address_01`, `kr/address_02`) due to incompatibility with Python regex named groups syntax
- Temporarily commented out Japanese address patterns (`jp/address_01`, `jp/address_02`) due to Unicode property escapes (`\p{Script=Han}`) not supported in Python `re` module
- Temporarily commented out Taiwan address patterns (`tw/address_01`, `tw/address_02`) due to Unicode property escapes not supported in Python `re` module

### Security
- Verification functions help prevent false positives by validating checksums and business logic

## Test Coverage
- 25 new tests for verification functionality
  - 15 unit tests for verification functions
  - 10 integration tests for verification with engine
- All tests passing ✅

## Migration Guide

### For Pattern Files
If you have custom patterns, you can now add verification:

```yaml
patterns:
  - id: my_pattern_01
    pattern: '[A-Z]{2}\d{10}'
    verification: custom_verify  # Optional: reference to verification function
```

### For Code
Register custom verification functions before loading patterns:

```python
from datadetector.verification import register_verification_function

def my_verify(value: str) -> bool:
    # Your validation logic
    return True

register_verification_function("custom_verify", my_verify)

# Now load patterns that reference "custom_verify"
registry = load_registry(paths=["patterns/"])
```

### Directory Loading
You can now load all patterns from a directory:

```python
# Old way (still works)
registry = load_registry(paths=[
    "patterns/common.yml",
    "patterns/kr.yml",
    "patterns/us.yml"
])

# New way (simpler)
registry = load_registry(paths=["patterns/"])
```

## Known Issues
- Korean address patterns with named groups need refactoring for Python compatibility
- Some test files skip tests that depend on all patterns loading
