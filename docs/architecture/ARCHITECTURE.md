# Data Detector Architecture

This document provides a detailed overview of the Data Detector system architecture, from its high-level structure to the specifics of its components and data flows. The diagrams are text-based to ensure they are accessible and easy to maintain.

## System Overview

The following diagram illustrates the high-level layers of the Data Detector system. It is designed with a clear separation of concerns, from the user-facing interfaces down to the storage of pattern files.

```
┌──────────────────────────────────────────────────────────────┐
│                        DATA DETECTOR                         │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    Interface Layer                      │ │
│  │                                                         │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │ │
│  │  │   CLI    │  │ Library  │  │   Server (HTTP/gRPC) │   │ │
│  │  │  (Click) │  │   API    │  │                      │   │ │
│  │  └────┬─────┘  └────┬─────┘  └──────────┬───────────┘   │ │
│  └───────┼─────────────┼───────────────────┼───────────────┘ │
│          │             │                   │                 │
│          └─────────────┼───────────────────┘                 │
│                        │                                     │
│  ┌─────────────────────▼────────────────────────────────┐    │
│  │              Core Engine Layer                       │    │
│  │                                                      │    │
│  │  ┌────────────────────────────────────────────────┐  │    │
│  │  │             Engine                             │  │    │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────────┐    │  │    │
│  │  │  │  find()  │ │validate()│ │  redact()    │    │  │    │
│  │  │  └──────────┘ └──────────┘ └──────────────┘    │  │    │
│  │  └────────────────┬───────────────────────────────┘  │    │
│  │                   │                                  │    │
│  │  ┌────────────────▼────────────────────────────┐     │    │
│  │  │         PatternRegistry                     │     │    │ 
│  │  │  - Pattern compilation & caching            │     │    │
│  │  │  - Namespace organization                   │     │    │
│  │  │  - Verification function registry           │     │    │
│  │  └────────────────┬────────────────────────────┘     │    │
│  └───────────────────┼──────────────────────────────────┘    │
│                      │                                       │
│  ┌───────────────────▼────────────────────────────────────┐  │
│  │           Data Model Layer                             │  │
│  │                                                        │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────────┐      │  │
│  │  │ Pattern    │ │  Policy    │ │ Match/Result   │      │  │
│  │  │ (dataclass)│ │(dataclass) │ │   Models       │      │  │
│  │  └────────────┘ └────────────┘ └────────────────┘      │  │
│  │  ┌──────────────────────────────────────────────┐      │  │
│  │  │ ScoringConfig                                │      │  │
│  │  │ (weights, thresholds, min_score, filtering)  │      │  │
│  │  └──────────────────────────────────────────────┘      │  │
│  │  ┌──────────────────────────────────────────────┐      │  │
│  │  │ TransformerConfig                            │      │  │
│  │  │ (NER, context classifier, fine-tuned models) │      │  │
│  │  └──────────────────────────────────────────────┘      │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │         YAML Utilities Layer                           │  │
│  │                                                        │  │
│  │  ┌──────────────────┐  ┌────────────────────┐          │  │
│  │  │  YAMLHandler     │  │ PatternFileHandler │          │  │
│  │  │  - read_yaml()   │  │ - create_pattern() │          │  │
│  │  │  - write_yaml()  │  │ - add_pattern()    │          │  │
│  │  │  - update_yaml() │  │ - update_pattern() │          │  │
│  │  │                  │  │ - remove_pattern() │          │  │
│  │  └──────────────────┘  └────────────────────┘          │  │
│  └─────────────────┬──────────────────────────────────────┘  │
│                    │                                         │
│  ┌─────────────────▼────────────────────────────────┐        │
│  │            Storage Layer                         │        │
│  │                                                  │        │
│  │  Pattern Files (YAML)                            │        │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────┐      │        │
│  │  │ common/  │ │   kr/    │ │   us/tw/jp/  │      │        │
│  │  │ patterns │ │ patterns │ │   cn/in...   │      │        │
│  │  └──────────┘ └──────────┘ └──────────────┘      │        │ 
│  │                                                  │        │
│  │  Custom Pattern Files (User-created)             │        │
│  │  ┌──────────────────────────────────────┐        │        │
│  │  │  custom_patterns.yml                 │        │        │
│  │  │  company_patterns.yml                │        │        │
│  │  │  ...                                 │        │        │
│  │  └──────────────────────────────────────┘        │        │
│  └──────────────────────────────────────────────────┘        │
└──────────────────────────────────────────────────────────────┘
```

