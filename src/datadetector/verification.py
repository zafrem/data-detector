"""Verification functions for additional validation after regex matching."""

import logging
import math
from collections import Counter
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


def iban_mod97(value: str) -> bool:
    """
    Verify IBAN using Mod-97 check algorithm.

    The IBAN check digits are calculated using mod-97 operation:
    1. Move the first 4 characters to the end
    2. Replace letters with numbers (A=10, B=11, ..., Z=35)
    3. Calculate mod 97
    4. Result should be 1 for valid IBAN

    Args:
        value: IBAN string (e.g., "GB82WEST12345698765432")

    Returns:
        True if IBAN passes mod-97 verification, False otherwise
    """
    # Remove spaces and convert to uppercase
    iban = value.replace(" ", "").upper()

    # Move first 4 chars to end
    rearranged = iban[4:] + iban[:4]

    # Replace letters with numbers (A=10, B=11, ..., Z=35)
    numeric_string = ""
    for char in rearranged:
        if char.isdigit():
            numeric_string += char
        elif char.isalpha():
            # A=10, B=11, ..., Z=35
            numeric_string += str(ord(char) - ord("A") + 10)
        else:
            # Invalid character
            return False

    # Calculate mod 97
    try:
        remainder = int(numeric_string) % 97
        return remainder == 1
    except (ValueError, OverflowError):
        return False


def luhn(value: str) -> bool:
    """
    Verify using Luhn algorithm (mod-10 checksum).

    Used for credit cards, some national IDs, etc.

    Args:
        value: Numeric string to verify

    Returns:
        True if passes Luhn check, False otherwise
    """
    # Remove non-digits
    digits = [int(d) for d in value if d.isdigit()]

    if not digits:
        return False

    # Luhn algorithm
    checksum = 0
    reverse_digits = digits[::-1]

    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:  # Every second digit from right
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit

    return checksum % 10 == 0


def dms_coordinate(value: str) -> bool:
    """
    Verify DMS (Degrees Minutes Seconds) coordinate format.

    Validates that:
    - Degrees: 0-180 (longitude) or 0-90 (latitude)
    - Minutes: 0-59
    - Seconds: 0-59.999...
    - Direction is valid for the coordinate type

    Args:
        value: DMS coordinate string (e.g., "37°46′29.7″N")

    Returns:
        True if valid DMS coordinate, False otherwise
    """
    import re

    # Parse DMS format
    pattern = r"(\d{1,3})°\s*(\d{1,2})′\s*(\d{1,2}(?:\.\d+)?)″\s*([NSEW])"
    match = re.match(pattern, value, re.IGNORECASE)
    if not match:
        return False

    degrees = int(match.group(1))
    minutes = int(match.group(2))
    seconds = float(match.group(3))
    direction = match.group(4).upper()

    # Validate minutes and seconds
    if minutes > 59 or seconds >= 60:
        return False

    # Validate degrees based on direction
    if direction in ("N", "S"):  # Latitude
        if degrees > 90:
            return False
    elif direction in ("E", "W"):  # Longitude
        if degrees > 180:
            return False

    return True


def high_entropy_token(value: str) -> bool:
    """
    Verify token has high entropy characteristics.

    Validates that the token meets criteria for random, high-entropy tokens:
    - 20+ characters minimum
    - No spaces or line breaks
    - Base64url/hex character set (A-Za-z0-9_-)
    - High Shannon entropy (randomness)

    This is useful for detecting API keys, tokens, secrets, etc.

    Args:
        value: Token string to verify

    Returns:
        True if token has high entropy characteristics, False otherwise
    """
    # Check minimum length
    if len(value) < 20:
        return False

    # Check for spaces or line breaks
    if any(c in value for c in " \n\r\t"):
        return False

    # Check character set (base64url: A-Za-z0-9_- or hex: A-Fa-f0-9)
    # Being permissive to catch various token formats including JWT (with dots)
    allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-+/=.")
    if not all(c in allowed_chars for c in value):
        return False

    # Calculate Shannon entropy
    char_counts = Counter(value)
    length = len(value)
    entropy = -sum((count / length) * math.log2(count / length) for count in char_counts.values())

    # High entropy threshold
    # Base64: theoretical max ~6 bits/char, practical ~5-5.5 for random data
    # Hex: theoretical max ~4 bits/char, practical ~3.5-4 for random data
    # Set threshold at 4.0 to catch both formats while filtering repetitive strings
    min_entropy = 4.0

    return entropy >= min_entropy


