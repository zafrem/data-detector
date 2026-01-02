"""Pre-configured context presets for common use cases.

This module provides ready-to-use ContextHint configurations for common
data scanning scenarios, making it easy to get started with context-aware
pattern filtering.

Quick Start:
    >>> from datadetector import Engine, load_registry
    >>> from datadetector.context_presets import DATABASE_SSN, DATABASE_EMAIL
    >>>
    >>> engine = Engine(registry=load_registry())
    >>> result = engine.find("123-45-6789", context=DATABASE_SSN)

Available Presets:
    - Database scanning: DATABASE_SSN, DATABASE_EMAIL, DATABASE_PHONE, etc.
    - Korean data: KOREAN_RRN, KOREAN_BANK_ACCOUNT, KOREAN_BUSINESS, etc.
    - Financial: FINANCIAL_DATA, PAYMENT_INFO
    - Contact: CONTACT_INFO
    - General: PII_ALL, PII_CRITICAL_ONLY
"""

from datadetector.context import ContextHint

# ==============================================================================
# DATABASE COLUMN SCANNING PRESETS
# ==============================================================================

DATABASE_SSN = ContextHint(
    keywords=["ssn", "social_security", "taxpayer"],
    categories=["ssn"],
    strategy="strict",
)
"""Scan database columns containing Social Security Numbers.

Use for: user_ssn, employee_ssn, taxpayer_id, social_security_number

Example:
    >>> result = engine.find(ssn_value, context=DATABASE_SSN)
"""

DATABASE_EMAIL = ContextHint(
    keywords=["email", "mail"],
    categories=["email"],
    strategy="strict",
)
"""Scan database columns containing email addresses.

Use for: user_email, contact_email, email_address, manager_email

Example:
    >>> result = engine.find(email_value, context=DATABASE_EMAIL)
"""

DATABASE_PHONE = ContextHint(
    keywords=["phone", "telephone", "mobile", "cell"],
    categories=["phone"],
    strategy="strict",
)
"""Scan database columns containing phone numbers.

Use for: phone_number, mobile_phone, contact_phone, telephone

Example:
    >>> result = engine.find(phone_value, context=DATABASE_PHONE)
"""

DATABASE_ADDRESS = ContextHint(
    keywords=["address", "zipcode", "zip", "postal"],
    categories=["address"],
    strategy="strict",
)
"""Scan database columns containing addresses or zip codes.

Use for: billing_zip, postal_code, address_zip, zipcode

Example:
    >>> result = engine.find(zip_value, context=DATABASE_ADDRESS)
"""

DATABASE_CREDIT_CARD = ContextHint(
    keywords=["credit_card", "card", "payment"],
    categories=["credit_card"],
    strategy="strict",
)
"""Scan database columns containing credit card numbers.

Use for: card_number, credit_card, payment_card, cc_number

Example:
    >>> result = engine.find(card_value, context=DATABASE_CREDIT_CARD)
"""

DATABASE_BANK_ACCOUNT = ContextHint(
    keywords=["account", "bank"],
    categories=["bank"],
    strategy="strict",
)
"""Scan database columns containing bank account numbers.

Use for: bank_account, account_number, routing_number

Example:
    >>> result = engine.find(account_value, context=DATABASE_BANK_ACCOUNT)
"""

DATABASE_PASSPORT = ContextHint(
    keywords=["passport"],
    categories=["passport"],
    strategy="strict",
)
"""Scan database columns containing passport numbers.

Use for: passport_number, passport_id, travel_document

Example:
    >>> result = engine.find(passport_value, context=DATABASE_PASSPORT)
"""

# ==============================================================================
# KOREAN DATA SCANNING PRESETS
# ==============================================================================

KOREAN_RRN = ContextHint(
    keywords=["주민등록번호", "주민번호", "rrn", "resident"],
    categories=["ssn"],
    strategy="strict",
)
"""Scan Korean Resident Registration Numbers (주민등록번호).

Use for: 주민등록번호, 주민번호, rrn, resident_registration

Example:
    >>> result = engine.find("900101-1234567", context=KOREAN_RRN)
"""

