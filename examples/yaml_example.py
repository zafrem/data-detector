#!/usr/bin/env python3
"""
Clean example demonstrating YAML utilities for pattern file management.

This example uses utility functions to demonstrate YAML pattern management
without cluttering the current directory with temporary files.
"""

from yaml_utils import YAMLPatternManager, run_all_examples


def demonstrate_yaml_utilities():
    """Demonstrate YAML utilities with clean output."""
    print("\n" + "=" * 60)
    print("YAML Pattern Management - Clean Examples")
    print("=" * 60)

    # Use the utility manager
    manager = YAMLPatternManager()

    try:
        # Example 1: Create pattern file
        print("\n📝 Creating Pattern File")
        result = manager.create_pattern_file()
        print(f"   ✅ Created file with {result['pattern_count']} patterns")
        print(f"   📁 Namespace: {result['namespace']}")
        print(f"   📄 Description: {result['description']}")

        # Example 2: Add pattern
        print("\n➕ Adding New Pattern")
        result = manager.add_pattern()
        print(f"   ✅ Added '{result['added_pattern']}'")
        print(f"   📊 Total patterns: {result['total_patterns']}")
        print(f"   📋 Pattern IDs: {', '.join(result['pattern_ids'])}")

        # Example 3: Update pattern
        print("\n✏️  Updating Pattern")
        result = manager.update_pattern()
        if result["success"]:
            print(f"   ✅ Updated '{result['pattern_id']}'")
            print(f"   🔄 Severity: {result['old_severity']} → {result['new_severity']}")
            print(f"   🔄 Action: redact → {result['new_action']}")

        # Example 4: Query patterns
        print("\n🔍 Querying Patterns")
        patterns = manager.query_patterns()
        print(f"   📊 Found {len(patterns)} patterns:")
        for pattern in patterns:
            print(f"   • {pattern['id']} ({pattern['category']}) - {pattern['severity']}")

        # Example 5: Test with engine
        print("\n🚀 Testing with Detection Engine")
        result = manager.test_with_engine()
        print(f"   ✅ Loaded {result['registry_size']} patterns")
        print(f"   🔍 Found {result['match_count']} matches in {result['text_length']} chars")
        print(f"   🔒 Made {result['redaction_count']} redactions")

        print("\n   Detected patterns:")
        for match in result["matches"]:
            print(f"   • {match['pattern_id']} ({match['category']}) at {match['position']}")

        # Example 6: Remove pattern
        print("\n🗑️  Removing Pattern")
        result = manager.remove_pattern()
        if result["success"]:
            print(f"   ✅ Removed '{result['removed_pattern']}'")
            print(f"   📋 Remaining: {', '.join(result['remaining_patterns'])}")

        # Example 7: Backup and restore
        print("\n💾 Backup and Restore")
        result = manager.backup_and_restore()
        print("   ✅ Created backup")
        print(f"   ➕ Added temp pattern: {result['temp_pattern_added']}")
        print("   🔄 Restored from backup")
        print(f"   ✅ Temp pattern removed: {result['temp_pattern_removed']}")

        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)

    finally:
        # Clean up
        print("\n🧹 Cleaning up temporary files...")
        cleaned = manager.cleanup()
        for file_path in cleaned:
            print(f"   ✅ Cleaned: {file_path}")


def demonstrate_batch_processing():
    """Demonstrate running all examples in batch mode."""
    print("\n" + "=" * 60)
    print("Batch Processing Example")
    print("=" * 60)

    print("🚀 Running all examples in batch mode...")
    results = run_all_examples()

    print("\n📊 Summary:")
    print(f"   • Created file with {results['create_file']['pattern_count']} patterns")
    print(f"   • Added {results['add_pattern']['added_pattern']}")
    print(f"   • Updated {results['update_pattern']['pattern_id']}")
    print(f"   • Queried {len(results['query_patterns'])} patterns")
    print(f"   • Engine found {results['engine_test']['match_count']} matches")
    print(f"   • Removed {results['remove_pattern']['removed_pattern']}")
    print(f"   • Backup/restore: {results['backup_restore']['temp_pattern_removed']}")
    print(f"   • Cleaned up {len(results['cleanup'])} files")


def main():
    """Run examples."""
    print("Choose an example to run:")
    print("1. Interactive demonstration")
    print("2. Batch processing")
    print("3. Both")

    choice = input("\nEnter choice (1-3) or press Enter for option 1: ").strip()

    if choice == "2":
        demonstrate_batch_processing()
    elif choice == "3":
        demonstrate_yaml_utilities()
        demonstrate_batch_processing()
    else:
        demonstrate_yaml_utilities()


if __name__ == "__main__":
    main()
