# Contextual Analysis Guide

This guide explains the **Contextual Analysis** feature (Step 3 of the detection pipeline), which significantly improves detection accuracy by analyzing the text surrounding a potential match.

## Overview

The detection engine uses a 4-step pipeline:
1.  **Regex Matching**: Finds candidate strings (e.g., "98004").
2.  **Verification**: Validates the format (e.g., Checksums, Data lookup). Verified matches get `verified=True` and a higher initial score (0.95 vs 0.50).
3.  **Context Analysis**: Scores the match based on surrounding "Anchor Keywords" and ML classifiers.
4.  **Post-pipeline Filtering**: Applies `min_score` threshold and placeholder detection.

Step 3 is crucial for resolving ambiguity. For example, the number `98004` could be a Zip Code or a transaction ID. If it appears as `Bellevue, WA 98004`, Context Analysis boosts the confidence score because valid address anchors are nearby.

## Proximity Scoring

The system uses a **Proximity (Distance)** algorithm rather than simple keyword existence.

### Logic
1.  **Windowing**: Captures a window of text (configurable via `ScoringConfig.keyword_window`, default ±60 characters) around the candidate match.
2.  **Distance Calculation**: Measures the character distance between the match and the nearest anchor keyword.
3.  **Scoring** (all values configurable via `ScoringConfig`):

    **Before match (keyword appears before the PII value):**
    *   **High Confidence**: Distance < 10 characters (e.g., `Zip: 90210`). Boost: **+0.45** (`keyword_pre_close_boost`).
    *   **Medium Confidence**: Distance < 30 characters (e.g., `123 Main St, 90210`). Boost: **+0.30** (`keyword_pre_far_boost`).
    *   **Low Confidence**: Distance < 60 characters. Boost: **+0.10** (`keyword_pre_weak_boost`).

    **After match (keyword appears after the PII value):**
    *   **High Confidence**: Distance < 10 characters. Boost: **+0.40** (`keyword_post_close_boost`).
    *   **Medium Confidence**: Distance < 30 characters. Boost: **+0.25** (`keyword_post_far_boost`).
    *   **Low Confidence**: Distance < 60 characters. Boost: **+0.10** (`keyword_post_weak_boost`).

## Address Detection (US, KR, JP)

The system includes built-in support for address context in three major regions.

### United States (US)
*   **Category**: `address_us`
*   **Anchors**:
    *   **State Abbreviations**: `WA`, `CA`, `NY`, `TX`, etc.
    *   **Street Types**: `St`, `Ave`, `Blvd`, `Rd`, `Dr`, `Lane`, `Apt`, `Suite`.
    *   **Labels**: `Zip`, `Zip Code`, `State`, `Address`.

### South Korea (KR)
*   **Category**: `address_kr`
*   **Anchors**:
    *   **Administrative**: `도`, `시`, `군`, `구`, `읍`, `면`, `동`, `리`.
    *   **Road Names**: `로`, `길`, `번지`.
    *   **Labels**: `우편번호` (Postal Code), `주소` (Address), `배송지` (Shipping Address).
    *   **Cities**: `서울`, `경기`, `부산`, `대구`, etc.

### Japan (JP)
*   **Category**: `address_jp`
*   **Anchors**:
    *   **Symbols**: `〒` (Postal Symbol).
    *   **Administrative**: `都`, `道`, `府`, `県`, `市`, `区`, `町`, `村`.
    *   **Address Components**: `丁目`, `番地`, `号`.
    *   **Labels**: `郵便番号`, `住所`.

## Configuration

Context keywords are defined in YAML files located in `pii-pattern-engine/keyword/`.

### Example: `address.yml`

```yaml
category: address
categories:
  address_us:
    description: US Address indicators
    patterns:
      - WA
      - CA
      - St
      - Ave
      - Zip Code
    contexts:
      - "Zip:"

  address_kr:
    description: Korean Address indicators
    patterns:
      - 서울
      - 경기
      - 우편번호
```

## ML Context Classification (Step 3b)

When `TransformerConfig(enable_context_classifier=True)` is set, the engine runs two fine-tuned DistilBERT classifiers after the keyword check to further refine match scores.

> **Context classification vs. NER.** This section is about *context
> classification* — scoring regex matches. For *named-entity recognition*
> (finding names/addresses regex misses) via the `pii-engine` (privyscope)
> backend, see the [NER Detection Guide](ner-detection.md).

### Models

| Model | Task | Location | Performance |
|:------|:-----|:---------|:------------|
| Binary Classifier | PII vs Non-PII | `pii-engine/models/transformer/binary_classifier/` | 96.2% accuracy, F1 96.9% |
| Category Classifier | 21 PII types | `pii-engine/models/transformer/category_classifier/` | 87.9% accuracy, F1 86.5% |

Fine-tuned models are **auto-discovered** from `pii-engine/models/transformer/`
when present. These weights are **not bundled** — the `pii-engine` submodule now
hosts the privyscope NER backend, not the classifier models. Train your own with
`python -m datadetector.training.train_pii_classifier` (see below) and place them
there, or the engine falls back to the generic zero-shot model
(`facebook/bart-large-mnli`). Performance figures above are for the reference
fine-tuned models.

### Scoring Logic

For each regex match, the matched text is extracted and classified:

**Binary Classifier** (is this actually PII?):
*   **Verified matches are skipped** — if the match passed a verification function (Luhn, IBAN mod-97, etc.), the binary classifier is not applied. These matches already have high confidence (0.95) from verification.
*   `pii` with confidence > 0.5 → **boost** score by `+0.35 * confidence` (capped at 0.99). Max boost configurable via `TransformerConfig.context_max_boost`.
*   `non_pii` with confidence > 0.5 → **penalize** score by `-0.2` (floored at 0.01). Penalty configurable via `TransformerConfig.context_penalty`.
*   Confidence <= 0.5 → no change. Threshold configurable via `TransformerConfig.context_confidence_threshold`.

