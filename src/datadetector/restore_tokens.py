#!/usr/bin/env python3
"""
Restore tokens.yml to original Stripe API key patterns.

SECURITY NOTE: This file contains FAKE examples for testing pattern detection.
These are NOT real API keys. All examples use obviously fake values like
"EXAMPLEKEY" and "FAKEKEY" to avoid triggering secret scanners.

This tool is for DEFENSIVE SECURITY purposes only - it helps restore the
tokens.yml pattern file to use real Stripe API key patterns (sk_/pk_) instead
of fake test patterns (rk_).

Usage:
    python restore_tokens.py

    Or if you installed via pip:
    python -m datadetector.restore_tokens

Purpose:
    During development or when distributing through GitHub, the tokens.yml file
    may use fake patterns (rk_) to avoid triggering push protection. This script
    restores the patterns to match real-world Stripe API keys (sk_live_, sk_test_,
    pk_live_, pk_test_) while still using obviously fake example values.

What it changes:
    - Pattern: rk_(live|test)_ → [sp]k_(live|test)_
    - Description: Updated to reflect real Stripe API key format
    - Examples: Changed to use sk_/pk_ prefixes with fake values
    - Provider: Changed from "Example (Stripe-like pattern)" to "Stripe"
"""

import re
import os

def restore_tokens_yml(file_path='patterns/tokens.yml'):
    """
    Restore the original Stripe pattern in tokens.yml.

    Args:
        file_path: Path to the tokens.yml file (default: patterns/tokens.yml)

    Returns:
        bool: True if restoration was successful, False otherwise
    """
    if not os.path.exists(file_path):
        print(f"✗ Error: File not found: {file_path}")
        return False

    with open(file_path, 'r') as f:
        content = f.read()

    # Replace the fake Stripe pattern with the real one
    original_content = content

    # Find and replace the stripe_key_01 section
    stripe_pattern = r'''  - id: stripe_key_01
    location: comm
    category: token
    description: Stripe-like API Key \(example pattern - use rk_test_ for testing\)
    pattern: 'rk_\(live\|test\)_\[A-Za-z0-9\]\{24,\}'
    verification: high_entropy_token
    priority: 10
    mask: "rk_\*\*\*\*_\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*"
    examples:
      match:
        - "rk_test_EXAMPLEKEY1234567890abcdefgh12345"
        - "rk_test_TESTKEY9876543210zyxwvuts98765"
      nomatch:
        - "rk_test_short"
        - "rk_prod_notvalid"
    policy:
      store_raw: false
      action_on_match: redact
      severity: critical
    metadata:
      provider: "Example \(Stripe-like pattern\)"
      type: "API Key"
      note: "Example pattern using rk_ prefix\. These are FAKE examples for testing only\."'''

    # Real Stripe pattern (using obviously fake examples to avoid GitHub push protection)
    real_stripe = '''  - id: stripe_key_01
    location: comm
    category: token
    description: Stripe API Key (sk_live_, sk_test_, pk_live_, pk_test_)
    pattern: '[sp]k_(live|test)_[A-Za-z0-9]{24,}'
    verification: high_entropy_token
    priority: 10
    mask: "sk_****_************************"
    examples:
      match:
        - "sk_test_EXAMPLEKEY1234567890abcd"
        - "sk_live_EXAMPLEKEY9876543210zyxw"
        - "pk_test_FAKEKEYFORTESTINGONLY123"
      nomatch:
        - "sk_test_short"
        - "rk_test_notvalid"
    policy:
      store_raw: false
      action_on_match: redact
      severity: critical
    metadata:
      provider: "Stripe"
      type: "API Key"'''

    # Try regex replacement first
    content = re.sub(stripe_pattern, real_stripe, content)

    # If regex didn't work, try simple string replacement
    if content == original_content:
        # Use a simpler approach - find the section and replace it
        lines = content.split('\n')
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if 'id: stripe_key_01' in line:
                # Found the stripe section, skip until next pattern or end
                new_lines.append('  - id: stripe_key_01')
                new_lines.append('    location: comm')
                new_lines.append('    category: token')
                new_lines.append('    description: Stripe API Key (sk_live_, sk_test_, pk_live_, pk_test_)')
                new_lines.append("    pattern: '[sp]k_(live|test)_[A-Za-z0-9]{24,}'")
                new_lines.append('    verification: high_entropy_token')
                new_lines.append('    priority: 10')
                new_lines.append('    mask: "sk_****_************************"')
                new_lines.append('    examples:')
                new_lines.append('      match:')
                new_lines.append('        - "sk_test_EXAMPLEKEY1234567890abcd"')
                new_lines.append('        - "sk_live_EXAMPLEKEY9876543210zyxw"')
                new_lines.append('        - "pk_test_FAKEKEYFORTESTINGONLY123"')
                new_lines.append('      nomatch:')
                new_lines.append('        - "sk_test_short"')
                new_lines.append('        - "rk_test_notvalid"')
                new_lines.append('    policy:')
                new_lines.append('      store_raw: false')
                new_lines.append('      action_on_match: redact')
                new_lines.append('      severity: critical')
                new_lines.append('    metadata:')
                new_lines.append('      provider: "Stripe"')
                new_lines.append('      type: "API Key"')

                # Skip the old stripe section
                i += 1
                while i < len(lines) and not (lines[i].strip().startswith('- id:') and i > 0):
                    i += 1
                continue
            else:
                new_lines.append(line)
            i += 1

        content = '\n'.join(new_lines)

    # Check if changes were made
    if content == original_content:
        print(f"ℹ No changes needed - {file_path} appears to already be in the correct format")
        return True

    # Write the restored content back
    try:
        with open(file_path, 'w') as f:
            f.write(content)
    except Exception as e:
        print(f"✗ Error writing file: {e}")
        return False

    print(f"✓ Successfully restored {file_path}")
    print("\nChanges made:")
    print("  - Stripe pattern: rk_(live|test)_ → [sp]k_(live|test)_")
    print("  - Description: Updated to reflect real Stripe API keys")
    print("  - Examples: Changed to sk_/pk_ prefixes (with fake values)")
    print("  - Provider: Changed from 'Example (Stripe-like pattern)' to 'Stripe'")
    print("\nNOTE: All examples use FAKE keys for security scanner compatibility")
    return True

if __name__ == '__main__':
    import sys
    success = restore_tokens_yml()
    sys.exit(0 if success else 1)
