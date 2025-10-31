# Data Detector Architecture

This document describes the architecture of the data-detector system using text-based diagrams.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA DETECTOR                            │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    Interface Layer                        │ │
│  │                                                           │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │ │
│  │  │   CLI    │  │ Library  │  │   Server (HTTP/gRPC) │   │ │
│  │  │  (Click) │  │   API    │  │                      │   │ │
│  │  └────┬─────┘  └────┬─────┘  └──────────┬───────────┘   │ │
│  └───────┼─────────────┼───────────────────┼───────────────┘ │
│          │             │                   │                 │
│          └─────────────┼───────────────────┘                 │
│                        │                                     │
│  ┌─────────────────────▼────────────────────────────────┐   │
│  │              Core Engine Layer                       │   │
│  │                                                      │   │
│  │  ┌────────────────────────────────────────────────┐ │   │
│  │  │             Engine                             │ │   │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────────┐  │ │   │
│  │  │  │  find()  │ │validate()│ │  redact()    │  │ │   │
│  │  │  └──────────┘ └──────────┘ └──────────────┘  │ │   │
│  │  └────────────────┬───────────────────────────── │ │   │
│  │                   │                               │   │
│  │  ┌────────────────▼────────────────────────────┐ │   │
│  │  │         PatternRegistry                     │ │   │
│  │  │  - Pattern compilation & caching            │ │   │
│  │  │  - Namespace organization                   │ │   │
│  │  │  - Verification function registry           │ │   │
│  │  └────────────────┬────────────────────────────┘ │   │
│  └───────────────────┼──────────────────────────────┘   │
│                      │                                   │
│  ┌───────────────────▼──────────────────────────────┐   │
│  │           Data Model Layer                       │   │
│  │                                                   │   │
│  │  ┌──────────┐ ┌──────────┐ ┌────────────────┐   │   │
│  │  │ Pattern  │ │  Policy  │ │ Match/Result   │   │   │
│  │  │ (dataclass)│ │(dataclass)│ │   Models      │   │   │
│  │  └──────────┘ └──────────┘ └────────────────┘   │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │         YAML Utilities Layer (NEW!)              │   │
│  │                                                   │   │
│  │  ┌──────────────────┐  ┌────────────────────┐   │   │
│  │  │  YAMLHandler     │  │ PatternFileHandler │   │   │
│  │  │  - read_yaml()   │  │ - create_pattern() │   │   │
│  │  │  - write_yaml()  │  │ - add_pattern()    │   │   │
│  │  │  - update_yaml() │  │ - update_pattern() │   │   │
│  │  │                  │  │ - remove_pattern() │   │   │
│  │  └──────────────────┘  └────────────────────┘   │   │
│  └─────────────────┬────────────────────────────────┘   │
│                    │                                     │
│  ┌─────────────────▼────────────────────────────────┐   │
│  │            Storage Layer                         │   │
│  │                                                   │   │
│  │  Pattern Files (YAML)                            │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────┐     │   │
│  │  │ common/  │ │   kr/    │ │   us/tw/jp/  │     │   │
│  │  │ patterns │ │ patterns │ │   cn/in...   │     │   │
│  │  └──────────┘ └──────────┘ └──────────────┘     │   │
│  │                                                   │   │
│  │  Custom Pattern Files (User-created)             │   │
│  │  ┌──────────────────────────────────────┐        │   │
│  │  │  custom_patterns.yml                 │        │   │
│  │  │  company_patterns.yml                │        │   │
│  │  │  ...                                 │        │   │
│  │  └──────────────────────────────────────┘        │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Interface Layer

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
│ registry = load_registry(paths=["patterns/"])      │
│ engine = Engine(registry)                          │
│                                                     │
│ # Operations                                        │
│ engine.find(text, namespaces=[...])                │
│ engine.validate(text, pattern_id)                  │
│ engine.redact(text, namespaces=[...])              │
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

