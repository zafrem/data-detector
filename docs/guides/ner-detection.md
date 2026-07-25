# NER Detection (pii-engine / privyscope)

Regex detection is precise for well-formatted values — emails, phone numbers,
card numbers, national IDs — but it cannot recognise free-form entities such as
person names or street addresses. Data Detector closes that gap with an optional
**Named Entity Recognition (NER)** backend, the `pii-engine` submodule.

`pii-engine` vendors [**privyscope**](https://github.com/zafrem/privyscope): a
two-stage, multilingual PII engine that combines a regex pre-filter with an
optional ONNX BIOES/Viterbi NER model. It is disabled by default; when enabled
it occupies the engine's single NER slot.

> **Note:** privyscope is **not** published on PyPI. It ships as the
> `pii-engine` git submodule and is installed from there (see
> [Installation](#installation)).

---

## How it fits the pipeline

NER runs alongside regex inside `Engine.find()`. Its spans are merged with the
regex matches, never appended blindly:

| Situation | Result |
|:----------|:-------|
| NER finds a span **no regex matched** | The span is **added** as a new match (`namespace="privyscope"`, `detection_method="ner"`). |
| NER **overlaps** a regex match | The regex match is **corroborated** — score boosted by `ScoringConfig.ner_corroboration_boost`, `detection_method` becomes `"regex+ner"`, and `NER-corroboration:<category>` is recorded in `context_evidence`. |

This means turning NER on never produces duplicate spans for the same value; it
only adds coverage or increases confidence.

### Relationship to the Transformer NER

privyscope and the legacy HuggingFace `TransformerNERDetector` share the same
slot and are **mutually exclusive**. When a `PrivyscopeConfig` is enabled it
takes precedence; otherwise the engine falls back to the transformer NER (if
`TransformerConfig(enable_ner=True)` is set). Context classification
(`--ml-context` / `TransformerConfig(enable_context_classifier=True)`) is a
separate feature and is unaffected.

---

## Entity mapping

privyscope emits eight canonical entity codes (its `BASE_ENTITIES`). Each maps
onto a Data Detector `Category`:

| privyscope label | Category | Default severity |
|:-----------------|:---------|:-----------------|
| `PER`    | `NAME`           | medium |
| `PHONE`  | `PHONE`          | high   |
| `ID_NUM` | `IDENTIFICATION` | high   |
| `EMAIL`  | `EMAIL`          | medium |
| `LOC`    | `ADDRESS`        | high   |
| `BANK`   | `BANK`           | high   |
| `DATE`   | `DATE_OF_BIRTH`  | medium |
| `SECRET` | `TOKEN`          | high   |

Unknown labels are skipped. privyscope spans carry no per-span confidence, so
every match is assigned the configured backend score (`PrivyscopeConfig.score`,
default `0.6`).

---

## Enabling

### CLI

The `find`, `redact`, and `scan` commands accept `--ner` (and `--ner-lang`):

```bash
data-detector find   --text "greeting from 홍길동" --ner --ner-lang ko
data-detector redact --text "email a@acme.io"      --ner
data-detector scan   db --uri postgres://…          --ner
```

### Python API

```python
from datadetector import Engine, load_registry
from datadetector.models import PrivyscopeConfig

engine = Engine(
    load_registry(),
    privyscope_config=PrivyscopeConfig(enabled=True, lang="ko"),
)
result = engine.find("greeting from 홍길동, reach me at a@acme.io")
for m in result.matches:
    print(m.category.value, m.detection_method, m.score)
```

### Server / RAG middleware

Both build their engine from `config.yml`. Enable the `privyscope:` section; the
RAG middleware wraps the same engine and inherits the setting automatically:

```yaml
privyscope:
  enabled: true
  lang: ko                 # omit to use the sole installed language pack
  # auto_language: false   # route each text to its own language engine
  # operating_point: balanced   # balanced | high_recall | high_precision
  # regex_only: false      # skip the ONNX stage (no model weights needed)
  # cache_dir:             # local weights bundle for fully offline use
  # score: 0.6             # confidence assigned to privyscope matches
```

---

## Configuration reference (`PrivyscopeConfig`)

| Field | Default | Meaning |
|:------|:--------|:--------|
| `enabled` | `False` | Master switch for the backend. |
| `lang` | `None` | Language pack to use (`"ko"`, `"en"`, …). `None` uses the sole installed pack. |
| `auto_language` | `False` | Route each text to its own language engine (per-text detection). |
| `operating_point` | `"balanced"` | Decoder bias: `balanced`, `high_recall`, or `high_precision`. |
| `regex_only` | `False` | Skip the ONNX NER stage — no model weights required, works offline. |
| `cache_dir` | `None` | Local weights bundle; enables fully offline use when pre-populated. |
| `score` | `0.6` | Confidence assigned to each privyscope match. |

`PrivyscopeConfig.from_dict(mapping)` builds a config from a `config.yml`
section, coercing types and ignoring unknown keys.

---

## Installation

privyscope ships no language data on its own. Install the core from the
submodule, then at least one language pack for the ONNX NER stage:

```bash
git submodule update --init pii-engine
pip install -e pii-engine
pip install privyscope-ko          # and/or privyscope-en
```

On first use the language pack downloads its ONNX weights from Hugging Face, so
the full NER path needs network access once (or a pre-populated `cache_dir`).

---

## Graceful degradation

The backend is designed to fail soft. If privyscope is not installed, no
language pack is present, or weights cannot be fetched, detection silently
falls back to **regex-only** — no exceptions are raised, and `find()` still
returns its regex matches. Set `regex_only=True` to run privyscope's own regex
stage without any model download.