KOREAN_BANK_ACCOUNT = ContextHint(
    keywords=["계좌번호", "계좌", "은행계좌", "bank_account"],
    categories=["bank"],
    strategy="strict",
)
"""Scan Korean bank account numbers (계좌번호).

Use for: 계좌번호, 은행계좌, bank_account

Example:
    >>> result = engine.find("110-123-456789", context=KOREAN_BANK_ACCOUNT)
"""

KOREAN_PHONE = ContextHint(
    keywords=["전화번호", "휴대폰", "핸드폰", "phone"],
    categories=["phone"],
    strategy="strict",
)
"""Scan Korean phone numbers (전화번호).

Use for: 전화번호, 휴대폰, 핸드폰, phone_number

Example:
    >>> result = engine.find("010-1234-5678", context=KOREAN_PHONE)
"""

KOREAN_BUSINESS = ContextHint(
    keywords=["사업자등록번호", "사업자번호", "business"],
    categories=["other"],
    pattern_ids=["kr/business_registration_01"],
    strategy="strict",
)
"""Scan Korean business registration numbers (사업자등록번호).

Use for: 사업자등록번호, 사업자번호, business_registration

Example:
    >>> result = engine.find("123-45-67890", context=KOREAN_BUSINESS)
"""

KOREAN_ADDRESS = ContextHint(
    keywords=["우편번호", "zipcode", "postal"],
    categories=["address"],
    strategy="strict",
)
"""Scan Korean postal codes (우편번호).

Use for: 우편번호, postal_code, zipcode

Example:
    >>> result = engine.find("06234", context=KOREAN_ADDRESS)
"""

# ==============================================================================
# CATEGORY-BASED PRESETS
# ==============================================================================

CONTACT_INFO = ContextHint(
    categories=["email", "phone", "address"],
    strategy="loose",
)
"""Scan for any contact information (email, phone, address).

Use for: Contact forms, user profiles, customer records

Example:
    >>> text = "Email: john@example.com, Phone: (555) 123-4567"
    >>> result = engine.find(text, context=CONTACT_INFO)
"""

FINANCIAL_DATA = ContextHint(
    categories=["ssn", "credit_card", "bank"],
    strategy="loose",
)
"""Scan for financial data (SSN, credit cards, bank accounts).

Use for: Payment forms, financial records, billing information

Example:
    >>> text = "SSN: 123-45-6789, Card: 4532-1234-5678-9010"
    >>> result = engine.find(text, context=FINANCIAL_DATA)
"""

PAYMENT_INFO = ContextHint(
    categories=["credit_card", "bank"],
    strategy="strict",
)
"""Scan for payment information only (credit cards, bank accounts).

Use for: Payment forms, checkout pages, transaction records

Example:
    >>> result = engine.find(card_number, context=PAYMENT_INFO)
"""

PERSONAL_IDENTIFIERS = ContextHint(
    categories=["ssn", "passport", "other"],
    strategy="loose",
)
"""Scan for personal identification numbers (SSN, passport, driver license, etc.).

Use for: Identity verification, KYC processes, registration forms

Example:
    >>> result = engine.find(id_number, context=PERSONAL_IDENTIFIERS)
"""

TECHNICAL_DATA = ContextHint(
    categories=["ip", "token"],
    strategy="loose",
)
"""Scan for technical data (IP addresses, API keys, tokens).

Use for: Log files, configuration files, API responses

Example:
    >>> result = engine.find(log_entry, context=TECHNICAL_DATA)
"""

LOCATION_DATA = ContextHint(
    categories=["address", "location"],
    strategy="loose",
)
"""Scan for location data (addresses, coordinates, zip codes).

Use for: Mapping applications, delivery addresses, geolocation data

Example:
    >>> result = engine.find(location_string, context=LOCATION_DATA)
"""

