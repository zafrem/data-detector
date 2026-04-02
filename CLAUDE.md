# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Data Detector** is a high-performance PII (Personally Identifiable Information) detection and redaction engine. It supports multi-language detection (Korean, Chinese, Japanese, English) with NLP features for improved accuracy with CJK languages. It also provides universal resource scanning for detecting PII in structured data sources (databases, Kafka, REST APIs, file storage) with inventory generation and data lineage tracing.

## Essential Commands

### Development Setup
```bash
# Install development dependencies
pip install -e ".[dev]"

# Install with NLP support (for CJK languages)
pip install -e ".[nlp]"

# Install with RE2 support (for large text processing)
pip install -e ".[re2]"

# Install resource scanning adapters
pip install -e ".[database]"       # SQLAlchemy for DB scanning
pip install -e ".[kafka]"          # Kafka + Schema Registry
pip install -e ".[file-storage]"   # Parquet + Excel
pip install -e ".[vector-db]"      # ChromaDB for vector store scanning
pip install -e ".[training-data]"  # HuggingFace datasets scanning
pip install -e ".[resources]"      # All resource adapters
```

### Testing
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=datadetector --cov-report=term-missing

# Run specific test file
pytest tests/test_engine.py

# Run specific test
pytest tests/test_engine.py::TestFind::test_find_korean_mobile

# Run all checks (mimics GitHub Actions)
make check
```

### Code Quality
```bash
# Format code
make format
# Or manually:
black src/ tests/
ruff check --fix src/ tests/

# Lint code
make lint
# Or manually:
ruff check src/ tests/
black --check src/ tests/
mypy src/

# Validate pattern files
make validate-patterns
# Or manually:
python -c "from datadetector import load_registry; load_registry(validate_examples=True); print('✓ All patterns valid')"
```

### Vercel API (Local)
```bash
# Start Vercel API locally
ADMIN_TOKEN=mysecret API_SECRET=testsecret API_LOG_FILE=/tmp/dd_api.log \
  python3 -m uvicorn api.index:app --reload --port 8000

# Run API test suite
python3 scripts/test_vercel_api.py --admin-token mysecret --system test-cli
```

### Building and Serving
```bash
# Build package
make build

# Start development server (with auto-reload)
make serve

# Start production server
make serve-prod

