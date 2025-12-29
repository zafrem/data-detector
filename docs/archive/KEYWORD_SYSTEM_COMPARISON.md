# Keyword System Comparison

## Two Different Keyword Systems

There are now TWO different keyword systems in this project, each serving a different purpose:

### 1. Pattern Mapping Keywords (`config/keywords.yml`)
**Purpose:** Programmatic mapping of keywords to specific pattern IDs

**Structure:**
```yaml
keywords:
  ssn:
    categories: [ssn]
    patterns: [us/ssn_01, us/itin_01]
    priority: high
```

**Use Case:** When you have a keyword like "ssn" or "계좌번호" and want to know which specific patterns to load/use

**Example:**
```python
# User provides keyword "bank_account"
# System looks up patterns: [kr/bank_account_01, kr/bank_account_02, ...]
keyword_config = load_keywords("config/keywords.yml")
patterns = keyword_config["bank_account"]["patterns"]
```

---

### 2. Context Detection Keywords (`regex-patterns/keywords/*.yml`)
**Purpose:** Contextual keywords that appear NEAR sensitive data in text (NEW - just created)

**Structure:**
```yaml
categories:
  bank:
    patterns:
      - bank account
      - 계좌번호
      - 口座番号
    contexts:
      - "Account Number:"
      - "계좌번호:"
```

**Use Case:** Detecting if a pattern match has relevant context keywords nearby to reduce false positives

**Example:**
```python
# Text: "Employee SSN: 123-45-6789"
# Check if "SSN" keyword is near the matched number
# If yes, higher confidence it's real PII
text = "Employee SSN: 123-45-6789"
context = get_nearby_text(text, match_position, window=50)
if has_keyword(context, ssn_keywords):
    confidence = "high"
```

---

## Comparison Table

| Feature | Pattern Mapping (`config/keywords.yml`) | Context Detection (`regex-patterns/keywords/`) |
|---------|----------------------------------------|-----------------------------------------------|
| **Purpose** | Map keywords to pattern IDs | Detect keywords near matched patterns |
| **Format** | Single YAML file | Multiple category files |
| **Structure** | `keyword → [pattern_ids]` | `category → [contextual_keywords]` |
| **Usage** | Select which patterns to load | Validate pattern matches with context |
| **Languages** | Korean, English keywords | English, Korean, Japanese, Chinese |
| **Example** | `bank_account: [kr/bank_account_*]` | `patterns: [bank account, 계좌번호, 口座番号]` |
| **Integration** | Pattern loading/selection | False positive reduction |

---

## Which Should You Use?

### Use `config/keywords.yml` when:
- ✅ You need to load specific patterns based on a keyword
- ✅ User provides a search term like "ssn" or "bank account"
- ✅ You want to know which pattern IDs handle a certain type of data
- ✅ You're building a pattern selection UI

### Use `regex-patterns/keywords/` when:
- ✅ You need to validate that a pattern match has relevant context
- ✅ Reducing false positives by checking surrounding text
- ✅ Multi-language context detection
- ✅ Understanding what labels/headers typically precede PII

---

## Example Workflows

### Workflow 1: Pattern Selection (Use `config/keywords.yml`)
```python
# User wants to detect "bank accounts"
keyword = "bank_account"

# Look up which patterns handle this
keyword_config = load_yaml("config/keywords.yml")
pattern_ids = keyword_config["keywords"]["bank_account"]["patterns"]
# Result: [kr/bank_account_01, kr/bank_account_02, ...]

# Load those patterns
registry = load_registry(pattern_ids=pattern_ids)
```

### Workflow 2: Context Validation (Use `regex-patterns/keywords/`)
```python
# Pattern matched a number: "110-123-456789"
# Is it really a bank account?

# Load context keywords
context_keywords = load_yaml("regex-patterns/keywords/financial.yml")
bank_keywords = context_keywords["categories"]["bank"]["patterns"]
# Result: [bank account, 계좌번호, ...]

# Check if any keyword is near the match
context = text[match_pos-50:match_pos+50]
if any(kw in context for kw in bank_keywords):
    confidence = "high"  # Likely real bank account
else:
    confidence = "low"   # Maybe false positive
```

### Workflow 3: Combined Approach (Use Both)
```python
# Step 1: User searches for "bank"
pattern_ids = get_patterns_for_keyword("bank_account")  # config/keywords.yml

# Step 2: Run detection with those patterns
matches = engine.find(text, patterns=pattern_ids)

# Step 3: Validate matches with context
context_kw = load_context_keywords("financial.yml")  # regex-patterns/keywords/
for match in matches:
    if has_context(match, context_kw):
        match.confidence = "high"
```

---

## Summary

**What exists:**
- ✅ `config/keywords.yml` - 534 lines, maps keywords to pattern IDs (already existed)

**What was created:**
- ✅ `regex-patterns/keywords/` - NEW directory with 5 category files
  - `financial.yml` - Bank, credit card, IBAN context keywords
  - `identification.yml` - SSN, passport, national ID context keywords  
  - `contact.yml` - Email, phone, address context keywords
  - `network.yml` - IP, URL context keywords
  - `personal.yml` - Name, DOB, gender context keywords

**Both systems are valuable** and serve different purposes in the PII detection pipeline!

---

## Files Overview

```
config/
└── keywords.yml                    # Pattern mapping (534 lines)

regex-patterns/keywords/
├── README.md                       # Context keywords docs
├── MAPPING.md                      # Pattern-to-category mapping
├── financial.yml                   # Financial context keywords
├── identification.yml              # ID context keywords
├── contact.yml                     # Contact context keywords
├── network.yml                     # Network context keywords
└── personal.yml                    # Personal context keywords
```

Total: 525+ lines of new context keywords across 5 category files
