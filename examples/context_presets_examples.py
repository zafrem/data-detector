"""Examples using pre-configured context presets.

This file demonstrates how to use ready-made presets for common scanning scenarios.
All examples are copy-paste ready!

Run this file:
    python3 examples/context_presets_examples.py
"""

from datadetector import Engine, load_registry, context_presets


def example_1_database_scanning():
    """Example 1: Database column scanning with presets."""
    print("=" * 70)
    print("Example 1: Database Column Scanning (English)")
    print("=" * 70)

    engine = Engine(registry=load_registry())

    # Simulate database table
    user_table = {
        "user_id": ["12345", "67890"],
        "user_ssn": ["123-45-6789", "987-65-4321"],
        "email_address": ["john@example.com", "jane@example.com"],
        "phone_number": ["(555) 123-4567", "(555) 987-6543"],
        "billing_zip": ["90210", "10001"],
    }

    # Scan each column with appropriate preset
    for column_name, values in user_table.items():
        print(f"\n📋 Column: {column_name}")

        # Select preset based on column name
        if "ssn" in column_name:
            preset = context_presets.DATABASE_SSN
            print(f"   Using: DATABASE_SSN")
        elif "email" in column_name:
            preset = context_presets.DATABASE_EMAIL
            print(f"   Using: DATABASE_EMAIL")
        elif "phone" in column_name:
            preset = context_presets.DATABASE_PHONE
            print(f"   Using: DATABASE_PHONE")
        elif "zip" in column_name:
            preset = context_presets.DATABASE_ADDRESS
            print(f"   Using: DATABASE_ADDRESS")
        else:
            preset = None

        for value in values:
            if preset:
                result = engine.find(value, context=preset)
                if result.has_matches:
                    match = result.matches[0]
                    print(f"   ✓ '{value}' → {match.ns_id}")
                else:
                    print(f"   ○ '{value}' → No PII")
            else:
                print(f"   - '{value}' → Skipped (no preset)")


def example_2_korean_database():
    """Example 2: Korean database scanning with presets."""
    print("\n" + "=" * 70)
    print("Example 2: Korean Database Scanning")
    print("=" * 70)

    engine = Engine(registry=load_registry())

    # Korean customer database
    customer_data = {
        "고객명": ["홍길동", "김철수"],
        "주민등록번호": ["900101-1234567", "850315-2345678"],
        "계좌번호": ["110-123-456789", "020-456-789012"],
        "전화번호": ["010-1234-5678", "02-9876-5432"],
        "우편번호": ["06234", "48058"],
    }

    # Preset mapping for Korean fields
    preset_map = {
        "주민등록번호": context_presets.KOREAN_RRN,
        "계좌번호": context_presets.KOREAN_BANK_ACCOUNT,
        "전화번호": context_presets.KOREAN_PHONE,
        "우편번호": context_presets.KOREAN_ADDRESS,
    }

    for field_name, values in customer_data.items():
        if field_name in preset_map:
            print(f"\n📋 {field_name}")
            preset = preset_map[field_name]
            print(f"   Using: {preset.__class__.__name__}")

            for value in values:
                result = engine.find(value, context=preset)
                if result.has_matches:
                    print(f"   ✓ {value} → {result.matches[0].ns_id}")
                else:
                    print(f"   ○ {value} → No match")


def example_3_contact_form():
    """Example 3: Contact form scanning with category preset."""
    print("\n" + "=" * 70)
    print("Example 3: Contact Form Scanning")
    print("=" * 70)

    engine = Engine(registry=load_registry())

    # Contact form submission
    contact_form = """
    Contact Form Submission:
    Name: John Doe
    Email: john.doe@example.com
    Phone: (555) 123-4567
    Address: 90210
    Message: Please call me about the product inquiry.
    """

    print("\nOriginal Form:")
    print(contact_form)

    # Scan for contact information using preset
    result = engine.find(contact_form, context=context_presets.CONTACT_INFO)

    print(f"\nFound {len(result.matches)} contact details using CONTACT_INFO preset:")
    for match in result.matches:
        text = contact_form[match.start:match.end]
        print(f"  • {text} ({match.category.value}, severity: {match.severity.value})")


def example_4_financial_data():
    """Example 4: Financial data scanning with preset."""
    print("\n" + "=" * 70)
    print("Example 4: Financial Data Scanning")
    print("=" * 70)

    engine = Engine(registry=load_registry())

    # Payment processing data
    payment_record = """
    Payment Record #12345
    Customer SSN: 123-45-6789
    Credit Card: 4532-1234-5678-9010
    Bank Account: 110-123-456789
    Amount: $1,500.00
    Date: 2024-01-15
    """

    print("\nOriginal Record:")
    print(payment_record)

    # Scan for financial PII using preset
    result = engine.find(payment_record, context=context_presets.FINANCIAL_DATA)

    print(f"\nFound {len(result.matches)} financial data points using FINANCIAL_DATA preset:")
    for match in result.matches:
        text = payment_record[match.start:match.end]
        print(f"  • {text} ({match.category.value}, severity: {match.severity.value})")


def example_5_critical_pii_scan():
    """Example 5: Quick security scan for critical PII only."""
    print("\n" + "=" * 70)
    print("Example 5: Critical PII Security Scan")
    print("=" * 70)

    engine = Engine(registry=load_registry())

    # Mixed data
    document = """
    Employee Record:
    Name: Jane Smith
    Email: jane@company.com
    Phone: (555) 987-6543
    SSN: 987-65-4321
    Passport: 123456789
    Office: Building A, Room 101
    """

    print("\nOriginal Document:")
    print(document)

    # Scan for CRITICAL PII only (ignores email, phone)
    result = engine.find(document, context=context_presets.PII_CRITICAL_ONLY)

    print(f"\nFound {len(result.matches)} CRITICAL PII items:")
    print("(Note: Email and phone are NOT critical, so they're ignored)")
    for match in result.matches:
        text = document[match.start:match.end]
        print(f"  🚨 {text} ({match.category.value}, severity: {match.severity.value})")