def not_timestamp(value: str) -> bool:
    """
    Verify that a numeric string is NOT a timestamp.

    Rejects values that look like:
    - Unix timestamps (10 digits, 1000000000-9999999999)
    - Unix timestamps in milliseconds (13 digits, 1000000000000-9999999999999)
    - Compact datetime formats (14+ digits like YYYYMMDDHHMMSS)

    Args:
        value: String to check

    Returns:
        True if NOT a timestamp (safe to classify as PII), False if looks like timestamp
    """
    # Remove common separators to get just digits
    digits_only = "".join(c for c in value if c.isdigit())

    if not digits_only:
        return True

    length = len(digits_only)

    # 10-digit Unix timestamp range check (2001-2286)
    if length == 10:
        try:
            num = int(digits_only)
            # Unix timestamp range: 1000000000 (Sep 2001) to 9999999999 (Nov 2286)
            if 1000000000 <= num <= 9999999999:
                return False  # Likely a timestamp
        except ValueError:
            pass

    # 13-digit Unix timestamp in milliseconds (2001-2286)
    if length == 13:
        try:
            num = int(digits_only)
            # Unix timestamp ms range: 1000000000000 to 9999999999999
            if 1000000000000 <= num <= 9999999999999:
                return False  # Likely a timestamp in ms
        except ValueError:
            pass

    # 14-digit compact datetime (YYYYMMDDHHMMSS)
    if length == 14:
        # Check if it looks like a date: YYYY (19xx or 20xx), MM (01-12), DD (01-31)
        try:
            year = int(digits_only[:4])
            month = int(digits_only[4:6])
            day = int(digits_only[6:8])
            hour = int(digits_only[8:10])
            minute = int(digits_only[10:12])
            second = int(digits_only[12:14])

            # Check if components are in valid ranges
            if (1900 <= year <= 2099 and
                1 <= month <= 12 and
                1 <= day <= 31 and
                0 <= hour <= 23 and
                0 <= minute <= 59 and
                0 <= second <= 59):
                return False  # Likely a compact datetime
        except (ValueError, IndexError):
            pass

    # Not a recognized timestamp format
    return True


def korean_zipcode_valid(value: str) -> bool:
    """
    Verify Korean postal code is valid and not a timestamp component.

    Korean postal codes are 5 digits (00000-99999).
    This function rejects:
    - Sequential numbers (12345, 11111, etc.)
    - Timestamps components
    - Error codes and other numeric IDs

    Args:
        value: 5-digit string to verify

    Returns:
        True if likely a valid Korean postal code, False otherwise
    """
    # Remove any separators
    digits_only = "".join(c for c in value if c.isdigit())

    if len(digits_only) != 5:
        return False

    # Reject sequential patterns (12345, 54321, etc.)
    is_sequential_up = all(int(digits_only[i]) == int(digits_only[i-1]) + 1
                          for i in range(1, len(digits_only)))
    is_sequential_down = all(int(digits_only[i]) == int(digits_only[i-1]) - 1
                            for i in range(1, len(digits_only)))

    if is_sequential_up or is_sequential_down:
        return False

    # Reject all same digit (00000, 11111, etc.)
    if len(set(digits_only)) == 1:
        return False

    # Reject numbers that are too round (multiples of 10000, like 50000, 60000)
    # Real postal codes have more variation
    try:
        num = int(digits_only)
        if num % 10000 == 0:
            return False
    except ValueError:
        return False

    # Accept as likely valid postal code
    return True