## Component Details

Here we break down the major components of each layer, explaining their roles and responsibilities.

### 1. Interface Layer

The Interface Layer is the entry point for all user interactions. It supports three distinct modes of operation, making it adaptable to different use cases.

```
┌─────────────────────────────────────────────────────┐
│                  CLI (Click)                        │
├─────────────────────────────────────────────────────┤
│ Commands:                                           │
│  • find        - Find PII in text                   │
│  • validate    - Validate text against pattern      │
│  • redact      - Redact PII from text/files         │
│  • list-patterns - List available patterns          │
│  • serve       - Start HTTP/gRPC server             │
│  • version     - Show version                       │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│              Library API (Python)                   │
├─────────────────────────────────────────────────────┤
│ from datadetector import Engine, load_registry      │
│                                                     │
│ registry = load_registry(paths=["patterns/"])       │
│ engine = Engine(registry)                           │
│                                                     │
│ # Operations                                        │
│ engine.find(text, namespaces=[...])                 │
│ engine.validate(text, pattern_id)                   │
│ engine.redact(text, namespaces=[...])               │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│          Server (HTTP/gRPC)                         │
├─────────────────────────────────────────────────────┤
│ Endpoints:                                          │
│  POST /find      - Find PII                         │
│  POST /validate  - Validate pattern                 │
│  POST /redact    - Redact PII                       │
│  GET  /patterns  - List patterns                    │
│  GET  /health    - Health check                     │
│  GET  /metrics   - Prometheus metrics               │
│                                                     │
│ Features:                                           │
│  • TLS support                                      │
│  • Rate limiting                                    │
│  • Hot reload                                       │
└─────────────────────────────────────────────────────┘
```

### 2. Core Engine Layer

The Core Engine is the heart of Data Detector. It contains the business logic for finding, validating, and redacting data. It uses a 4-step pipeline: Regex Matching -> Verification -> Context Analysis -> Post-pipeline Filtering.

```
┌──────────────────────────────────────────────────────────┐
│                       Engine                             │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  find(text, namespaces, include_matched_text)            │
│  ┌────────────────────────────────────────────┐          │
│  │ 1. Get patterns from registry              │          │
│  │ 2. Apply each pattern to text (Regex)      │          │
│  │ 3. Run verification functions (Logic)      │          │
│  │    → verified=True: score=0.95             │          │
│  │    → unverified:    score=0.50             │          │
│  │ 4. Apply Context Analysis (Scoring)        │          │
│  │ 5. Post-pipeline: min_score + placeholder  │          │
│  │ 6. Collect matches with metadata           │          │
│  │ 7. Return FindResult                       │          │
│  └────────────────────────────────────────────┘          │
│                                                          │
│  validate(text, pattern_id)                              │
│  ┌────────────────────────────────────────────┐          │
│  │ 1. Get single pattern from registry        │          │
│  │ 2. Check if text matches pattern           │          │
│  │ 3. Run verification function if present    │          │
│  │ 4. Return ValidationResult (bool)          │          │
│  └────────────────────────────────────────────┘          │
│                                                          │
│  redact(text, namespaces, strategy)                      │
│  ┌────────────────────────────────────────────┐          │
│  │ 1. Find all matches in text                │          │
│  │ 2. Apply redaction strategy:               │          │
│  │    - mask: Replace with mask value         │          │
│  │    - hash: Replace with hash               │          │
│  │    - tokenize: Replace with token          │          │
│  │ 3. Build redacted text                     │          │
│  │ 4. Return RedactionResult                  │          │
│  └────────────────────────────────────────────┘          │
└────────┬───────────────────────────────┬─────────────────┘
         │                               │
┌────────▼─────────────────────┐  ┌──────▼──────────────────────┐
│      PatternRegistry         │  │     ContextAnalyzer         │
│ - Pattern compilation/cache  │  │ - Proximity Scoring         │
│ - Namespace organization     │  │ - Keyword/Anchor detection  │
│ - Verification func registry │  │ - ML: Binary PII classifier │
└──────────────────────────────┘  │ - ML: Category classifier   │
                                  └─────────────────────────────┘
```

