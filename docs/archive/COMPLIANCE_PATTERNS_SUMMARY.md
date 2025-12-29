# Data Privacy Compliance Patterns Summary

## Overview
This document summarizes the pattern coverage for major data privacy regulations: GDPR (EU), PIPA (Korea), PIPL (China), and APPI (Japan).

## 1. EU GDPR Compliance ✓ COMPLETE

The General Data Protection Regulation (GDPR) is the EU's comprehensive data protection law. We've implemented patterns for key personal data categories across major EU member states.

### Patterns Implemented:

#### VAT Numbers (12 countries) - `patterns/eu/vat.yml`
Tax identification numbers for businesses, important for B2B data processing:
- **Germany**: DE + 9 digits
- **France**: FR + 2 alphanumeric + 9 digits
- **Italy**: IT + 11 digits
- **Spain**: ES + alphanumeric + 7-8 digits + alphanumeric
- **Netherlands**: NL + 9 digits + B + 2 digits
- **Belgium**: BE + 10 digits (starting with 0 or 1)
- **Austria**: ATU + 8 digits
- **Poland**: PL + 10 digits
- **Sweden**: SE + 10 digits + 01
- **Ireland**: IE + various formats
- **Portugal**: PT + 9 digits
- **Greece**: EL + 9 digits

**Total**: 12 patterns | **Severity**: Medium | **Action**: Report

#### National ID Numbers (13 countries) - `patterns/eu/identification.yml`
The most sensitive PII under GDPR Article 9:
- **Germany**: Personalausweisnummer (9 alphanumeric with at least 1 letter)
- **France**: INSEE/NIR (15 digits - social security number)
- **Italy**: Codice Fiscale (16 alphanumeric)
- **Spain**: DNI (8 digits + letter) and NIE (foreigner ID)
- **Netherlands**: BSN (8-9 digits with 11-proof check)
- **Belgium**: National Register Number (11 digits YYMMDD-XXX-CC)
- **Poland**: PESEL (11 digits)
- **Sweden**: Personnummer (10 or 12 digits)
- **Denmark**: CPR (10 digits DDMMYY-XXXX)
- **Portugal**: NIF (9 digits starting with 1-3)
- **Austria**: Sozialversicherungsnummer (10 digits)
- **Finland**: HETU (11 characters DDMMYYCZZZQ)
- **UK**: National Insurance Number (2 letters + 6 digits + letter)

**Total**: 14 patterns | **Severity**: Critical | **Action**: Redact

#### Passport Numbers (12 countries) - `patterns/eu/passport.yml`
Travel documents, sensitive under GDPR:
- **Germany**: Letter + 8 alphanumeric (C/F/G/H/J/K series)
- **France**: 2 digits + 2 letters + 5 digits
- **Italy**: 2 letters + 7 digits
- **Spain**: 3 letters + 6 digits
- **UK**: 9 digits or 12 alphanumeric
- **Netherlands**: 2 letters + 6 digits
- **Belgium**: 2 letters + 6 digits
- **Sweden**: 8 digits
- **Poland**: 2 letters + 7 digits
- **Austria**: Letter + 7 digits
- **Portugal**: Letter + 6 digits
- **Ireland**: 2 letters + 7 digits

**Total**: 12 patterns | **Severity**: High | **Action**: Redact

### GDPR Coverage Summary:
- **Total Patterns**: 38
- **Countries Covered**: 13 major EU member states
- **Categories**: Tax IDs, National IDs, Passports
- **Compliance**: Article 6 (lawfulness), Article 9 (special categories), Article 32 (security)

### Testing Status:
✓ All patterns validated with positive and negative examples
✓ Schema compliance verified
✓ Integration tests passing

---

## 2. Korea PIPA Compliance

The Personal Information Protection Act (개인정보 보호법) is Korea's comprehensive privacy law.

### Current Pattern Coverage:

#### Personal Identification - `patterns/kr/rrn.yml`
- **RRN (Resident Registration Number)**: YYMMDD-XXXXXXX (Critical - 주민등록번호)
- **Alien Registration Number**: YYMMDD-XXXXXXX (Critical - 외국인등록번호)

**Total**: 2 patterns | **Severity**: Critical | **PIPA Article**: Article 24 (sensitive information)

#### Contact Information - `patterns/kr/phone.yml`
- **Mobile Numbers**: 010/011/016/017/018/019 formats
- **Landline Numbers**: Seoul (02), regional area codes

**Total**: 3 patterns | **Severity**: High

