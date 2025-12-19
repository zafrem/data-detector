# Context Presets - Quick Reference Guide

## Overview

**Context presets** are pre-configured `ContextHint` objects for common scanning scenarios. Instead of manually creating `ContextHint` configurations, you can simply import and use these ready-made presets.

## Why Use Presets?

✅ **Easy to use** - No configuration needed
✅ **Best practices** - Optimized settings for each scenario
✅ **Faster development** - Copy-paste ready code
✅ **Consistent** - Standardized across your team

## Quick Start

```python
from datadetector import Engine, load_registry, context_presets

engine = Engine(registry=load_registry())

# Use preset directly
result = engine.find("123-45-6789", context=context_presets.DATABASE_SSN)
```

That's it! No need to configure keywords, categories, or strategies.

---

## 📊 Database Scanning Presets

### Complete Example

```python
from datadetector import Engine, load_registry, context_presets

engine = Engine(registry=load_registry())

# Database table
user_data = {
    "user_ssn": "123-45-6789",
    "email_address": "john@example.com",
    "phone_number": "(555) 123-4567",
    "billing_zip": "90210",
    "credit_card": "4532-1234-5678-9010"
}

# Scan each column with appropriate preset
results = {}
for column, value in user_data.items():
    if "ssn" in column:
        result = engine.find(value, context=context_presets.DATABASE_SSN)
    elif "email" in column:
        result = engine.find(value, context=context_presets.DATABASE_EMAIL)
    elif "phone" in column:
        result = engine.find(value, context=context_presets.DATABASE_PHONE)
    elif "zip" in column:
        result = engine.find(value, context=context_presets.DATABASE_ADDRESS)
    elif "card" in column:
        result = engine.find(value, context=context_presets.DATABASE_CREDIT_CARD)

    if result.has_matches:
        results[column] = result.matches[0].ns_id

print(results)
# Output: {
#   'user_ssn': 'us/ssn_01',
#   'email_address': 'comm/email_01',
#   'phone_number': 'us/phone_01',
#   'billing_zip': 'us/zipcode_01',
#   'credit_card': 'comm/credit_card_01'
# }
```

### Available Database Presets

| Preset | Use For | Example Columns |
|--------|---------|-----------------|
| `DATABASE_SSN` | Social Security Numbers | `user_ssn`, `employee_ssn`, `ssn` |
| `DATABASE_EMAIL` | Email addresses | `email`, `contact_email`, `user_email` |
| `DATABASE_PHONE` | Phone numbers | `phone`, `mobile`, `contact_phone` |
| `DATABASE_ADDRESS` | Addresses/ZIP codes | `zipcode`, `postal_code`, `billing_zip` |
| `DATABASE_CREDIT_CARD` | Credit card numbers | `card_number`, `cc_number`, `payment_card` |
| `DATABASE_BANK_ACCOUNT` | Bank account numbers | `account_number`, `bank_account` |
| `DATABASE_PASSPORT` | Passport numbers | `passport_number`, `passport_id` |

---

## 🇰🇷 Korean Data Scanning Presets

### Complete Example

```python
from datadetector import Engine, load_registry, context_presets

engine = Engine(registry=load_registry())

# Korean customer database
customer_data = {
    "고객명": "홍길동",
    "주민등록번호": "900101-1234567",
    "계좌번호": "110-123-456789",
    "전화번호": "010-1234-5678",
    "사업자등록번호": "123-45-67890",
    "우편번호": "06234"
}

# Use Korean presets
for field_name, value in customer_data.items():
    if "주민" in field_name:
        context = context_presets.KOREAN_RRN
    elif "계좌" in field_name:
        context = context_presets.KOREAN_BANK_ACCOUNT
    elif "전화" in field_name:
        context = context_presets.KOREAN_PHONE
    elif "사업자" in field_name:
        context = context_presets.KOREAN_BUSINESS
    elif "우편" in field_name:
        context = context_presets.KOREAN_ADDRESS
    else:
        continue

    result = engine.find(value, context=context)
    if result.has_matches:
        print(f"{field_name}: {result.matches[0].ns_id}")

# Output:
# 주민등록번호: kr/rrn_01
# 계좌번호: kr/bank_account_01
# 전화번호: kr/phone_02
# 사업자등록번호: kr/business_registration_01
# 우편번호: kr/zipcode_01
```

