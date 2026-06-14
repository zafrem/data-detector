# Software Requirements Specification (SRS)

**Project:** Data Detector
**Document status:** Reflects the *current implemented state* of the codebase.
**Audience:** Contributors and integrators extending Data Detector.

> This SRS describes what the software currently does. Capabilities that are
> documented elsewhere but **not yet implemented** are listed explicitly in
> §7 (Planned / Out of Scope) rather than stated as current requirements.

---

## 1. Introduction

### 1.1 Purpose

Data Detector identifies personal information (PII) so that sensitive data does
not leak into AI systems. Its two primary targets are:

1. **RAG pipelines** — detect/redact PII in user queries, indexed documents, and
   LLM responses.
2. **AI training data** — detect/catalog PII in fine-tuning and instruction
   datasets before training.

Both build on a shared, general-purpose PII detection **Engine** that is also
usable standalone (library, CLI, HTTP server).

### 1.2 Scope

In scope (implemented today):

- Pattern-based PII detection with format verification, NLP, and optional ML.
- RAG three-layer security middleware with reversible tokenization.
- Resource scanning for training data and other structured stores, with
  inventory reporting and PII lineage.
- Library API, Click CLI, and FastAPI HTTP server interfaces.

Out of scope today (see §7): gRPC interface, server TLS/rate limiting, and an
HTTP pattern-listing endpoint.

### 1.3 Definitions

| Term | Meaning |
|------|---------|
| **PII** | Personally Identifiable Information. |
| **Namespace** | A pattern grouping, usually by country (`kr`, `us`, `common`, …). |
| **ns_id** | Fully-qualified pattern identifier, `namespace/pattern_id`. |
| **Verification** | Logic check on a match (e.g., Luhn, IBAN Mod-97). |
| **Tokenization** | Reversible replacement of PII with a token + token map. |
| **Resource** | A scannable data store (DB, Kafka, API, file store, vector DB, training data). |
| **Container / Field** | A table/topic/file (container) and its columns/keys (fields). |

### 1.4 References

- `docs/architecture/ARCHITECTURE.md` — system architecture.
- `docs/architecture/RAG_SECURITY_ARCHITECTURE.md` — RAG security design.
- `docs/guides/` — feature guides. `pyproject.toml` — dependency source of truth.

---

## 2. Overall Description

### 2.1 Product perspective

A Python package (`datadetector`) layered as: Interface (CLI / Library / HTTP)
→ Core Engine → Pattern Registry → YAML pattern storage. PII patterns ship as a
git submodule (`pii-pattern-engine`); optional ML models live in
`pii-ml-engine`.

### 2.2 User classes

- **Integrator** — embeds the library/RAG middleware into an application.
- **Data/ML engineer** — scans training data and resources for PII.
- **Operator** — runs the HTTP server and CLI in pipelines/CI.
- **Pattern author** — adds or edits YAML PII patterns.

### 2.3 Operating environment

- Python **3.8+** (tested on 3.8–3.12); Linux/macOS/Windows.
- Core install is dependency-light; advanced features are gated behind extras
  (§6.5) so unused capabilities impose no install cost.

### 2.4 Constraints & assumptions

- Patterns are defined in YAML and validated against a JSON schema.
- Raw PII is never written to logs (only hashes/metadata).
- Optional features degrade gracefully when their extra is not installed.

---

## 3. Functional Requirements — Detection Engine

- **FR-1** The Engine SHALL detect PII in text via namespace-scoped regex
  patterns and return structured matches (`ns_id`, category, span, severity, score).
- **FR-2** The Engine SHALL validate a single text against a specific pattern
  (`validate(text, ns_id)`) and return a boolean result.
- **FR-3** The Engine SHALL redact detected PII using strategies **mask**,
  **hash**, and **tokenize**, returning the redacted text and a redaction count.
- **FR-4** The Engine SHALL run verification functions (e.g., Luhn, IBAN Mod-97,
  and custom registered functions) on matches; verified matches SHALL be scored
  at high confidence (0.95) and skip the ML binary classifier.
- **FR-5** The Engine SHALL support configurable scoring (`ScoringConfig`):
  minimum-score filtering, keyword proximity weighting, and placeholder/test-data
  filtering.
- **FR-6** Detection SHALL support a context-analysis stage combining keyword
  proximity scoring and (optionally) ML classifiers.

## 4. Functional Requirements — RAG Security

- **FR-7** The middleware SHALL scan **user queries** (INPUT layer) and apply a
  policy action: allow, warn, sanitize, or block.
- **FR-8** The middleware SHALL scan **documents** (STORAGE layer) before
  indexing, supporting tokenization so PII can be restored later.
- **FR-9** The middleware SHALL scan **LLM responses** (OUTPUT layer), optionally
  detokenizing authorized token maps and blocking high-severity leakage.
- **FR-10** Tokenization SHALL be reversible via a token map that can be stored
  and supplied for authorized restoration.
- **FR-11** Each layer SHALL be independently configurable with a `SecurityPolicy`
  (action + severity threshold + redaction strategy).

## 5. Functional Requirements — Resource & Training-Data Scanning

- **FR-12** The system SHALL scan a registered resource and produce a
  `ResourceScanResult` of containers/fields with PII confidence
  (NONE→LOW→MEDIUM→HIGH→CONFIRMED).
