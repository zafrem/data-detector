# Changelog

All notable changes to this project will be documented in this file.

## [0.0.5] - 2026-02-22

### Changed
- **License Update**: Formally transitioned project from MIT to **Apache License 2.0**.
  - Updated `LICENSE`, `README.md`, `CONTRIBUTING.md`, and all documentation.
  - Submodule `pattern-engine` also updated to Apache 2.0.
- **API Authentication**: Enhanced Vercel serverless API with robust authentication.
  - Implemented `ADMIN_TOKEN` requirement for API key issuance.
  - Stateless HMAC-based API keys with embedded system identifiers.
  - Mandatory `Authorization: Bearer dd_...` headers for all functional endpoints.
  - Updated "Try It" interactive documentation to support API key authentication.
- **Version Standardized**: Unified versioning across Python package, CLI, and API to `0.0.5`.

## [0.0.3] - 2025-11-29

### Added
- **RAG Security Implementation**: Complete three-layer PII protection system for RAG applications
  - New `rag_config.py` module for RAG-specific configuration
  - New `rag_middleware.py` for request/response processing
  - New `rag_models.py` with RAG-specific data models
  - New `stream_engine.py` for streaming PII detection
  - New `tokenization.py` for advanced token management
  - MASK vs FAKE strategy comparison for RAG systems
  - Token mapping and restoration capabilities

- **Enhanced Documentation**: Comprehensive RAG integration guides
  - `RAG_IMPLEMENTATION_SUMMARY.md` - Complete implementation overview
  - `RAG_QUICKSTART.md` - Quick start guide for RAG integration
  - `RAG_SECURITY_ARCHITECTURE.md` - Security architecture documentation
  - `TOKEN_MAP_STORAGE.md` - Token storage and management guide
  - Multi-language documentation (Korean, Chinese)
  - Architecture documentation and templates

- **New Examples**: RAG integration examples
  - `langchain_integration.py` - LangChain integration example
  - `rag_api_example.py` - RAG API usage example
  - `rag_mask_vs_fake.py` - Strategy comparison example
  - `rag_quickstart.py` - Quick start example

- **Security Configuration**: RAG security policy configuration
  - `config/rag_security_policy.yml` - Security policy configuration file
  - Configurable PII protection levels and strategies

### Changed
- **Server Enhancement**: Updated FastAPI server with RAG middleware support
- **Engine Enhancement**: Enhanced core engine with streaming capabilities
- **Model Updates**: Extended data models to support RAG use cases
- **Code Style**: Improved code formatting and style consistency

### Fixed
- **CI/CD Pipeline**: Fixed Ubuntu + Python 3.8 compatibility issues
  - Resolved test failures on Ubuntu with Python 3.8
  - Updated GitHub workflow configurations
  - Improved cross-platform compatibility

- **Testing**: Enhanced test coverage for new RAG features
  - Added `test_rag_security.py` for RAG security testing
  - Updated `test_fake_strategy.py` with additional test cases
  - Improved fake file generator tests

### Documentation
- **Improvement Considerations**: Added comprehensive code quality assessment
  - Performance optimization recommendations
  - Maintainability improvements
  - Production readiness guidelines
  - Overall assessment: 6.3/10 with improvement roadmap

## [0.0.2] - 2025-10-31

### Fixed
- **CI/CD Pipeline**: Updated GitHub Actions workflows
  - Updated `actions/upload-artifact` from v3 to v4 (deprecated v3 was causing build failures)
  - Added `load: true` to Docker build step to properly load image for testing
- **Linting**: Fixed all ruff linting errors (58 errors fixed)
  - Fixed line length issues (E501) in bulk_generator.py, fake_file_generators.py, fake_generator.py
  - Replaced bare except statements with specific exception types
  - Removed unused imports and variables
  - Improved code formatting and readability

### Changed
- **Module Organization**: Moved `yaml_utils.py` to `utils/` folder
  - New location: `src/datadetector/utils/yaml_utils.py`
  - Updated all imports to use `datadetector.utils.yaml_utils`
  - Maintained backward compatibility through `datadetector.__init__.py` exports
  - Updated documentation to reflect new structure
- **Dependencies**: Added missing optional dependencies to `pyproject.toml`
  - Added `faker`, `Pillow`, `reportlab`, `python-docx`, `openpyxl`, `python-pptx` to test dependencies
  - Created new `fake` optional dependency group for fake data generation features
  - Fixed CI test failures due to missing dependencies

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

### Added
- **Universal Resource Scanning**: Complete system for detecting PII in structured data resources
  - New `resource_models.py` — Shared enums and dataclasses (`ResourceType`, `ScanStrategy`, `PIIConfidence`, `ContainerType`, etc.)
  - New `resource_adapter.py` — Abstract `ResourceAdapter` base class with pluggable adapter pattern
  - New `data_explorer.py` — `DataExplorer` orchestrator that scans any adapter using metadata + sample value analysis
  - New `data_inventory.py` — `DataInventoryGenerator` for PII catalog generation, export (JSON/CSV/YAML/HTML), diff, and summary
  - New `data_lineage.py` — `DataLineageTracer` for PII flow tracing within and across resources, with Mermaid/D3.js export

- **Resource Adapters** (6 adapters for different data sources):
  - `adapters/database.py` — `DatabaseAdapter` using SQLAlchemy for RDBMS (PostgreSQL, MySQL, SQLite, etc.)
  - `adapters/kafka.py` — `KafkaAdapter` for Kafka topics via Schema Registry (Avro/JSON Schema)
  - `adapters/api.py` — `APIAdapter` for REST API scanning via OpenAPI/Swagger specs
  - `adapters/file_storage.py` — `FileStorageAdapter` for CSV, JSON, JSONL, Parquet, and Excel files
  - `adapters/vector_db.py` — `VectorDBAdapter` for scanning vector databases (ChromaDB) — document chunks and metadata
  - `adapters/training_data.py` — `TrainingDataAdapter` for scanning AI training data (JSONL instruction-tuning, chat format, prompt/completion, HuggingFace datasets)

- **New Optional Dependencies** in `pyproject.toml`:
  - `database` — SQLAlchemy for database scanning
  - `kafka` — confluent-kafka, requests, fastavro for Kafka scanning
  - `file-storage` — openpyxl, pyarrow for Excel/Parquet support
  - `vector-db` — chromadb for vector database scanning
  - `training-data` — datasets (HuggingFace) for training data scanning
  - `resources` — Meta-group installing all resource adapter dependencies

- **Comprehensive Test Suite**: 180 new tests across 10 test files covering models, all adapters, explorer, inventory, and lineage

### Changed
- None

### Fixed
- None

### Deprecated
- None

### Removed
- None

### Security
- None