### Available Korean Presets

| Preset | Use For | Example Fields |
|--------|---------|----------------|
| `KOREAN_RRN` | 주민등록번호 | `주민등록번호`, `주민번호`, `rrn` |
| `KOREAN_BANK_ACCOUNT` | 계좌번호 | `계좌번호`, `은행계좌`, `계좌` |
| `KOREAN_PHONE` | 전화번호 | `전화번호`, `휴대폰`, `핸드폰` |
| `KOREAN_BUSINESS` | 사업자등록번호 | `사업자등록번호`, `사업자번호` |
| `KOREAN_ADDRESS` | 우편번호 | `우편번호`, `zipcode` |

---

## 📋 Category-Based Presets

### Contact Information Scanning

```python
from datadetector import Engine, load_registry, context_presets

engine = Engine(registry=load_registry())

# Contact form submission
contact_form = """
Name: John Doe
Email: john@example.com
Phone: (555) 123-4567
Address: 90210
Message: Please contact me about...
"""

# Scan for any contact information
result = engine.find(contact_form, context=context_presets.CONTACT_INFO)

print(f"Found {len(result.matches)} contact details:")
for match in result.matches:
    text = contact_form[match.start:match.end]
    print(f"  - {text} ({match.category.value})")

# Output:
# Found 3 contact details:
#   - john@example.com (email)
#   - (555) 123-4567 (phone)
#   - 90210 (address)
```

### Financial Data Scanning

```python
# Payment form
payment_data = """
Customer SSN: 123-45-6789
Credit Card: 4532-1234-5678-9010
Bank Account: 110-123-456789
"""

# Scan for financial PII
result = engine.find(payment_data, context=context_presets.FINANCIAL_DATA)

print(f"Found {len(result.matches)} financial data points")
# Output: Found 3 financial data points
```

### Available Category Presets

| Preset | Scans For | Use Cases |
|--------|-----------|-----------|
| `CONTACT_INFO` | Email, phone, address | Contact forms, user profiles |
| `FINANCIAL_DATA` | SSN, credit cards, bank accounts | Payment forms, financial records |
| `PAYMENT_INFO` | Credit cards, bank accounts only | Checkout pages, transactions |
| `PERSONAL_IDENTIFIERS` | SSN, passport, driver license | Identity verification, KYC |
| `TECHNICAL_DATA` | IP addresses, API keys | Log files, configurations |
| `LOCATION_DATA` | Addresses, coordinates, ZIP codes | Mapping apps, delivery |

---

## 🎯 Comprehensive Scanning Presets

### Critical PII Only

```python
from datadetector import Engine, load_registry, context_presets

engine = Engine(registry=load_registry())

# Quick security scan - critical PII only
document = """
Customer record:
Name: John Doe
SSN: 123-45-6789
Email: john@example.com
Passport: 123456789
Credit Card: 4532-1234-5678-9010
"""

# Only scan for critical PII (SSN, passport, credit card)
result = engine.find(document, context=context_presets.PII_CRITICAL_ONLY)

print("Critical PII found:")
for match in result.matches:
    print(f"  - {match.category.value} (severity: {match.severity.value})")

# Output:
# Critical PII found:
#   - ssn (severity: critical)
#   - passport (severity: critical)
#   - credit_card (severity: high)
# Note: Email is not included (not critical)
```

### All PII Types

```python
# Comprehensive scan - all 61 patterns
result = engine.find(document, context=context_presets.PII_ALL)

print(f"Total PII found: {len(result.matches)}")
# Output: Total PII found: 4 (includes email)
```

### Available Comprehensive Presets

| Preset | What It Scans | Performance | Use When |
|--------|---------------|-------------|----------|
| `PII_CRITICAL_ONLY` | SSN, credit cards, passports | Fast | Quick security checks |
| `PII_MEDIUM_HIGH` | Above + phone, bank accounts | Medium | Standard compliance |
| `PII_ALL` | All 61 patterns | Slower | Unknown data types |

---

## 🌐 API Scanning Presets

### API Response Scanning

