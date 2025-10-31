#!/usr/bin/env python3
"""
Comprehensive demonstration of fake data generation capabilities.

This script demonstrates:
1. Generating fake data from specific patterns
2. Creating various file formats (CSV, JSON, SQLite, XML, logs, text)
3. Creating Office files (Word, Excel, PowerPoint)
4. Creating images with embedded text/PII
5. Integration with the detector (generate → detect pipeline)
"""

import tempfile
from pathlib import Path

from datadetector import (
    Engine,
    FakeDataGenerator,
    ImageGenerator,
    OfficeFileGenerator,
    PDFGenerator,
    XMLGenerator,
    load_registry,
)


def demo_pattern_generation():
    """Demonstrate generating data from specific patterns."""
    print("=" * 80)
    print("DEMO 1: Pattern-Based Generation")
    print("=" * 80)

    generator = FakeDataGenerator(seed=12345)

    print("\n1. Email addresses:")
    for _ in range(3):
        print(f"   - {generator.from_pattern('comm/email_01')}")

    print("\n2. US Social Security Numbers:")
    for _ in range(3):
        print(f"   - {generator.from_pattern('us/ssn_01')}")

    print("\n3. Korean Mobile Numbers:")
    for _ in range(3):
        print(f"   - {generator.from_pattern('kr/mobile_01')}")

    print("\n4. Credit Card Numbers:")
    visa = generator.from_pattern("comm/credit_card_visa_01")
    mastercard = generator.from_pattern("comm/credit_card_mastercard_01")
    print(f"   - Visa: {visa}")
    print(f"   - Mastercard: {mastercard}")

    print("\n5. API Tokens:")
    print(f"   - AWS Access Key: {generator.from_pattern('comm/aws_access_key_01')}")
    print(f"   - GitHub Token: {generator.from_pattern('comm/github_token_01')}")
    print(f"   - Google API Key: {generator.from_pattern('comm/google_api_key_01')}")

    print("\n6. IP Addresses:")
    print(f"   - IPv4: {generator.from_pattern('comm/ipv4_01')}")
    print(f"   - IPv6: {generator.from_pattern('comm/ipv6_01')}")

    print("\n7. Coordinates:")
    print(f"   - Latitude: {generator.from_pattern('comm/latitude_01')}")
    print(f"   - Longitude: {generator.from_pattern('comm/longitude_01')}")

    print(f"\n✓ Total supported patterns: {len(generator.supported_patterns())}")


def demo_file_generation():
    """Demonstrate generating various file formats."""
    print("\n" + "=" * 80)
    print("DEMO 2: File Format Generation")
    print("=" * 80)

    generator = FakeDataGenerator(seed=12345)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # CSV file
        print("\n1. Creating CSV file...")
        csv_path = tmpdir / "users.csv"
        generator.create_csv_file(csv_path, rows=100, include_pii=True)
        print(f"   ✓ Created: {csv_path.name} ({csv_path.stat().st_size:,} bytes)")
        print(f"     Contains: 100 rows with name, email, phone, SSN, credit card, etc.")

        # JSON file
        print("\n2. Creating JSON file...")
        json_path = tmpdir / "users.json"
        generator.create_json_file(json_path, records=50, include_pii=True)
        print(f"   ✓ Created: {json_path.name} ({json_path.stat().st_size:,} bytes)")
        print(f"     Contains: 50 user records with structured data")

        # SQLite database
        print("\n3. Creating SQLite database...")
        db_path = tmpdir / "users.db"
        generator.create_sqlite_file(db_path, records=200, include_pii=True)
        print(f"   ✓ Created: {db_path.name} ({db_path.stat().st_size:,} bytes)")
        print(f"     Contains: 200 records in 'users' table")

        # XML file
        print("\n4. Creating XML file...")
        xml_gen = XMLGenerator(generator)
        xml_path = tmpdir / "users.xml"
        xml_gen.create_xml_file(xml_path, records=50, include_pii=True)
        print(f"   ✓ Created: {xml_path.name} ({xml_path.stat().st_size:,} bytes)")
        print(f"     Contains: 50 user records in XML format")

        # Log files
        print("\n5. Creating log files...")
        for log_format in ["apache", "json", "syslog"]:
            log_path = tmpdir / f"application.{log_format}.log"
            generator.create_log_file(
                log_path, lines=1000, include_pii=True, log_format=log_format
            )
            print(f"   ✓ Created: {log_path.name} ({log_path.stat().st_size:,} bytes)")

        # Text file
        print("\n6. Creating text file...")
        text_path = tmpdir / "document.txt"
        generator.create_text_file(text_path, paragraphs=20, include_pii=True)
        print(f"   ✓ Created: {text_path.name} ({text_path.stat().st_size:,} bytes)")
        print(f"     Contains: 20 paragraphs with embedded PII")


