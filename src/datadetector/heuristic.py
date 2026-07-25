"""Heuristic filter to exclude well-known placeholder and test data.

Matches that look like synthetic/example data are filtered out to reduce
false positives. This complements the per-pattern ``verification`` functions
with a cross-cutting check that applies to *all* matches.
"""

import re
from typing import FrozenSet

# ---------------------------------------------------------------------------
# Well-known placeholder values (normalised: digits only or lowercased)
# ---------------------------------------------------------------------------

# Phone numbers commonly used as examples / placeholders
_PLACEHOLDER_PHONES: FrozenSet[str] = frozenset(
    {
        "01012345678",
        "01011111111",
        "01022222222",
        "01000000000",
        "01099999999",
        "01001010101",
        "0101234567",
        "0212345678",
        "0311234567",
        "15771577",
        "1234567890",
        "0000000000",
        "1111111111",
        "9999999999",
        # US placeholder
        "5551234567",
        "15551234567",
        "2025551234",
    }
)

# SSN / ID placeholders
_PLACEHOLDER_IDS: FrozenSet[str] = frozenset(
    {
        "000000000",
        "123456789",
        "111111111",
        "999999999",
        # Korean RRN examples
        "0000001234567",
        "9001011234567",
        "1234561234567",
        # US SSN
        "0000000000",
        "123456789",
    }
)

# Credit card test numbers (Luhn-valid test cards)
_PLACEHOLDER_CARDS: FrozenSet[str] = frozenset(
    {
        "4111111111111111",
        "5500000000000004",
        "340000000000009",
        "30000000000004",
        "6011000000000004",
        "3530111333300000",
        "0000000000000000",
    }
)

# Well-known test/placeholder emails (lowercased)
_PLACEHOLDER_EMAILS: FrozenSet[str] = frozenset(
    {
        "test@test.com",
        "test@example.com",
        "user@example.com",
        "admin@example.com",
        "info@example.com",
        "example@example.com",
        "foo@bar.com",
        "test@test.co.kr",
        "aaa@aaa.com",
        "abc@abc.com",
        "name@domain.com",
        "your@email.com",
        "email@email.com",
        "sample@sample.com",
        "noreply@example.com",
        "no-reply@example.com",
        "user@domain.com",
        "someone@example.org",
    }
)

# Well-known test/placeholder URLs and IPs
_PLACEHOLDER_URLS: FrozenSet[str] = frozenset(
    {
        "127.0.0.1",
        "0.0.0.0",
        "192.168.0.1",
        "192.168.1.1",
        "10.0.0.1",
        "255.255.255.255",
        "8.8.8.8",
        "1.1.1.1",
    }
)

# Combine all placeholder sets for quick digit-only lookup
_ALL_PLACEHOLDER_DIGITS: FrozenSet[str] = (
    _PLACEHOLDER_PHONES | _PLACEHOLDER_IDS | _PLACEHOLDER_CARDS
)

# ---------------------------------------------------------------------------
# Heuristic patterns (compiled once)
# ---------------------------------------------------------------------------

# Sequential digits (ascending/descending), at least 4 digits
_RE_DIGITS = re.compile(r"\d")

# Repeating single group like 1111, aaaa
_RE_ALL_SAME = re.compile(r"^(.)\1+$")


def _extract_digits(value: str) -> str:
    """Extract only digits from a string."""
    return "".join(_RE_DIGITS.findall(value))


def _is_sequential(digits: str) -> bool:
    """Check if digits are sequential (ascending or descending)."""
    if len(digits) < 4:
        return False
    ascending = all(int(digits[i]) == (int(digits[i - 1]) + 1) % 10 for i in range(1, len(digits)))
    descending = all(int(digits[i]) == (int(digits[i - 1]) - 1) % 10 for i in range(1, len(digits)))
    return ascending or descending


def _is_repeating(digits: str) -> bool:
    """Check if all characters are the same."""
    return len(digits) >= 2 and len(set(digits)) == 1


def is_placeholder(value: str, category: str = "") -> bool:
    """Check if a matched value is likely placeholder/test data.

    Args:
        value: The matched PII string.
        category: Pattern category (e.g., "phone", "email", "ssn", "credit_card").

    Returns:
        True if the value appears to be placeholder/test data.
    """
    if not value:
        return False

    digits = _extract_digits(value)
    lower = value.strip().lower()
    cat = category.lower()

    # --- Email-specific ---
    if cat == "email" or "@" in value:
        if lower in _PLACEHOLDER_EMAILS:
            return True
        # Patterns like x@x.com, a@a.com
        local, _, domain = lower.partition("@")
        if local and domain:
            domain_name = domain.split(".")[0] if "." in domain else domain
            if local == domain_name:
                return True
            # test+anything@example.com
            if domain.endswith(("example.com", "example.org", "example.net")):
                return True

    # --- IP-specific ---
    if cat == "ip" or cat == "ipv4":
        if lower in _PLACEHOLDER_URLS:
            return True

    # --- Digit-based checks (phone, ssn, bank, credit_card, etc.) ---
    if digits:
        if digits in _ALL_PLACEHOLDER_DIGITS:
            return True
        if _is_repeating(digits):
            return True
        if _is_sequential(digits):
            return True

    return False