# Docker commands
make docker-build
make docker-run
```

## Architecture

### Core Components

1. **Engine** (`src/datadetector/engine.py`)
   - Main entry point for PII detection, validation, and redaction
   - Supports multiple redaction strategies: MASK, HASH, TOKENIZE, FAKE
   - Context-aware filtering for performance optimization
   - NLP preprocessing pipeline for CJK languages

2. **Pattern Registry** (`src/datadetector/registry.py`)
   - Loads and compiles regex patterns from YAML files
   - Patterns organized by namespace (country code: us, kr, cn, jp, etc.)
   - Patterns stored in `pattern-engine` submodule at `pattern-engine/regex/pii/`
   - Each pattern has: id, location, category, regex, verification function, examples

3. **NLP Processor** (`src/datadetector/nlp.py`)
   - Language detection using `langdetect`
   - Tokenization for Korean (KoNLPy), Chinese (jieba), Japanese (sudachi)
   - Stopword filtering to remove grammatical particles
   - Improves detection accuracy for languages where particles attach to PII

4. **Context Filtering** (`src/datadetector/context.py`)
   - Performance optimization that filters patterns based on keywords/categories
   - KeywordRegistry maps field names/keywords to relevant patterns
   - Reduces pattern checks from all patterns to only relevant ones

5. **Verification Functions** (`src/datadetector/verification.py`)
   - Additional validation beyond regex matching
   - Examples: Luhn algorithm (credit cards), IBAN mod-97, entropy checks
   - Located in `pattern-engine/verification/python/verification.py` (symlinked)

6. **Regex Compatibility Layer** (`src/datadetector/regex_compat.py`)
   - Unified interface for regex operations
   - Supports both `google-re2` (ReDoS-safe, fast for large texts) and standard `re` (fast for small texts)
   - Configurable via `set_engine(RegexEngine.STANDARD|RE2|AUTO)`
   - Handles Unicode/CJK pattern transformations automatically

7. **Vercel API** (`api/index.py`)
   - Serverless FastAPI app for Vercel deployment
   - Endpoints: detect, validate, mask, fake (with change counts)
   - HMAC-based stateless API key auth with embedded system name
   - Token issuance via admin token + system identifier
   - Structured JSON usage logging per system
   - Logs endpoint with system/event filtering
   - See `docs/vercel-api.md` for full documentation

8. **Resource Scanning** (`src/datadetector/data_explorer.py`, `data_inventory.py`, `data_lineage.py`)
   
   The resource scanning system follows a three-stage pipeline designed so that each stage can be used independently or linked together:
   
   **Stage 1: Search for Security Information** → **Stage 2: Create Security Inventory** → **Stage 3: Security Data Lineage**
   
   - **Stage 1 — Data Explorer** (`data_explorer.py`): Scans any `ResourceAdapter` for sensitive information (PII, etc.) using metadata analysis + sample value detection. Produces `ResourceScanResult`.
   - **Stage 2 — Data Inventory Generator** (`data_inventory.py`): Aggregates scan results into a security inventory catalog. Exports to JSON/CSV/YAML/HTML, supports diff between inventories. Produces `DataInventory`.
   - **Stage 3 — Data Lineage Tracer** (`data_lineage.py`): Traces how security-sensitive data flows within and across resources. BFS traversal, source/sink detection, Mermaid/D3.js visualization.
   
   Each stage is a standalone component. `ResourceScanResult` is the shared interface that links them:
   - Use Stage 1 alone to just scan for sensitive data
   - Use Stage 1 + 2 to scan and generate an inventory report
   - Use Stage 1 + 3 to scan and trace data lineage
   - Use Stage 1 + 2 + 3 for the full pipeline
   - Use Stage 2 or 3 independently with manually constructed `ResourceScanResult`
   
   Pluggable adapter pattern (`src/datadetector/adapters/`):
   - `DatabaseAdapter` (SQLAlchemy), `KafkaAdapter` (Schema Registry), `APIAdapter` (OpenAPI), `FileStorageAdapter` (CSV/JSON/Parquet/Excel)
   - `VectorDBAdapter` (ChromaDB — scan document chunks and metadata in vector stores for PII)
   - `TrainingDataAdapter` (JSONL/HuggingFace — scan AI training data, instruction-tuning, chat, prompt/completion formats)
   
   Reuses existing Engine.find() and context filtering for PII detection.
   See `docs/guides/resource-scanning.md` for full documentation.

### Detection Pipeline

The engine processes text through these steps:

1. **NLP Preprocessing** (if enabled):
   - Detect language
   - Tokenize text
   - Filter stopwords (grammatical particles)
   - Create position mapping back to original text

2. **Pattern Matching**:
   - Apply context filtering to select relevant patterns
   - Sort patterns by priority (lower number = higher priority)
   - Run regex matching on preprocessed text
   - Apply verification functions
   - Handle overlaps based on `allow_overlaps` flag

3. **Context Analysis**:
   - Analyze surrounding text for confidence boosting
   - Use keyword analysis to validate matches

4. **Post-processing**:
   - Map positions back to original text
   - Sort matches by position
   - Return FindResult/RedactionResult

### Pattern Structure

Patterns are defined in YAML files with this structure:

```yaml
namespace: kr  # Country/region code
patterns:
  - id: mobile_01  # Must end with _01, _02 suffix
    location: kr   # Must match namespace
    category: phone  # e.g., phone, ssn, email, bank
    pattern: '...'  # Regex pattern
    description: "..."
    flags: [IGNORECASE]  # Optional: MULTILINE, DOTALL, etc.
    mask: "[PHONE]"  # Optional custom mask
    verification: verify_luhn  # Optional verification function
    priority: 50  # Optional (default: 100, lower = higher priority)
    policy:
      store_raw: false  # Usually false for PII
      action_on_match: redact
      severity: high  # low, medium, high, critical
    examples:
      match:
        - "010-1234-5678"
      nomatch:
        - "02-1234-5678"
```

## Key Patterns

### Pattern Loading
- Default patterns loaded from `pattern-engine/regex/pii/{country}/`
- Countries supported: common, us, kr, cn, jp, tw, in, eu, iban
- Custom patterns can be loaded via `load_registry(paths=["path/to/patterns.yml"])`
- Patterns are validated against JSON schema at `schemas/pattern-schema.json`

### Pattern Naming Convention
- All pattern IDs MUST end with `_01`, `_02`, etc. suffix
- Example: `mobile_01`, `mobile_02`, `ssn_01`
- This enables multiple variations of similar patterns

### Submodules
- `pattern-engine` is a git submodule containing all pattern definitions
- Run `git submodule update --init` to initialize
- The `verification` module is symlinked from `pattern-engine/verification`

## API Usage Examples

### Basic Detection
```python
from datadetector import Engine, load_registry

