#!/usr/bin/env python3
"""
Quick start example for fake data generation.

This example shows the most common use cases for generating fake data.

Note: This example creates files in a temporary directory to avoid
cluttering your current working directory.
"""

import os
import tempfile

from datadetector import (
    BulkDataGenerator,
    FakeDataGenerator,
    ImageGenerator,
    OfficeFileGenerator,
    PDFGenerator,
    XMLGenerator,
)

# Create temporary directory for examples
TEMP_DIR = tempfile.mkdtemp()
print(f"Files will be created in: {TEMP_DIR}")


def main():
    # Create generator with optional seed for reproducibility
    generator = FakeDataGenerator(seed=12345)
    generated_files = []

    print("1. Generate individual PII values:")
    print(f"   Email: {generator.from_pattern('comm/email_01')}")
    print(f"   SSN: {generator.from_pattern('us/ssn_01')}")
    print(f"   Phone (KR): {generator.from_pattern('kr/mobile_01')}")
    print(f"   AWS Key: {generator.from_pattern('comm/aws_access_key_01')}")

    print("\n2. Generate CSV file:")
    csv_path = os.path.join(TEMP_DIR, "output.csv")
    generator.create_csv_file(csv_path, rows=100, include_pii=True)
    generated_files.append(csv_path)
    print(f"   ✓ Created {os.path.basename(csv_path)} with 100 rows")

    print("\n3. Generate JSON file:")
    json_path = os.path.join(TEMP_DIR, "output.json")
    generator.create_json_file(json_path, records=50, include_pii=True)
    generated_files.append(json_path)
    print(f"   ✓ Created {os.path.basename(json_path)} with 50 records")

    print("\n4. Generate SQLite database:")
    db_path = os.path.join(TEMP_DIR, "output.db")
    generator.create_sqlite_file(db_path, records=200, include_pii=True)
    generated_files.append(db_path)
    print(f"   ✓ Created {os.path.basename(db_path)} with 200 records")

    print("\n5. Generate log file:")
    log_path = os.path.join(TEMP_DIR, "output.log")
    generator.create_log_file(log_path, lines=1000, log_format="apache")
    generated_files.append(log_path)
    print(f"   ✓ Created {os.path.basename(log_path)} with 1000 Apache-format log lines")

    print("\n6. Generate Office files:")
    try:
        office_gen = OfficeFileGenerator(generator)

        docx_path = os.path.join(TEMP_DIR, "output.docx")
        office_gen.create_word_file(docx_path, paragraphs=10)
        generated_files.append(docx_path)
        print(f"   ✓ Created {os.path.basename(docx_path)} with 10 paragraphs")

        xlsx_path = os.path.join(TEMP_DIR, "output.xlsx")
        office_gen.create_excel_file(xlsx_path, rows=500)
        generated_files.append(xlsx_path)
        print(f"   ✓ Created {os.path.basename(xlsx_path)} with 500 rows")

        pptx_path = os.path.join(TEMP_DIR, "output.pptx")
        office_gen.create_powerpoint_file(pptx_path, slides=5)
        generated_files.append(pptx_path)
        print(f"   ✓ Created {os.path.basename(pptx_path)} with 5 slides")
    except ImportError:
        print("   ⚠ Install python-docx, openpyxl, python-pptx for Office files")

    print("\n7. Generate image with text:")
    try:
        img_gen = ImageGenerator(generator)
        png_path = os.path.join(TEMP_DIR, "output.png")
        img_gen.create_image_with_text(png_path, width=800, height=600)
        generated_files.append(png_path)
        print(f"   ✓ Created {os.path.basename(png_path)} (800x600)")
    except ImportError:
        print("   ⚠ Install Pillow for image generation")

    print("\n8. Generate PDF files:")
    try:
        pdf_gen = PDFGenerator(generator)

        pdf_path = os.path.join(TEMP_DIR, "output.pdf")
        pdf_gen.create_pdf_file(pdf_path, pages=5)
        generated_files.append(pdf_path)
        print(f"   ✓ Created {os.path.basename(pdf_path)} with 5 pages")

        invoice_path = os.path.join(TEMP_DIR, "invoice.pdf")
        pdf_gen.create_pdf_invoice(invoice_path)
        generated_files.append(invoice_path)
        print(f"   ✓ Created {os.path.basename(invoice_path)}")
    except ImportError:
        print("   ⚠ Install reportlab for PDF generation")

    print("\n9. Generate XML file:")
    xml_gen = XMLGenerator(generator)
    xml_path = os.path.join(TEMP_DIR, "output.xml")
    xml_gen.create_xml_file(xml_path, records=50)
    generated_files.append(xml_path)
    print(f"   ✓ Created {os.path.basename(xml_path)} with 50 records")

    print("\n10. Generate bulk training data:")
    bulk_gen = BulkDataGenerator(seed=12345)
    jsonl_path = os.path.join(TEMP_DIR, "training_data.jsonl")
    bulk_gen.save_bulk_data_jsonl(jsonl_path, num_records=1000)
    generated_files.append(jsonl_path)
    print(f"   ✓ Created {os.path.basename(jsonl_path)} with 1000 labeled records")
    print("   Use case: ML training data with PII labels")

    print("\n✓ All files generated successfully!")
    print(f"\n📁 Files created in: {TEMP_DIR}")
    print(f"📊 Total files: {len(generated_files)}")

    # Calculate total size
    total_size = sum(os.path.getsize(f) for f in generated_files if os.path.exists(f))
    print(f"💾 Total size: {total_size / 1024 / 1024:.2f} MB")

    print("\n🧹 To clean up, delete the temporary directory:")
    print(f"   rm -rf {TEMP_DIR}")
    print("\nSee fake_data_demo.py and bulk_training_data_demo.py for more examples.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
        print(f"🧹 Remember to clean up: rm -rf {TEMP_DIR}")
