#!/usr/bin/env python3
"""
Script to restore tokens.yml patterns to their original format.
This changes the Stripe-like pattern back to actual Stripe API key patterns.
"""

import re

def restore_tokens_yml(file_path='patterns/tokens.yml'):
    """Restore the original Stripe pattern in tokens.yml"""

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

    # Real Stripe pattern
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
        - "sk_test_51HqJ4KIr8RzN3M2P3vVh4Lq5"
        - "sk_live_51HqJ4KIr8RzN3M2P3vVh4Lq5"
        - "pk_test_51HqJ4KIr8RzN3M2P3vVh4Lq5"
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
                new_lines.append('        - "sk_test_51HqJ4KIr8RzN3M2P3vVh4Lq5"')
                new_lines.append('        - "sk_live_51HqJ4KIr8RzN3M2P3vVh4Lq5"')
                new_lines.append('        - "pk_test_51HqJ4KIr8RzN3M2P3vVh4Lq5"')
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

    # Write the restored content back
    with open(file_path, 'w') as f:
        f.write(content)

    print(f"✓ Restored {file_path}")
    print("\nChanges made:")
    print("  - Stripe pattern: rk_(live|test)_ → [sp]k_(live|test)_")
    print("  - Description updated to reflect real Stripe API keys")
    print("  - Examples updated with realistic Stripe key format")
    print("  - Provider changed from 'Example (Stripe-like pattern)' to 'Stripe'")

if __name__ == '__main__':
    restore_tokens_yml()
