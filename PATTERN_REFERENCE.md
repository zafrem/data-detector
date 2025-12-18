# Data Detector Pattern Reference

This document provides a comprehensive reference for all regular expression patterns organized by category.

**Last Updated:** 2025-12-18
**Total Patterns:** 61

---

## Table of Contents

- [Address Patterns](#address-patterns) (2)
- [Bank Account Patterns](#bank-account-patterns) (16)
- [Credit Card Patterns](#credit-card-patterns) (6)
- [Email Patterns](#email-patterns) (1)
- [IP Address Patterns](#ip-address-patterns) (2)
- [Location Patterns](#location-patterns) (4)
- [Name Patterns](#name-patterns) (1)
- [Other Patterns](#other-patterns) (7)
- [Passport Patterns](#passport-patterns) (2)
- [Phone Patterns](#phone-patterns) (6)
- [RRN Patterns](#rrn-patterns) (2)
- [SSN Patterns](#ssn-patterns) (2)
- [Token/API Key Patterns](#tokenapi-key-patterns) (10)

---

## Address Patterns

### Korean Postal Code (kr/zipcode_01)

**Description:** Korean postal code (5 digits)

**Pattern:**
```regex
(?<![A-Za-z0-9])[0-9]{5}(?![A-Za-z0-9])
```

**Format:** XXXXX (5 digits)

**Verification:** `korean_zipcode_valid`
- Rejects sequential numbers (12345, 54321)
- Rejects repetitive digits (11111, 00000)
- Rejects round numbers (50000, 60000)
- Rejects when embedded in alphanumeric strings

**Examples:**
- ✓ Matches: `06234`, `48058`, `63309`
- ✗ Does not match: `12345` (sequential), `ABC12345` (embedded), `MODEL90210A` (alphanumeric)

**Severity:** Low

---

### US ZIP Code (us/zipcode_01)

**Description:** US ZIP code (5 digits or ZIP+4)

**Pattern:**
```regex
(?<![A-Za-z0-9])[0-9]{5}(?:-[0-9]{4})?(?![A-Za-z0-9])
```

**Format:** XXXXX or XXXXX-XXXX

**Verification:** `us_zipcode_valid`
- Same validation as Korean zipcode
- Supports ZIP+4 format with 9 digits

**Examples:**
- ✓ Matches: `90210`, `90210-1234`, `48201`
- ✗ Does not match: `12345` (sequential), `11111` (repetitive), `SN90210END` (embedded)

**Severity:** Low

---

## Bank Account Patterns

### Korean Kookmin Bank (kr/bank_account_01)

**Description:** Korean Kookmin Bank account number (국민은행)

**Pattern:**
```regex
(?<!\d)(?:110|120|150|190|830)[- ]?[0-9]{3}[- ]?[0-9]{6,7}(?!\d)
```

**Format:** XXX-XXX-XXXXXX(X) where first 3 digits are bank code (110/120/150/190/830)

**Verification:** `korean_bank_account_valid` (recognizes Kookmin Bank prefixes)

**Priority:** 150

**Examples:**
- ✓ Matches: `110-123-456789`, `150-999-1234567`, `190 888 654321`
- ✗ Does not match: `999-111-222222` (invalid prefix), `120123456789` (no verification)

**Severity:** Critical

---

### Korean Shinhan Bank (kr/bank_account_02)

**Description:** Korean Shinhan Bank account number (신한은행)

**Pattern:**
```regex
(?<!\d)(?:110)-?[0-9]{3}-?[0-9]{6,7}(?!\d)
```

**Format:** 110-XXX-XXXXXX(X)

**Verification:** `korean_bank_account_valid`

**Priority:** 150

**Severity:** Critical

---

### Korean Woori Bank (kr/bank_account_03)

**Description:** Korean Woori Bank account number (우리은행)

**Pattern:**
```regex
(?<!\d)(?:1002)-?[0-9]{3}-?[0-9]{6,7}(?!\d)
```

**Format:** 1002-XXX-XXXXXX(X)

**Verification:** `korean_bank_account_valid`

**Priority:** 150

**Severity:** Critical

---

### Korean Hana Bank (kr/bank_account_04)

**Description:** Korean Hana Bank account number (하나은행)

**Pattern:**
```regex
(?<!\d)[0-9]{3}-?[0-9]{6}-?[0-9]{4,5}(?!\d)
```

**Format:** XXX-XXXXXX-XXXX(X) (13-14 digits total)

**Verification:** `generic_number_not_timestamp`
- Rejects Unix timestamps (10, 13, 14 digits in timestamp ranges)
- Accepts if value has separators (hyphens/spaces)

**Priority:** 150

**Examples:**
- ✓ Matches: `321-987654-3210`, `999-888777-66655`
- ✗ Does not match: `1734567890123` (Unix timestamp in ms), `20231201103045` (datetime)

**Severity:** Critical

---

### Korean Nonghyup Bank (kr/bank_account_05)

**Description:** Korean Nonghyup Bank account number (농협은행)

**Pattern:**
```regex
(?<!\d)(?:301)-?[0-9]{4}-?[0-9]{4}-?[0-9]{2}(?!\d)
```

**Format:** 301-XXXX-XXXX-XX

**Verification:** `korean_bank_account_valid`

**Priority:** 150

**Severity:** Critical

---

### Korean IBK Industrial Bank (kr/bank_account_06)

**Description:** Korean IBK Industrial Bank account number (IBK기업은행)

**Pattern:**
```regex
(?<!\d)[0-9]{3}-?[0-9]{6}-?[0-9]{2}-?[0-9]{3}(?!\d)
```

**Format:** XXX-XXXXXX-XX-XXX (14 digits total)

**Verification:** `generic_number_not_timestamp`

**Priority:** 150

**Examples:**
- ✓ Matches: `123-456789-01-234`, `999-123456-99-888`
- ✗ Does not match: `20231201103045` (datetime format)

**Severity:** Critical

---

### Korean SC First Bank (kr/bank_account_07)

**Description:** Korean SC First Bank account number (SC제일은행)

**Pattern:**
```regex
(?<!\d)[0-9]{3}-[0-9]{2}-[0-9]{6}(?!\d)
```

**Format:** XXX-XX-XXXXXX (11 digits, requires hyphens)

**Verification:** `generic_number_not_timestamp`

**Priority:** 50

**Examples:**
- ✓ Matches: `123-45-678901`, `999-88-123456`
- ✗ Does not match: `12345678901` (no hyphens), `1734567890123` (timestamp)

**Severity:** Critical

**Note:** Same format as Jeonbuk Bank (bank_account_12). Lower priority (50) means checked after longer patterns.

---

### Korean Citibank (kr/bank_account_08)

**Description:** Korean Citibank account number (한국씨티은행)

**Pattern:**
```regex
(?<!\d)[0-9]{3}-?[0-9]{5}-?[0-9]{2}-?[0-9]{3}(?!\d)
```

**Format:** XXX-XXXXX-XX-XXX (13 digits)

**Verification:** `generic_number_not_timestamp`

**Priority:** 150

**Examples:**
- ✓ Matches: `123-45678-90-123`, `999-12345-88-999`
- ✗ Does not match: `1734567890123` (timestamp), `20231201103045` (datetime)

**Severity:** Critical

---

### Korean Busan Bank (kr/bank_account_09)

**Description:** Korean Busan Bank account number (부산은행)

**Pattern:**
```regex
(?<!\d)[0-9]{3}-?[0-9]{4}-?[0-9]{4}-?[0-9]{2}(?!\d)
```

**Format:** XXX-XXXX-XXXX-XX (13 digits)

**Verification:** `generic_number_not_timestamp`

**Priority:** 150

**Examples:**
- ✓ Matches: `123-4567-8901-23`, `999-1234-5678-90`

**Severity:** Critical

---

### Korean Daegu Bank (kr/bank_account_10)

**Description:** Korean Daegu Bank account number (대구은행)

**Pattern:**
```regex
(?<!\d)[0-9]{3}-[0-9]{2}-[0-9]{6}-[0-9](?!\d)
```

**Format:** XXX-XX-XXXXXX-X (12 digits, requires hyphens)

**Verification:** `generic_number_not_timestamp`

**Priority:** 40 (higher precedence - checked before 11-digit patterns)

**Examples:**
- ✓ Matches: `123-45-678901-2`, `999-88-123456-7`
- ✗ Does not match: Business registration (only 10 digits)

**Severity:** Critical

---

### Korean Gwangju Bank (kr/bank_account_11)

**Description:** Korean Gwangju Bank account number (광주은행)

**Pattern:**
```regex
(?<!\d)[0-9]{3}-[0-9]{3}-[0-9]{6}(?!\d)
```

**Format:** XXX-XXX-XXXXXX (12 digits, requires hyphens)

**Verification:** `generic_number_not_timestamp`

**Priority:** 40 (higher precedence - checked before US SSN)

**Examples:**
- ✓ Matches: `123-456-789012`, `999-123-456789`
- ✗ Does not match: US SSN (only 9 digits)

**Severity:** Critical

---

### Korean Jeonbuk Bank (kr/bank_account_12)

**Description:** Korean Jeonbuk Bank account number (전북은행)

**Pattern:**
```regex
(?<!\d)[0-9]{3}-[0-9]{2}-[0-9]{6}(?!\d)
```

**Format:** XXX-XX-XXXXXX (11 digits, requires hyphens)

**Verification:** `generic_number_not_timestamp`

**Priority:** 50 (same as SC First Bank)

**Examples:**
- ✓ Matches: `123-45-678901`, `999-88-123456`

**Severity:** Critical

**Note:** Identical format to SC First Bank (bank_account_07). Either may match.

---

### Korean Jeju Bank (kr/bank_account_13)

**Description:** Korean Jeju Bank account number (제주은행)

**Pattern:**
```regex
(?<!\d)[0-9]{2}-?[0-9]{6}-?[0-9]{2}(?!\d)
```

**Format:** XX-XXXXXX-XX (10 digits)

**Verification:** `generic_number_not_timestamp`

**Priority:** 150

**Examples:**
- ✓ Matches: `89-876543-21`, `99-888777-66`
- ✗ Does not match: `1734567890` (timestamp)

**Severity:** Critical

**Note:** Same format as Driver License (driver_license_01). May have ambiguity.

---

### Korean Kakao Bank (kr/bank_account_14)

**Description:** Korean Kakao Bank account number (카카오뱅크)

**Pattern:**
```regex
(?<!\d)(?:3333)-?[0-9]{2}-?[0-9]{7}(?!\d)
```

**Format:** 3333-XX-XXXXXXX

**Verification:** `korean_bank_account_valid`

**Priority:** 150

**Severity:** Critical

---

### Korean K Bank (kr/bank_account_15)

**Description:** Korean K Bank account number (케이뱅크)

**Pattern:**
```regex
(?<!\d)(?:100)-?[0-9]{3}-?[0-9]{6}(?!\d)
```

**Format:** 100-XXX-XXXXXX

**Verification:** `korean_bank_account_valid`

**Priority:** 150

**Severity:** Critical

---

### Korean Toss Bank (kr/bank_account_16)

**Description:** Korean Toss Bank account number (토스뱅크)

**Pattern:**
```regex
(?<!\d)(?:100)-?[0-9]{3}-?[0-9]{6}(?!\d)
```

**Format:** 100-XXX-XXXXXX

**Verification:** `korean_bank_account_valid`

**Priority:** 150

**Severity:** Critical

**Note:** Same format as K Bank (bank_account_15).

---

## Credit Card Patterns

All credit card patterns use Luhn checksum verification.

### Visa (comm/credit_card_visa_01)

**Pattern:**
```regex
\b4[0-9]{12}(?:[0-9]{3})?\b
```

**Format:** 13 or 16 digits starting with 4

**Verification:** `luhn` (Luhn checksum algorithm)

**Examples:**
- ✓ Matches: Valid 16-digit Visa starting with 4
- ✗ Does not match: Invalid Luhn checksum

**Severity:** Critical

---

### MasterCard (comm/credit_card_mastercard_01)

**Pattern:**
```regex
\b(?:5[1-5][0-9]{2}|222[1-9]|22[3-9][0-9]|2[3-6][0-9]{2}|27[01][0-9]|2720)[0-9]{12}\b
```

**Format:** 16 digits, ranges 51-55, 2221-2720

**Verification:** `luhn`

**Severity:** Critical

---

### American Express (comm/credit_card_amex_01)

**Pattern:**
```regex
\b3[47][0-9]{13}\b
```

**Format:** 15 digits starting with 34 or 37

**Verification:** `luhn`

**Severity:** Critical

---

### Discover (comm/credit_card_discover_01)

**Pattern:**
```regex
\b6(?:011|5[0-9]{2})[0-9]{12}\b
```

**Format:** 16 digits, starts with 6011 or 65

**Verification:** `luhn`

**Severity:** Critical

---

### JCB (comm/credit_card_jcb_01)

**Pattern:**
```regex
\b(?:2131|1800|35[0-9]{2})[0-9]{11}\b
```

**Format:** 15-16 digits

**Verification:** `luhn`

**Severity:** Critical

---

### Diners Club (comm/credit_card_diners_01)

**Pattern:**
```regex
\b3(?:0[0-5]|[68][0-9])[0-9]{11}\b
```

**Format:** 14 digits

**Verification:** `luhn`

**Severity:** Critical

---

## Email Patterns

### Standard Email (comm/email_01)

**Description:** Standard email address (RFC 5322 simplified with RFC 1034 domain rules)

**Pattern:**
```regex
\b[A-Za-z0-9._%+-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*\b
```

**Examples:**
- ✓ Matches: `user@example.com`, `name.surname+tag@domain.co.uk`
- ✗ Does not match: `@example.com`, `user@`, `user@.com`

**Severity:** Low

---

## IP Address Patterns

### IPv4 (comm/ipv4_01)

**Pattern:**
```regex
\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b
```

**Format:** X.X.X.X (0-255 for each octet)

**Examples:**
- ✓ Matches: `192.168.1.1`, `10.0.0.1`, `255.255.255.255`
- ✗ Does not match: `256.1.1.1`, `192.168.1`

**Severity:** Medium

---

### IPv6 (comm/ipv6_01)

**Pattern:** Complex regex supporting full and compressed notation

**Format:** Standard IPv6 notation including :: compression

**Examples:**
- ✓ Matches: `2001:0db8:85a3:0000:0000:8a2e:0370:7334`, `::1`, `fe80::1`

**Severity:** Medium

---

## Location Patterns

### Latitude (comm/latitude_01)

**Pattern:**
```regex
(?<!\d)[-+]?(?:[0-8]?[0-9](?:\.[0-9]{4,})|90(?:\.0{4,})?)(?!\d)
```

**Format:** -90.0000 to +90.0000 (requires at least 4 decimal places)

**Examples:**
- ✓ Matches: `37.7749`, `-40.7128`, `+45.123456`
- ✗ Does not match: `91.0`, `2024` (date), `01` (too short)

**Severity:** Medium

**Note:** Requires 4+ decimal places to avoid matching dates.

---

### Longitude (comm/longitude_01)

**Pattern:**
```regex
(?<!\d)[-+]?(?:1[0-7][0-9](?:\.[0-9]{4,})|[0-9]?[0-9](?:\.[0-9]{4,})|180(?:\.0{4,})?)(?!\d)
```

**Format:** -180.0000 to +180.0000 (requires at least 4 decimal places)

**Examples:**
- ✓ Matches: `122.4194`, `-74.0060`, `+123.456789`
- ✗ Does not match: `181.0`, `12` (date component)

**Severity:** Medium

---

### Coordinate Pair (comm/coordinates_pair_01)

**Pattern:** Latitude, Longitude pair (both with 4+ decimal places)

**Format:** XX.XXXX, YYY.YYYY

**Examples:**
- ✓ Matches: `37.7749, -122.4194`, `40.7128,-74.0060`
- ✗ Does not match: `2024, 12` (dates)

**Severity:** Medium

---

### Coordinates DMS (comm/coordinates_dms_01)

**Pattern:** Degrees Minutes Seconds format

**Format:** DD°MM'SS"N/S/E/W

**Verification:** `dms_coordinate`

**Examples:**
- ✓ Matches: `40°26'46"N`, `79°58'56"W`

**Severity:** Medium

---

## Name Patterns

### Korean Name (kr/korean_name_01)

**Pattern:**
```regex
\b[가-힣]{2,4}\b
```

**Format:** 2-4 Korean characters (Hangul)

**Examples:**
- ✓ Matches: `김철수`, `이영희`, `박`
- ✗ Does not match: English names, single character

**Severity:** Low

---

## Other Patterns

### Business Registration Number (kr/business_registration_01)

**Description:** Korean Business Registration Number (사업자등록번호)

**Pattern:**
```regex
(?<!\d)[0-9]{3}-[0-9]{2}-[0-9]{5}(?!\d)
```

**Format:** XXX-XX-XXXXX (10 digits, requires hyphens)

**Examples:**
- ✓ Matches: `123-45-67890`
- ✗ Does not match: `1234567890` (no hyphens), `123-45-678901` (11 digits - bank account)

**Severity:** Medium

**Note:** Requires hyphens to avoid ambiguity with 10-digit numbers without separators.

---

### Corporate Registration (kr/corporate_registration_01)

**Description:** Korean Corporate Registration Number (법인등록번호)

**Pattern:**
```regex
[0-9]{6}-[0-9]{7}
```

**Format:** XXXXXX-XXXXXXX (13 digits)

**Severity:** Medium

---

### Driver License (kr/driver_license_01)

**Description:** Korean driver's license number

**Pattern:**
```regex
(?<!\d)[0-9]{2}-[0-9]{6}-[0-9]{2}(?!\d)
```

**Format:** XX-XXXXXX-XX (10 digits, requires hyphens)

**Priority:** 90

**Examples:**
- ✓ Matches: `12-345678-90`
- ✗ Does not match: `1234567890` (no hyphens), `123-456789-01` (bank account)

**Severity:** High

**Note:** Same format as Jeju Bank (bank_account_13). May have ambiguity.

---

### California Driver License (us/driver_license_ca_01)

**Pattern:**
```regex
\b[A-Z][0-9]{7}\b
```

**Format:** 1 letter + 7 digits

**Examples:**
- ✓ Matches: `A1234567`, `Z9876543`

**Severity:** High

---

### Employer Identification Number (us/ein_01)

**Description:** US Employer Identification Number

**Pattern:**
```regex
(?<!\d)[0-9]{2}-[0-9]{7}(?!\d)
```

**Format:** XX-XXXXXXX (9 digits, requires hyphen)

**Verification:** `not_timestamp`

**Priority:** 150

**Examples:**
- ✓ Matches: `12-3456789`, `98-7654321`
- ✗ Does not match: `123456789` (no hyphen)

**Severity:** Medium

**Note:** Requires hyphen to avoid matching plain 9-digit numbers.

---

### Medicare (us/medicare_01)

**Description:** Medicare Beneficiary Identifier (MBI format)

**Pattern:** Excludes ambiguous characters S/L/O/I/B/Z

**Format:** 1ABC2D3EF4G (specific character positions)

**Severity:** High

---

### URL (comm/url_01)

**Pattern:**
```regex
\bhttps?://[^\s/$.?#].[^\s]*\b
```

**Format:** http:// or https:// followed by domain and path

**Examples:**
- ✓ Matches: `https://example.com`, `http://site.com/path?query=1`

**Severity:** Low

---

## Passport Patterns

### Korean Passport (kr/passport_01)

**Pattern:**
```regex
\b[MS][0-9]{8}\b
```

**Format:** M or S + 8 digits

**Examples:**
- ✓ Matches: `M12345678`, `S87654321`

**Severity:** High

---

### US Passport (us/passport_01)

**Pattern:**
```regex
\b(?:[0-9]{9}|[A-Z][0-9]{8})\b
```

**Format:** 9 digits OR 1 letter + 8 digits

**Examples:**
- ✓ Matches: `123456789`, `A12345678`

**Severity:** High

---

## Phone Patterns

### Korean Mobile (kr/mobile_01)

**Pattern:**
```regex
(?:010|011|016|017|018|019)-?[0-9]{3,4}-?[0-9]{4}
```

**Format:** 01X-XXXX-XXXX or 01X-XXX-XXXX

**Examples:**
- ✓ Matches: `010-1234-5678`, `01012345678`, `011-123-4567`

**Severity:** Medium

---

### Korean Landline (kr/landline_01, 02, 03)

**Pattern:** Multiple patterns for different area codes

**Format:** 0XX-XXX-XXXX or 0XX-XXXX-XXXX

**Examples:**
- ✓ Matches: `02-1234-5678` (Seoul), `031-123-4567` (Gyeonggi)

**Severity:** Low

---

### US Phone (us/phone_01)

**Pattern:**
```regex
\b(?:\+?1[-.]?)?(?:\([0-9]{3}\)|[0-9]{3})[-.]?[0-9]{3}[-.]?[0-9]{4}\b
```

**Format:** (XXX) XXX-XXXX or XXX-XXX-XXXX, optional +1 country code

**Examples:**
- ✓ Matches: `(555) 123-4567`, `555-123-4567`, `+1-555-123-4567`

**Severity:** Medium

---

## RRN Patterns

### Korean RRN (kr/rrn_01)

**Description:** Korean Resident Registration Number (주민등록번호)

**Pattern:**
```regex
[0-9]{6}-?[1-4][0-9]{6}
```

**Format:** YYMMDD-GXXXXXX (G = gender/century: 1-4)

**Examples:**
- ✓ Matches: `900101-1234567`, `850315-2123456`
- ✗ Does not match: Gender digit 5-9 (reserved for foreigners)

**Severity:** Critical

---

### Korean Alien Registration (kr/alien_registration_01)

**Description:** Korean Alien Registration Number (외국인등록번호)

**Pattern:**
```regex
[0-9]{6}-?[5-8][0-9]{6}
```

**Format:** YYMMDD-GXXXXXX (G = 5-8 for foreigners)

**Severity:** Critical

---

## SSN Patterns

### US SSN (us/ssn_01)

**Description:** US Social Security Number

**Pattern:**
```regex
\b(?!000|666|9[0-9]{2})[0-9]{3}-?(?!00)[0-9]{2}-?(?!0000)[0-9]{4}\b
```

**Format:** XXX-XX-XXXX

**Validation:**
- Area number: not 000, 666, or 900-999
- Group number: not 00
- Serial number: not 0000

**Examples:**
- ✓ Matches: `123-45-6789`, `555-12-3456`
- ✗ Does not match: `000-12-3456`, `123-00-4567`, `666-12-3456`

**Severity:** Critical

---

### US ITIN (us/itin_01)

**Description:** Individual Taxpayer Identification Number

**Pattern:**
```regex
\b9[0-9]{2}-?(?!00)[0-9]{2}-?(?!0000)[0-9]{4}\b
```

**Format:** 9XX-XX-XXXX (starts with 9)

**Severity:** Critical

---

## Token/API Key Patterns

### AWS Access Key (comm/aws_access_key_01)

**Pattern:**
```regex
\b(AKIA[0-9A-Z]{16})\b
```

**Format:** AKIA + 16 alphanumeric characters (20 total)

**Examples:**
- ✓ Matches: `AKIAIOSFODNN7EXAMPLE`

**Severity:** Critical

---

### AWS Secret Key (comm/aws_secret_key_01)

**Pattern:**
```regex
\b[A-Za-z0-9/+=]{40}\b
```

**Format:** 40 base64 characters

**Verification:** Must be exactly 40 characters

**Severity:** Critical

---

### GitHub Token (comm/github_token_01)

**Pattern:**
```regex
\b(ghp_[A-Za-z0-9]{36}|gho_[A-Za-z0-9]{36}|ghu_[A-Za-z0-9]{36}|ghs_[A-Za-z0-9]{36}|ghr_[A-Za-z0-9]{36})\b
```

**Format:**
- `ghp_` - Personal Access Token
- `gho_` - OAuth Token
- `ghu_` - User-to-server token
- `ghs_` - Server-to-server token
- `ghr_` - Refresh token

**Severity:** Critical

---

### Google API Key (comm/google_api_key_01)

**Pattern:**
```regex
\b(AIza[0-9A-Za-z_-]{35})\b
```

**Format:** AIza + 35 characters

**Severity:** Critical

---

### Slack Token (comm/slack_token_01)

**Pattern:**
```regex
\b(xoxb-[0-9]{10,13}-[0-9]{10,13}-[A-Za-z0-9]{24}|xoxp-[0-9]{10,13}-[0-9]{10,13}-[A-Za-z0-9]{24}|xoxa-[0-9]{10,13}-[0-9]{10,13}-[A-Za-z0-9]{24}|xoxr-[0-9]{10,13}-[A-Za-z0-9]{24})\b
```

**Format:**
- `xoxb-` - Bot token
- `xoxp-` - User token
- `xoxa-` - App token
- `xoxr-` - Refresh token

**Severity:** Critical

---

### Stripe API Key (comm/stripe_key_01)

**Pattern:**
```regex
\b(rk_test_[0-9a-zA-Z]{24})\b
```

**Format:** rk_test_ + 24 characters (test key pattern)

**Severity:** Critical

---

### JWT Token (comm/jwt_token_01)

**Pattern:**
```regex
\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b
```

**Format:** Three base64url parts separated by dots (header.payload.signature)

**Examples:**
- ✓ Matches: `eyJhbGc...eyJzdWI...SflKxw...`

**Severity:** High

---

### Private Key (comm/private_key_01)

**Pattern:**
```regex
-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----
```

**Format:** Private key header (RSA, EC, SSH, PGP)

**Severity:** Critical

---

### Generic API Key (comm/generic_api_key_01)

**Pattern:** 32+ random characters without common prefixes

**Format:** High-entropy string without known prefixes (AIza, AKIA, ghp_, etc.)

**Verification:** Checks for randomness and excludes known token patterns

**Severity:** High

---

### Generic Token (comm/generic_token_01)

**Pattern:** 20+ characters, base64url/hex, high entropy

**Format:** Random high-entropy string

**Verification:** `high_entropy_token`
- Minimum 20 characters
- No spaces or line breaks
- Base64url or hex character set
- Shannon entropy >= 4.0 bits/char

**Severity:** High

---

## Pattern Priorities

**Lower number = Higher precedence (checked first)**

| Priority | Patterns |
|----------|----------|
| 40 | 12-digit bank accounts (Daegu, Gwangju) |
| 50 | 11-digit bank accounts (SC First, Jeonbuk) |
| 90 | Driver License |
| 100 | Most patterns (default) |
| 150 | Patterns with verification, coordinates, most bank accounts |

---

## Verification Functions

### `luhn`
Luhn algorithm checksum validation for credit cards.

### `iban_mod97`
IBAN mod-97 validation.

### `korean_zipcode_valid`
- Rejects sequential (12345, 54321)
- Rejects repetitive (11111, 00000)
- Rejects round numbers (50000)
- Rejects when embedded in alphanumeric strings

### `us_zipcode_valid`
Same as `korean_zipcode_valid`, supports ZIP+4 (9 digits).

### `not_timestamp`
- Rejects 10-digit Unix timestamps (1000000000-9999999999)
- Rejects 13-digit Unix timestamps in ms
- Rejects 14-digit datetime (YYYYMMDDHHMMSS)

### `korean_bank_account_valid`
- Recognizes known bank prefixes (110, 120, 1002, 301, 3333, 100)
- More lenient for accounts with known prefixes
- Rejects timestamp patterns
- Rejects excessive sequential digits

### `generic_number_not_timestamp`
- If has separators (hyphens/spaces): likely real account
- Otherwise checks timestamp ranges
- More permissive than `korean_bank_account_valid`

### `high_entropy_token`
- Minimum 20 characters
- Shannon entropy >= 4.0 bits/char
- No spaces or line breaks
- Base64url/hex character set

### `dms_coordinate`
Validates Degrees Minutes Seconds coordinate format.

---

## Notes

1. **Alphanumeric Boundaries:** Zip codes and many patterns use `(?<![A-Za-z0-9])` and `(?![A-Za-z0-9])` to prevent matching when embedded in product codes, serial numbers, etc.

2. **Separator Requirements:** Some patterns require hyphens/spaces to disambiguate (business registration, driver license, some bank accounts).

3. **Ambiguous Patterns:** Some patterns have identical formats:
   - SC First Bank vs Jeonbuk Bank (both `XXX-XX-XXXXXX`)
   - Jeju Bank vs Driver License (both `XX-XXXXXX-XX`)
   - K Bank vs Toss Bank (both `100-XXX-XXXXXX`)

4. **Timestamp Rejection:** Multiple verification functions prevent false positives from Unix timestamps and datetime formats.

5. **Priority System:** Longer/more-specific patterns have lower priority numbers to be checked first when overlaps occur.

---

**For implementation details, see:**
- Pattern definitions: `patterns/*.yml`
- Verification functions: `src/datadetector/verification.py`
- Engine logic: `src/datadetector/engine.py`