The `PatternRegistry` handles pattern loading, while the `ContextAnalyzer` provides the intelligence to score matches based on their surrounding context using keywords and fine-tuned Transformer classifiers.

#### Context Analysis Detail

The `ContextAnalyzer` runs a 3-step pipeline on every regex match:

```
Step 3a: Keyword Check     — proximity-based anchor scoring (±60 chars)
Step 3b: ML Context Check  — fine-tuned Transformer classifiers
Step 3c: LLM Check         — (reserved for future use)
```

**Step 3b** uses two DistilBERT models stored in `pii-engine/models/transformer/`:

```
┌──────────────────────────────────────────────────────────┐
│          ML Context Check (Fine-tuned Mode)              │
│                                                          │
│  For each regex match:                                   │
│    matched_text = text[start:end]                        │
│                                                          │
│  ┌────────────────────────────────────────────┐          │
│  │  Model 1: Binary Classifier                │          │
│  │  (DistilBERT — "pii" vs "non_pii")         │          │
│  │                                            │          │
│  │  ⚠ SKIPPED if match.verified=True          │          │
│  │  (Luhn/checksum already confirmed)         │          │
│  │                                            │          │
│  │  if pii  AND conf > 0.5 → boost +0.35*conf│          │
│  │  if non_pii AND conf > 0.5 → penalty -0.2 │          │
│  │  Score clamped to [0.01, 0.99]             │          │
│  └────────────────────────────────────────────┘          │
│                                                          │
│  ┌────────────────────────────────────────────┐          │
│  │  Model 2: Category Classifier              │          │
│  │  (DistilBERT — 21 PII categories)           │          │
│  │                                            │          │
│  │  if ML cat == regex cat AND conf > 0.5     │          │
│  │    → boost +0.15*conf                      │          │
│  │  if ML cat != regex cat AND conf > 0.7     │          │
│  │    → log mismatch (no score change)        │          │
│  └────────────────────────────────────────────┘          │
│                                                          │
│  Models auto-discovered from:                            │
│    pii-engine/models/transformer/                        │
│      binary_classifier/   (model.safetensors ~256MB)     │
│      category_classifier/ (model.safetensors ~256MB)     │
└──────────────────────────────────────────────────────────┘
```

Training code: `src/datadetector/training/train_pii_classifier.py`
Data generation: `pii-engine/generate_data.py`

```
┌──────────────────────────────────────────────────────────┐
│                  PatternRegistry                         │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Data Structures:                                        │
│  ┌──────────────────────────────────────────────┐        │
│  │ _patterns: Dict[str, Pattern]                │        │
│  │   Key: "namespace/pattern_id"                │        │
│  │   Value: Pattern object                      │        │
│  │                                              │        │
│  │ _by_namespace: Dict[str, List[Pattern]]      │        │
│  │   Key: "namespace"                           │        │
│  │   Value: List of patterns                    │        │
│  │                                              │        │
│  │ _verification_funcs: Dict[str, Callable]     │        │
│  │   Key: "function_name"                       │        │
│  │   Value: Verification function               │        │
│  └──────────────────────────────────────────────┘        │
│                                                          │
│  Methods:                                                │
│  • register_pattern(pattern)                             │
│  • get_pattern(pattern_id)                               │
│  • get_patterns_by_namespace(namespace)                  │
│  • register_verification(name, func)                     │
│  • list_namespaces()                                     │
└──────────────────────────────────────────────────────────┘
```

### 3. Data Flow

This diagram shows the typical flow of a request through the system, from the initial user interaction to the final result.

