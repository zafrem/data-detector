# Context-Aware Pattern Filtering Design

## Overview

Context-aware filtering uses keywords from metadata (column names, descriptions, labels, etc.) to pre-filter which regex patterns should be checked. This significantly improves performance and reduces false positives.

## Use Cases

1. **Database Column Scanning**
   - Column name: `user_ssn` → Check only SSN patterns
   - Column name: `billing_zip` → Check only zipcode patterns
   - Description: "Bank account number" → Check only bank account patterns

2. **Document Processing**
   - Section header: "Contact Information" → Check phone, email, address
   - Form label: "Passport Number" → Check only passport patterns

3. **API Response Scanning**
   - JSON key: `credit_card_number` → Check only credit card patterns
   - Field name: `resident_registration` → Check only RRN patterns

## Architecture

### 1. Keyword Registry (`patterns/keywords.yml`)

Maps contextual keywords to pattern categories/IDs:

```yaml
# Keyword-to-Pattern Mapping
keywords:
  # SSN-related keywords
  ssn:
    categories: [ssn]
    patterns: [us/ssn_01, us/itin_01]
    priority: high

  social_security:
    categories: [ssn]
    patterns: [us/ssn_01]
    priority: high

  # Bank account keywords
  bank_account:
    categories: [bank]
    patterns: [kr/bank_account_*]  # Wildcard matching
    priority: high

  account_number:
    categories: [bank]
    patterns: [kr/bank_account_*]
    priority: medium

  # Address/Zipcode keywords
  zipcode:
    categories: [address]
    patterns: [us/zipcode_01, kr/zipcode_01]
    priority: high

  postal_code:
    categories: [address]
    patterns: [us/zipcode_01, kr/zipcode_01]
    priority: high

  zip:
    categories: [address]
    patterns: [us/zipcode_01]
    priority: high

  # Phone keywords
  phone:
    categories: [phone]
    patterns: [us/phone_01, kr/phone_01, kr/phone_02, kr/phone_03]
    priority: high

  telephone:
    categories: [phone]
    patterns: [us/phone_01, kr/phone_01, kr/phone_02, kr/phone_03]
    priority: high

  mobile:
    categories: [phone]
    patterns: [kr/phone_02]
    priority: high

  # Credit card keywords
  credit_card:
    categories: [credit_card]
    patterns: [common/credit_card_01, common/credit_card_02]
    priority: high

  card_number:
    categories: [credit_card]
    patterns: [common/credit_card_01, common/credit_card_02]
    priority: medium

  # Email keywords
  email:
    categories: [email]
    patterns: [common/email_01]
    priority: high

  # Passport keywords
  passport:
    categories: [passport]
    patterns: [us/passport_01, kr/passport_01, kr/passport_02]
    priority: high

  # Korean-specific
  resident_registration:
    categories: [ssn]
    patterns: [kr/resident_registration_01, kr/resident_registration_02]
    priority: high

  rrn:
    categories: [ssn]
    patterns: [kr/resident_registration_01, kr/resident_registration_02]
    priority: high

  주민등록번호:
    categories: [ssn]
    patterns: [kr/resident_registration_01, kr/resident_registration_02]
    priority: high

  사업자등록번호:
    categories: [other]
    patterns: [kr/business_registration_01]
    priority: high

  운전면허:
    categories: [other]
    patterns: [kr/driver_license_01]
    priority: high

  계좌번호:
    categories: [bank]
    patterns: [kr/bank_account_*]
    priority: high

# Category-based groupings
categories:
  ssn:
    description: Social Security Numbers and equivalents
    patterns:
      - us/ssn_01
      - us/itin_01
      - kr/resident_registration_01
      - kr/resident_registration_02

  bank:
    description: Bank account numbers
    patterns:
      - kr/bank_account_01
      - kr/bank_account_02
      - kr/bank_account_03
      - kr/bank_account_04
      - kr/bank_account_05
      - kr/bank_account_06
      - kr/bank_account_07
      - kr/bank_account_08
      - kr/bank_account_09
      - kr/bank_account_10
      - kr/bank_account_11
      - kr/bank_account_12
      - kr/bank_account_13
      - kr/bank_account_14
      - kr/bank_account_15
      - kr/bank_account_16

  address:
    description: Address-related information
    patterns:
      - us/zipcode_01
      - kr/zipcode_01

  phone:
    description: Phone numbers
    patterns:
      - us/phone_01
      - kr/phone_01
      - kr/phone_02
      - kr/phone_03

  credit_card:
    description: Credit card numbers
    patterns:
      - common/credit_card_01
      - common/credit_card_02

  email:
    description: Email addresses
    patterns:
      - common/email_01

  passport:
    description: Passport numbers
    patterns:
      - us/passport_01
      - kr/passport_01
      - kr/passport_02

  other:
    description: Other identification numbers
    patterns:
      - us/ein_01
      - us/driver_license_ca_01
      - us/medicare_01
      - kr/business_registration_01
      - kr/driver_license_01
      - kr/foreign_registration_01

  ip:
    description: IP addresses
    patterns:
      - common/ipv4_01
      - common/ipv6_01

  location:
    description: Geographic coordinates
    patterns:
      - common/latitude_01
      - common/longitude_01
      - common/dms_coordinate_01

  token:
    description: API keys and tokens
    patterns:
      - common/jwt_token_01
      - common/aws_access_key_01
      - common/aws_secret_key_01
      - common/github_token_01
      - common/slack_token_01
      - common/stripe_key_01
      - common/openai_key_01
      - common/google_api_key_01
      - common/generic_api_key_01
      - common/bearer_token_01
      - common/basic_auth_01
      - common/private_key_01
```

