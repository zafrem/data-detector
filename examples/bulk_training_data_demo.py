#!/usr/bin/env python3
"""
Demonstration of bulk training data generation.

This script shows how to generate large volumes of labeled training data
for machine learning models and testing purposes.

Note: This example creates files in a temporary directory to avoid
cluttering your current working directory.
"""

import json
import os
import tempfile
from pathlib import Path

from datadetector import BulkDataGenerator

# Create temporary directory for examples
TEMP_DIR = tempfile.mkdtemp()
print(f"Files will be created in: {TEMP_DIR}")


def demo_basic_usage():
    """Demonstrate basic bulk data generation."""
    print("=" * 80)
    print("DEMO 1: Basic Labeled Record Generation")
    print("=" * 80)

    bulk_gen = BulkDataGenerator(seed=12345)

    # Generate a single labeled record
    print("\n1. Generating a single labeled record:")
    record = bulk_gen.generate_labeled_record(num_pii_items=3)

    print(f"\n   Text: {record['text'][:100]}...")
    print(f"\n   PII Items found: {record['metadata']['num_pii_items']}")
    for item in record['pii_items']:
        print(f"     - {item['pattern_id']}: {item['value']}")

    print(f"\n   Metadata:")
    print(f"     - Text length: {record['metadata']['text_length']}")
    print(f"     - Patterns used: {', '.join(record['metadata']['patterns_used'])}")