```
User Request (CLI/API/Server)
        │
        ▼
┌───────────────────┐
│ Interface Layer   │
│ - Parse args      │
│ - Validate input  │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Engine Layer     │
│ - Route to method │
│   (find/validate/ │
│    redact)        │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Registry Lookup   │
│ - Get patterns    │
│   by namespace    │
│ - Get compiled    │
│   regex           │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Pattern Matching  │
│ - Apply regex     │
│ - Find matches    │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Verification      │
│ (if applicable)   │
│ - Luhn check      │
│ - IBAN Mod-97     │
│ - Custom funcs    │
│ → verified=True:  │
│   score=0.95      │
│ → unverified:     │
│   score=0.50      │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Context Analysis  │
│ a. Keyword check  │
│ b. ML classifiers │
│    - Binary (PII?)│
│      (skip if     │
│       verified)   │
│    - Category     │
│ c. LLM (reserved) │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Post-pipeline     │
│ - min_score filter│
│ - Placeholder     │
│   detection       │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Result Building   │
│ - Create Match    │
│   objects         │
│ - Apply policy    │
│ - Format output   │
└────────┬──────────┘
         │
         ▼
    Return Result
   (FindResult/
    ValidationResult/
    RedactionResult)
```

### 4. Pattern Loading Flow

The pattern loading process is a key part of the system's startup routine. This flow illustrates how YAML pattern files are read, validated, compiled, and loaded into the `PatternRegistry`.

```
Application Startup
        │
        ▼
┌─────────────────────────────────┐
│ load_registry(paths=[...])      │
│                                 │
│ Options:                        │
│  • paths: List of YAML files    │
│  • validate_schema: bool        │
│  • validate_examples: bool      │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ For each YAML file:             │
│                                 │
│ 1. Read YAML (via YAMLHandler)  │
│ 2. Parse namespace & patterns   │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ Validation (if enabled):        │
│                                 │
│ 1. Validate against JSON schema │
│ 2. Check required fields        │
│ 3. Validate examples            │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ Pattern Compilation:            │
│                                 │
│ 1. Compile regex with flags     │
│ 2. Link verification function   │
│ 3. Create Pattern object        │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ Registry Population:            │
│                                 │
│ 1. Add to _patterns dict        │
│ 2. Add to _by_namespace dict    │
│ 3. Register verification funcs  │
└────────┬────────────────────────┘
         │
         ▼
  PatternRegistry Ready
```

### 5. YAML Utilities Architecture

To make pattern management easier, Data Detector includes a set of YAML utilities. This layer provides a programmatic way to create, read, update, and delete pattern files and individual patterns.

```
┌─────────────────────────────────────────────────────┐
│              YAML Utilities Layer                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────────────────────────────────┐       │
│  │         YAMLHandler (Base)               │       │
│  │                                          │       │
│  │  read_yaml(file_path)                    │       │
│  │  ┌────────────────────────────────────┐  │       │
│  │  │ 1. Check file exists               │  │       │
│  │  │ 2. Load YAML with safe_load        │  │       │
│  │  │ 3. Validate is dict                │  │       │
│  │  │ 4. Return data                     │  │       │
│  │  └────────────────────────────────────┘  │       │
│  │                                          │       │
│  │  write_yaml(file_path, data, ...)        │       │
│  │  ┌────────────────────────────────────┐  │       │
│  │  │ 1. Validate data is dict           │  │       │
│  │  │ 2. Check overwrite flag            │  │       │
│  │  │ 3. Create parent dirs              │  │       │
│  │  │ 4. Dump YAML with formatting       │  │       │
│  │  └────────────────────────────────────┘  │       │
│  │                                          │       │
│  │  update_yaml(file_path, updates, ...)    │       │
│  │  ┌────────────────────────────────────┐  │       │
│  │  │ 1. Read existing data              │  │       │
│  │  │ 2. Merge or replace                │  │       │
│  │  │ 3. Write updated data              │  │       │
│  │  └────────────────────────────────────┘  │       │
│  └──────────────────────────────────────────┘       │
│                                                     │
│  ┌──────────────────────────────────────────┐       │
│  │   PatternFileHandler (Specialized)       │       │
│  │                                          │       │
│  │  create_pattern_file(...)                │       │  
│  │  ┌────────────────────────────────────┐  │       │
│  │  │ 1. Build pattern file structure    │  │       │
│  │  │ 2. Validate namespace & patterns   │  │       │
│  │  │ 3. Write via YAMLHandler           │  │       │
│  │  └────────────────────────────────────┘  │       │
│  │                                          │       │
│  │  add_pattern_to_file(...)                │       │
│  │  ┌────────────────────────────────────┐  │       │
│  │  │ 1. Read existing file              │  │       │
│  │  │ 2. Validate pattern structure      │  │       │
│  │  │ 3. Check for duplicates            │  │       │
│  │  │ 4. Append to patterns list         │  │       │
│  │  │ 5. Write updated file              │  │       │
│  │  └────────────────────────────────────┘  │       │
│  │                                          │       │
│  │  update_pattern_in_file(...)             │       │
│  │  ┌────────────────────────────────────┐  │       │
│  │  │ 1. Read file                       │  │       │
│  │  │ 2. Find pattern by ID              │  │       │
│  │  │ 3. Deep merge updates              │  │       │
│  │  │ 4. Write file                      │  │       │
│  │  └────────────────────────────────────┘  │       │
│  │                                          │       │
│  │  remove_pattern_from_file(...)           │       │
│  │  ┌────────────────────────────────────┐  │       │
│  │  │ 1. Read file                       │  │       │
│  │  │ 2. Find pattern by ID              │  │       │
│  │  │ 3. Remove from list                │  │       │
│  │  │ 4. Write file                      │  │       │
│  │  └────────────────────────────────────┘  │       │
│  │                                          │       │
│  │  get_pattern_from_file(...)              │       │
│  │  list_patterns_in_file(...)              │       │
│  └──────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────┘
```

