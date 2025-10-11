#!/usr/bin/env python3
"""
Example script demonstrating YAML utilities for pattern file management.

This script shows how to:
1. Create pattern files
2. Add/update/remove patterns
3. Query pattern files
4. Use patterns with the detection engine
"""

from datadetector import (
    Engine,
    PatternFileHandler,
    load_registry,
    read_yaml,
    write_yaml,
)


def example_1_create_pattern_file():
    """Example 1: Create a new pattern file from scratch."""
    print("\n" + "=" * 60)
    print("Example 1: Creating a Pattern File")
    print("=" * 60)

    # Define custom patterns
    patterns = [
        {
            "id": "api_key_01",
            "location": "custom",
            "category": "token",
            "description": "Custom API key format",
            "pattern": r"APIKEY-[A-Z0-9]{32}",
            "mask": "APIKEY-" + "*" * 32,
            "examples": {
                "match": ["APIKEY-ABC123XYZ789ABC123XYZ789ABC123"],
                "nomatch": ["APIKEY-SHORT", "API-KEY-ABC123"],
            },
            "policy": {"store_raw": False, "action_on_match": "redact", "severity": "critical"},
        },
        {
            "id": "internal_id_01",
            "location": "custom",
            "category": "other",
            "description": "Internal user ID",
            "pattern": r"USR-\d{8}",
            "mask": "USR-********",
            "policy": {"store_raw": False, "action_on_match": "redact", "severity": "medium"},
        },
    ]

    # Create the pattern file
    PatternFileHandler.create_pattern_file(
        file_path="custom_patterns.yml",
        namespace="custom",
        description="Custom patterns for our application",
        patterns=patterns,
        overwrite=True,  # Overwrite if exists
    )

    print("✅ Created custom_patterns.yml with 2 patterns")

    # Read and display
    data = read_yaml("custom_patterns.yml")
    print(f"   Namespace: {data['namespace']}")
    print(f"   Description: {data['description']}")
    print(f"   Patterns: {len(data['patterns'])}")


def example_2_add_pattern():
    """Example 2: Add a new pattern to existing file."""
    print("\n" + "=" * 60)
    print("Example 2: Adding a Pattern")
    print("=" * 60)

    new_pattern = {
        "id": "session_token_01",
        "location": "custom",
        "category": "token",
        "description": "Session token",
        "pattern": r"SESSION_[A-F0-9]{40}",
        "mask": "SESSION_" + "*" * 40,
        "policy": {"store_raw": False, "action_on_match": "redact", "severity": "high"},
    }

    PatternFileHandler.add_pattern_to_file("custom_patterns.yml", new_pattern)

    print("✅ Added session_token_01 to custom_patterns.yml")

    # List all patterns
    pattern_ids = PatternFileHandler.list_patterns_in_file("custom_patterns.yml")
    print(f"   Total patterns: {len(pattern_ids)}")
    for pid in pattern_ids:
        print(f"   - {pid}")


def example_3_update_pattern():
    """Example 3: Update an existing pattern."""
    print("\n" + "=" * 60)
    print("Example 3: Updating a Pattern")
    print("=" * 60)

    # Get current pattern
    pattern = PatternFileHandler.get_pattern_from_file("custom_patterns.yml", "api_key_01")
    print(f"Current severity: {pattern['policy']['severity']}")

    # Update severity
    success = PatternFileHandler.update_pattern_in_file(
        file_path="custom_patterns.yml",
        pattern_id="api_key_01",
        updates={"policy": {"severity": "critical", "action_on_match": "tokenize"}},
    )

    if success:
        # Get updated pattern
        updated = PatternFileHandler.get_pattern_from_file("custom_patterns.yml", "api_key_01")
        print(f"✅ Updated api_key_01")
        print(f"   New severity: {updated['policy']['severity']}")
        print(f"   New action: {updated['policy']['action_on_match']}")


def example_4_query_patterns():
    """Example 4: Query and inspect patterns."""
    print("\n" + "=" * 60)
    print("Example 4: Querying Patterns")
    print("=" * 60)

    # List all patterns
    pattern_ids = PatternFileHandler.list_patterns_in_file("custom_patterns.yml")
    print(f"Found {len(pattern_ids)} patterns:\n")

    # Get details for each
    for pid in pattern_ids:
        pattern = PatternFileHandler.get_pattern_from_file("custom_patterns.yml", pid)
        print(f"Pattern ID: {pid}")
        print(f"  Category: {pattern['category']}")
        print(f"  Description: {pattern['description']}")
        print(f"  Severity: {pattern['policy']['severity']}")
        print(f"  Regex: {pattern['pattern']}")
        print()


