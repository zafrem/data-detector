# Context Presets - Cheat Sheet

Quick reference for using pre-configured context presets. Copy-paste ready!

## 🚀 Quick Start

```python
from datadetector import Engine, load_registry, context_presets

engine = Engine(registry=load_registry())

# Use any preset
result = engine.find(value, context=context_presets.DATABASE_SSN)
```

---

## 📊 Database Presets (English)

```python
from datadetector import context_presets

# Social Security Numbers
result = engine.find(ssn_value, context=context_presets.DATABASE_SSN)

# Email addresses
result = engine.find(email_value, context=context_presets.DATABASE_EMAIL)

# Phone numbers
result = engine.find(phone_value, context=context_presets.DATABASE_PHONE)

# ZIP codes / Addresses
result = engine.find(zip_value, context=context_presets.DATABASE_ADDRESS)

# Credit card numbers
result = engine.find(card_value, context=context_presets.DATABASE_CREDIT_CARD)

# Bank account numbers
result = engine.find(account_value, context=context_presets.DATABASE_BANK_ACCOUNT)

# Passport numbers
result = engine.find(passport_value, context=context_presets.DATABASE_PASSPORT)
```

---

## 🇰🇷 Korean Presets

```python
from datadetector import context_presets

# 주민등록번호 (RRN)
result = engine.find("900101-1234567", context=context_presets.KOREAN_RRN)

# 계좌번호 (Bank Account)
result = engine.find("110-123-456789", context=context_presets.KOREAN_BANK_ACCOUNT)

# 전화번호 (Phone)
result = engine.find("010-1234-5678", context=context_presets.KOREAN_PHONE)

# 사업자등록번호 (Business Registration)
result = engine.find("123-45-67890", context=context_presets.KOREAN_BUSINESS)

# 우편번호 (Postal Code)
result = engine.find("06234", context=context_presets.KOREAN_ADDRESS)
```

---

## 📋 Category Presets

```python
from datadetector import context_presets

# Contact information (email, phone, address)
result = engine.find(contact_data, context=context_presets.CONTACT_INFO)

# Financial data (SSN, credit card, bank account)
result = engine.find(financial_data, context=context_presets.FINANCIAL_DATA)

# Payment info only (credit card, bank account)
result = engine.find(payment_data, context=context_presets.PAYMENT_INFO)

# Personal IDs (SSN, passport, driver license)
result = engine.find(id_data, context=context_presets.PERSONAL_IDENTIFIERS)

# Technical data (IP addresses, API keys)
result = engine.find(log_data, context=context_presets.TECHNICAL_DATA)

# Location data (addresses, coordinates)
result = engine.find(location_data, context=context_presets.LOCATION_DATA)
```

---

## 🎯 Comprehensive Presets

```python
from datadetector import context_presets

# All PII types (61 patterns - slower but comprehensive)
result = engine.find(unknown_data, context=context_presets.PII_ALL)

# Critical PII only (SSN, credit card, passport)
result = engine.find(data, context=context_presets.PII_CRITICAL_ONLY)

# Medium-high severity PII
result = engine.find(data, context=context_presets.PII_MEDIUM_HIGH)
```

---

## 🌐 API Presets

```python
from datadetector import context_presets

# User data APIs
result = engine.find(api_response, context=context_presets.API_USER_DATA)

# Payment APIs
result = engine.find(payment_response, context=context_presets.API_PAYMENT_DATA)
```

---

## 📄 Document Presets

```python
from datadetector import context_presets

# General documents
result = engine.find(document_text, context=context_presets.DOCUMENT_GENERAL)

# Medical records
result = engine.find(medical_record, context=context_presets.DOCUMENT_MEDICAL)

# Financial documents
result = engine.find(financial_doc, context=context_presets.DOCUMENT_FINANCIAL)
```

---

## 💡 Common Patterns

### Pattern 1: Database Table Scanning

```python
from datadetector import Engine, load_registry, context_presets

engine = Engine(registry=load_registry())

# Map column names to presets
preset_map = {
    "user_ssn": context_presets.DATABASE_SSN,
    "email": context_presets.DATABASE_EMAIL,
    "phone": context_presets.DATABASE_PHONE,
    "zipcode": context_presets.DATABASE_ADDRESS,
}

for column_name, preset in preset_map.items():
    for value in database[column_name]:
        result = engine.find(value, context=preset)
        if result.has_matches:
            print(f"PII found in {column_name}")
```

### Pattern 2: Korean Database Scanning

```python
from datadetector import Engine, load_registry, context_presets

engine = Engine(registry=load_registry())

# Korean field mapping
korean_presets = {
    "주민등록번호": context_presets.KOREAN_RRN,
    "계좌번호": context_presets.KOREAN_BANK_ACCOUNT,
    "전화번호": context_presets.KOREAN_PHONE,
    "우편번호": context_presets.KOREAN_ADDRESS,
}

for field, preset in korean_presets.items():
    result = engine.find(data[field], context=preset)
```

### Pattern 3: API Response Scanning