### 6. Pattern File Structure

All patterns are defined in a straightforward YAML format. This structure is designed to be human-readable and easy to edit. Each pattern file contains a namespace, a description, and a list of pattern definitions.

```yaml
# Pattern File (YAML)
┌─────────────────────────────────────────────┐
│ namespace: "kr"                             │  # Required
│ description: "Korean patterns"              │  # Required
│                                             │
│ patterns:                                   │  # Required (list)
│   - id: "mobile_01"                         │  # Required
│     location: "kr"                          │  # Required
│     category: "phone"                       │  # Required (enum)
│     description: "Korean mobile"            │  # Optional
│     pattern: "01[0-9]-\\d{4}-\\d{4}"        │  # Required (regex)
│     mask: "***-****-****"                   │  # Optional
│     flags: ["IGNORECASE"]                   │  # Optional
│     verification: "luhn"                    │  # Optional
│                                             │
│     examples:                               │  # Optional
│       match:                                │
│         - "010-1234-5678"                   │
│       nomatch:                              │
│         - "02-1234-5678"                    │
│                                             │
│     policy:                                 │  # Required
│       store_raw: false                      │  # Required
│       action_on_match: "redact"             │  # Required (enum)
│       severity: "high"                      │  # Required (enum)
│                                             │
│   - id: "rrn_01"                            │
│     # ... next pattern                      │
└─────────────────────────────────────────────┘
```

### 7. Deployment Architecture

This diagram shows a recommended architecture for deploying the Data Detector server in a production environment. It is designed to be horizontally scalable and resilient.

```
┌────────────────────────────────────────────────────────┐
│                  Production Deployment                 │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────────────────────────────────────────┐      │
│  │          Load Balancer                       │      │
│  │         (nginx/HAProxy)                      │      │
│  └─────────┬────────────────────────────────────┘      │
│            │                                           │
│    ┌───────┼────────┬──────────┬──────────┐            │
│    │       │        │          │          │            │
│    ▼       ▼        ▼          ▼          ▼            │
│  ┌────┐ ┌────┐  ┌────┐     ┌────┐     ┌─────┐          │
│  │Pod1│ │Pod2│  │Pod3│ ... │PodN│     │Pod  │          │
│  │    │ │    │  │    │     │    │     │(new)│          │
│  └────┘ └────┘  └────┘     └────┘     └─────┘          │
│    │       │        │          │         │             │
│    │  Each Pod contains:                 │             │
│    │  ┌──────────────────────────┐       │             │
│    │  │ data-detector server     │       │             │
│    │  │ - REST API               │       │             │
│    │  │ - gRPC API               │       │             │
│    │  │ - Pattern registry       │       │             │
│    │  │ - Prometheus metrics     │       │             │
│    │  └──────────────────────────┘       │             │
│    │                                     │             │
│    └─────────────┬───────────────────────┘             │
│                  │                                     │
│                  ▼                                     │
│         ┌──────────────────┐                           │
│         │ Pattern Storage  │                           │
│         │ (ConfigMap/      │                           │
│         │  Volume Mount)   │                           │
│         │                  │                           │
│         │ - common.yml     │                           │
│         │ - kr.yml         │                           │
│         │ - us.yml         │                           │
│         │ - custom.yml     │                           │
│         └────────────────--┘                           │
│                                                        │
│  ┌──────────────────────────────────────────────┐      │
│  │          Monitoring                          │      │
│  │  ┌──────────────┐  ┌──────────────────┐      │      │
│  │  │ Prometheus   │  │  Grafana         │      │      │
│  │  │ (metrics)    │  │  (dashboards)    │      │      │
│  │  └──────────────┘  └──────────────────┘      │      │
│  └──────────────────────────────────────────────┘      │
└────────────────────────────────────────────────────────┘
```

