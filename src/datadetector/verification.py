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


# Registry of verification functions
VERIFICATION_FUNCTIONS: Dict[str, Callable[[str], bool]] = {
    "iban_mod97": iban_mod97,
    "luhn": luhn,
    "dms_coordinate": dms_coordinate,
    "high_entropy_token": high_entropy_token,
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
