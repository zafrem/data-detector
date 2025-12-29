# Keywords Folder Creation Summary

## What Was Done

Created a comprehensive keyword system organized by category to enable context-aware pattern detection for PII across multiple languages.

## Directory Structure Created

```
regex-patterns/keywords/
├── README.md              # Complete documentation
├── MAPPING.md            # Pattern-to-keyword mapping reference
├── financial.yml         # Bank, credit card, IBAN keywords
├── identification.yml    # SSN, passport, national ID keywords
├── contact.yml          # Email, phone, address keywords
├── network.yml          # IP, URL, MAC address keywords
└── personal.yml         # Name, DOB, gender keywords
```

## Keyword Categories

### 1. Financial (financial.yml)
**Subcategories:**
- `bank` - Bank account numbers, routing numbers
- `credit_card` - Credit/debit card numbers, CVV
- `iban` - International Bank Account Numbers

**Languages:** English, Korean (한국어), Japanese (日本語), Chinese (中文)

**Example Keywords:**
- English: bank account, credit card, IBAN
- Korean: 계좌번호, 신용카드, 카드번호
- Japanese: 口座番号, クレジットカード, カード番号
- Chinese: 银行账号, 信用卡, 卡号

**Related Patterns:**
- `regex-patterns/pii/*/banks.yml`
- `regex-patterns/pii/common/credit-cards.yml`
- `regex-patterns/pii/iban.yml`

### 2. Identification (identification.yml)
**Subcategories:**
- `ssn` - US Social Security Numbers
- `rrn` - Korean Resident Registration Numbers
- `passport` - Passport numbers
- `national_id` - National ID cards (Aadhaar, MyNumber, etc.)
- `drivers_license` - Driver's license numbers

**Languages:** English, Korean, Japanese, Chinese

**Example Keywords:**
- SSN, social security number, 주민등록번호, マイナンバー, 身份证
- Passport, 여권, パスポート, 护照

**Related Patterns:**
- `regex-patterns/pii/us/ssn.yml`
- `regex-patterns/pii/kr/rrn.yml`
- `regex-patterns/pii/*/identification.yml`

### 3. Contact (contact.yml)
**Subcategories:**
- `email` - Email addresses
- `phone` - Phone/mobile numbers
- `address` - Physical addresses
- `zipcode` - Postal/ZIP codes

**Languages:** English, Korean, Japanese, Chinese

**Example Keywords:**
- Email: email, e-mail, 이메일, メール, 电子邮件
- Phone: phone, mobile, 전화번호, 電話番号, 电话

**Related Patterns:**
- `regex-patterns/pii/common/email.yml`
- `regex-patterns/pii/*/phone.yml`
- `regex-patterns/pii/*/other.yml`

### 4. Network (network.yml)
**Subcategories:**
- `ip_address` - IPv4/IPv6 addresses
- `url` - URLs and web addresses
- `mac_address` - MAC addresses

**Languages:** Primarily English (technical terms)

**Example Keywords:**
- IP address, IPv4, IPv6, server, host
- URL, link, website, endpoint

**Related Patterns:**
- `regex-patterns/pii/common/ip.yml`
- `regex-patterns/pii/common/urls.yml`

### 5. Personal (personal.yml)
**Subcategories:**
- `name` - Personal names
- `date_of_birth` - Birth dates
- `age` - Age information
- `gender` - Gender/sex
- `nationality` - Citizenship/nationality

**Languages:** English, Korean, Japanese, Chinese

**Example Keywords:**
- Name: name, 이름, 氏名, 姓名
- DOB: date of birth, 생년월일, 生年月日, 出生日期

**Related Patterns:**
- `regex-patterns/pii/*/other.yml`

## File Format

Each keyword file follows this structure:

```yaml
category: <category_name>
description: <description>

categories:
  <subcategory>:
    description: <subcategory_description>
    patterns:
      - keyword1
      - keyword2
      - 한국어_키워드
      - 日本語キーワード
      - 中文关键词
    contexts:
      - "Label: "
      - "Context phrase"

metadata:
  related_categories: [...]
  severity: <critical|high|medium|low>
  common_contexts: [...]
```