```python
from datadetector import Engine, load_registry, context_presets

engine = Engine(registry=load_registry())

# Scan API response fields
for key, value in api_response.items():
    if isinstance(value, str):
        result = engine.find(value, context=context_presets.API_USER_DATA)
        if result.has_matches:
            print(f"⚠️ PII in field: {key}")
```

### Pattern 4: Document Redaction

```python
from datadetector import Engine, load_registry, context_presets

engine = Engine(registry=load_registry())

# Redact PII from document
redacted = engine.redact(
    document_text,
    context=context_presets.DOCUMENT_GENERAL
)

print(redacted.redacted_text)
```

### Pattern 5: Multi-column Database Redaction

```python
from datadetector import Engine, load_registry, context_presets

engine = Engine(registry=load_registry())

# Redact sensitive columns
for column in ["ssn", "email", "phone"]:
    if "ssn" in column:
        preset = context_presets.DATABASE_SSN
    elif "email" in column:
        preset = context_presets.DATABASE_EMAIL
    elif "phone" in column:
        preset = context_presets.DATABASE_PHONE

    for i, value in enumerate(df[column]):
        result = engine.redact(value, context=preset)
        df.at[i, column] = result.redacted_text
```

---

## 🔧 Advanced Usage

### Using Preset Dictionaries

```python
from datadetector.context_presets import DATABASE_PRESETS, KOREAN_PRESETS

# Get preset by key
ssn_preset = DATABASE_PRESETS["ssn"]
rrn_preset = KOREAN_PRESETS["rrn"]

# Iterate
for name, preset in DATABASE_PRESETS.items():
    print(f"{name}: {preset.keywords}")
```

### Using get_preset() Helper

```python
from datadetector.context_presets import get_preset

# Get by dotted name
preset = get_preset("database.ssn")
preset = get_preset("korean.rrn")
preset = get_preset("contact")
```

### List All Presets

```python
from datadetector.context_presets import list_presets

presets = list_presets()
print(presets["database"])    # ['ssn', 'email', 'phone', ...]
print(presets["korean"])      # ['rrn', 'bank_account', 'phone', ...]
print(presets["category"])    # ['contact', 'financial', 'payment', ...]
```

---

## 📊 Quick Comparison

| Scenario | Without Context | With Preset | Speedup |
|----------|----------------|-------------|---------|
| SSN column (10K rows) | 3.2s | 0.3s | **10x** |
| Email validation | All 61 patterns | 1 pattern | **30x** |
| Korean RRN | All 61 patterns | 1 pattern | **25x** |

---

## ✅ Best Practices

```python
# ✅ DO: Use specific presets when you know the data type
result = engine.find(ssn, context=context_presets.DATABASE_SSN)

# ✅ DO: Cache preset references
SSN_PRESET = context_presets.DATABASE_SSN
for value in large_dataset:
    result = engine.find(value, context=SSN_PRESET)

# ✅ DO: Use category presets for multi-type data
result = engine.find(form, context=context_presets.CONTACT_INFO)

# ❌ DON'T: Use wrong preset for data type
result = engine.find(email, context=context_presets.DATABASE_PHONE)

# ❌ DON'T: Use PII_ALL in performance-critical code
for row in million_rows:
    result = engine.find(row, context=context_presets.PII_ALL)  # Slow!
```

---

## 📚 Complete Preset List

### Database (7)
`DATABASE_SSN` • `DATABASE_EMAIL` • `DATABASE_PHONE` • `DATABASE_ADDRESS` • `DATABASE_CREDIT_CARD` • `DATABASE_BANK_ACCOUNT` • `DATABASE_PASSPORT`

### Korean (5)
`KOREAN_RRN` • `KOREAN_BANK_ACCOUNT` • `KOREAN_PHONE` • `KOREAN_BUSINESS` • `KOREAN_ADDRESS`

### Category (6)
`CONTACT_INFO` • `FINANCIAL_DATA` • `PAYMENT_INFO` • `PERSONAL_IDENTIFIERS` • `TECHNICAL_DATA` • `LOCATION_DATA`

### Comprehensive (3)
`PII_ALL` • `PII_CRITICAL_ONLY` • `PII_MEDIUM_HIGH`

### API (2)
`API_USER_DATA` • `API_PAYMENT_DATA`

### Document (3)
`DOCUMENT_GENERAL` • `DOCUMENT_MEDICAL` • `DOCUMENT_FINANCIAL`

---

## 🚀 Performance Tips

1. **Cache presets** - Don't recreate them in loops
2. **Use strict presets** - DATABASE_SSN is faster than CONTACT_INFO
3. **Avoid PII_ALL** - Unless you really need all 61 patterns
4. **Batch processing** - Process similar data with same preset
5. **Profile first** - Measure before optimizing

---

## 📖 More Info

- Full Guide: [CONTEXT_PRESETS_GUIDE.md](CONTEXT_PRESETS_GUIDE.md)
- Examples: [examples/context_presets_examples.py](examples/context_presets_examples.py)
- Architecture: [CONTEXT_FILTERING_GUIDE.md](CONTEXT_FILTERING_GUIDE.md)