```python
from datadetector import Engine, load_registry, context_presets
import json

engine = Engine(registry=load_registry())

# API response
api_response = {
    "user_id": 12345,
    "username": "johndoe",
    "email": "john@example.com",
    "ssn": "123-45-6789",
    "phone": "(555) 123-4567",
    "created_at": "2024-01-01"
}

# Scan user data fields
for key, value in api_response.items():
    if isinstance(value, str):
        result = engine.find(value, context=context_presets.API_USER_DATA)

        if result.has_matches:
            print(f"⚠️  {key}: Contains PII ({result.matches[0].category.value})")
        else:
            print(f"✓ {key}: Safe")

# Output:
# ✓ user_id: Safe
# ✓ username: Safe
# ⚠️  email: Contains PII (email)
# ⚠️  ssn: Contains PII (ssn)
# ⚠️  phone: Contains PII (phone)
# ✓ created_at: Safe
```

### Available API Presets

| Preset | Scans For | Use For |
|--------|-----------|---------|
| `API_USER_DATA` | Email, phone, SSN | User profile endpoints |
| `API_PAYMENT_DATA` | Credit cards, bank accounts | Payment API responses |

---

## 📄 Document Scanning Presets

### General Document Scanning

```python
from datadetector import Engine, load_registry, context_presets

engine = Engine(registry=load_registry())

# Read document
with open('customer_letter.txt', 'r') as f:
    document = f.read()

# Scan with general document preset
result = engine.find(document, context=context_presets.DOCUMENT_GENERAL)

print(f"Found {len(result.matches)} PII instances in document")

# Redact PII
redacted = engine.redact(document, context=context_presets.DOCUMENT_GENERAL)
print(redacted.redacted_text)
```

### Medical Document Scanning

```python
# Medical record
medical_record = """
Patient: John Doe
SSN: 123-45-6789
Medicare: A123CD4567E
Diagnosis: ...
"""

# Use medical document preset
result = engine.find(medical_record, context=context_presets.DOCUMENT_MEDICAL)
```

### Available Document Presets

| Preset | Scans For | Use For |
|--------|-----------|---------|
| `DOCUMENT_GENERAL` | Common PII (SSN, email, phone, address, CC) | PDF files, general text |
| `DOCUMENT_MEDICAL` | Healthcare PII (SSN, Medicare, patient data) | Medical records |
| `DOCUMENT_FINANCIAL` | Financial PII (SSN, CC, bank accounts) | Bank statements, invoices |

---

## 🔧 Advanced Usage

### Using Preset Dictionaries

```python
from datadetector.context_presets import DATABASE_PRESETS

# Get preset by key
ssn_preset = DATABASE_PRESETS["ssn"]
email_preset = DATABASE_PRESETS["email"]

# Iterate over all database presets
for name, preset in DATABASE_PRESETS.items():
    print(f"{name}: {preset.keywords}")
```

### Using get_preset() Helper

```python
from datadetector.context_presets import get_preset

# Get preset by dotted name
preset = get_preset("database.ssn")
preset = get_preset("korean.rrn")
preset = get_preset("contact")
```

### List All Available Presets

```python
from datadetector.context_presets import list_presets

presets = list_presets()

print("Database presets:", presets["database"])
# Output: ['ssn', 'email', 'phone', 'address', 'credit_card', 'bank_account', 'passport']

print("Korean presets:", presets["korean"])
# Output: ['rrn', 'bank_account', 'phone', 'business', 'address']

print("Category presets:", presets["category"])
# Output: ['contact', 'financial', 'payment', 'identifiers', 'technical', 'location']
```

---

## 📊 Performance Comparison

### With Presets vs. Without Context

```python
import time

text = "SSN: 123-45-6789"
iterations = 10000

# Without context (checks all 61 patterns)
start = time.time()
for _ in range(iterations):
    engine.find(text)
no_context_time = time.time() - start

# With preset (checks only 2-3 SSN patterns)
start = time.time()
for _ in range(iterations):
    engine.find(text, context=context_presets.DATABASE_SSN)
preset_time = time.time() - start

print(f"Without context: {no_context_time:.2f}s")
print(f"With preset: {preset_time:.2f}s")
print(f"Speedup: {no_context_time / preset_time:.1f}x faster")

# Typical Output:
# Without context: 3.20s
# With preset: 0.28s
# Speedup: 11.4x faster
```