#### Financial Information - `patterns/kr/banks.yml`
- **16 Major Korean Banks**: KB, Shinhan, Woori, Hana, NH, etc.
- Account formats specific to each bank

**Total**: 17 patterns | **Severity**: Critical | **PIPA Article**: Article 24 (financial information)

#### Other Identification - `patterns/kr/identification.yml`
- **Passport**: 9 alphanumeric (M or S prefix)
- **Driver's License**: 12-14 digits

**Total**: 2 patterns

#### Business & Address - `patterns/kr/other.yml`
- **Business Registration Number**: XXX-XX-XXXXX
- **ZIP Code**: 5 digits
- **Korean Names**: 2-4 Hangul characters

**Total**: 3 patterns

### PIPA Coverage Summary:
- **Total Patterns**: 27
- **PIPA Key Categories Covered**: ✓
  - Resident Registration Number (주민등록번호) ✓
  - Passport Numbers (여권번호) ✓
  - Driver's License (운전면허번호) ✓
  - Alien Registration Numbers (외국인등록번호) ✓
  - Bank Accounts (계좌번호) ✓
  - Phone Numbers (전화번호) ✓
  - Names (이름) ✓

### Recommendations for Enhancement:
- Consider adding: Health insurance numbers, tax identification for individuals
- Add verification functions for RRN checksum validation

---

## 3. China PIPL Compliance

The Personal Information Protection Law (个人信息保护法) is China's comprehensive data protection law, similar to GDPR.

### Current Pattern Coverage:

#### Personal Identification - `patterns/cn/identification.yml`
- **National ID (身份证)**: 18 digits with checksum
- **Passport (护照)**: Various formats (E/G/P/S + 7-8 digits)

**Total**: 2 patterns | **Severity**: Critical | **PIPL Article**: Article 28 (sensitive information)

#### Contact Information - `patterns/cn/phone.yml`
- **Mobile Numbers**: 11 digits (13X-19X prefixes)
- **Landline Numbers**: Area code + 7-8 digits

**Total**: 2 patterns | **Severity**: High

#### Financial Information - `patterns/cn/banks.yml`
- **6 Major Chinese Banks**: ICBC, CCB, ABC, BOC, BOCOM, PSBC
- Account formats: 16-19 digits

**Total**: 6 patterns | **Severity**: Critical

#### Other Information - `patterns/cn/other.yml`
- **ZIP Code**: 6 digits
- **Social Credit Code**: 18 characters (企业统一社会信用代码)
- **Chinese Names**: 2-4 Chinese characters

**Total**: 3 patterns

### PIPL Coverage Summary:
- **Total Patterns**: 13
- **PIPL Key Categories Covered**: ✓
  - National ID Numbers (身份证号) ✓
  - Passport Numbers (护照号) ✓
  - Bank Accounts (银行账号) ✓
  - Phone Numbers (电话号码) ✓
  - Names (姓名) ✓
  - Biometric data: Not applicable (pattern-based detection)

### Recommendations for Enhancement:
- Consider adding: Vehicle license plates, property deed numbers
- Add verification functions for National ID checksum (last digit)

---

## 4. Japan APPI Compliance

The Act on Protection of Personal Information (個人情報の保護に関する法律) is Japan's privacy law.

### Current Pattern Coverage:

#### Personal Identification - `patterns/jp/identification.yml`
- **My Number (マイナンバー)**: 12 digits (XXXX-XXXX-XXXX)
- **Passport (パスポート)**: 2 letters + 7 digits
- **Driver's License (運転免許証)**: 12 digits

**Total**: 3 patterns | **Severity**: Critical | **APPI Article**: Article 2 (special care-required information)

#### Contact Information - `patterns/jp/phone.yml`
- **Mobile Numbers**: 070/080/090 + 8 digits
- **Landline Numbers**: Area code + 8 digits

**Total**: 2 patterns | **Severity**: High

#### Financial Information - `patterns/jp/banks.yml`
- **9 Major Japanese Banks**: Mizuho, SMBC, MUFG, Resona, Japan Post, Seven, Rakuten, etc.
- Account formats: Bank-specific (XXXX-XXX-XXXXXXX)

**Total**: 9 patterns | **Severity**: Critical

#### Other Information - `patterns/jp/other.yml`
- **ZIP Code**: XXX-XXXX (3-4 digits)
- **Addresses**: Prefecture + city + street + number
- **Japanese Names**: Hiragana, Katakana, Kanji formats

**Total**: 6 patterns

