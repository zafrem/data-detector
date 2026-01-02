#!/usr/bin/env python3
"""
Clean demonstration of file generation capabilities.

This example uses utility functions to demonstrate file generation
without cluttering the current directory with output files.
"""

from file_generators import FileGenerationManager, run_quick_demo


def demonstrate_basic_generation():
    """Demonstrate basic file generation with clean output."""
    print("\n" + "=" * 60)
    print("File Generation - Basic Demo")
    print("=" * 60)

    manager = FileGenerationManager()

    try:
        # Basic data samples
        print("\n📝 Generating Basic Data Samples")
        basic_data = manager.generate_basic_data()
        print("   ✅ Generated sample PII data:")
        for key, value in basic_data.items():
            print(f"   • {key}: {value}")

        # CSV file
        print("\n📊 Creating CSV File")
        csv_result = manager.create_csv_file(rows=50)
        print(f"   ✅ Created CSV with {csv_result['rows']} rows")
        print(f"   💾 Size: {csv_result['size_mb']:.2f} MB")

        # JSON file
        print("\n📄 Creating JSON File")
        json_result = manager.create_json_file(records=25)
        print(f"   ✅ Created JSON with {json_result['records']} records")
        print(f"   💾 Size: {json_result['size_mb']:.2f} MB")

        # XML file
        print("\n🏷️  Creating XML File")
        xml_result = manager.create_xml_file(records=25)
        print(f"   ✅ Created XML with {xml_result['records']} records")
        print(f"   💾 Size: {xml_result['size_mb']:.2f} MB")

        # Summary
        print("\n📊 Generation Summary")
        summary = manager.get_summary()
        print(f"   📁 Temp directory: {summary['temp_directory']}")
        print(f"   📈 Total files: {summary['total_files']}")
        print(f"   💾 Total size: {summary['total_size_mb']:.2f} MB")

        print("\n" + "=" * 60)
        print("✅ Basic demo completed successfully!")
        print("=" * 60)

    finally:
        print("\n🧹 Cleaning up...")
        cleaned = manager.cleanup()
        for file_path in cleaned:
            print(f"   ✅ Cleaned: {file_path}")


def demonstrate_advanced_generation():
    """Demonstrate advanced file generation capabilities."""
    print("\n" + "=" * 60)
    print("File Generation - Advanced Demo")
    print("=" * 60)

    manager = FileGenerationManager()

    try:
        # Office files
        print("\n📄 Creating Office Files")
        office_results = manager.create_office_files()
        if office_results.get("success", True):
            for file_type, result in office_results.items():
                if isinstance(result, dict) and result.get("success"):
                    size_mb = result["file_size"] / 1024 / 1024
                    print(f"   ✅ {file_type.title()}: {size_mb:.2f} MB")
        else:
            print(f"   ⚠️  {office_results.get('error', 'Unknown error')}")

        # Image file
        print("\n🖼️  Creating Image File")
        image_result = manager.create_image_file()
        if image_result["success"]:
            size_mb = image_result["file_size"] / 1024 / 1024
            print(
                f"   ✅ Image ({image_result['width']}x{image_result['height']}): {size_mb:.2f} MB"
            )
        else:
            print(f"   ⚠️  {image_result.get('error', 'Unknown error')}")

        # PDF files
        print("\n📑 Creating PDF Files")
        pdf_results = manager.create_pdf_files()
        if pdf_results.get("success", True):
            for file_type, result in pdf_results.items():
                if isinstance(result, dict) and result.get("success"):
                    size_mb = result["file_size"] / 1024 / 1024
                    print(f"   ✅ {file_type.title()}: {size_mb:.2f} MB")
        else:
            print(f"   ⚠️  {pdf_results.get('error', 'Unknown error')}")

        # Bulk training data
        print("\n🎯 Creating Bulk Training Data")
        bulk_results = manager.create_bulk_training_data()
        for format_type, result in bulk_results.items():
            size_mb = result["file_size"] / 1024 / 1024
            print(f"   ✅ {format_type.upper()}: {result['records']} records, {size_mb:.2f} MB")

        # Summary
        print("\n📊 Generation Summary")
        summary = manager.get_summary()
        print(f"   📁 Temp directory: {summary['temp_directory']}")
        print(f"   📈 Total files: {summary['total_files']}")
        print(f"   💾 Total size: {summary['total_size_mb']:.2f} MB")

        print("\n" + "=" * 60)
        print("✅ Advanced demo completed successfully!")
        print("=" * 60)

    finally:
        print("\n🧹 Cleaning up...")
        cleaned = manager.cleanup()
        print(f"   ✅ Cleaned up {len(cleaned)} items")


def demonstrate_batch_processing():
    """Demonstrate batch processing capabilities."""
    print("\n" + "=" * 60)
    print("Batch Processing Demo")
    print("=" * 60)

    print("🚀 Running quick demo...")
    quick_results = run_quick_demo()

    print("\n📊 Quick Demo Results:")
    print(f"   • Basic data: {len(quick_results['basic_data'])} samples")
    print(f"   • CSV: {quick_results['csv']['rows']} rows")
    print(f"   • JSON: {quick_results['json']['records']} records")
    print(f"   • XML: {quick_results['xml']['records']} records")
    print(f"   • Total size: {quick_results['summary']['total_size_mb']:.2f} MB")
    print(f"   • Cleaned up: {len(quick_results['cleanup'])} items")


def main():
    """Run file generation examples."""
    print("Choose a demo to run:")
    print("1. Basic file generation")
    print("2. Advanced file generation")
    print("3. Batch processing")
    print("4. All demos")

    choice = input("\nEnter choice (1-4) or press Enter for option 1: ").strip()

    if choice == "2":
        demonstrate_advanced_generation()
    elif choice == "3":
        demonstrate_batch_processing()
    elif choice == "4":
        demonstrate_basic_generation()
        demonstrate_advanced_generation()
        demonstrate_batch_processing()
    else:
        demonstrate_basic_generation()


if __name__ == "__main__":
    main()