def us_zipcode_valid(value: str) -> bool:
    """
    Verify US postal code is valid and not a timestamp component.

    US postal codes are 5 digits (00000-99999) or ZIP+4 (00000-0000).
    This function rejects:
    - Sequential numbers in the base 5 digits (12345, 54321, etc.)
    - Timestamps components
    - Error codes and other numeric IDs

    Args:
        value: 5 or 9-digit string (with optional hyphen) to verify

    Returns:
        True if likely a valid US postal code, False otherwise
    """
    # Remove any separators
    digits_only = "".join(c for c in value if c.isdigit())

    # US ZIP can be 5 digits or 9 digits (ZIP+4)
    if len(digits_only) not in [5, 9]:
        return False

    # Check the first 5 digits (the base ZIP code)
    base_zip = digits_only[:5]

    # Reject sequential patterns in base ZIP (12345, 54321, etc.)
    is_sequential_up = all(int(base_zip[i]) == int(base_zip[i-1]) + 1
                          for i in range(1, len(base_zip)))
    is_sequential_down = all(int(base_zip[i]) == int(base_zip[i-1]) - 1
                            for i in range(1, len(base_zip)))

    if is_sequential_up or is_sequential_down:
        return False

    # Reject all same digit in base ZIP (00000, 11111, etc.)
    if len(set(base_zip)) == 1:
        return False

    # Reject numbers that are too round (multiples of 10000, like 50000, 60000)
    # Real postal codes have more variation
    try:
        num = int(base_zip)
        if num % 10000 == 0:
            return False
    except ValueError:
        return False

    # Accept as likely valid postal code
    return True


def korean_bank_account_valid(value: str) -> bool:
    """
    Verify Korean bank account is valid and not a timestamp.

    This function provides additional validation beyond regex matching
    to reject timestamps and other numeric sequences.

    Args:
        value: Bank account string to verify

    Returns:
        True if likely a valid bank account, False if likely timestamp/other
    """
    # Remove common separators
    digits_only = "".join(c for c in value if c.isdigit())

    if not digits_only:
        return False

    length = len(digits_only)

    # Check if it starts with a known Korean bank prefix
    # Common prefixes: 110, 120, 150, 190, 830 (Kookmin), 1002 (Woori), 301 (Nonghyup), 3333 (Kakao), 100 (K Bank/Toss)
    has_known_prefix = False
    known_prefixes = ['110', '120', '150', '190', '830', '1002', '301', '3333', '100']
    for prefix in known_prefixes:
        if digits_only.startswith(prefix):
            has_known_prefix = True
            break

    # If it has a known bank prefix, be more lenient - it's likely a real bank account
    # Still check for obvious timestamps though
    if has_known_prefix:
        # For accounts with known prefixes, only reject obvious timestamps
        if length == 10:
            try:
                num = int(digits_only)
                # Very tight timestamp range to avoid false positives
                if 1600000000 <= num <= 1800000000:
                    return False  # Current era timestamps (2020-2027)
            except ValueError:
                pass
        return True  # Accept if it has a known bank prefix

    # For accounts without known prefixes, be more strict
    # Reject if it's a known timestamp length and range
    # 10 digits: Unix timestamp
    if length == 10:
        try:
            num = int(digits_only)
            if 1000000000 <= num <= 9999999999:
                return False  # Likely Unix timestamp
        except ValueError:
            pass

    # 13 digits: Unix timestamp in milliseconds
    if length == 13:
        try:
            num = int(digits_only)
            if 1000000000000 <= num <= 9999999999999:
                return False  # Likely Unix timestamp ms
        except ValueError:
            pass

    # 14 digits: Compact datetime (YYYYMMDDHHMMSS)
    if length == 14:
        try:
            year = int(digits_only[:4])
            month = int(digits_only[4:6])
            day = int(digits_only[6:8])

            # Check if first 8 digits look like YYYYMMDD
            if (1900 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31):
                return False  # Likely compact datetime
        except (ValueError, IndexError):
            pass

    # Check for sequential patterns in longer numbers (but only for non-prefixed accounts)
    if length >= 10 and not has_known_prefix:
        # Reject if too many sequential digits (like 123456789...)
        sequential_count = 0
        max_sequential = 0
        for i in range(1, len(digits_only)):
            if int(digits_only[i]) == int(digits_only[i-1]) + 1:
                sequential_count += 1
                max_sequential = max(max_sequential, sequential_count)
            else:
                sequential_count = 0

        # If we see 6+ consecutive sequential digits, likely not a real account
        if max_sequential >= 6:
            return False

    return True