### APPI Coverage Summary:
- **Total Patterns**: 20
- **APPI Key Categories Covered**: ✓
  - My Number (マイナンバー) ✓
  - Passport Numbers (旅券番号) ✓
  - Driver's License (運転免許証番号) ✓
  - Bank Accounts (口座番号) ✓
  - Phone Numbers (電話番号) ✓
  - Names (氏名) ✓
  - Addresses (住所) ✓

### Recommendations for Enhancement:
- Consider adding: Basic pension numbers, health insurance numbers
- Add verification functions for My Number checksum

---

## Overall Statistics

| Region | Regulation | Patterns | Critical | High | Medium/Low | Files |
|--------|-----------|----------|----------|------|------------|-------|
| EU     | GDPR      | 38       | 14       | 12   | 12         | 3     |
| Korea  | PIPA      | 27       | 19       | 3    | 5          | 5     |
| China  | PIPL      | 13       | 8        | 2    | 3          | 4     |
| Japan  | APPI      | 20       | 12       | 2    | 6          | 4     |
| **Total** | -      | **98**   | **53**   | **19**| **26**    | **16** |

Plus existing patterns:
- **US**: 8 patterns (4 files)
- **Taiwan**: 15 patterns (4 files)
- **India**: 10 patterns (3 files)
- **Common**: 14 patterns (5 files)

**Grand Total**: ~145+ patterns across 35+ files

---

## Compliance Mapping

### GDPR (EU) - Article Coverage
| Article | Requirement | Pattern Coverage |
|---------|-------------|------------------|
| Art. 6  | Lawful basis for processing | All patterns enable lawful detection & consent |
| Art. 9  | Special categories (sensitive data) | National IDs, Passports, Tax IDs covered |
| Art. 32 | Security of processing | Enables detection for encryption/pseudonymization |
| Art. 35 | Data Protection Impact Assessment | Patterns aid in DPIA risk identification |

### PIPA (Korea) - Article Coverage
| Article | Requirement | Pattern Coverage |
|---------|-------------|------------------|
| Art. 23 | Prohibition on collecting sensitive info | RRN, financial data patterns |
| Art. 24 | Special requirements for sensitive info | RRN, alien registration, bank accounts |
| Art. 24-2 | Unique identification info (RRN) | Dedicated RRN patterns |

### PIPL (China) - Article Coverage
| Article | Requirement | Pattern Coverage |
|---------|-------------|------------------|
| Art. 28 | Sensitive personal information | National ID, passports, financial data |
| Art. 29 | Processing sensitive info | All critical-severity patterns |

### APPI (Japan) - Article Coverage
| Article | Requirement | Pattern Coverage |
|---------|-------------|------------------|
| Art. 2  | Special care-required information | My Number, sensitive identification |
| Art. 20 | Safety control measures | Enables detection for access controls |

---

## Testing & Validation

All compliance patterns have been validated with:
- ✓ Positive examples (should match)
- ✓ Negative examples (should not match)
- ✓ Schema compliance
- ✓ Integration tests
- ✓ Documentation with legal references

**Test Results**: 14/14 tests passing across all regions

---

## Future Enhancements

### Priority 1 (High Impact):
1. Add checksum validation functions for:
   - Korean RRN
   - Chinese National ID
   - Japanese My Number
   - Dutch BSN (11-proof)

2. Add missing sensitive categories:
   - Health insurance numbers (all regions)
   - Tax identification for individuals (EU/JP)

### Priority 2 (Medium Impact):
1. Add more EU countries:
   - Czech Republic, Hungary, Romania
   - Nordic countries (Norway, Iceland)

2. Expand APPI coverage:
   - Basic pension numbers
   - Corporate numbers

### Priority 3 (Low Impact):
1. Add regional-specific patterns:
   - UK after Brexit (separate from EU)
   - Swiss data protection patterns

2. Add verification functions for complex patterns:
   - Italian Codice Fiscale checksum
   - Spanish DNI letter validation

---

## Golang Compatibility Notes

**Current Status**: Most EU patterns use lookahead/lookbehind assertions that are NOT compatible with Golang's `regexp` package.

**Affected Patterns**:
- Most national ID patterns: `(?<!\d)...(? !\d)`
- Some passport patterns
- VAT numbers

**Solution**: See `GOLANG_COMPATIBILITY.md` for migration strategies using verification functions.

---

## References

- **GDPR**: https://gdpr-info.eu/
- **PIPA (Korea)**: https://www.privacy.go.kr/eng/
- **PIPL (China)**: http://www.npc.gov.cn/englishnpc/c23934/202107/
- **APPI (Japan)**: https://www.ppc.go.jp/en/

---

Generated: 2025-12-28
Version: 1.0