# ==============================================================================
# COMPREHENSIVE PRESETS
# ==============================================================================

PII_ALL = ContextHint(
    strategy="none",
)
"""Scan for all PII types (no filtering - checks all 61 patterns).

Use for: Comprehensive scans, unknown data types, general purpose scanning

Example:
    >>> result = engine.find(unknown_text, context=PII_ALL)
"""

PII_CRITICAL_ONLY = ContextHint(
    categories=["ssn", "credit_card", "passport"],
    strategy="loose",
)
"""Scan for critical PII only (SSN, credit cards, passports).

Use for: Quick security scans, high-risk data detection

Example:
    >>> result = engine.find(text, context=PII_CRITICAL_ONLY)
"""

PII_MEDIUM_HIGH = ContextHint(
    categories=["ssn", "credit_card", "passport", "phone", "bank"],
    strategy="loose",
)
"""Scan for medium-to-high severity PII.

Use for: Standard security scans, compliance checks

Example:
    >>> result = engine.find(text, context=PII_MEDIUM_HIGH)
"""

# ==============================================================================
# API/JSON SCANNING PRESETS
# ==============================================================================

API_USER_DATA = ContextHint(
    categories=["email", "phone", "ssn"],
    keywords=["user", "customer", "account"],
    strategy="loose",
)
"""Scan API responses containing user data.

Use for: REST API responses, user profile endpoints, customer data APIs

Example:
    >>> result = engine.find(api_response_text, context=API_USER_DATA)
"""

API_PAYMENT_DATA = ContextHint(
    categories=["credit_card", "bank"],
    keywords=["payment", "billing", "transaction"],
    strategy="loose",
)
"""Scan API responses containing payment data.

Use for: Payment API responses, billing endpoints, transaction data

Example:
    >>> result = engine.find(payment_response, context=API_PAYMENT_DATA)
"""

# ==============================================================================
# DOCUMENT SCANNING PRESETS
# ==============================================================================

DOCUMENT_GENERAL = ContextHint(
    categories=["ssn", "email", "phone", "address", "credit_card"],
    strategy="loose",
)
"""Scan general documents for common PII.

Use for: PDF documents, text files, unstructured data

Example:
    >>> result = engine.find(document_text, context=DOCUMENT_GENERAL)
"""

DOCUMENT_MEDICAL = ContextHint(
    categories=["ssn", "other"],  # Includes Medicare
    keywords=["patient", "medical", "medicare", "health"],
    strategy="loose",
)
"""Scan medical documents for healthcare-related PII.

Use for: Medical records, patient data, healthcare documents

Example:
    >>> result = engine.find(medical_record, context=DOCUMENT_MEDICAL)
"""

DOCUMENT_FINANCIAL = ContextHint(
    categories=["ssn", "credit_card", "bank"],
    keywords=["account", "transaction", "payment"],
    strategy="loose",
)
"""Scan financial documents for finance-related PII.

Use for: Bank statements, invoices, financial reports

Example:
    >>> result = engine.find(financial_doc, context=DOCUMENT_FINANCIAL)
"""

# ==============================================================================
# PRESET COLLECTIONS
# ==============================================================================

DATABASE_PRESETS = {
    "ssn": DATABASE_SSN,
    "email": DATABASE_EMAIL,
    "phone": DATABASE_PHONE,
    "address": DATABASE_ADDRESS,
    "credit_card": DATABASE_CREDIT_CARD,
    "bank_account": DATABASE_BANK_ACCOUNT,
    "passport": DATABASE_PASSPORT,
}
"""Dictionary of database scanning presets for easy lookup."""

KOREAN_PRESETS = {
    "rrn": KOREAN_RRN,
    "bank_account": KOREAN_BANK_ACCOUNT,
    "phone": KOREAN_PHONE,
    "business": KOREAN_BUSINESS,
    "address": KOREAN_ADDRESS,
}
"""Dictionary of Korean data scanning presets for easy lookup."""