- **FR-13** Field scoring SHALL combine metadata signals (field name/type) with
  sampled-value detection via the Engine.
- **FR-14** Adapters SHALL be provided for: **training data** (JSONL / chat /
  HuggingFace), **database** (SQLAlchemy), **Kafka** (Schema Registry), **REST
  API** (OpenAPI), **file storage** (CSV/JSON/Parquet/Excel), and **vector DB**
  (ChromaDB).
- **FR-15** The system SHALL generate a PII **inventory** and export it as JSON,
  CSV, YAML, or HTML, and SHALL diff two inventories (added/removed/changed).
- **FR-16** The system SHALL build a **lineage** graph of PII flow across
  resources, support directional tracing, and export to Mermaid and D3-style JSON.

## 6. External Interface Requirements

### 6.1 Library API

- **FR-17** The package SHALL expose `Engine`, `load_registry`, results models,
  the RAG middleware, scanning components, and configs via `datadetector`.

### 6.2 Command-Line Interface (Click)

- **FR-18** The CLI SHALL provide: `find`, `validate`, `redact`, `list-patterns`,
  `serve`, and a `resource` group (`scan`, `inventory`).
- **FR-19** `find` SHALL support a `--on-match exit` mode for CI gating
  (non-zero exit when PII is found).

### 6.3 HTTP API (FastAPI)

- **FR-20** The server SHALL expose `POST /find`, `POST /validate`,
  `POST /redact`, `GET /health`, `POST /reload`, and `GET /metrics`
  (Prometheus).
- **FR-21** The server SHALL expose RAG endpoints `POST /rag/scan-query`,
  `/rag/scan-document`, `/rag/scan-response`.
- **FR-22** The server SHALL expose resource-scanning endpoints under
  `/resources`, `/scans`, `/inventory`, and `/lineage`.
- **FR-23** The server SHALL support hot-reloading patterns via `POST /reload`.

### 6.4 Pattern Management

- **FR-24** Patterns SHALL be loaded from YAML, validated against a JSON schema,
  compiled (with flags), and organized by namespace in a registry.
- **FR-25** YAML utilities (`YAMLHandler`, `PatternFileHandler`) SHALL support
  create/read/update/delete of pattern files and individual patterns.

### 6.5 Dependencies (environment interface)

`pyproject.toml` is the single source of truth. Core install:
`pip install -e .`. Optional extras: `test`, `dev`, `fake`, `nlp`, `re2`,
`transformer`, `database`, `kafka`, `file-storage`, `vector-db`,
`training-data`, `resources` (all adapters). Extras may be combined, e.g.
`pip install -e ".[nlp,transformer]"`.

---

## 7. Non-Functional Requirements

- **NFR-1 (Privacy)** Raw PII SHALL NOT be written to logs; only hashes/metadata.
  Storage of raw values is governed by each pattern's `store_raw` policy.
- **NFR-2 (Performance)** Compiled regex SHALL be cached; namespace filtering
  SHALL limit work. Target p95: <10ms @1KB, <50ms @10KB, <200ms @100KB on
  ~50 patterns (1 vCPU / 512MB).
- **NFR-3 (Extensibility)** New verification functions, patterns, namespaces, and
  resource adapters SHALL be addable without modifying the core Engine.
- **NFR-4 (Graceful degradation)** Features requiring an uninstalled extra SHALL
  fail with a clear, actionable message rather than an opaque error.
- **NFR-5 (Portability)** The package SHALL run on Python 3.8–3.12 across
  Linux/macOS/Windows.
- **NFR-6 (Observability)** The server SHALL expose Prometheus metrics for
  request counts, durations, and pattern matches.
- **NFR-7 (Quality)** Code SHALL pass `ruff`, `black --check`, and `mypy`, with
  the test suite (`pytest`) green.

---

## 8. Planned / Out of Scope (Not Yet Implemented)

These appear in some architecture diagrams/marketing but are **not** implemented
in the current codebase. They are recorded here so the SRS stays truthful and to
scope future work:

- **PR-1** gRPC server interface (only HTTP/FastAPI exists today; `grpcio`
  dependencies are present but unused).
- **PR-2** Server TLS termination and request rate limiting.
- **PR-3** `GET /patterns` HTTP endpoint to list loaded patterns.
- **PR-4** LLM-based context-analysis stage (currently reserved/placeholder).
- **PR-5** CLI `validate --pattern-id`, `list-patterns --ns/--category`, and a
  standalone `version` subcommand (current CLI uses `--ns-id`, `--version`).

---

## 9. Traceability summary

| Area | Requirements | Primary modules |
|------|-------------|-----------------|
| Detection engine | FR-1…FR-6 | `engine.py`, `verification.py`, `analysis.py`, `models.py` |
| RAG security | FR-7…FR-11 | `rag_middleware.py`, `tokenization.py`, `rag_models.py` |
| Resource/training scan | FR-12…FR-16 | `data_explorer.py`, `data_inventory.py`, `data_lineage.py`, `adapters/` |
| Interfaces | FR-17…FR-23 | `__init__.py`, `cli.py`, `server.py` |
| Patterns | FR-24…FR-25 | `registry.py`, `utils/yaml_utils.py` |
| Non-functional | NFR-1…NFR-7 | cross-cutting |
| Planned | PR-1…PR-5 | — |