### 8. Resource Scanning Architecture

Data Detector can scan structured data resources (databases, Kafka, REST APIs, file storage, vector databases, AI training data) for PII using a pluggable adapter pattern. The system has three progressive components:

```
┌──────────────────────────────────────────────────────────────────┐
│                  Resource Scanning System                        │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                  Resource Adapters                         │  │
│  │                                                            │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │  │
│  │  │ Database │ │  Kafka   │ │   API    │ │File Storage  │  │  │
│  │  │(SQLAlch.)│ │(Schema R)│ │(OpenAPI) │ │(CSV/JSON/..) │  │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘  │  │
│  │       │             │            │              │          │  │
│  │  ┌──────────┐ ┌──────────────┐   │              │          │  │
│  │  │Vector DB │ │Training Data │   │              │          │  │
│  │  │(ChromaDB)│ │(JSONL/HF)    │   │              │          │  │
│  │  └────┬─────┘ └──────┬───────┘   │              │          │  │
│  │       │              │           │              │          │  │
│  │       └──────────────┴───────────┴──────────────┘          │  │
│  │                         │                                  │  │
│  │              ┌──────────▼───────────┐                      │  │
│  │              │  ResourceAdapter     │  (Abstract Base)     │  │
│  │              │  - connect()         │                      │  │
│  │              │  - list_containers() │                      │  │
│  │              │  - list_fields()     │                      │  │
│  │              │  - sample_values()   │                      │  │
│  │              └──────────┬───────────┘                      │  │
│  └──────────────────────────┼─────────────────────────────────┘  │
│                             │                                    │
│  ┌──────────────────────────▼─────────────────────────────────┐  │
│  │                  Data Explorer                             │  │
│  │                                                            │  │
│  │  scan(adapter) → ResourceScanResult                        │  │
│  │                                                            │  │
│  │  Pipeline:                                                 │  │
│  │  1. List containers (tables/topics/endpoints/files)        │  │
│  │  2. For each field: analyze metadata (field name/type)     │  │
│  │  3. Sample values → run Engine.find() per value            │  │
│  │  4. Combine scores: metadata_weight * meta + sample * val  │  │
│  │  5. Map to PIIConfidence (NONE→LOW→MEDIUM→HIGH→CONFIRMED) │  │
│  └──────────────────────────┬─────────────────────────────────┘  │
│                             │                                    │
│  ┌──────────────────────────▼─────────────────────────────────┐  │
│  │              Data Inventory Generator                      │  │
│  │                                                            │  │
│  │  generate() → DataInventory                                │  │
│  │  export(format) → JSON / CSV / YAML / HTML                 │  │
│  │  diff(old, new) → InventoryDiff (added/removed/changed)    │  │
│  │  summary() → breakdown by category, severity, resource     │  │
│  └──────────────────────────┬─────────────────────────────────┘  │
│                             │                                    │
│  ┌──────────────────────────▼─────────────────────────────────┐  │
│  │                Data Lineage Tracer                         │  │
│  │                                                            │  │
│  │  build_graph() → LineageGraph (nodes + edges)              │  │
│  │  trace(field, direction) → subgraph (BFS traversal)        │  │
│  │  get_pii_flow_summary() → {category: [field_paths]}        │  │
│  │  find_pii_sources() / find_pii_sinks()                     │  │
│  │  to_mermaid() → Mermaid diagram                            │  │
│  │  to_dict() → D3.js-compatible JSON                         │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

#### Resource Scanning Data Flow

```
Register DataResource (name, type, connection)
        │
        ▼