### 2. Context Filter API

```python
# src/datadetector/context.py

from typing import List, Set, Optional, Dict, Union
from dataclasses import dataclass
import yaml
import re
from pathlib import Path


@dataclass
class ContextHint:
    """Contextual information to guide pattern selection."""

    # Direct keywords from metadata (column names, labels, etc.)
    keywords: List[str] = None

    # Category hints
    categories: List[str] = None

    # Explicit pattern IDs to include
    pattern_ids: List[str] = None

    # Pattern IDs to exclude
    exclude_patterns: List[str] = None

    # Strategy: 'strict', 'loose', 'none'
    # - strict: Only use keyword-matched patterns
    # - loose: Use keyword-matched + high-priority patterns
    # - none: Use all patterns (default behavior)
    strategy: str = 'loose'

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.categories is None:
            self.categories = []
        if self.pattern_ids is None:
            self.pattern_ids = []
        if self.exclude_patterns is None:
            self.exclude_patterns = []


class KeywordRegistry:
    """Registry mapping keywords to pattern categories/IDs."""

    def __init__(self, keywords_file: Optional[Path] = None):
        if keywords_file is None:
            keywords_file = Path(__file__).parent.parent.parent / "patterns" / "keywords.yml"

        self.keywords_file = keywords_file
        self.keyword_map: Dict[str, Dict] = {}
        self.category_map: Dict[str, Dict] = {}
        self._load_keywords()

    def _load_keywords(self):
        """Load keyword mappings from YAML file."""
        if not self.keywords_file.exists():
            return

        with open(self.keywords_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        self.keyword_map = data.get('keywords', {})
        self.category_map = data.get('categories', {})

    def get_patterns_for_keyword(self, keyword: str) -> Set[str]:
        """Get pattern IDs for a given keyword."""
        keyword_lower = keyword.lower().replace('_', ' ').replace('-', ' ')

        # Direct match
        if keyword_lower in self.keyword_map:
            return self._expand_patterns(self.keyword_map[keyword_lower].get('patterns', []))

        # Partial match (contains keyword)
        matched_patterns = set()
        for kw, config in self.keyword_map.items():
            if kw in keyword_lower or keyword_lower in kw:
                matched_patterns.update(self._expand_patterns(config.get('patterns', [])))

        return matched_patterns

    def get_patterns_for_category(self, category: str) -> Set[str]:
        """Get pattern IDs for a given category."""
        if category in self.category_map:
            return set(self.category_map[category].get('patterns', []))
        return set()

    def _expand_patterns(self, patterns: List[str]) -> Set[str]:
        """Expand wildcard patterns like 'kr/bank_account_*'."""
        expanded = set()
        for pattern in patterns:
            if '*' in pattern:
                # For now, just handle the wildcard case
                # In full implementation, would query registry for matching patterns
                expanded.add(pattern)
            else:
                expanded.add(pattern)
        return expanded


class ContextFilter:
    """Filter patterns based on contextual hints."""

    def __init__(self, registry: Optional[KeywordRegistry] = None):
        self.registry = registry or KeywordRegistry()

    def filter_patterns(
        self,
        hint: ContextHint,
        all_patterns: List[str]
    ) -> List[str]:
        """
        Filter pattern list based on context hint.

        Args:
            hint: Context hint with keywords, categories, etc.
            all_patterns: List of all available pattern IDs

        Returns:
            Filtered list of pattern IDs to check
        """
        if hint.strategy == 'none':
            return all_patterns

        # Collect patterns from various sources
        selected_patterns = set()

        # 1. Explicit pattern IDs
        selected_patterns.update(hint.pattern_ids)

        # 2. Keywords
        for keyword in hint.keywords:
            patterns = self.registry.get_patterns_for_keyword(keyword)
            selected_patterns.update(patterns)

        # 3. Categories
        for category in hint.categories:
            patterns = self.registry.get_patterns_for_category(category)
            selected_patterns.update(patterns)

        # Handle wildcards
        expanded_patterns = set()
        for pattern in selected_patterns:
            if '*' in pattern:
                # Match against all patterns
                pattern_re = re.compile(pattern.replace('*', '.*'))
                matched = [p for p in all_patterns if pattern_re.match(p)]
                expanded_patterns.update(matched)
            else:
                if pattern in all_patterns:
                    expanded_patterns.add(pattern)

        # If loose strategy and no patterns found, fall back to all patterns
        if hint.strategy == 'loose' and not expanded_patterns:
            return all_patterns

        # Apply exclusions
        expanded_patterns -= set(hint.exclude_patterns)

        # Maintain original order
        return [p for p in all_patterns if p in expanded_patterns]
```