registry = load_registry()
engine = Engine(registry)

# Find PII
results = engine.find("My phone: 010-1234-5678")

# Validate against specific pattern
result = engine.validate("010-1234-5678", "kr/mobile_01")

# Redact PII
redacted = engine.redact("Contact: test@example.com")
```

### NLP-Enhanced Detection (CJK)
```python
from datadetector import Engine, load_registry, NLPConfig

nlp_config = NLPConfig(
    enable_language_detection=True,
    enable_korean_particles=True,
    enable_chinese_segmentation=True,
    enable_japanese_segmentation=True
)

registry = load_registry()
engine = Engine(registry, nlp_config=nlp_config)

# Detects PII with particles: "전화번호는 010-1234-5678입니다"
results = engine.find(text, namespaces=["kr"])
```

### Context-Aware Filtering
```python
from datadetector import Engine, load_registry, ContextHint

registry = load_registry()
engine = Engine(registry)

# Only check SSN and bank patterns
context = ContextHint(keywords=["ssn", "bank_account"])
results = engine.find(text, context=context)
```

## Testing Strategy

- Target coverage: >90% (currently 94%)
- Test files in `tests/` directory
- Use pytest fixtures: `engine`, `registry`, `client`, `runner`
- Run `make check` before committing to ensure all checks pass
- CI runs tests on Python 3.8-3.12 across Ubuntu, macOS, Windows

## Important Notes

### Pattern Development
- Always validate patterns after changes: `make validate-patterns`
- Never include real PII in examples or tests - use synthetic data only
- Set `store_raw: false` for sensitive patterns
- Include comprehensive `match` and `nomatch` examples
- Avoid ReDoS (catastrophic backtracking) patterns

### Code Style
- Line length: 100 characters
- Use Black for formatting, Ruff for linting, mypy for type checking
- Follow existing patterns in codebase
- The `src/verification` directory is excluded from Black/Ruff/mypy (symlink)

### NLP Dependencies
- NLP features require optional dependencies: `pip install -e ".[nlp]"`
- Dependencies: langdetect, konlpy, jieba, sudachipy
- Code gracefully degrades if NLP dependencies not available

### Git Workflow
- Main branch: `main`
- Submodules: Use `--recurse-submodules` when cloning
- Pattern changes may require updating the `pattern-engine` submodule
- CI automatically runs on PRs to `main` and `develop` branches

## CLI Commands

```bash
# Find PII in text
data-detector find --text "010-1234-5678" --ns kr

# Find PII in file
data-detector find --in input.txt --ns us kr

# Redact a file
data-detector redact --in input.log --out redacted.log --format mask

# Validate text against pattern
data-detector validate --text "010-1234-5678" --pattern-id kr/mobile_01

# List available patterns
data-detector list-patterns --ns kr

# Start REST API server
data-detector serve --port 8080
```

## Performance Optimization

- Use `context` parameter in `find()` to filter patterns by keywords
- Use `stop_on_first_match=True` when you only need to detect PII presence
- Patterns are checked in priority order (lower priority number = checked first)
- NLP preprocessing adds overhead but improves CJK detection accuracy

### Regex Engine Selection

The regex engine can be configured based on your use case:

```python
from datadetector import RegexEngine, set_engine, get_engine

# For small texts with frequent searches - use standard re (faster for small data)
set_engine(RegexEngine.STANDARD)

# For large texts (several MB) - use RE2 (linear-time, ReDoS-safe)
set_engine(RegexEngine.RE2)

# Auto-detect (default) - uses RE2 if available, otherwise standard re
set_engine(RegexEngine.AUTO)

# Check current setting
current = get_engine()
```

| Engine | Best For | Notes |
|--------|----------|-------|
| `STANDARD` | Small texts, frequent searches | Supports lookahead/lookbehind |
| `RE2` | Large texts (MB+), security-critical | Linear-time guarantee, ReDoS-safe |
| `AUTO` | Default behavior | Uses RE2 if installed |

**Note:** Engine preference affects only patterns compiled *after* the setting is changed. Install RE2 with `pip install -e ".[re2]"`.
