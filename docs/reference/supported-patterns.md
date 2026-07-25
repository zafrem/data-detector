# Supported Patterns

## Overview

data-detector includes built-in patterns for detecting PII across multiple countries and categories.

**Total Patterns**: 60+
**Locations**: 7 (Common, KR, US, TW, JP, CN, IN)

## Common/International (location: co)

### Email & Network
- `email_01` - Email addresses (RFC 5322 simplified)
- `ipv4_01` - IPv4 addresses
- `ipv6_01` - IPv6 addresses (simplified)
- `url_01` - URLs with http/https protocol

### Credit Cards
- `credit_card_visa_01` - Visa credit cards
- `credit_card_mastercard_01` - MasterCard credit cards
- `credit_card_amex_01` - American Express credit cards
- `credit_card_discover_01` - Discover credit cards
- `credit_card_jcb_01` - JCB credit cards
- `credit_card_diners_01` - Diners Club credit cards

### IBAN (with Mod-97 verification)
- `iban_01` - Generic IBAN (all countries)
- `iban_ad_01` - Andorra
- `iban_al_01` - Albania
- `iban_at_01` - Austria
- `iban_de_01` - Germany
- `iban_fr_01` - France
- `iban_gb_01` - United Kingdom
- `iban_it_01` - Italy
- `iban_nl_01` - Netherlands
- `iban_es_01` - Spain

## South Korea (location: kr)

### Phone Numbers
- `mobile_01` - Mobile phone numbers (010/011/016-019)
- `landline_01` - Landline numbers (02/031-055/061-064)

### National IDs
- `rrn_01` - Resident Registration Number (주민등록번호)
- `business_registration_01` - Business Registration Number (사업자등록번호)
- `corporate_registration_01` - Corporate Registration Number (법인등록번호)
- `passport_01` - Passport numbers
- `driver_license_01` - Driver's license numbers

### Financial
- `bank_account_01` - Bank account numbers

### Names
- `korean_name_01` - Korean names (Hangul)

## United States (location: us)

### National IDs
- `ssn_01` - Social Security Number (SSN)
- `ein_01` - Employer Identification Number
- `itin_01` - Individual Taxpayer Identification Number

### Phone & Location
- `phone_01` - Phone numbers (with area codes)
- `zipcode_01` - ZIP codes (5-digit and ZIP+4)

### Documents
- `passport_01` - Passport numbers
- `driver_license_ca_01` - California driver's license
- `medicare_01` - Medicare Beneficiary Identifier

## Taiwan (location: tw)

### Phone Numbers
- `mobile_01` - Mobile phone numbers
- `landline_01` - Landline numbers

### IDs & Documents
- `national_id_01` - National ID (身分證字號)
- `passport_01` - Passport numbers
- `business_id_01` - Business Uniform Number (統一編號)

### Names
- `chinese_name_01` - Traditional Chinese names

## Japan (location: jp)

### Phone Numbers
- `mobile_01` - Mobile phone numbers
- `landline_01` - Landline numbers

### IDs & Documents
- `my_number_01` - My Number (individual number)
- `passport_01` - Passport numbers
- `driver_license_01` - Driver's license numbers
- `zipcode_01` - Postal codes

### Financial
- `bank_account_01` - Bank account numbers

### Names
- `japanese_name_hiragana_01` - Japanese names (Hiragana)
- `japanese_name_katakana_01` - Japanese names (Katakana)
- `japanese_name_kanji_01` - Japanese names (Kanji)

## China (location: cn)

### Phone Numbers
- `mobile_01` - Mobile phone numbers
- `landline_01` - Landline numbers

### IDs & Documents
- `national_id_01` - National ID (18 digits)
- `passport_01` - Passport numbers
- `social_credit_01` - Unified Social Credit Code

### Financial
- `bank_card_01` - Bank card numbers

### Names
- `chinese_name_01` - Simplified Chinese names

## India (location: in)

### Phone Numbers
- `mobile_01` - Mobile phone numbers
- `landline_01` - Landline numbers

### IDs & Documents
- `aadhaar_01` - Aadhaar number
- `pan_01` - PAN (Permanent Account Number)
- `passport_01` - Passport numbers
- `voter_id_01` - Voter ID (EPIC)
- `driving_license_01` - Driving license

### Location & Financial
- `pincode_01` - PIN codes
- `ifsc_01` - IFSC codes
- `gst_01` - GST numbers

### Names
- `indian_name_01` - Indian names (Latin script)

## Categories

Patterns are organized into these categories:

- **phone** - Phone numbers
- **ssn** - Social Security Numbers
- **rrn** - Resident Registration Numbers
- **email** - Email addresses
- **bank** - Bank account numbers
- **passport** - Passport numbers
- **address** - Physical addresses
- **credit_card** - Credit card numbers
- **ip** - IP addresses
- **iban** - International Bank Account Numbers
- **name** - Personal names
- **other** - Other PII types

## Severity Levels

- **low** - IP addresses, URLs
- **medium** - Email addresses, names
- **high** - Phone numbers, national IDs, IBANs
- **critical** - Credit cards, SSN, RRN, bank accounts

## Using Patterns

### Find by Namespace
```python
# Search Korean patterns only
result = engine.find(text, namespaces=["kr"])

# Search multiple namespaces
result = engine.find(text, namespaces=["kr", "us", "co"])
```

### Find by Specific Pattern
```python
# Validate against specific pattern
result = engine.validate("010-1234-5678", "kr/mobile_01")
```

### Find All Patterns
```python
# Search all loaded patterns
result = engine.find(text)
```

## Pattern Accuracy

### With Verification
Patterns with verification functions (e.g., IBAN, credit cards with Luhn) have higher accuracy:
- **IBAN patterns**: ~99% accuracy (Mod-97 validation)
- **Credit card patterns**: Can add Luhn verification

### Regex-Only
Patterns without verification rely solely on regex matching:
- **Phone numbers**: Format validation only
- **IDs**: Format and length validation

To improve accuracy, consider adding custom verification functions for your use case.

## Adding New Patterns

See [Custom Patterns](custom-patterns.md) for instructions on adding your own patterns.
