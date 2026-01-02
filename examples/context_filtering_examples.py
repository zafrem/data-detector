"""Examples demonstrating context-aware pattern filtering.

This module shows how to use ContextHint to improve performance by only
checking relevant patterns based on contextual information like column names,
field labels, or descriptions.
"""

from datadetector import ContextHint, Engine, create_context_from_field_name, load_registry


def example_1_database_column_scanning():
    """Example 1: Scanning database columns with metadata."""
    print("=" * 70)
    print("Example 1: Database Column Scanning")
    print("=" * 70)

    engine = Engine(registry=load_registry())

    # Simulate database table
    table_data = [
        {
            "column_name": "user_ssn",
            "data_type": "VARCHAR(11)",
            "values": ["123-45-6789", "987-65-4321", "555-12-3456"],
        },
        {
            "column_name": "billing_zip",
            "data_type": "VARCHAR(10)",
            "values": ["90210", "48201-1234", "12345"],
        },
        {
            "column_name": "phone_number",
            "data_type": "VARCHAR(20)",
            "values": ["(555) 123-4567", "+1-555-987-6543"],
        },
    ]

    for column in table_data:
        print(f"\nColumn: {column['column_name']}")
        print(f"Data Type: {column['data_type']}")

        # Create context hint from column name
        context = create_context_from_field_name(column["column_name"], strategy="strict")

        print(f"Context keywords: {context.keywords}")

        for value in column["values"]:
            # Find with context filtering - only checks relevant patterns
            result = engine.find(value, context=context)

            if result.has_matches:
                match = result.matches[0]
                print(f"  ✓ '{value}' -> {match.ns_id} ({match.category.value})")
            else:
                print(f"  ✗ '{value}' -> No match")


def example_2_form_processing():
    """Example 2: Processing form fields with labels."""
    print("\n" + "=" * 70)
    print("Example 2: Form Processing")
    print("=" * 70)

    engine = Engine(registry=load_registry())

    # Form field data
    form_fields = [
        {
            "label": "Social Security Number",
            "description": "Enter your 9-digit SSN",
            "value": "123-45-6789",
        },
        {
            "label": "Credit Card",
            "description": "16-digit card number",
            "value": "4532-1234-5678-9010",
        },
        {
            "label": "Email Address",
            "description": "Your contact email",
            "value": "user@example.com",
        },
    ]

    for field in form_fields:
        print(f"\nLabel: {field['label']}")
        print(f"Description: {field['description']}")

        # Create context from label
        context = ContextHint(keywords=[field["label"].lower()], strategy="loose")

        result = engine.find(field["value"], context=context)

        if result.has_matches:
            match = result.matches[0]
            print(f"Value: {field['value']} -> {match.ns_id}")
            print(f"Severity: {match.severity.value}")
        else:
            print(f"Value: {field['value']} -> No PII detected")


def example_3_category_based_filtering():
    """Example 3: Using category-based filtering."""
    print("\n" + "=" * 70)
    print("Example 3: Category-based Filtering")
    print("=" * 70)

    engine = Engine(registry=load_registry())

    # Document sections with different content types
    document_sections = [
        {
            "header": "Contact Information",
            "categories": ["email", "phone"],
            "content": "Email: user@example.com, Phone: (555) 123-4567",
        },
        {
            "header": "Payment Details",
            "categories": ["credit_card", "bank"],
            "content": "Card: 4532-1234-5678-9010",
        },
        {
            "header": "Personal Information",
            "categories": ["ssn", "passport"],
            "content": "SSN: 123-45-6789, Passport: 123456789",
        },
    ]

    for section in document_sections:
        print(f"\nSection: {section['header']}")
        print(f"Categories to check: {section['categories']}")

        context = ContextHint(categories=section["categories"], strategy="strict")

        result = engine.find(section["content"], context=context)

        print(f"Content: {section['content']}")
        print(f"Matches found: {len(result.matches)}")

        for match in result.matches:
            matched_text = section["content"][match.start : match.end]
            print(f"  - {matched_text} -> {match.ns_id} ({match.category.value})")


def example_4_explicit_pattern_ids():
    """Example 4: Using explicit pattern IDs."""
    print("\n" + "=" * 70)
    print("Example 4: Explicit Pattern IDs")
    print("=" * 70)

    engine = Engine(registry=load_registry())

    # Only check specific patterns
    context = ContextHint(pattern_ids=["us/ssn_01", "us/zipcode_01"], strategy="strict")

    test_data = [
        "SSN: 123-45-6789",
        "ZIP: 90210",
        "Email: user@example.com",  # Won't match - email pattern not included
        "Phone: (555) 123-4567",  # Won't match - phone pattern not included
    ]

    print("Only checking patterns: us/ssn_01, us/zipcode_01")

    for text in test_data:
        result = engine.find(text, context=context)

        if result.has_matches:
            match = result.matches[0]
            print(f"✓ '{text}' -> {match.ns_id}")
        else:
            print(f"✗ '{text}' -> No match (pattern not in filter list)")