┌───────────────────┐
│  Adapter connects  │  (DB: SQLAlchemy inspect, Kafka: Schema Registry,
│  to resource       │   API: parse OpenAPI spec, File: discover files,
│                    │   VectorDB: ChromaDB collections, Training: JSONL/HF)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ List containers    │  (tables, topics, endpoints, files, collections, datasets)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ For each field:    │
│ 1. Metadata score  │  ← create_context_from_field_name()
│ 2. Sample values   │  ← adapter.sample_values()
│ 3. Engine.find()   │  ← existing regex/verification pipeline
│ 4. Combined score  │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ ResourceScanResult │  → DataInventoryGenerator → Export
│                    │  → DataLineageTracer → Graph / Mermaid
└───────────────────┘
```

## Key Design Principles

The architecture is guided by several key principles that ensure the system is robust, performant, and easy to use.

### 1. Separation of Concerns
- **Interface Layer**: User interaction (CLI/API/Server)
- **Core Engine**: Business logic (find/validate/redact)
- **Registry**: Pattern management and caching
- **Storage**: YAML file persistence
- **Utilities**: Reusable YAML operations

### 2. Extensibility
- Plugin architecture for verification functions
- Namespace-based pattern organization
- Custom pattern file support via YAML utilities
- Multiple interface options (CLI/Library/Server)

### 3. Performance
- Compiled regex caching in registry
- Namespace-based filtering
- Efficient pattern matching
- Hot reload without downtime

### 4. Security & Privacy
- No raw PII in logs (only hashes)
- Policy-based data handling (store_raw flag)
- TLS support for server
- Configurable severity levels

### 5. Developer Experience
- Simple API (Engine with 3 main methods)
- Comprehensive YAML utilities for pattern management
- Strong typing with dataclasses
- Extensive documentation and examples
- High test coverage

## Component Dependencies

The following diagram illustrates how the major components depend on each other.

```
┌─────────────────────────────────────────┐
│         Dependency Graph                │
├─────────────────────────────────────────┤
│                                         │
│  CLI ────────┐                          │
│              │                          │
│  Library API ├──► Engine                │
│              │      │                   │
│  Server ─────┘      │                   │
│                     │                   │
│                     ▼                   │
│              PatternRegistry            │
│                     │                   │
│                     ├──► Pattern        │
│                     │    (dataclass)    │
│                     │                   │
│                     ├──► Policy         │
│                     │    (dataclass)    │
│                     │                   │
│                     └──► Verification   │
│                          Functions      │
│                                         │
│  YAML Utilities ───► YAML Files         │
│  (PatternFileHandler)    (Storage)      │
│                                         │
└─────────────────────────────────────────┘
```

## Module Organization

The source code is organized into modules that correspond to the architectural layers.

```
data-detector/
├── src/datadetector/
│   ├── __init__.py          # Public API exports
│   ├── engine.py            # Core Engine class
│   ├── registry.py          # PatternRegistry & load_registry
│   ├── models.py            # Data models (Pattern, Policy, Results, ScoringConfig)
│   ├── analysis.py          # Context Analysis (keyword scoring + ML classifiers)
│   ├── nlp.py               # NLP processor (Korean/Chinese/Japanese)
│   ├── context.py           # Context-aware filtering
│   ├── utils/
│   │   └── yaml_utils.py    # YAML utilities
│   ├── verification.py      # Verification functions (Luhn, IBAN)
│   ├── transformer_ner.py   # Transformer NER detector (Way 1)
│   ├── training/
│   │   └── train_pii_classifier.py  # Fine-tune binary + category models
│   ├── cli.py               # Click CLI implementation
│   ├── server.py            # HTTP/gRPC server
│   │
│   │  # Resource Scanning
│   ├── resource_models.py   # Shared enums & dataclasses for resources
│   ├── resource_adapter.py  # Abstract ResourceAdapter base class
│   ├── data_explorer.py     # DataExplorer — scan any resource for PII
│   ├── data_inventory.py    # DataInventoryGenerator — catalog/export/diff
│   ├── data_lineage.py      # DataLineageTracer — PII flow graph
│   └── adapters/
│       ├── __init__.py      # Adapter registry & get_adapter_class()
│       ├── database.py      # DatabaseAdapter (SQLAlchemy)
│       ├── kafka.py         # KafkaAdapter (Schema Registry)
│       ├── api.py           # APIAdapter (OpenAPI spec)
│       ├── file_storage.py  # FileStorageAdapter (CSV/JSON/Parquet/Excel)
│       ├── vector_db.py     # VectorDBAdapter (ChromaDB)
│       └── training_data.py # TrainingDataAdapter (JSONL/HuggingFace)
│
├── pii-pattern-engine/      # Git submodule with pattern definitions
│   ├── regex/pii/           # PII patterns by country
│   │   ├── common/          # Cross-country patterns
│   │   ├── kr/              # Korean patterns
│   │   ├── us/              # US patterns
│   │   └── ...              # Other countries
│   └── ml/
│       ├── generate_data.py # Training data generation
│       ├── model.py         # sklearn model definitions
│       ├── train.py         # sklearn training script
│       ├── predict.py       # sklearn inference
│       └── models/transformer/  # Fine-tuned DistilBERT models (gitignored)
│           ├── binary_classifier/   # PII vs non-PII
│           └── category_classifier/ # 21 PII category types
│
├── tests/
│   ├── test_engine.py
│   ├── test_registry.py
│   ├── test_resource_models.py
│   ├── test_adapter_database.py
│   ├── test_adapter_kafka.py
│   ├── test_adapter_api.py
│   ├── test_adapter_file_storage.py
│   ├── test_adapter_vector_db.py
│   ├── test_adapter_training_data.py
│   ├── test_data_explorer.py
│   ├── test_data_inventory.py
│   ├── test_data_lineage.py
│   └── ...
│
├── docs/
│   ├── architecture/ARCHITECTURE.md  # This file
│   ├── guides/resource-scanning.md   # Resource scanning guide
│   └── ...
│
└── examples/
    └── yaml_usage_example.py