CATEGORY_PRESETS = {
    "contact": CONTACT_INFO,
    "financial": FINANCIAL_DATA,
    "payment": PAYMENT_INFO,
    "identifiers": PERSONAL_IDENTIFIERS,
    "technical": TECHNICAL_DATA,
    "location": LOCATION_DATA,
}
"""Dictionary of category-based presets for easy lookup."""

COMPREHENSIVE_PRESETS = {
    "all": PII_ALL,
    "critical": PII_CRITICAL_ONLY,
    "medium_high": PII_MEDIUM_HIGH,
}
"""Dictionary of comprehensive scanning presets for easy lookup."""

API_PRESETS = {
    "user_data": API_USER_DATA,
    "payment_data": API_PAYMENT_DATA,
}
"""Dictionary of API scanning presets for easy lookup."""

DOCUMENT_PRESETS = {
    "general": DOCUMENT_GENERAL,
    "medical": DOCUMENT_MEDICAL,
    "financial": DOCUMENT_FINANCIAL,
}
"""Dictionary of document scanning presets for easy lookup."""

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================


def get_preset(name: str) -> ContextHint:
    """Get a preset by name.

    Args:
        name: Preset name (e.g., 'database.ssn', 'korean.rrn', 'contact')

    Returns:
        ContextHint preset

    Raises:
        ValueError: If preset not found

    Examples:
        >>> preset = get_preset('database.ssn')
        >>> preset = get_preset('korean.rrn')
        >>> preset = get_preset('contact')
    """
    all_presets = {
        # Database
        "database.ssn": DATABASE_SSN,
        "database.email": DATABASE_EMAIL,
        "database.phone": DATABASE_PHONE,
        "database.address": DATABASE_ADDRESS,
        "database.credit_card": DATABASE_CREDIT_CARD,
        "database.bank_account": DATABASE_BANK_ACCOUNT,
        "database.passport": DATABASE_PASSPORT,
        # Korean
        "korean.rrn": KOREAN_RRN,
        "korean.bank_account": KOREAN_BANK_ACCOUNT,
        "korean.phone": KOREAN_PHONE,
        "korean.business": KOREAN_BUSINESS,
        "korean.address": KOREAN_ADDRESS,
        # Categories
        "contact": CONTACT_INFO,
        "financial": FINANCIAL_DATA,
        "payment": PAYMENT_INFO,
        "identifiers": PERSONAL_IDENTIFIERS,
        "technical": TECHNICAL_DATA,
        "location": LOCATION_DATA,
        # Comprehensive
        "all": PII_ALL,
        "critical": PII_CRITICAL_ONLY,
        "medium_high": PII_MEDIUM_HIGH,
        # API
        "api.user_data": API_USER_DATA,
        "api.payment_data": API_PAYMENT_DATA,
        # Documents
        "document.general": DOCUMENT_GENERAL,
        "document.medical": DOCUMENT_MEDICAL,
        "document.financial": DOCUMENT_FINANCIAL,
    }

    if name not in all_presets:
        raise ValueError(
            f"Preset '{name}' not found. Available presets: {', '.join(all_presets.keys())}"
        )

    return all_presets[name]


def list_presets() -> dict:
    """List all available presets grouped by category.

    Returns:
        Dictionary of preset categories and their names

    Example:
        >>> presets = list_presets()
        >>> print(presets['database'])
        ['ssn', 'email', 'phone', 'address', 'credit_card', 'bank_account', 'passport']
    """
    return {
        "database": list(DATABASE_PRESETS.keys()),
        "korean": list(KOREAN_PRESETS.keys()),
        "category": list(CATEGORY_PRESETS.keys()),
        "comprehensive": list(COMPREHENSIVE_PRESETS.keys()),
        "api": list(API_PRESETS.keys()),
        "document": list(DOCUMENT_PRESETS.keys()),
    }