def example_5_use_with_engine():
    """Example 5: Use custom patterns with detection engine."""
    print("\n" + "=" * 60)
    print("Example 5: Using Patterns with Engine")
    print("=" * 60)

    # Load custom patterns (skip example validation for demo)
    registry = load_registry(
        paths=["custom_patterns.yml"], validate_schema=False, validate_examples=False
    )

    print(f"✅ Loaded {len(registry)} patterns from custom namespace")

    # Create engine
    engine = Engine(registry)

    # Test detection
    test_text = """
    Here are some sensitive items:
    - API Key: APIKEY-ABC123XYZ789ABC123XYZ789ABC123
    - User ID: USR-12345678
    - Session: SESSION_1A2B3C4D5E6F7A8B9C0D1E2F3A4B5C6D7E8F9A0B
    """

    # Find PII
    result = engine.find(test_text, namespaces=["custom"])

    print(f"\n📊 Detection Results:")
    print(f"   Text length: {len(test_text)} chars")
    print(f"   Matches found: {result.match_count}")
    print(f"   Namespaces searched: {result.namespaces_searched}")

    print(f"\n🔍 Matches:")
    for match in result.matches:
        print(f"   - {match.pattern_id} ({match.category.value})")
        print(f"     Position: {match.start}-{match.end}")
        print(f"     Severity: {match.severity.value}")

    # Redact PII
    redacted = engine.redact(test_text, namespaces=["custom"])

    print(f"\n🔒 Redacted Text:")
    print(redacted.redacted_text)
    print(f"\n   Redactions: {redacted.redaction_count}")


def example_6_remove_pattern():
    """Example 6: Remove a pattern."""
    print("\n" + "=" * 60)
    print("Example 6: Removing a Pattern")
    print("=" * 60)

    # Remove pattern
    success = PatternFileHandler.remove_pattern_from_file(
        "custom_patterns.yml", "internal_id_01"
    )

    if success:
        print("✅ Removed internal_id_01")

        # List remaining
        pattern_ids = PatternFileHandler.list_patterns_in_file("custom_patterns.yml")
        print(f"   Remaining patterns: {pattern_ids}")
    else:
        print("❌ Pattern not found")


def example_7_backup_and_restore():
    """Example 7: Backup and restore pattern files."""
    print("\n" + "=" * 60)
    print("Example 7: Backup and Restore")
    print("=" * 60)

    # Read current state
    current = read_yaml("custom_patterns.yml")

    # Create backup
    write_yaml("custom_patterns.backup.yml", current, overwrite=True)
    print("✅ Created backup: custom_patterns.backup.yml")

    # Simulate modification
    PatternFileHandler.add_pattern_to_file(
        "custom_patterns.yml",
        {
            "id": "temp_pattern_01",
            "location": "custom",
            "category": "other",
            "pattern": "temp",
            "policy": {"store_raw": False, "action_on_match": "redact", "severity": "low"},
        },
    )

    print("   Added temporary pattern")

    # Restore from backup
    backup = read_yaml("custom_patterns.backup.yml")
    write_yaml("custom_patterns.yml", backup, overwrite=True)

    print("✅ Restored from backup")


def cleanup():
    """Clean up example files."""
    import os

    files_to_remove = [
        "custom_patterns.yml",
        "custom_patterns.backup.yml",
    ]

    for file in files_to_remove:
        if os.path.exists(file):
            os.remove(file)
            print(f"🧹 Cleaned up: {file}")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("YAML Utilities - Complete Examples")
    print("=" * 60)

    try:
        example_1_create_pattern_file()
        example_2_add_pattern()
        example_3_update_pattern()
        example_4_query_patterns()
        example_5_use_with_engine()
        example_6_remove_pattern()
        example_7_backup_and_restore()

        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60 + "\n")

    finally:
        # Clean up
        print("\n" + "=" * 60)
        print("Cleanup")
        print("=" * 60)
        cleanup()


if __name__ == "__main__":
    main()