def example_6_api_response_scanning():
    """Example 6: API response scanning with preset."""
    print("\n" + "=" * 70)
    print("Example 6: API Response Scanning")
    print("=" * 70)

    engine = Engine(registry=load_registry())

    # Simulated API response
    api_response = {
        "user_id": 12345,
        "username": "johndoe",
        "email": "john@example.com",
        "ssn": "123-45-6789",
        "phone": "(555) 123-4567",
        "created_at": "2024-01-01T10:00:00Z",
        "status": "active",
    }

    print("\nAPI Response:")
    import json
    print(json.dumps(api_response, indent=2))

    # Scan each string field using API_USER_DATA preset
    print(f"\nScanning with API_USER_DATA preset:")
    for key, value in api_response.items():
        if isinstance(value, str):
            result = engine.find(value, context=context_presets.API_USER_DATA)

            if result.has_matches:
                match = result.matches[0]
                print(f"  ⚠️  {key}: '{value}' → {match.category.value}")
            else:
                print(f"  ✓ {key}: '{value}' → Safe")


def example_7_redaction_with_presets():
    """Example 7: Redacting sensitive data with presets."""
    print("\n" + "=" * 70)
    print("Example 7: Redaction with Presets")
    print("=" * 70)

    engine = Engine(registry=load_registry())

    # Customer record
    customer_record = {
        "customer_id": "CUST-12345",
        "name": "John Doe",
        "ssn": "123-45-6789",
        "email": "john@example.com",
        "phone": "(555) 123-4567",
    }

    print("\nOriginal Customer Record:")
    for key, value in customer_record.items():
        print(f"  {key}: {value}")

    # Redact sensitive fields
    redacted_record = {}
    for key, value in customer_record.items():
        # Select appropriate preset
        if "ssn" in key:
            preset = context_presets.DATABASE_SSN
        elif "email" in key:
            preset = context_presets.DATABASE_EMAIL
        elif "phone" in key:
            preset = context_presets.DATABASE_PHONE
        else:
            preset = None

        if preset:
            result = engine.redact(value, context=preset)
            redacted_record[key] = result.redacted_text
        else:
            redacted_record[key] = value

    print("\nRedacted Customer Record:")
    for key, value in redacted_record.items():
        print(f"  {key}: {value}")


def example_8_preset_dictionaries():
    """Example 8: Using preset dictionaries and helpers."""
    print("\n" + "=" * 70)
    print("Example 8: Preset Dictionaries and Helpers")
    print("=" * 70)

    from datadetector.context_presets import (
        DATABASE_PRESETS,
        KOREAN_PRESETS,
        get_preset,
        list_presets,
    )

    engine = Engine(registry=load_registry())

    # Use preset dictionary
    print("\n1. Using DATABASE_PRESETS dictionary:")
    test_data = {
        "ssn": "123-45-6789",
        "email": "test@example.com",
        "phone": "(555) 123-4567",
    }

    for data_type, value in test_data.items():
        preset = DATABASE_PRESETS[data_type]
        result = engine.find(value, context=preset)
        print(f"  {data_type}: {result.has_matches}")

    # Use get_preset helper
    print("\n2. Using get_preset() helper:")
    preset = get_preset("database.ssn")
    result = engine.find("123-45-6789", context=preset)
    print(f"  database.ssn preset: {result.has_matches}")

    preset = get_preset("korean.rrn")
    result = engine.find("900101-1234567", context=preset)
    print(f"  korean.rrn preset: {result.has_matches}")

    # List all presets
    print("\n3. List all available presets:")
    all_presets = list_presets()
    for category, names in all_presets.items():
        print(f"  {category}: {', '.join(names)}")


def example_9_performance_comparison():
    """Example 9: Performance comparison with and without presets."""
    print("\n" + "=" * 70)
    print("Example 9: Performance Comparison")
    print("=" * 70)

    import time

    engine = Engine(registry=load_registry())
    text = "SSN: 123-45-6789"
    iterations = 1000

    # Without context (all 61 patterns)
    start = time.time()
    for _ in range(iterations):
        engine.find(text)
    no_context_time = time.time() - start

    # With preset (only ~3 SSN patterns)
    start = time.time()
    for _ in range(iterations):
        engine.find(text, context=context_presets.DATABASE_SSN)
    preset_time = time.time() - start

    print(f"\nIterations: {iterations}")
    print(f"Text: '{text}'")
    print(f"\nWithout context (all 61 patterns): {no_context_time:.3f}s")
    print(f"With DATABASE_SSN preset (~3 patterns): {preset_time:.3f}s")
    print(f"\nSpeedup: {no_context_time / preset_time:.1f}x faster with preset! 🚀")


if __name__ == "__main__":
    # Run all examples
    example_1_database_scanning()
    example_2_korean_database()
    example_3_contact_form()
    example_4_financial_data()
    example_5_critical_pii_scan()
    example_6_api_response_scanning()
    example_7_redaction_with_presets()
    example_8_preset_dictionaries()
    example_9_performance_comparison()

    print("\n" + "=" * 70)
    print("All examples completed! ✅")
    print("=" * 70)
    print("\nTry these presets in your own code:")
    print("  from datadetector import context_presets")
    print("  result = engine.find(value, context=context_presets.DATABASE_SSN)")
    print("\nSee CONTEXT_PRESETS_GUIDE.md for complete documentation.")