def demo_office_files():
    """Demonstrate generating Office files."""
    print("\n" + "=" * 80)
    print("DEMO 3: Office File Generation")
    print("=" * 80)

    try:
        generator = FakeDataGenerator(seed=12345)
        office_gen = OfficeFileGenerator(generator)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Word document
            print("\n1. Creating Word document...")
            word_path = tmpdir / "document.docx"
            office_gen.create_word_file(word_path, paragraphs=10, include_pii=True)
            print(f"   ✓ Created: {word_path.name} ({word_path.stat().st_size:,} bytes)")
            print(f"     Contains: 10 paragraphs with tables of PII data")

            # Excel spreadsheet
            print("\n2. Creating Excel spreadsheet...")
            excel_path = tmpdir / "users.xlsx"
            office_gen.create_excel_file(excel_path, rows=500, include_pii=True)
            print(
                f"   ✓ Created: {excel_path.name} ({excel_path.stat().st_size:,} bytes)"
            )
            print(f"     Contains: 500 rows with styled headers and PII columns")

            # PowerPoint presentation
            print("\n3. Creating PowerPoint presentation...")
            ppt_path = tmpdir / "presentation.pptx"
            office_gen.create_powerpoint_file(ppt_path, slides=10, include_pii=True)
            print(f"   ✓ Created: {ppt_path.name} ({ppt_path.stat().st_size:,} bytes)")
            print(f"     Contains: Title slide + 10 content slides with PII")

            # PDF documents
            print("\n4. Creating PDF document...")
            try:
                pdf_gen = PDFGenerator(generator)
                pdf_path = tmpdir / "document.pdf"
                pdf_gen.create_pdf_file(pdf_path, pages=5, include_pii=True)
                print(f"   ✓ Created: {pdf_path.name} ({pdf_path.stat().st_size:,} bytes)")
                print(f"     Contains: 5 pages with tables and PII")

                # PDF invoice
                print("\n5. Creating PDF invoice...")
                invoice_path = tmpdir / "invoice.pdf"
                pdf_gen.create_pdf_invoice(invoice_path, include_pii=True)
                print(f"   ✓ Created: {invoice_path.name} ({invoice_path.stat().st_size:,} bytes)")
                print(f"     Contains: Professional invoice with line items and PII")
            except ImportError:
                print("\n   ⚠ PDF generation requires reportlab:")
                print("      pip install reportlab")

    except ImportError as e:
        print(f"\n⚠ Office file generation requires additional packages:")
        print(f"   pip install python-docx openpyxl python-pptx")
        print(f"\n   Error: {e}")


def demo_image_generation():
    """Demonstrate generating images with embedded text."""
    print("\n" + "=" * 80)
    print("DEMO 4: Image Generation")
    print("=" * 80)

    try:
        generator = FakeDataGenerator(seed=12345)
        img_gen = ImageGenerator(generator)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Basic image with text
            print("\n1. Creating image with embedded text...")
            img_path = tmpdir / "document.png"
            img_gen.create_image_with_text(
                img_path, width=800, height=600, include_pii=True, format="PNG"
            )
            print(f"   ✓ Created: {img_path.name} ({img_path.stat().st_size:,} bytes)")
            print(f"     Size: 800x600, Format: PNG")
            print(f"     Contains: Name, email, phone, SSN, credit card, etc.")

            # Screenshot-like image
            print("\n2. Creating screenshot-like image...")
            screenshot_path = tmpdir / "config_screenshot.png"
            img_gen.create_screenshot_like_image(screenshot_path, include_pii=True)
            print(
                f"   ✓ Created: {screenshot_path.name} ({screenshot_path.stat().st_size:,} bytes)"
            )
            print(f"     Size: 1200x800, looks like terminal/editor")
            print(f"     Contains: Username, email, API keys, passwords")

            # JPEG format
            print("\n3. Creating JPEG image...")
            jpg_path = tmpdir / "document.jpg"
            img_gen.create_image_with_text(
                jpg_path, width=1920, height=1080, include_pii=True, format="JPEG"
            )
            print(f"   ✓ Created: {jpg_path.name} ({jpg_path.stat().st_size:,} bytes)")
            print(f"     Size: 1920x1080, Format: JPEG")

    except ImportError as e:
        print(f"\n⚠ Image generation requires Pillow:")
        print(f"   pip install Pillow")
        print(f"\n   Error: {e}")