---

## 🎓 Best Practices

### ✅ DO

```python
# ✅ Use presets for common scenarios
result = engine.find(ssn, context=context_presets.DATABASE_SSN)

# ✅ Cache preset references for repeated use
SSN_PRESET = context_presets.DATABASE_SSN
for value in large_dataset:
    result = engine.find(value, context=SSN_PRESET)

# ✅ Use category presets for multi-type data
result = engine.find(form_data, context=context_presets.CONTACT_INFO)
```

### ❌ DON'T

```python
# ❌ Don't use presets for unknown data
# Use create_context_from_field_name() instead
context = context_presets.DATABASE_SSN  # Wrong if you don't know it's SSN

# ❌ Don't use PII_ALL for performance-critical code
for value in million_rows:
    result = engine.find(value, context=context_presets.PII_ALL)  # Slow!

# ❌ Don't mix presets incorrectly
result = engine.find(email, context=context_presets.DATABASE_PHONE)  # Wrong type
```

---

## 📚 Complete Preset Reference

### Database Presets
- `DATABASE_SSN` - Social Security Numbers
- `DATABASE_EMAIL` - Email addresses
- `DATABASE_PHONE` - Phone numbers
- `DATABASE_ADDRESS` - Addresses/ZIP codes
- `DATABASE_CREDIT_CARD` - Credit card numbers
- `DATABASE_BANK_ACCOUNT` - Bank account numbers
- `DATABASE_PASSPORT` - Passport numbers

### Korean Presets
- `KOREAN_RRN` - 주민등록번호
- `KOREAN_BANK_ACCOUNT` - 계좌번호
- `KOREAN_PHONE` - 전화번호
- `KOREAN_BUSINESS` - 사업자등록번호
- `KOREAN_ADDRESS` - 우편번호

### Category Presets
- `CONTACT_INFO` - Email, phone, address
- `FINANCIAL_DATA` - SSN, credit cards, bank accounts
- `PAYMENT_INFO` - Credit cards, bank accounts only
- `PERSONAL_IDENTIFIERS` - SSN, passport, driver license
- `TECHNICAL_DATA` - IP addresses, API keys
- `LOCATION_DATA` - Addresses, coordinates

### Comprehensive Presets
- `PII_ALL` - All PII types (61 patterns)
- `PII_CRITICAL_ONLY` - Critical PII only
- `PII_MEDIUM_HIGH` - Medium-to-high severity PII

### API Presets
- `API_USER_DATA` - User profile data
- `API_PAYMENT_DATA` - Payment information

### Document Presets
- `DOCUMENT_GENERAL` - General documents
- `DOCUMENT_MEDICAL` - Medical records
- `DOCUMENT_FINANCIAL` - Financial documents

---

## 🚀 Migration from Manual ContextHint

### Before (Manual Configuration)

```python
from datadetector import ContextHint

context = ContextHint(
    keywords=["ssn", "social_security"],
    categories=["ssn"],
    strategy="strict"
)
result = engine.find(value, context=context)
```

### After (Using Preset)

```python
from datadetector import context_presets

result = engine.find(value, context=context_presets.DATABASE_SSN)
```

**Benefits:**
- ✅ 3 lines → 1 line
- ✅ No configuration needed
- ✅ Guaranteed best practices
- ✅ Easier to maintain

---

## 💡 Tips

1. **Import once, use everywhere**: Import `context_presets` at module level
2. **Cache preset references**: Store presets in variables for repeated use
3. **Combine with redaction**: Presets work with `find()` and `redact()`
4. **Check documentation**: Each preset has docstring with examples
5. **Use helpers**: `get_preset()` and `list_presets()` for dynamic use

---

## 📖 See Also

- [Context Filtering Guide](CONTEXT_FILTERING_GUIDE.md) - Complete guide to context filtering
- [Context Filtering Design](CONTEXT_FILTERING_DESIGN.md) - Architecture and design
- [examples/context_filtering_examples.py](examples/context_filtering_examples.py) - Working examples
- [Pattern Reference](PATTERN_REFERENCE.md) - All 61 patterns documented