### 3. Enhanced Engine API

```python
# Modifications to src/datadetector/engine.py

class Engine:
    """Enhanced engine with context-aware filtering."""

    def __init__(
        self,
        registry: Optional[PatternRegistry] = None,
        keyword_registry: Optional[KeywordRegistry] = None
    ):
        self.registry = registry or load_registry()
        self.keyword_registry = keyword_registry or KeywordRegistry()
        self.context_filter = ContextFilter(self.keyword_registry)

    def find(
        self,
        text: str,
        context: Optional[ContextHint] = None
    ) -> DetectionResult:
        """
        Find PII in text with optional context filtering.

        Args:
            text: Text to scan
            context: Optional context hint for pattern filtering

        Returns:
            DetectionResult with matches
        """
        if context is None:
            # Default behavior: check all patterns
            patterns_to_check = list(self.registry.patterns.keys())
        else:
            # Filter patterns based on context
            all_patterns = list(self.registry.patterns.keys())
            patterns_to_check = self.context_filter.filter_patterns(
                context, all_patterns
            )

        # Sort by priority
        patterns_to_check = self._sort_by_priority(patterns_to_check)

        # Run detection on filtered patterns
        matches = []
        for pattern_id in patterns_to_check:
            pattern = self.registry.get_pattern(pattern_id)
            # ... existing matching logic ...

        return DetectionResult(matches=matches)
```

## Usage Examples

### Example 1: Database Column Scanning

```python
from datadetector import Engine
from datadetector.context import ContextHint

engine = Engine()

# Scan a database column with metadata
column_name = "user_ssn"
column_values = ["123-45-6789", "987-65-4321"]

# Create context hint from column name
context = ContextHint(
    keywords=[column_name],
    strategy='strict'  # Only check SSN patterns
)

for value in column_values:
    result = engine.find(value, context=context)
    # Only SSN patterns are checked, much faster!
```

### Example 2: Form Processing

```python
# Form field with label
form_data = {
    "label": "Bank Account Number",
    "description": "Enter your 12-digit bank account",
    "value": "123-456-789012"
}

context = ContextHint(
    keywords=["bank", "account"],
    strategy='strict'
)

result = engine.find(form_data["value"], context=context)
# Only bank account patterns are checked
```

### Example 3: Multi-field Document

```python
# Scan entire document with section-based filtering
document_sections = [
    {
        "header": "Contact Information",
        "content": "Email: user@example.com, Phone: (555) 123-4567"
    },
    {
        "header": "Payment Details",
        "content": "Card: 4532-1234-5678-9010"
    }
]

for section in document_sections:
    # Auto-detect context from header
    if "contact" in section["header"].lower():
        context = ContextHint(categories=['email', 'phone'])
    elif "payment" in section["header"].lower():
        context = ContextHint(categories=['credit_card', 'bank'])
    else:
        context = None

    result = engine.find(section["content"], context=context)
```

### Example 4: API Response Scanning

```python
import json

# Scan API response with field name hints
api_response = {
    "user_id": 12345,
    "ssn": "123-45-6789",
    "billing_zip": "90210",
    "phone_number": "(555) 123-4567"
}

for field_name, value in api_response.items():
    if not isinstance(value, str):
        continue

    context = ContextHint(
        keywords=[field_name],
        strategy='loose'
    )

    result = engine.find(str(value), context=context)
    if result.matches:
        print(f"{field_name}: {result.matches[0].category}")
```

## Performance Benefits

1. **Reduced Pattern Checks**: Instead of checking all 61 patterns, only check 2-5 relevant patterns
2. **Faster Execution**: ~10-20x faster for targeted scans
3. **Fewer False Positives**: Context reduces ambiguous matches
4. **Better Accuracy**: Category hints improve pattern selection

## Migration Path

1. **Backward Compatible**: If no context provided, engine works as before
2. **Opt-in**: Users can gradually add context hints
3. **Auto-detection**: Can build heuristics to auto-detect context from field names