**Category Classifier** (does ML agree with regex?):
*   ML category **matches** regex category with confidence > 0.5 → **boost** score by `+0.15 * confidence` (configurable via `ScoringConfig.ml_category_boost`)
*   ML category **mismatches** regex category with confidence > 0.7 → **log warning** only (no score change)

### Usage

```python
from datadetector import Engine, load_registry
from datadetector.models import TransformerConfig

config = TransformerConfig(enable_context_classifier=True)
registry = load_registry()
engine = Engine(registry, transformer_config=config)

results = engine.find("My phone is 010-1234-5678")
for m in results.matches:
    print(m.score, m.context_evidence)
    # 0.99 ['phone (dist: -4)', 'ML-binary:pii (conf=0.999, boost=+0.350)', 'ML-category:phone (conf=0.817, boost=+0.123)']
```

### Configuration

ML thresholds are configurable via `TransformerConfig`:

| Parameter | Default | Description |
|:----------|:--------|:------------|
| `context_confidence_threshold` | 0.5 | Minimum confidence to act on ML result |
| `context_max_boost` | 0.35 | Maximum boost from binary classifier |
| `context_penalty` | 0.2 | Penalty for non-PII classification |
| `binary_model_path` | (auto) | Override binary model path |
| `category_model_path` | (auto) | Override category model path |
| `device` | "cpu" | Device for inference ("cpu" or GPU index) |

## ScoringConfig — Centralized Weight Tuning

All scoring weights, initial scores, and filtering options are centralized in `ScoringConfig`. Pass it to the `Engine` constructor to customize detection behavior.

```python
from datadetector import Engine, ScoringConfig, load_registry

# High-precision mode: require higher scores, lower keyword boosts
scoring = ScoringConfig(
    min_score=0.7,
    keyword_pre_close_boost=0.20,
    keyword_pre_far_boost=0.10,
    keyword_pre_weak_boost=0.05,
)
engine = Engine(load_registry(), scoring_config=scoring)
```

### Full Parameter Reference

| Parameter | Default | Description |
|:----------|:--------|:------------|
| **Initial Scores** | | |
| `initial_verified` | 0.95 | Score for matches that pass verification (Luhn, checksum) |
| `initial_unverified` | 0.50 | Score for regex-only matches |
| **Keyword Proximity (before match)** | | |
| `keyword_window` | 60 | Window size (chars) for keyword search |
| `keyword_pre_close_boost` | 0.45 | Keyword < 10 chars before match |
| `keyword_pre_far_boost` | 0.30 | Keyword < 30 chars before match |
| `keyword_pre_weak_boost` | 0.10 | Keyword < 60 chars before match |
| **Keyword Proximity (after match)** | | |
| `keyword_post_close_boost` | 0.40 | Keyword < 10 chars after match |
| `keyword_post_far_boost` | 0.25 | Keyword < 30 chars after match |
| `keyword_post_weak_boost` | 0.10 | Keyword < 60 chars after match |
| **ML Weights** | | |
| `ml_category_boost` | 0.15 | Boost when ML category matches regex category |
| `ner_corroboration_boost` | 0.15 | Boost when NER agrees with regex span |
| **Filtering** | | |
| `min_score` | 0.0 | Drop matches below this score after all scoring |
| `filter_placeholders` | True | Filter test/placeholder data (e.g., `010-1234-5678`, `test@example.com`) |

### Verified Matches

Matches that pass a verification function (Luhn algorithm for credit cards, IBAN mod-97, checksum validation, etc.) receive special treatment:

1. **Higher initial score**: `initial_verified` (0.95) instead of `initial_unverified` (0.50)
2. **Skip binary ML classifier**: The binary PII/non-PII classifier is not applied — mathematical verification already confirms the match is valid
3. **Category ML still applies**: The category classifier still runs to validate the PII type

This prevents verified matches from being incorrectly penalized by the ML model.

### min_score Filtering

After all scoring steps complete, matches with a score below `min_score` are removed:

```python
# Only keep high-confidence matches
engine = Engine(load_registry(), scoring_config=ScoringConfig(min_score=0.7))
result = engine.find("some text with data 12345")
# Only matches scoring >= 0.7 are returned
```

### Placeholder Filtering

When `filter_placeholders=True` (default), common test/placeholder values are automatically removed:
- Sequential digits: `010-1234-5678`, `123-45-6789`
- Example domains: `test@example.com`, `user@test.org`

Disable for testing: `ScoringConfig(filter_placeholders=False)`

### Training Custom Models

To retrain models on your own data:

```bash
python -m datadetector.training.train_pii_classifier \
    --data-dir /path/to/data \
    --output-dir pii-engine/transformer \
    --base-model distilbert-base-uncased \
    --epochs 5 --batch-size 16
```

Data generation: `pii-engine/generate_data.py`

### Fallback Behavior

If fine-tuned models are not found, and `enable_context_classifier=True`, the system falls back to a zero-shot classifier (`facebook/bart-large-mnli`) which classifies context windows around matches without task-specific training.

Requires: `pip install data-detector[transformer]`

## Adding Custom Contexts

To add context for a new category (e.g., "medical"):

1.  Create `pii-pattern-engine/keyword/medical.yml`.
2.  Define the category and anchor patterns:
    ```yaml
    category: medical
    categories:
      medical_ids:
        patterns:
          - patient
          - mrn
          - diagnosis
          - hospital
    ```
3.  The engine will automatically load this file and apply it to matches with `category: medical`.