```

## Performance Characteristics

Performance is a key feature of Data Detector. The following table summarizes the typical performance profile.

```
┌──────────────────────────────────────────────────┐
│         Performance Profile                      │
├──────────────────────────────────────────────────┤
│                                                  │
│  Text Size    │  Latency (p95)  │  Throughput    │
│  ────────────────────────────────────────────    │
│  1 KB         │  < 10ms         │  500+ RPS      │
│  10 KB        │  < 50ms         │  200+ RPS      │
│  100 KB       │  < 200ms        │  50+ RPS       │
│                                                  │
│  Notes:                                          │
│  - Single namespace filtering                    │
│  - 1 vCPU, 512MB RAM                             │
│  - ~50 patterns loaded                           │
│                                                  │
│  Optimization Techniques:                        │
│  - Regex compilation caching                     │
│  - Early exit on validation                      │
│  - Namespace filtering                           │
│  - Compiled pattern reuse                        │
└──────────────────────────────────────────────────┘
```

## Error Handling Flow

The system has a clear error handling flow to ensure that issues are reported in a user-friendly way.

```
Error Occurs
     │
     ▼
┌─────────────────────┐
│ Exception Type?     │
└─────────┬───────────┘
          │
    ┌─────┼──────┬──────────────┬────────────┐
    │     │      │              │            │
    ▼     ▼      ▼              ▼            ▼
   FileNot  File   Value      Pattern      Other
   Found   Exists  Error      Error        Error
    │     │      │              │            │
    │     │      │              │            │
    └─────┴──────┴──────────────┴────────────┘
                 │
                 ▼
        ┌────────────────┐
        │ Log Error      │
        │ (level=ERROR)  │
        └────────┬───────┘
                 │
                 ▼
        ┌────────────────┐
        │ Format Message │
        │ (user-friendly)│
        └────────┬───────┘
                 │
                 ▼
        ┌────────────────┐
        │ Return/Raise   │
        │ - CLI: exit(1) │
        │ - API: raise   │
        │ - Server: 500  │
        └────────────────┘
```

---

This architecture supports:
- ✅ Multiple interfaces (CLI/Library/Server)
- ✅ Extensible pattern management
- ✅ High performance
- ✅ Easy pattern creation via YAML utilities
- ✅ Security and privacy by default
- ✅ Horizontal scalability
- ✅ Hot reload capability
- ✅ Comprehensive testing

```