def demo_bulk_jsonl():
    """Demonstrate JSONL format generation."""
    print("\n" + "=" * 80)
    print("DEMO 2: Bulk JSONL Generation")
    print("=" * 80)

    bulk_gen = BulkDataGenerator(seed=12345)

    print("\n1. Generating 1000 labeled records in JSONL format...")
    output_path = Path(TEMP_DIR) / "training_data.jsonl"
    bulk_gen.save_bulk_data_jsonl(
        output_path,
        num_records=1000,
        patterns_per_record=(3, 8),
    )

    # Show sample
    print("\n2. Sample record from file:")
    with open(output_path, 'r', encoding='utf-8') as f:
        sample = json.loads(f.readline())

    print(f"   Record ID: {sample['record_id']}")
    print(f"   Text: {sample['text'][:80]}...")
    print(f"   PII Items: {sample['metadata']['num_pii_items']}")

    # Show statistics
    print("\n3. File statistics:")
    file_size = output_path.stat().st_size
    print(f"   File size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
    print(f"   Records: 1000")
    print(f"   Format: JSONL (one JSON object per line)")
    
    print(f"   Use case: Streaming, line-by-line processing, ML pipelines")
    return [str(output_path)]


def demo_bulk_json():
    """Demonstrate JSON format generation."""
    print("\n" + "=" * 80)
    print("DEMO 3: Bulk JSON Generation")
    print("=" * 80)

    bulk_gen = BulkDataGenerator(seed=12345)

    print("\n1. Generating 500 labeled records in JSON format...")
    output_path = Path(TEMP_DIR) / "training_data.json"
    bulk_gen.save_bulk_data_json(
        output_path,
        num_records=500,
        patterns_per_record=(2, 6),
    )

    # Load and show metadata
    print("\n2. Dataset metadata:")
    with open(output_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"   Total records: {data['metadata']['num_records']}")
    print(f"   Total PII items: {data['metadata']['total_pii_items']}")
    print(f"   Avg PII per record: {data['metadata']['total_pii_items'] / data['metadata']['num_records']:.1f}")
    print(f"   Supported patterns: {len(data['metadata']['supported_patterns'])}")
    return [str(output_path)]


def demo_bulk_csv():
    """Demonstrate CSV format generation."""
    print("\n" + "=" * 80)
    print("DEMO 4: Bulk CSV Generation")
    print("=" * 80)

    bulk_gen = BulkDataGenerator(seed=12345)

    print("\n1. Generating 200 labeled records in CSV format...")
    output_path = Path(TEMP_DIR) / "training_data.csv"
    bulk_gen.save_bulk_data_csv(
        output_path,
        num_records=200,
        patterns_per_record=(1, 5),
    )

    # Show preview
    print("\n2. CSV preview (first row):")
    with open(output_path, 'r', encoding='utf-8') as f:
        header = f.readline().strip()
        first_row = f.readline().strip()

    print(f"   Columns: {header}")
    print(f"   First row (truncated): {first_row[:100]}...")
    return [str(output_path)]


def demo_detection_pairs():
    """Demonstrate binary classification pairs."""
    print("\n" + "=" * 80)
    print("DEMO 5: Detection Pairs (Binary Classification)")
    print("=" * 80)

    bulk_gen = BulkDataGenerator(seed=12345)

    print("\n1. Generating 1000 detection pairs (70% positive, 30% negative)...")
    pairs = bulk_gen.generate_detection_pairs(
        num_pairs=1000,
        positive_ratio=0.7,
    )

    # Show statistics
    positive = sum(1 for p in pairs if p['has_pii'])
    negative = sum(1 for p in pairs if not p['has_pii'])

    print(f"\n2. Dataset composition:")
    print(f"   Total pairs: {len(pairs)}")
    print(f"   Positive (has PII): {positive} ({positive/len(pairs)*100:.1f}%)")
    print(f"   Negative (no PII): {negative} ({negative/len(pairs)*100:.1f}%)")

    # Show samples
    print("\n3. Sample positive example:")
    pos_sample = next(p for p in pairs if p['has_pii'])
    print(f"   Text: {pos_sample['text'][:100]}...")
    print(f"   Label: {pos_sample['label']}")
    print(f"   PII count: {pos_sample['pii_count']}")
    print(f"   Patterns: {', '.join(pos_sample['patterns'][:3])}")

    print("\n4. Sample negative example:")
    neg_sample = next(p for p in pairs if not p['has_pii'])
    print(f"   Text: {neg_sample['text'][:100]}...")
    print(f"   Label: {neg_sample['label']}")
    print(f"   PII count: {neg_sample['pii_count']}")

    # Save to file
    print("\n5. Saving detection pairs...")
    jsonl_pairs_path = os.path.join(TEMP_DIR, "detection_pairs.jsonl")
    csv_pairs_path = os.path.join(TEMP_DIR, "detection_pairs.csv")
    bulk_gen.save_detection_pairs(jsonl_pairs_path, num_pairs=1000, format='jsonl')
    bulk_gen.save_detection_pairs(csv_pairs_path, num_pairs=1000, format='csv')
    return [jsonl_pairs_path, csv_pairs_path]


def demo_specific_patterns():
    """Demonstrate generation with specific patterns."""
    print("\n" + "=" * 80)
    print("DEMO 6: Generating Data with Specific Patterns")
    print("=" * 80)

    bulk_gen = BulkDataGenerator(seed=12345)

    # Generate only email and phone patterns
    print("\n1. Generating data with only emails and phones...")
    specific_patterns = ["comm/email_01", "us/phone_01", "kr/mobile_01"]

    records = bulk_gen.generate_bulk_labeled_data(
        num_records=100,
        patterns_per_record=(2, 3),
        include_patterns=specific_patterns,
    )

    # Show statistics
    stats = bulk_gen.generate_statistics(records)
    print(f"\n2. Statistics:")
    print(f"   Total records: {stats['total_records']}")
    print(f"   Total PII items: {stats['total_pii_items']}")
    print(f"   Avg PII per record: {stats['avg_pii_per_record']:.2f}")
    print(f"   Avg text length: {stats['avg_text_length']:.0f} characters")

    print(f"\n3. Pattern distribution:")
    for pattern_id, count in sorted(stats['pattern_distribution'].items(), key=lambda x: x[1], reverse=True):
        print(f"   {pattern_id}: {count} occurrences ({count/stats['total_pii_items']*100:.1f}%)")
    return []


def demo_large_scale():
    """Demonstrate large-scale generation."""
    print("\n" + "=" * 80)
    print("DEMO 7: Large-Scale Training Data Generation")
    print("=" * 80)

    bulk_gen = BulkDataGenerator(seed=12345)

    print("\n1. Generating 10,000 records (this may take a moment)...")
    output_path = Path(TEMP_DIR) / "training_data_large.jsonl"

    bulk_gen.save_bulk_data_jsonl(
        output_path,
        num_records=10000,
        patterns_per_record=(3, 10),
    )

    print(f"\n2. Large dataset created:")
    file_size = output_path.stat().st_size
    print(f"   File: {output_path}")
    print(f"   Size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
    print(f"   Records: 10,000")

    # Estimate total PII items by sampling
    print("\n3. Sampling to estimate content...")
    sample_size = 100
    total_pii = 0

    with open(output_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= sample_size:
                break
            record = json.loads(line)
            total_pii += record['metadata']['num_pii_items']

    avg_pii = total_pii / sample_size
    estimated_total = avg_pii * 10000

    print(f"   Estimated total PII items: ~{estimated_total:.0f}")
    print(f"   Avg PII per record: ~{avg_pii:.1f}")
    return [str(output_path)]


def main():
    """Run all demonstrations."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 18 + "BULK TRAINING DATA GENERATOR DEMO" + " " * 27 + "║")
    print("╚" + "=" * 78 + "╝")
    print(f"Working in temporary directory: {TEMP_DIR}")
    
    generated_files = []

    try:
        demo_basic_usage()
        generated_files.extend(demo_bulk_jsonl())
        generated_files.extend(demo_bulk_json())
        generated_files.extend(demo_bulk_csv())
        generated_files.extend(demo_detection_pairs())
        generated_files.extend(demo_specific_patterns())
        generated_files.extend(demo_large_scale())

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        
        # Calculate total size
        total_size = sum(os.path.getsize(f) for f in generated_files if os.path.exists(f))
        print(f"\n📁 Files created in: {TEMP_DIR}")
        print(f"📊 Total files: {len(generated_files)}")
        print(f"💾 Total size: {total_size / 1024 / 1024:.2f} MB")
        
        print("\n🧹 To clean up, delete the temporary directory:")
        print(f"   rm -rf {TEMP_DIR}")
        
        print("\nThe BulkDataGenerator provides:")
        print("  ✓ Labeled training data with PII and metadata")
        print("  ✓ Multiple output formats (JSONL, JSON, CSV)")
        print("  ✓ Binary classification pairs (has PII / no PII)")
        print("  ✓ Customizable pattern selection")
        print("  ✓ Scalable to millions of records")
        print("  ✓ Perfect for ML training and testing")
        print("\nOutput files created:")
        for file_path in generated_files:
            if os.path.exists(file_path):
                size_mb = os.path.getsize(file_path) / 1024 / 1024
                print(f"  - {os.path.basename(file_path)} ({size_mb:.2f} MB)")
        print("\nUse cases:")
        print("  - Training PII detection models")
        print("  - Testing detection systems at scale")
        print("  - Benchmarking performance")
        print("  - Creating labeled datasets")
        print("\n" + "=" * 80)
        print("✓ All demonstrations completed successfully!")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n✗ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
        print(f"🧹 Remember to clean up: rm -rf {TEMP_DIR}")


if __name__ == "__main__":
    main()