def example_5_performance_comparison():
    """Example 5: Performance comparison with/without context filtering."""
    print("\n" + "=" * 70)
    print("Example 5: Performance Comparison")
    print("=" * 70)

    import time

    engine = Engine(registry=load_registry())

    text = "My SSN is 123-45-6789 and my zip code is 90210"

    # Without context filtering (checks all 61 patterns)
    start = time.time()
    for _ in range(100):
        engine.find(text)
    elapsed_no_context = time.time() - start

    # With context filtering (checks only ~5 relevant patterns)
    context = ContextHint(keywords=["ssn", "zip"], strategy="strict")
    start = time.time()
    for _ in range(100):
        engine.find(text, context=context)
    elapsed_with_context = time.time() - start

    print(f"Text: '{text}'")
    print(f"\nWithout context filtering (all patterns): {elapsed_no_context:.4f}s")
    print(f"With context filtering (filtered): {elapsed_with_context:.4f}s")
    print(f"Speedup: {elapsed_no_context / elapsed_with_context:.2f}x faster")


def example_6_redaction_with_context():
    """Example 6: Using context filtering with redaction."""
    print("\n" + "=" * 70)
    print("Example 6: Redaction with Context Filtering")
    print("=" * 70)

    engine = Engine(registry=load_registry())

    # Database export with column metadata
    data = {
        "user_id": "12345",
        "user_ssn": "123-45-6789",
        "billing_address_zip": "90210",
        "contact_email": "user@example.com",
    }

    print("Original data:")
    for field, value in data.items():
        print(f"  {field}: {value}")

    print("\nRedacted data:")
    redacted_data = {}

    for field, value in data.items():
        # Create context from field name
        context = create_context_from_field_name(field, strategy="loose")

        # Redact with context filtering
        redaction_result = engine.redact(str(value), context=context)

        redacted_data[field] = redaction_result.redacted_text
        print(f"  {field}: {redaction_result.redacted_text}")


def example_7_korean_patterns():
    """Example 7: Korean-specific patterns with context."""
    print("\n" + "=" * 70)
    print("Example 7: Korean Patterns with Context")
    print("=" * 70)

    engine = Engine(registry=load_registry())

    # Korean data with field names
    korean_data = [
        {
            "field": "주민등록번호",  # RRN
            "value": "990101-1234567",
            "keywords": ["주민번호", "rrn"],
        },
        {
            "field": "계좌번호",  # Bank account
            "value": "123-456789-01234",
            "keywords": ["계좌", "bank_account"],
        },
        {"field": "우편번호", "value": "06234", "keywords": ["우편번호", "postal"]},  # Zipcode
    ]

    for item in korean_data:
        print(f"\nField: {item['field']}")

        context = ContextHint(keywords=item["keywords"], strategy="strict")

        result = engine.find(item["value"], context=context)

        if result.has_matches:
            match = result.matches[0]
            print(f"Value: {item['value']}")
            print(f"Matched: {match.ns_id} ({match.category.value})")
        else:
            print(f"Value: {item['value']} -> No match")


def example_8_wildcard_patterns():
    """Example 8: Using wildcard patterns in context."""
    print("\n" + "=" * 70)
    print("Example 8: Wildcard Pattern Matching")
    print("=" * 70)

    engine = Engine(registry=load_registry())

    # Use wildcard to match all Korean bank account patterns
    context = ContextHint(
        pattern_ids=["kr/bank_account_*"], strategy="strict"  # Matches all bank_account patterns
    )

    bank_accounts = [
        "123-456789-01234",  # 13-digit
        "123-45-678901-2",  # 12-digit (Daegu)
        "12-345678-90",  # 10-digit (Jeju)
    ]

    print("Checking with wildcard: kr/bank_account_*")

    for account in bank_accounts:
        result = engine.find(account, context=context)

        if result.has_matches:
            match = result.matches[0]
            print(f"✓ '{account}' -> {match.ns_id}")
        else:
            print(f"✗ '{account}' -> No match")


if __name__ == "__main__":
    example_1_database_column_scanning()
    example_2_form_processing()
    example_3_category_based_filtering()
    example_4_explicit_pattern_ids()
    example_5_performance_comparison()
    example_6_redaction_with_context()
    example_7_korean_patterns()
    example_8_wildcard_patterns()

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)