```
┌──────────────────────────────────────────────────────────┐
│                       Engine                             │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  find(text, namespaces, include_matched_text)            │
│  ┌────────────────────────────────────────────┐         │
│  │ 1. Get patterns from registry              │         │
│  │ 2. Apply each pattern to text              │         │
│  │ 3. Run verification functions if present   │         │
│  │ 4. Collect matches with metadata           │         │
│  │ 5. Return FindResult                       │         │
│  └────────────────────────────────────────────┘         │
│                                                          │
│  validate(text, pattern_id)                              │
│  ┌────────────────────────────────────────────┐         │
│  │ 1. Get single pattern from registry        │         │
│  │ 2. Check if text matches pattern           │         │
│  │ 3. Run verification function if present    │         │
│  │ 4. Return ValidationResult (bool)          │         │
│  └────────────────────────────────────────────┘         │
│                                                          │
│  redact(text, namespaces, strategy)                      │
│  ┌────────────────────────────────────────────┐         │
│  │ 1. Find all matches in text                │         │
│  │ 2. Apply redaction strategy:               │         │
│  │    - mask: Replace with mask value         │         │
│  │    - hash: Replace with hash               │         │
│  │    - tokenize: Replace with token          │         │
│  │ 3. Build redacted text                     │         │
│  │ 4. Return RedactionResult                  │         │
│  └────────────────────────────────────────────┘         │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                  PatternRegistry                         │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Data Structures:                                        │
│  ┌──────────────────────────────────────────────┐       │
│  │ _patterns: Dict[str, Pattern]                │       │
│  │   Key: "namespace/pattern_id"                │       │
│  │   Value: Pattern object                      │       │
│  │                                              │       │
│  │ _by_namespace: Dict[str, List[Pattern]]      │       │
│  │   Key: "namespace"                           │       │
│  │   Value: List of patterns                    │       │
│  │                                              │       │
│  │ _verification_funcs: Dict[str, Callable]     │       │
│  │   Key: "function_name"                       │       │
│  │   Value: Verification function               │       │
│  └──────────────────────────────────────────────┘       │
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

```
┌─────────────────────────────────────────────────────┐
│              YAML Utilities Layer                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────────────────────────────────┐      │
│  │         YAMLHandler (Base)               │      │
│  │                                          │      │
│  │  read_yaml(file_path)                    │      │
│  │  ┌────────────────────────────────────┐  │      │
│  │  │ 1. Check file exists               │  │      │
│  │  │ 2. Load YAML with safe_load        │  │      │
│  │  │ 3. Validate is dict                │  │      │
│  │  │ 4. Return data                     │  │      │
│  │  └────────────────────────────────────┘  │      │
│  │                                          │      │
│  │  write_yaml(file_path, data, ...)        │      │
│  │  ┌────────────────────────────────────┐  │      │
│  │  │ 1. Validate data is dict           │  │      │
│  │  │ 2. Check overwrite flag            │  │      │
│  │  │ 3. Create parent dirs              │  │      │
│  │  │ 4. Dump YAML with formatting       │  │      │
│  │  └────────────────────────────────────┘  │      │
│  │                                          │      │
│  │  update_yaml(file_path, updates, ...)    │      │
│  │  ┌────────────────────────────────────┐  │      │
│  │  │ 1. Read existing data              │  │      │
│  │  │ 2. Merge or replace                │  │      │
│  │  │ 3. Write updated data              │  │      │
│  │  └────────────────────────────────────┘  │      │
│  └──────────────────────────────────────────┘      │
│                                                     │
│  ┌──────────────────────────────────────────┐      │
│  │   PatternFileHandler (Specialized)       │      │
│  │                                          │      │
│  │  create_pattern_file(...)                │      │
│  │  ┌────────────────────────────────────┐  │      │
│  │  │ 1. Build pattern file structure    │  │      │
│  │  │ 2. Validate namespace & patterns   │  │      │
│  │  │ 3. Write via YAMLHandler           │  │      │
│  │  └────────────────────────────────────┘  │      │
│  │                                          │      │
│  │  add_pattern_to_file(...)                │      │
│  │  ┌────────────────────────────────────┐  │      │
│  │  │ 1. Read existing file              │  │      │
│  │  │ 2. Validate pattern structure      │  │      │
│  │  │ 3. Check for duplicates            │  │      │
│  │  │ 4. Append to patterns list         │  │      │
│  │  │ 5. Write updated file              │  │      │
│  │  └────────────────────────────────────┘  │      │
│  │                                          │      │
│  │  update_pattern_in_file(...)             │      │
│  │  ┌────────────────────────────────────┐  │      │
│  │  │ 1. Read file                       │  │      │
│  │  │ 2. Find pattern by ID              │  │      │
│  │  │ 3. Deep merge updates              │  │      │
│  │  │ 4. Write file                      │  │      │
│  │  └────────────────────────────────────┘  │      │
│  │                                          │      │
│  │  remove_pattern_from_file(...)           │      │
│  │  ┌────────────────────────────────────┐  │      │
│  │  │ 1. Read file                       │  │      │
│  │  │ 2. Find pattern by ID              │  │      │
│  │  │ 3. Remove from list                │  │      │
│  │  │ 4. Write file                      │  │      │
│  │  └────────────────────────────────────┘  │      │
│  │                                          │      │
│  │  get_pattern_from_file(...)              │      │
│  │  list_patterns_in_file(...)              │      │
│  └──────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────┘
```

### 6. Pattern File Structure

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
│     pattern: "01[0-9]-\\d{4}-\\d{4}"       │  # Required (regex)
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
│     # ... next pattern                     │
└─────────────────────────────────────────────┘
```