def generic_number_not_timestamp(value: str) -> bool:
    """
    Verify that a numeric string is likely NOT a timestamp (for generic patterns).

    This is less strict than korean_bank_account_valid and is suitable for
    generic numeric patterns that don't have known prefixes.

    Args:
        value: String to check

    Returns:
        True if NOT a timestamp (safe to classify as account/ID), False if looks like timestamp
    """
    # Check if value contains separators (hyphens, spaces)
    # If it has separators, it's more likely a formatted account number than a timestamp
    has_separators = any(c in value for c in ['-', ' ', '/'])

    # Remove common separators
    digits_only = "".join(c for c in value if c.isdigit())

    if not digits_only:
        return True

    length = len(digits_only)

    # If the value has separators (like "123-456-789"), be more lenient
    # Timestamps are rarely written with separators
    if has_separators:
        # Only reject if it's clearly a datetime pattern
        if length >= 14:
            try:
                year = int(digits_only[:4])
                month = int(digits_only[4:6])
                day = int(digits_only[6:8])

                # Check if first 8 digits look like YYYYMMDD
                if (1900 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31):
                    return False  # Likely compact datetime even with separators
            except (ValueError, IndexError):
                pass
        return True  # Has separators and not a datetime - likely a real account/ID

    # No separators - be more strict about timestamps
    # 10 digits: Unix timestamp
    if length == 10:
        try:
            num = int(digits_only)
            if 1000000000 <= num <= 9999999999:
                return False  # Likely Unix timestamp
        except ValueError:
            pass

    # 13 digits: Unix timestamp in milliseconds
    if length == 13:
        try:
            num = int(digits_only)
            if 1000000000000 <= num <= 9999999999999:
                return False  # Likely Unix timestamp ms
        except ValueError:
            pass

    # 14+ digits: Compact datetime (YYYYMMDDHHMMSS)
    if length >= 14:
        try:
            year = int(digits_only[:4])
            month = int(digits_only[4:6])
            day = int(digits_only[6:8])

            # Check if first 8 digits look like YYYYMMDD
            if (1900 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31):
                return False  # Likely compact datetime
        except (ValueError, IndexError):
            pass

    return True


# Registry of verification functions
VERIFICATION_FUNCTIONS: Dict[str, Callable[[str], bool]] = {
    "iban_mod97": iban_mod97,
    "luhn": luhn,
    "dms_coordinate": dms_coordinate,
    "high_entropy_token": high_entropy_token,
    "not_timestamp": not_timestamp,
    "korean_zipcode_valid": korean_zipcode_valid,
    "us_zipcode_valid": us_zipcode_valid,
    "korean_bank_account_valid": korean_bank_account_valid,
    "generic_number_not_timestamp": generic_number_not_timestamp,
}


def get_verification_function(name: str) -> Optional[Callable[[str], bool]]:
    """
    Get verification function by name.

    Args:
        name: Name of verification function

    Returns:
        Verification function or None if not found
    """
    return VERIFICATION_FUNCTIONS.get(name)


def register_verification_function(name: str, func: Callable[[str], bool]) -> None:
    """
    Register a custom verification function.

    This allows users to add their own verification functions at runtime.

    Args:
        name: Name to register the function under
        func: Verification function that takes a string and returns bool

    Example:
        def custom_verify(value: str) -> bool:
            # Custom verification logic
            return True

        register_verification_function("custom", custom_verify)
    """
    VERIFICATION_FUNCTIONS[name] = func
    logger.info(f"Registered verification function: {name}")


def unregister_verification_function(name: str) -> bool:
    """
    Unregister a verification function.

    Args:
        name: Name of function to unregister

    Returns:
        True if function was removed, False if not found
    """
    if name in VERIFICATION_FUNCTIONS:
        del VERIFICATION_FUNCTIONS[name]
        logger.info(f"Unregistered verification function: {name}")
        return True
    return False