## Usage Examples

### 1. Context-Aware Detection

```python
from datadetector import Engine, load_registry

# Load patterns
registry = load_registry(paths=["regex-patterns/pii/us/ssn.yml"])
engine = Engine(registry)

# Text with context
text = "Employee SSN: 123-45-6789"

# The keyword "SSN" provides context that this is likely real PII
result = engine.find(text)
```

### 2. Multi-Language Context

```python
# Korean context
korean_text = "계좌번호: 110-123-456789"  # "Account number: ..."

# Chinese context
chinese_text = "身份证号: 110101199001011234"  # "ID number: ..."

# Japanese context
japanese_text = "クレジットカード番号: 4532-0151-1283-0366"  # "Credit card: ..."
```

### 3. False Positive Reduction

```python
def has_context_keywords(text, position, keywords):
    """Check if match has nearby context keywords."""
    # Get 50 chars before and after match
    context = text[max(0, position-50):position+50].lower()

    # Check for any keyword
    return any(kw.lower() in context for kw in keywords)

# Use with SSN detection
ssn_keywords = ["ssn", "social security", "ss#", "tax id"]
if has_context_keywords(text, match_pos, ssn_keywords):
    # More likely to be real SSN
    pass
```

## Pattern to Keyword Mapping

| Pattern Category | Keyword File | Severity |
|-----------------|--------------|----------|
| Bank accounts | financial.yml | critical |
| Credit cards | financial.yml | critical |
| IBAN | financial.yml | critical |
| SSN/ITIN | identification.yml | critical |
| Passport | identification.yml | critical |
| National ID | identification.yml | critical |
| Email | contact.yml | medium |
| Phone | contact.yml | medium |
| Address | contact.yml | medium |
| IP Address | network.yml | low |
| URLs | network.yml | low |
| Names | personal.yml | medium |
| DOB | personal.yml | medium |

## Multi-Language Support

Keywords are provided in 4 languages:

1. **English** - Primary keywords (all categories)
2. **Korean (한국어)** - 계좌번호, 주민등록번호, 이메일, etc.
3. **Japanese (日本語)** - 口座番号, マイナンバー, メール, etc.
4. **Chinese (中文)** - 银行账号, 身份证, 电子邮件, etc.

## Benefits

1. **Context-Aware Detection** - Reduce false positives by checking surrounding text
2. **Multi-Language Support** - Detect PII in multiple languages
3. **Organized by Category** - Easy to find relevant keywords
4. **Extensible** - Easy to add new keywords or languages
5. **Well Documented** - Comprehensive README and mapping guides

## Integration Points

Keywords complement:
- **Regex Patterns** (`regex-patterns/pii/`) - Primary detection mechanism
- **Verification Functions** (`regex-patterns/_verification/`) - Additional validation
- **Context Filtering** - Reduce false positives

## Files Created

1. `regex-patterns/keywords/README.md` - Complete documentation (200+ lines)
2. `regex-patterns/keywords/MAPPING.md` - Pattern-to-keyword mapping (150+ lines)
3. `regex-patterns/keywords/financial.yml` - Financial keywords
4. `regex-patterns/keywords/identification.yml` - ID keywords
5. `regex-patterns/keywords/contact.yml` - Contact keywords
6. `regex-patterns/keywords/network.yml` - Network keywords
7. `regex-patterns/keywords/personal.yml` - Personal keywords
8. `KEYWORDS_CREATION_SUMMARY.md` - This summary document

## Next Steps (Optional)

1. **Implement context-aware filtering** in detection engine
2. **Add more languages** - Spanish, Portuguese, German, etc.
3. **Create language-specific keyword files** if needed
4. **Add more context phrases** based on real-world usage
5. **Integrate with ML models** for better context understanding

## See Also

- [Keywords README](regex-patterns/keywords/README.md) - Detailed documentation
- [Pattern-Keyword Mapping](regex-patterns/keywords/MAPPING.md) - Reference guide
- [PII Patterns](regex-patterns/pii/) - Regex pattern definitions
- [Verification Functions](regex-patterns/_verification/) - Validation logic