### 7. Deployment Architecture

```
┌────────────────────────────────────────────────────────┐
│                  Production Deployment                 │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────────────────────────────────────────┐     │
│  │          Load Balancer                       │     │
│  │         (nginx/HAProxy)                      │     │
│  └─────────┬────────────────────────────────────┘     │
│            │                                           │
│    ┌───────┼────────┬──────────┬──────────┐           │
│    │       │        │          │          │           │
│    ▼       ▼        ▼          ▼          ▼           │
│  ┌────┐ ┌────┐  ┌────┐     ┌────┐     ┌────┐         │
│  │Pod1│ │Pod2│  │Pod3│ ... │PodN│     │Pod │         │
│  │    │ │    │  │    │     │    │     │(new)│         │
│  └────┘ └────┘  └────┘     └────┘     └────┘         │
│    │       │        │          │          │           │
│    │  Each Pod contains:                 │           │
│    │  ┌──────────────────────────┐       │           │
│    │  │ data-detector server     │       │           │
│    │  │ - REST API               │       │           │
│    │  │ - gRPC API               │       │           │
│    │  │ - Pattern registry       │       │           │
│    │  │ - Prometheus metrics     │       │           │
│    │  └──────────────────────────┘       │           │
│    │                                     │           │
│    └─────────────┬───────────────────────┘           │
│                  │                                    │
│                  ▼                                    │
│         ┌──────────────────┐                          │
│         │ Pattern Storage  │                          │
│         │ (ConfigMap/      │                          │
│         │  Volume Mount)   │                          │
│         │                  │                          │
│         │ - common.yml     │                          │
│         │ - kr.yml         │                          │
│         │ - us.yml         │                          │
│         │ - custom.yml     │                          │
│         └──────────────────┘                          │
│                                                        │
│  ┌──────────────────────────────────────────────┐     │
│  │          Monitoring                          │     │
│  │  ┌──────────────┐  ┌──────────────────┐     │     │
│  │  │ Prometheus   │  │  Grafana         │     │     │
│  │  │ (metrics)    │  │  (dashboards)    │     │     │
│  │  └──────────────┘  └──────────────────┘     │     │
│  └──────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────┘
```

## Key Design Principles

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
- Efficient pattern matching (p95 < 10ms for 1KB)
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
- 94% test coverage

## Component Dependencies

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

```
data-detector/
├── src/datadetector/
│   ├── __init__.py          # Public API exports
│   ├── engine.py            # Core Engine class
│   ├── registry.py          # PatternRegistry & load_registry
│   ├── models.py            # Data models (Pattern, Policy, Results)
│   ├── utils/               # Utility modules
│   │   └── yaml_utils.py    # YAML utilities
│   ├── verification.py      # Verification functions (Luhn, IBAN)
│   ├── cli.py               # Click CLI implementation
│   └── server.py            # HTTP/gRPC server
│
├── patterns/                # Built-in pattern files
│   ├── common.yml           # Cross-country patterns
│   ├── kr.yml               # Korean patterns
│   ├── us.yml               # US patterns
│   └── ...                  # Other countries
│
├── tests/                   # Test suite (94% coverage)
│   ├── test_engine.py
│   ├── test_registry.py
│   ├── test_yaml_utils.py   # YAML utilities tests (NEW!)
│   └── ...
│
├── docs/                    # Documentation
│   ├── ARCHITECTURE.md      # This file
│   ├── yaml_utilities.md    # YAML utilities guide
│   └── ...
│
└── examples/
    └── yaml_usage_example.py  # YAML utilities examples
```

## Performance Characteristics

```
┌──────────────────────────────────────────────────┐
│         Performance Profile                      │
├──────────────────────────────────────────────────┤
│                                                  │
│  Text Size    │  Latency (p95)  │  Throughput   │
│  ────────────────────────────────────────────   │
│  1 KB         │  < 10ms         │  500+ RPS     │
│  10 KB        │  < 50ms         │  200+ RPS     │
│  100 KB       │  < 200ms        │  50+ RPS      │
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
- ✅ High performance (p95 < 10ms)
- ✅ Easy pattern creation via YAML utilities
- ✅ Security and privacy by default
- ✅ Horizontal scalability
- ✅ Hot reload capability
- ✅ Comprehensive testing (94% coverage)