def demo_generate_and_detect():
    """Demonstrate the generate → detect pipeline."""
    print("\n" + "=" * 80)
    print("DEMO 5: Generate → Detect Pipeline")
    print("=" * 80)

    generator = FakeDataGenerator(seed=12345)
    registry = load_registry()
    engine = Engine(registry)

    print("\n1. Generate fake CSV data...")
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "test.csv"
        generator.create_csv_file(csv_path, rows=10, include_pii=True)

        # Read CSV content
        with open(csv_path, "r", encoding="utf-8") as f:
            content = f.read()

        print(f"   ✓ Generated CSV with 10 rows")
        print(f"   File size: {len(content):,} bytes")

        # Detect PII
        print("\n2. Detect PII in generated data...")
        result = engine.find(content)

        print(f"   ✓ Found {len(result.matches)} PII matches:")
        print(f"     - Emails: {sum(1 for m in result.matches if m.category.value == 'email')}")
        print(f"     - Phone numbers: {sum(1 for m in result.matches if m.category.value == 'phone')}")
        print(f"     - SSNs: {sum(1 for m in result.matches if m.category.value == 'national_id')}")
        print(f"     - Credit cards: {sum(1 for m in result.matches if m.category.value == 'credit_card')}")
        print(f"     - IP addresses: {sum(1 for m in result.matches if m.category.value == 'ip_address')}")

        # Redact PII
        print("\n3. Redact PII from data...")
        redacted_result = engine.redact(content)
        print(f"   ✓ Redacted {redacted_result.redaction_count} PII items")
        print(f"   Original size: {len(content):,} bytes")
        print(f"   Redacted size: {len(redacted_result.redacted_text):,} bytes")

    print("\n4. Validate generated patterns...")
    test_cases = [
        ("comm/email_01", generator.from_pattern("comm/email_01")),
        ("us/ssn_01", generator.from_pattern("us/ssn_01")),
        ("kr/mobile_01", generator.from_pattern("kr/mobile_01")),
        ("comm/aws_access_key_01", generator.from_pattern("comm/aws_access_key_01")),
    ]

    all_valid = True
    for pattern_id, value in test_cases:
        result = engine.validate(value, pattern_id)
        status = "✓" if result.is_valid else "✗"
        print(f"   {status} {pattern_id}: {value[:30]}...")
        if not result.is_valid:
            all_valid = False

    if all_valid:
        print("\n   ✓ All generated patterns validated successfully!")


def demo_text_generation():
    """Demonstrate generating text with embedded PII."""
    print("\n" + "=" * 80)
    print("DEMO 6: Text Generation with PII")
    print("=" * 80)

    generator = FakeDataGenerator(seed=12345)

    print("\n1. Generate text with all PII types:")
    text = generator.generate_text_with_pii(num_records=3)
    print("\n" + "-" * 80)
    print(text[:500] + "...")
    print("-" * 80)

    print("\n2. Generate text with specific patterns:")
    text = generator.generate_text_with_pii(
        num_records=2, include_patterns=["us/ssn_01", "comm/credit_card_visa_01"]
    )
    print("\n" + "-" * 80)
    print(text)
    print("-" * 80)


def main():
    """Run all demonstrations."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "FAKE DATA GENERATOR DEMONSTRATION" + " " * 25 + "║")
    print("╚" + "=" * 78 + "╝")

    try:
        demo_pattern_generation()
        demo_text_generation()
        demo_file_generation()
        demo_office_files()
        demo_image_generation()
        demo_generate_and_detect()

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print("\nThe FakeDataGenerator provides comprehensive capabilities:")
        print("  ✓ 20+ pattern types (emails, phones, SSNs, tokens, IPs, etc.)")
        print("  ✓ Multiple file formats (CSV, JSON, SQLite, XML, logs, text)")
        print("  ✓ Office documents (Word, Excel, PowerPoint, PDF)")
        print("  ✓ Images with embedded text/PII (PNG, JPEG)")
        print("  ✓ PDF documents and invoices")
        print("  ✓ Configurable PII inclusion")
        print("  ✓ Reproducible with seed parameter")
        print("  ✓ Full integration with detector engine")
        print("\nFor more information, see:")
        print("  - src/datadetector/fake_generator.py")
        print("  - src/datadetector/fake_file_generators.py")
        print("  - tests/test_fake_generator.py")
        print("  - tests/test_fake_file_generators.py")
        print("\n" + "=" * 80)
        print("✓ All demonstrations completed successfully!")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n✗ Error during demonstration: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
