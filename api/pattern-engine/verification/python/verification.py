"""Verification functions for additional validation after regex matching.

This module contains reusable verification functions that can be used
across different pattern detection systems. These functions provide
additional validation beyond regex matching.

All verification functions follow the signature: (str) -> bool
"""

import logging
import math
import os
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Set

try:
    import numpy as np
    from scipy.spatial.distance import cosine

    HAS_VECTOR_DEPS = True
except ImportError:
    HAS_VECTOR_DEPS = False
    np = None  # type: ignore
    cosine = None  # type: ignore

logger = logging.getLogger(__name__)

# --- Configuration for ML/Vector Based Verification ---
# Default to false to avoid performance/dependency overhead
USE_VECTOR_MODEL = (
    os.getenv("ENABLE_KOREAN_VECTOR_VERIFICATION", "false").lower() == "true"
)
VECTOR_MODEL_PATH = os.getenv("KOREAN_VECTOR_MODEL_PATH", "datas/ko_w2v.vec")
_VECTOR_MODEL_CACHE: Dict[str, Any] = {}
_KEYWORDS_CENTROID: Optional[Any] = None


def _load_vector_model():
    """Load a lightweight vector model (Word2Vec .vec format)."""
    global _VECTOR_MODEL_CACHE, _KEYWORDS_CENTROID
    if _VECTOR_MODEL_CACHE:
        return _VECTOR_MODEL_CACHE

    if not HAS_VECTOR_DEPS:
        if USE_VECTOR_MODEL:
            logger.error("Vector verification enabled but numpy/scipy not installed.")
        return None

    model_path = Path(VECTOR_MODEL_PATH)
    if not model_path.exists():
        # Only log if specifically enabled
        if USE_VECTOR_MODEL:
            logger.warning(
                f"Vector model not found at {VECTOR_MODEL_PATH}. Skipping vector verification."
            )
        return None

    try:
        # Simple parser for .vec (word dim1 dim2 ...)
        with open(model_path, encoding="utf-8") as f:
            header = f.readline().split()
            if len(header) < 2:
                return None

            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                word = parts[0]
                vector = np.array([float(x) for x in parts[1:]], dtype=np.float32)
                _VECTOR_MODEL_CACHE[word] = vector

        # Calculate a "Keyword Centroid" to represent common contact-related words
        keyword_vectors = []
        for kw in KOREAN_NON_NAME_KEYWORDS:
            if kw in _VECTOR_MODEL_CACHE:
                keyword_vectors.append(_VECTOR_MODEL_CACHE[kw])

        if keyword_vectors:
            _KEYWORDS_CENTROID = np.mean(keyword_vectors, axis=0)

        logger.info(f"Loaded {len(_VECTOR_MODEL_CACHE)} vectors for similarity check.")
    except Exception as e:
        logger.error(f"Failed to load vector model: {e}")

    return _VECTOR_MODEL_CACHE


def get_vector_similarity_score(value: str) -> float:
    """
    Calculate similarity score between a word and the contact-keyword centroid.
    A higher score (closer to 1.0) means it's likely a keyword (not a name).
    """
    if not HAS_VECTOR_DEPS:
        return 0.0

    model = _load_vector_model()
    if not model or _KEYWORDS_CENTROID is None or value not in model:
        return 0.0

    # 1.0 - cosine_distance = cosine_similarity
    sim = 1.0 - cosine(model[value], _KEYWORDS_CENTROID)
    return float(sim)


# --- Existing Data Loading Logic ---
# Cache for data-driven verification
_DATA_CACHE: Dict[str, Set[str]] = {}


def _get_data_path() -> Path:
    """Determine data directory path."""
    # Data is in pattern-engine/datas/
    return Path(__file__).parent.parent.parent / "datas"


def _load_data_file(filename: str) -> Set[str]:
    """Load values from a CSV data file."""
    if filename in _DATA_CACHE:
        return _DATA_CACHE[filename]

    data_path = _get_data_path() / filename
    values = set()

    if data_path.exists():
        try:
            with open(data_path, encoding="utf-8") as f:
                # Skip header
                lines = f.readlines()
                if len(lines) > 1:
                    for line in lines[1:]:
                        val = line.strip()
                        if val:
                            values.add(val)
            logger.info(f"Loaded {len(values)} entries from {filename}")
        except Exception as e:
            logger.error(f"Failed to load data file {filename}: {e}")

    _DATA_CACHE[filename] = values
    return values


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
    allowed_chars = set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-+/.="
    )
    if not all(c in allowed_chars for c in value):
        return False

    # Normalize for entropy calculation: lowercase and treat separators as spaces
    normalized = value.lower().replace("-", " ").replace("_", " ")

    # Calculate Shannon entropy
    char_counts = Counter(normalized)
    length = len(normalized)
    entropy = -sum(
        (count / length) * math.log2(count / length) for count in char_counts.values()
    )

    # High entropy threshold
    # Base64: theoretical max ~6 bits/char, practical ~5-5.5 for random data
    # Hex: theoretical max ~4 bits/char, practical ~3.5-4 for random data
    # Set threshold at 4.5 to filter more strictly for random strings
    min_entropy = 4.5

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
            if (
                1900 <= year <= 2099
                and 1 <= month <= 12
                and 1 <= day <= 31
                and 0 <= hour <= 23
                and 0 <= minute <= 59
                and 0 <= second <= 59
            ):
                return False  # Likely a compact datetime
        except (ValueError, IndexError):
            pass

    # Not a recognized timestamp format
    return True


def korean_zipcode_valid(value: str) -> bool:
    """
    Verify Korean postal code is valid.
    """
    digits_only = "".join(c for c in value if c.isdigit())
    if len(digits_only) != 5:
        return False
    return "0" <= digits_only[0] <= "6"

    # Reject sequential patterns (12345, 54321, etc.)
    is_sequential_up = all(
        int(digits_only[i]) == int(digits_only[i - 1]) + 1
        for i in range(1, len(digits_only))
    )
    is_sequential_down = all(
        int(digits_only[i]) == int(digits_only[i - 1]) - 1
        for i in range(1, len(digits_only))
    )

    if is_sequential_up or is_sequential_down:
        return False

    # Reject all same digit (00000, 11111, etc.)
    if len(set(digits_only)) == 1:
        return False

    # Accept as likely valid postal code
    return True


def us_zipcode_valid(value: str) -> bool:
    """
    Verify US postal code is valid.

    Checks against us_zipcodes.csv if available, otherwise uses heuristics.
    """
    # Remove any separators to get raw digits first
    digits_only = "".join(c for c in value if c.isdigit())

    # 1. Data-driven check if data exists
    valid_zips = _load_data_file("us_zipcodes.csv")
    if valid_zips:
        # If we have 5 digits, check exact match
        if len(digits_only) == 5:
            return digits_only in valid_zips
        # If we have 9 digits (ZIP+4), check if the base 5-digit zip is valid
        elif len(digits_only) == 9:
            return digits_only[:5] in valid_zips

        # If length is weird but data is present, we might want to fail?
        # But let's fall back to heuristics just in case regex matched something else

    # 2. Heuristic fallback
    # US ZIP can be 5 digits or 9 digits (ZIP+4)
    if len(digits_only) not in [5, 9]:
        return False

    # Check the first 5 digits (the base ZIP code)
    base_zip = digits_only[:5]

    # Reject sequential patterns in base ZIP (12345, 54321, etc.)
    is_sequential_up = all(
        int(base_zip[i]) == int(base_zip[i - 1]) + 1 for i in range(1, len(base_zip))
    )
    is_sequential_down = all(
        int(base_zip[i]) == int(base_zip[i - 1]) - 1 for i in range(1, len(base_zip))
    )

    if is_sequential_up or is_sequential_down:
        return False

    # Reject all same digit in base ZIP (00000, 11111, etc.)
    if len(set(base_zip)) == 1:
        return False

    return True


def jp_zipcode_valid(value: str) -> bool:
    """
    Verify Japanese postal code is valid.

    Checks against jp_zipcodes.csv if available, otherwise uses heuristics.
    Japanese postal codes are 7 digits, often formatted as XXX-XXXX.
    """
    # Normalize: remove hyphen
    digits_only = value.replace("-", "").replace("−", "").replace("‐", "")
    digits_only = "".join(c for c in digits_only if c.isdigit())

    if len(digits_only) != 7:
        return False

    # 1. Data-driven check if data exists
    valid_zips = _load_data_file("jp_zipcodes.csv")
    if valid_zips:
        # Try with hyphen format (stored format)
        hyphen_format = f"{digits_only[:3]}-{digits_only[3:]}"
        return hyphen_format in valid_zips or digits_only in valid_zips

    # 2. Heuristic fallback
    # Reject all same digit (0000000, 1111111, etc.)
    if len(set(digits_only)) == 1:
        return False

    # Reject sequential patterns (1234567, 7654321)
    is_sequential_up = all(
        int(digits_only[i]) == int(digits_only[i - 1]) + 1
        for i in range(1, len(digits_only))
    )
    is_sequential_down = all(
        int(digits_only[i]) == int(digits_only[i - 1]) - 1
        for i in range(1, len(digits_only))
    )
    if is_sequential_up or is_sequential_down:
        return False

    # Valid Japanese postal code prefixes range from 001 to 999
    # but 000 and 999 are not assigned to any prefecture
    prefix = int(digits_only[:3])
    if prefix == 0 or prefix >= 999:
        return False

    return True


def cn_zipcode_valid(value: str) -> bool:
    """
    Verify Chinese postal code is valid.

    Checks against cn_zipcodes.csv if available, otherwise uses heuristics.
    Chinese postal codes are 6 digits (e.g., 100000).
    """
    digits_only = "".join(c for c in value if c.isdigit())

    if len(digits_only) != 6:
        return False

    # 1. Data-driven check if data exists
    valid_zips = _load_data_file("cn_zipcodes.csv")
    if valid_zips:
        return digits_only in valid_zips

    # 2. Heuristic fallback
    # Reject all same digit (000000, 111111, etc.)
    if len(set(digits_only)) == 1:
        return False

    # Reject sequential patterns (123456, 654321)
    is_sequential_up = all(
        int(digits_only[i]) == int(digits_only[i - 1]) + 1
        for i in range(1, len(digits_only))
    )
    is_sequential_down = all(
        int(digits_only[i]) == int(digits_only[i - 1]) - 1
        for i in range(1, len(digits_only))
    )
    if is_sequential_up or is_sequential_down:
        return False

    # Chinese postal codes: first 2 digits range 01-86
    first_two = int(digits_only[:2])
    if first_two < 1 or first_two > 86:
        return False

    return True


def tw_zipcode_valid(value: str) -> bool:
    """
    Verify Taiwan postal code is valid.

    Checks against tw_zipcodes.csv if available, otherwise uses heuristics.
    Taiwan postal codes are 3 or 5 digits (e.g., 100 or 10041).
    """
    digits_only = "".join(c for c in value if c.isdigit())

    if len(digits_only) not in [3, 5]:
        return False

    # 1. Data-driven check if data exists
    valid_zips = _load_data_file("tw_zipcodes.csv")
    if valid_zips:
        # Check exact match, or for 5-digit check if first 3 digits are valid
        if digits_only in valid_zips:
            return True
        if len(digits_only) == 5 and digits_only[:3] in valid_zips:
            return True
        return False

    # 2. Heuristic fallback
    # Reject all same digit
    if len(set(digits_only)) == 1:
        return False

    # Taiwan postal codes: first digit 1-9, valid range roughly 100-983
    first_digit = int(digits_only[0])
    if first_digit == 0:
        return False

    return True


def in_pincode_valid(value: str) -> bool:
    """
    Verify Indian PIN code is valid.

    Checks against in_pincodes.csv if available, otherwise uses heuristics.
    Indian PIN codes are 6 digits starting with 1-9 (e.g., 110001).
    """
    digits_only = "".join(c for c in value if c.isdigit())

    if len(digits_only) != 6:
        return False

    # First digit must be 1-9
    if digits_only[0] == "0":
        return False

    # 1. Data-driven check if data exists
    valid_pins = _load_data_file("in_pincodes.csv")
    if valid_pins:
        return digits_only in valid_pins

    # 2. Heuristic fallback
    # Reject all same digit (111111, 222222, etc.)
    if len(set(digits_only)) == 1:
        return False

    # Reject sequential patterns (123456, 654321)
    is_sequential_up = all(
        int(digits_only[i]) == int(digits_only[i - 1]) + 1
        for i in range(1, len(digits_only))
    )
    is_sequential_down = all(
        int(digits_only[i]) == int(digits_only[i - 1]) - 1
        for i in range(1, len(digits_only))
    )
    if is_sequential_up or is_sequential_down:
        return False

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
    # Common prefixes: 110, 120, 150, 190, 830 (Kookmin), 1002 (Woori),
    # 301 (Nonghyup), 3333 (Kakao), 100 (K Bank/Toss)
    has_known_prefix = False
    known_prefixes = ["110", "120", "150", "190", "830", "1002", "301", "3333", "100"]
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
            if 1900 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31:
                return False  # Likely compact datetime
        except (ValueError, IndexError):
            pass

    # Check for sequential patterns in longer numbers (but only for non-prefixed accounts)
    if length >= 10 and not has_known_prefix:
        # Reject if too many sequential digits (like 123456789...)
        sequential_count = 0
        max_sequential = 0
        for i in range(1, len(digits_only)):
            if int(digits_only[i]) == int(digits_only[i - 1]) + 1:
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
    has_separators = any(c in value for c in ["-", " ", "/"])

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
                if 1900 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31:
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
            if 1900 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31:
                return False  # Likely compact datetime
        except (ValueError, IndexError):
            pass

    return True


def contains_letter(value: str) -> bool:
    """
    Verify that the value contains at least one letter.

    Args:
        value: String to check

    Returns:
        True if value contains at least one letter, False otherwise
    """
    return any(c.isalpha() for c in value)


def us_ssn_valid(value: str) -> bool:
    """
    Verify US SSN is valid.

    Rejects:
    - Area numbers 000, 666, 900-999
    - Group number 00
    - Serial number 0000

    Args:
        value: SSN string (e.g. "123-45-6789" or "123456789")

    Returns:
        True if valid SSN format, False otherwise
    """
    digits = "".join(c for c in value if c.isdigit())
    if len(digits) != 9:
        return False

    area = int(digits[:3])
    group = int(digits[3:5])
    serial = int(digits[5:9])

    # Check area (first 3 digits)
    # Cannot be 000, 666, or 900-999
    if area == 0 or area == 666 or area >= 900:
        return False

    # Check group (middle 2 digits)
    # Cannot be 00
    if group == 0:
        return False

    # Check serial (last 4 digits)
    # Cannot be 0000
    if serial == 0:
        return False

    return True


# Common surnames for CJK name verification
# Chinese surnames - covers ~85% of population (simplified + traditional)
CHINESE_SURNAMES = {
    # Single-character surnames (most common)
    "王",
    "李",
    "张",
    "刘",
    "陈",
    "杨",
    "黄",
    "赵",
    "吴",
    "周",
    "徐",
    "孙",
    "马",
    "朱",
    "胡",
    "郭",
    "何",
    "林",
    "高",
    "罗",
    "郑",
    "梁",
    "谢",
    "宋",
    "唐",
    "许",
    "邓",
    "冯",
    "韩",
    "曹",
    "曾",
    "彭",
    "萧",
    "蔡",
    "潘",
    "田",
    "董",
    "袁",
    "于",
    "余",
    "叶",
    "蒋",
    "杜",
    "苏",
    "魏",
    "程",
    "吕",
    "丁",
    "沈",
    "任",
    "姚",
    "卢",
    "傅",
    "钟",
    "姜",
    "崔",
    "谭",
    "廖",
    "范",
    "汪",
    "陆",
    "金",
    "石",
    "戴",
    "贾",
    "韦",
    "夏",
    "邱",
    "方",
    "侯",
    "邹",
    "熊",
    "孟",
    "秦",
    "白",
    "江",
    "阎",
    "薛",
    "尹",
    "段",
    "雷",
    "黎",
    "史",
    "龙",
    "陶",
    "贺",
    "顾",
    "毛",
    "郝",
    "龚",
    "邵",
    "万",
    "钱",
    "严",
    "赖",
    "覃",
    "洪",
    "武",
    "莫",
    "孔",
    # Traditional variants
    "張",
    "劉",
    "陳",
    "楊",
    "黃",
    "趙",
    "吳",
    "許",
    "鄭",
    "謝",
    "鄧",
    "馮",
    "韓",
    "蕭",
    "葉",
    "蔣",
    "蘇",
    "魏",
    "呂",
    "瀋",
    "盧",
    "傅",
    "鐘",
    "薑",
    "譚",
    "廖",
    "範",
    "陸",
    "賈",
    "鄒",
    "閻",
    "龍",
    "陶",
    "賀",
    "顧",
    "郝",
    "龔",
    "萬",
    "錢",
    "嚴",
    "賴",
    "覃",
    # Compound surnames (2 characters)
    "欧阳",
    "歐陽",
    "司马",
    "司馬",
    "上官",
    "诸葛",
    "諸葛",
    "东方",
    "東方",
    "皇甫",
    "尉迟",
    "尉遲",
    "公孙",
    "公孫",
    "令狐",
    "慕容",
    "轩辕",
    "軒轅",
    "夏侯",
    "司徒",
    "独孤",
    "獨孤",
}

# Korean surnames - covers ~95% of population
KOREAN_SURNAMES = {
    # Most common (covers ~45%)
    "김",
    "이",
    "박",
    "최",
    "정",
    # Very common (covers another ~30%)
    "강",
    "조",
    "윤",
    "장",
    "임",
    "한",
    "오",
    "서",
    "신",
    "권",
    "황",
    "안",
    "송",
    "류",
    "유",
    "홍",
    "전",
    "고",
    "문",
    "양",
    # Common
    "손",
    "배",
    "백",
    "허",
    "남",
    "심",
    "노",
    "하",
    "곽",
    "성",
    "차",
    "주",
    "우",
    "구",
    "민",
    "진",
    "나",
    "지",
    "엄",
    "변",
    "채",
    "원",
    "천",
    "방",
    "공",
    "현",
    "함",
    "염",
    "여",
    "추",
    # Less common but still notable
    "도",
    "소",
    "석",
    "선",
    "설",
    "마",
    "길",
    "연",
    "위",
    "표",
    "명",
    "기",
    "반",
    "왕",
    "금",
    "옥",
    "육",
    "인",
    "맹",
    "제",
    "모",
    "탁",
    "국",
    "어",
    "은",
    "편",
    "용",
    "예",
    "경",
    "봉",
    "사",
    "부",
    "황보",
    "남궁",
    "독고",
    "사공",
    "제갈",
    "선우",
}

# Japanese surnames (kanji) - most common
JAPANESE_SURNAMES = {
    # Top 50 most common
    "佐藤",
    "鈴木",
    "高橋",
    "田中",
    "伊藤",
    "渡辺",
    "山本",
    "中村",
    "小林",
    "加藤",
    "吉田",
    "山田",
    "佐々木",
    "山口",
    "松本",
    "井上",
    "木村",
    "林",
    "斎藤",
    "清水",
    "山崎",
    "森",
    "阿部",
    "池田",
    "橋本",
    "山下",
    "石川",
    "中島",
    "前田",
    "藤田",
    "小川",
    "後藤",
    "岡田",
    "長谷川",
    "村上",
    "近藤",
    "石井",
    "斉藤",
    "坂本",
    "遠藤",
    "青木",
    "藤井",
    "西村",
    "福田",
    "太田",
    "三浦",
    "藤原",
    "岡本",
    "松田",
    "中川",
    # Additional common surnames
    "原田",
    "小野",
    "竹内",
    "金子",
    "和田",
    "中野",
    "原",
    "田村",
    "安藤",
    "河野",
    "上田",
    "大野",
    "高木",
    "工藤",
    "内田",
    "丸山",
    "今井",
    "酒井",
    "宮崎",
    "横山",
    # Single character surnames (less common but valid)
    "森",
    "林",
    "原",
    "関",
    "堀",
    "島",
    "谷",
    "浜",
    "沢",
    "杉",
}


# Common Chinese words that start with surname characters but aren't names.
# Used by chinese_name_valid to filter false positives.
CHINESE_NON_NAME_KEYWORDS = {
    # Common words starting with surname characters
    "王国",
    "王朝",
    "王牌",
    "王者",
    "李子",
    "张开",
    "张力",
    "张贴",
    "黄金",
    "黄色",
    "黄油",
    "黄土",
    "黄瓜",
    "黄河",
    "黄昏",
    "高度",
    "高级",
    "高中",
    "高速",
    "高考",
    "高峰",
    "高手",
    "高端",
    "周围",
    "周期",
    "周末",
    "周年",
    "周边",
    "周到",
    "马上",
    "马路",
    "马力",
    "朱红",
    "曹操",
    "白色",
    "白天",
    "白云",
    "白金",
    "白菜",
    "金属",
    "金融",
    "金额",
    "金钱",
    "金牌",
    "田地",
    "田野",
    "田园",
    "石头",
    "石油",
    "石材",
    "方法",
    "方案",
    "方向",
    "方式",
    "方面",
    "方便",
    "任务",
    "任何",
    "任意",
    "任命",
    "程度",
    "程序",
    "江山",
    "江南",
    "江河",
    "余额",
    "余下",
    "于是",
    "何时",
    "何处",
    "何必",
    # Contact/form keywords (simplified + traditional)
    "电话",
    "電話",
    "邮箱",
    "郵箱",
    "地址",
    "姓名",
    "信息",
    "資訊",
    "联系",
    "聯繫",
    "手机",
    "手機",
    "号码",
    "號碼",
    "传真",
    "傳真",
    "邮件",
    "郵件",
    "密码",
    "密碼",
    "账号",
    "帳號",
    "注册",
    "註冊",
    "登录",
    "登錄",
    "确认",
    "確認",
    "验证",
    "驗證",
    "性别",
    "性別",
    "生日",
    "职业",
    "職業",
    "公司",
    "部门",
    "部門",
    "任务",
    "任務",
}


def chinese_name_valid(value: str) -> bool:
    """
    Verify Chinese name has a valid surname prefix and given name.

    Uses multi-tier verification: keyword filtering, surname extraction,
    given name dictionary lookup, and length heuristics.

    Args:
        value: Chinese name string

    Returns:
        True if name is a plausible Chinese name, False otherwise
    """
    if not value or len(value) < 2 or len(value) > 4:
        return False

    # 1. Filter out non-name keywords (exact match)
    if value in CHINESE_NON_NAME_KEYWORDS:
        return False

    # 2. Extract surname and given name
    surname = None
    given_name = None

    # Check compound surnames first (2 chars)
    if len(value) >= 3 and value[:2] in CHINESE_SURNAMES:
        surname = value[:2]
        given_name = value[2:]
    elif value[0] in CHINESE_SURNAMES:
        surname = value[0]
        given_name = value[1:]

    if not surname:
        return False

    # 3. Given name dictionary lookup
    valid_given_names = _load_data_file("cn_given_names.csv")
    if valid_given_names and given_name in valid_given_names:
        return True

    # 4. Length heuristic: for names not in dictionary, only accept 2-4 char names
    # (Chinese names: 1-2 surname chars + 1-3 given name chars)
    # Most common: 1 surname + 1-2 given (2-3 total) or 2 surname + 1-2 given (3-4 total)
    if not (2 <= len(value) <= 4):
        return False

    return True


# Common Korean words that are not names but frequently appear in contact info
# and start with common surnames (e.g., "전", "이", "정"), leading to false positives.
# This list is used by korean_name_valid to filter matches.
KOREAN_NON_NAME_KEYWORDS = {
    "전화번호",
    "이메일",
    "연락처",
    "주소",
    "이름",
    "성명",
    "휴대폰",
    "핸드폰",
    "번호",
    "전화",
    "메일",
    "팩스",
    "모바일",
    "정보",
    "문의",
    "확인",
    "성별",
    "생년",
    "월일",
    "생일",
    "성별",
    "직업",
    "나이",
    "회사",
    "부서",
    "직책",
    "전화번",
    "메일주",
    "이메일주",
    "연락처는",
    "주소는",
    "이름은",
    "성명은",
}


def korean_name_valid(value: str) -> bool:
    """
    Verify Korean name has a valid surname prefix and is not a common keyword.

    Checks if the first 1-2 characters match known Korean surnames.
    Most Korean names are 2-4 characters (1 surname + 1-3 given name).
    This function also filters out common non-name words (like "이메일은")
    and uses a given name dictionary for higher confidence.

    Args:
        value: Korean name string

    Returns:
        True if name has known surname and isn't a known keyword, False otherwise
    """
    if not value or len(value) < 2 or len(value) > 5:
        return False

    # 1. Filter out common non-name keywords (exact match or with common particles)
    if value in KOREAN_NON_NAME_KEYWORDS:
        return False

    # Check for keyword + Korean particles (은/는/이/가/을/를/의)
    if len(value) >= 3 and value[-1] in ("은", "는", "이", "가", "을", "를", "의"):
        if value[:-1] in KOREAN_NON_NAME_KEYWORDS:
            return False

    # 2. Extract potential surname and given name
    surname = None
    given_name = None

    if len(value) >= 3 and value[:2] in KOREAN_SURNAMES:
        surname = value[:2]
        given_name = value[2:]
    elif value[0] in KOREAN_SURNAMES:
        surname = value[0]
        given_name = value[1:]

    if not surname:
        return False

    # 3. Hybrid Dictionary-Heuristic Check
    valid_given_names = _load_data_file("kr_given_names.csv")

    # If the given name part is in our common dictionary, it's very likely a name (High Confidence)
    if valid_given_names and given_name in valid_given_names:
        return True

    # If NOT in the dictionary, we apply stricter length heuristics:
    # Most false positives (전화, 정보, 전화번호) are length 2, 4, or 5.
    # We reject these unless they were found in the dictionary above.
    if len(value) != 3:
        return False

    # 4. (Optional) Vector Similarity Check
    # If the user has enabled ML-based filtering, we check if the word
    # has high similarity to our "Contact Keyword Centroid".
    # Similarity > 0.8 usually means it's conceptually a keyword, not a proper noun.
    if USE_VECTOR_MODEL:
        sim_score = get_vector_similarity_score(value)
        if sim_score > 0.8:
            return False

    # For 3-character matches (the most common Korean name format), we allow them
    # to avoid missing rare names, provided they aren't in the blacklist.
    return True


# Common Japanese words that could false-positive as names.
# Used by japanese_name_kanji_valid to filter false positives.
JAPANESE_NON_NAME_KEYWORDS = {
    # Common kanji compounds that start with surname characters
    "田園",
    "田畑",
    "田舎",
    "中心",
    "中央",
    "中間",
    "中古",
    "中止",
    "中国",
    "中学",
    "山脈",
    "山岳",
    "山林",
    "山地",
    "山頂",
    "高速",
    "高校",
    "高層",
    "高価",
    "高原",
    "高齢",
    "林業",
    "林道",
    "森林",
    "石油",
    "石材",
    "石炭",
    "石器",
    "金属",
    "金融",
    "金額",
    "金銭",
    "金庫",
    "上記",
    "上昇",
    "上手",
    "上司",
    "大学",
    "大会",
    "大臣",
    "大量",
    "大型",
    "大切",
    "大変",
    "小学",
    "小説",
    "小型",
    "小売",
    "原因",
    "原則",
    "原料",
    "原発",
    "内容",
    "内部",
    "内閣",
    "前回",
    "前者",
    "前提",
    "前日",
    "後半",
    "後者",
    "後日",
    "西洋",
    "西側",
    "青年",
    "青春",
    "近代",
    "近年",
    "近所",
    "遠方",
    "遠足",
    "池袋",
    # Contact/form keywords
    "電話",
    "住所",
    "名前",
    "情報",
    "連絡",
    "番号",
    "携帯",
    "確認",
    "登録",
    "氏名",
    "性別",
    "生年",
    "職業",
    "会社",
    "部署",
    "郵便",
    "暗号",
    "認証",
    "口座",
}


def japanese_name_kanji_valid(value: str) -> bool:
    """
    Verify Japanese name (kanji) matches known surname patterns and given name.

    Uses multi-tier verification: keyword filtering, surname extraction,
    given name dictionary lookup, and length heuristics.

    Args:
        value: Japanese name string in kanji

    Returns:
        True if name is a plausible Japanese name, False otherwise
    """
    if not value or len(value) < 2 or len(value) > 6:
        return False

    # 1. Filter out non-name keywords (exact match)
    if value in JAPANESE_NON_NAME_KEYWORDS:
        return False

    # 2. For 2-char strings, check if it's a 2-char surname (like 田中, 鈴木)
    if len(value) == 2:
        return value in JAPANESE_SURNAMES

    # 3. Extract surname and given name
    surname = None
    given_name = None

    # Check 3-char surnames first (e.g., 佐々木, 長谷川)
    if len(value) >= 4 and value[:3] in JAPANESE_SURNAMES:
        surname = value[:3]
        given_name = value[3:]
    # Check 2-char surnames (most common)
    elif value[:2] in JAPANESE_SURNAMES:
        surname = value[:2]
        given_name = value[2:]
    # Check 1-char surnames (e.g., 森, 林)
    elif value[0] in JAPANESE_SURNAMES:
        surname = value[0]
        given_name = value[1:]

    if not surname:
        return False

    # 4. Given name dictionary lookup
    valid_given_names = _load_data_file("jp_given_names.csv")
    if valid_given_names and given_name in valid_given_names:
        return True

    # 5. Length heuristic: for names not in dictionary, accept 3-4 char names
    # (most common: 2 surname + 1-2 given name chars)
    if len(value) not in (3, 4):
        return False

    return True


def cjk_name_standalone(value: str) -> bool:
    """
    Verify that a CJK name match is standalone (expected length for a name).

    This verification is used with CJK name patterns to reject matches that
    are likely parts of longer text (titles, sentences, etc).

    For Chinese names: 2-4 characters is typical
    For Korean names: 2-5 characters is typical (mostly 3)
    For Japanese names: 2-6 characters is typical

    This function checks that the matched value doesn't exceed typical name lengths
    and contains only CJK characters (no mixed scripts).

    Args:
        value: The matched string to verify

    Returns:
        True if likely a standalone name, False otherwise
    """
    if not value:
        return False

    # Check length - names are typically short
    # Chinese: 2-4, Korean: 2-5, Japanese: 2-6
    if len(value) > 6:
        return False

    # Check it's all CJK characters (no mixing with ASCII)
    for char in value:
        code = ord(char)
        # CJK ranges: Chinese (4E00-9FFF), Korean Hangul (AC00-D7AF),
        # Japanese Hiragana (3040-309F), Katakana (30A0-30FF), CJK (4E00-9FFF)
        is_cjk = (
            0x4E00 <= code <= 0x9FFF  # CJK Unified Ideographs
            or 0xAC00 <= code <= 0xD7AF  # Korean Hangul
            or 0x3040 <= code <= 0x309F  # Hiragana
            or 0x30A0 <= code <= 0x30FF  # Katakana
        )
        if not is_cjk:
            return False

    return True


def cn_national_id_valid(value: str) -> bool:
    """
    Verify Chinese National ID (18 digits) using checksum algorithm.

    The 18th digit is a check digit calculated using weighted sum mod 11.
    Weights: [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    Check digit map: ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']

    Also validates:
    - Area code (first 2 digits) is valid province
    - Birth date (digits 7-14) is valid date

    Args:
        value: Chinese National ID string (18 characters)

    Returns:
        True if valid, False otherwise
    """
    # Remove spaces and convert to uppercase
    id_str = value.replace(" ", "").upper()

    if len(id_str) != 18:
        return False

    # Valid province codes (first 2 digits)
    valid_provinces = {
        "11",
        "12",
        "13",
        "14",
        "15",  # Beijing, Tianjin, Hebei, Shanxi, Inner Mongolia
        "21",
        "22",
        "23",  # Liaoning, Jilin, Heilongjiang
        "31",
        "32",
        "33",
        "34",
        "35",
        "36",
        "37",  # Shanghai, Jiangsu, Zhejiang, Anhui, Fujian, Jiangxi, Shandong
        "41",
        "42",
        "43",
        "44",
        "45",
        "46",  # Henan, Hubei, Hunan, Guangdong, Guangxi, Hainan
        "50",
        "51",
        "52",
        "53",
        "54",  # Chongqing, Sichuan, Guizhou, Yunnan, Tibet
        "61",
        "62",
        "63",
        "64",
        "65",  # Shaanxi, Gansu, Qinghai, Ningxia, Xinjiang
        "71",  # Taiwan (ROC)
        "81",
        "82",  # Hong Kong, Macau
        "91",  # Foreign nationals
    }

    if id_str[:2] not in valid_provinces:
        return False

    # Validate birth date (YYYYMMDD at positions 6-14)
    try:
        year = int(id_str[6:10])
        month = int(id_str[10:12])
        day = int(id_str[12:14])

        # Basic date validation
        if not (1900 <= year <= 2100):
            return False
        if not (1 <= month <= 12):
            return False
        if not (1 <= day <= 31):
            return False

        # More precise day validation per month
        days_in_month = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if day > days_in_month[month]:
            return False
    except (ValueError, IndexError):
        return False

    # Calculate checksum
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check_digits = ["1", "0", "X", "9", "8", "7", "6", "5", "4", "3", "2"]

    try:
        total = sum(int(id_str[i]) * weights[i] for i in range(17))
        expected_check = check_digits[total % 11]
        return id_str[17] == expected_check
    except (ValueError, IndexError):
        return False


def tw_national_id_valid(value: str) -> bool:
    """
    Verify Taiwan National ID using checksum algorithm.

    Format: 1 letter + 9 digits
    - First letter: Birth place code (A-Z, excluding I, O, W)
    - 2nd digit: Gender (1=male, 2=female)
    - Last digit: Check digit

    Checksum algorithm:
    1. Convert letter to 2 digits (A=10, B=11, ..., Z=35)
    2. First digit of letter code * 1 + second digit * 9
    3. Sum with remaining digits weighted [8,7,6,5,4,3,2,1,1]
    4. Valid if sum % 10 == 0

    Args:
        value: Taiwan National ID string

    Returns:
        True if valid, False otherwise
    """
    id_str = value.replace(" ", "").upper()

    if len(id_str) != 10:
        return False

    # First character must be A-Z
    if not id_str[0].isalpha():
        return False

    # Remaining 9 must be digits
    if not id_str[1:].isdigit():
        return False

    # Convert letter to 2-digit number (A=10, B=11, ..., Z=35)
    letter_code = ord(id_str[0]) - ord("A") + 10

    # Invalid letters: I=18, O=24, W=32 are not used
    if id_str[0] in ("I", "O", "W"):
        return False

    # Gender digit (position 1) should be 1 or 2
    gender = int(id_str[1])
    if gender not in (1, 2):
        return False

    # Calculate checksum
    # Letter contributes: first_digit * 1 + second_digit * 9
    first_digit = letter_code // 10
    second_digit = letter_code % 10

    total = first_digit * 1 + second_digit * 9

    # Weights for digits 2-9 (positions 1-8 in string, 0-indexed)
    weights = [8, 7, 6, 5, 4, 3, 2, 1]
    for i, weight in enumerate(weights):
        total += int(id_str[i + 1]) * weight

    # Add check digit (last digit)
    total += int(id_str[9])

    return total % 10 == 0


def india_aadhaar_valid(value: str) -> bool:
    """
    Verify India Aadhaar number using Verhoeff checksum algorithm.

    Aadhaar is a 12-digit number where the last digit is a Verhoeff check digit.
    The Verhoeff algorithm uses multiplication and permutation tables.

    Additional validations:
    - First digit cannot be 0 or 1
    - Cannot be all same digits

    Args:
        value: Aadhaar number string (12 digits, may have hyphens/spaces)

    Returns:
        True if valid, False otherwise
    """
    # Remove separators
    digits_only = "".join(c for c in value if c.isdigit())

    if len(digits_only) != 12:
        return False

    # First digit cannot be 0 or 1
    if digits_only[0] in ("0", "1"):
        return False

    # Reject all same digits
    if len(set(digits_only)) == 1:
        return False

    # Verhoeff multiplication table
    d = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
        [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
        [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
        [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
        [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
        [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
        [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
        [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
        [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
    ]

    # Verhoeff permutation table
    p = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
        [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
        [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
        [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
        [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
        [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
        [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
    ]

    # Calculate Verhoeff checksum
    c = 0
    reversed_digits = digits_only[::-1]
    for i, char in enumerate(reversed_digits):
        c = d[c][p[i % 8][int(char)]]

    return c == 0


def india_pan_valid(value: str) -> bool:
    """
    Verify India PAN (Permanent Account Number) format.

    Format: AAAAA9999A (5 letters + 4 digits + 1 letter)

    The 4th character indicates entity type:
    - A: Association of Persons (AOP)
    - B: Body of Individuals (BOI)
    - C: Company
    - F: Firm
    - G: Government
    - H: Hindu Undivided Family (HUF)
    - L: Local Authority
    - J: Artificial Juridical Person
    - P: Individual (Person)
    - T: Trust (AOP)
    - K: Krishi (not found often)

    The 5th character is typically the first letter of surname/name.

    Args:
        value: PAN string

    Returns:
        True if valid PAN format, False otherwise
    """
    pan = value.replace(" ", "").upper()

    if len(pan) != 10:
        return False

    # Check format: 5 letters + 4 digits + 1 letter
    if not (pan[:5].isalpha() and pan[5:9].isdigit() and pan[9].isalpha()):
        return False

    # Valid 4th character (entity type)
    valid_entity_types = {"A", "B", "C", "F", "G", "H", "J", "K", "L", "P", "T"}
    if pan[3] not in valid_entity_types:
        return False

    # Reject obvious test patterns
    if pan[:5] in ("AAAAA", "ABCDE", "XXXXX", "ZZZZZ"):
        return False

    return True


def kr_business_registration_valid(value: str) -> bool:
    """
    Verify Korean Business Registration Number (사업자등록번호) checksum.

    Format: XXX-XX-XXXXX (10 digits)

    Checksum algorithm:
    1. Multiply each of first 9 digits by weights [1,3,7,1,3,7,1,3,5]
    2. For the 9th position (weight 5), also add (digit * 5) // 10
    3. Sum all products
    4. Check digit = (10 - (sum % 10)) % 10

    Args:
        value: Business registration number string

    Returns:
        True if valid, False otherwise
    """
    # Remove hyphens
    digits_only = "".join(c for c in value if c.isdigit())

    if len(digits_only) != 10:
        return False

    # Reject all same digits or sequential
    if len(set(digits_only)) == 1:
        return False

    # Checksum calculation
    weights = [1, 3, 7, 1, 3, 7, 1, 3, 5]
    total = 0

    for i in range(9):
        digit = int(digits_only[i])
        total += digit * weights[i]
        # Special handling for 9th position
        if i == 8:
            total += (digit * 5) // 10

    check_digit = (10 - (total % 10)) % 10

    return int(digits_only[9]) == check_digit


def ipv4_public(value: str) -> bool:
    """
    Verify IPv4 address is a public (routable) address.

    Rejects:
    - Private ranges: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
    - Loopback: 127.0.0.0/8
    - Link-local: 169.254.0.0/16
    - Documentation: 192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24
    - Broadcast: 255.255.255.255
    - Reserved: 0.0.0.0/8, 240.0.0.0/4

    Args:
        value: IPv4 address string (e.g., "192.168.1.1")

    Returns:
        True if public IP, False if private/reserved
    """
    try:
        parts = value.split(".")
        if len(parts) != 4:
            return False

        octets = [int(p) for p in parts]

        # Validate octets are in range
        if not all(0 <= o <= 255 for o in octets):
            return False

        first, second, third, fourth = octets

        # 0.0.0.0/8 - Current network
        if first == 0:
            return False

        # 10.0.0.0/8 - Private
        if first == 10:
            return False

        # 127.0.0.0/8 - Loopback
        if first == 127:
            return False

        # 169.254.0.0/16 - Link-local
        if first == 169 and second == 254:
            return False

        # 172.16.0.0/12 - Private (172.16.0.0 - 172.31.255.255)
        if first == 172 and 16 <= second <= 31:
            return False

        # 192.0.2.0/24 - Documentation (TEST-NET-1)
        if first == 192 and second == 0 and third == 2:
            return False

        # 192.168.0.0/16 - Private
        if first == 192 and second == 168:
            return False

        # 198.51.100.0/24 - Documentation (TEST-NET-2)
        if first == 198 and second == 51 and third == 100:
            return False

        # 203.0.113.0/24 - Documentation (TEST-NET-3)
        if first == 203 and second == 0 and third == 113:
            return False

        # 224.0.0.0/4 - Multicast
        if 224 <= first <= 239:
            return False

        # 240.0.0.0/4 - Reserved for future use
        if first >= 240:
            return False

        return True

    except (ValueError, AttributeError):
        return False


def not_repeating_pattern(value: str) -> bool:
    """
    Verify that a value is not a simple repeating pattern.

    Rejects patterns like:
    - All same character: "1111111", "AAAAAAA"
    - Two-char repeat: "121212", "ABABAB"
    - Three-char repeat: "123123123"
    - Sequential: "12345678", "ABCDEFGH"

    Args:
        value: String to check

    Returns:
        True if NOT a repeating pattern, False if is a repeating pattern
    """
    if not value:
        return True

    # Normalize for numeric strings (remove hyphens, spaces)
    normalized = "".join(c for c in value if c.isdigit())
    if not normalized:
        # If no digits, use the original string for basic checks
        normalized = value

    # Check all same character (VERY IMPORTANT for 010-0000-0000)
    if len(set(normalized)) == 1:
        return False

    if len(normalized) < 4:
        return True

    # Check for sequential digits
    if normalized.isdigit() and len(normalized) >= 4:
        is_ascending = all(
            int(normalized[i]) == int(normalized[i - 1]) + 1
            for i in range(1, len(normalized))
        )
        is_descending = all(
            int(normalized[i]) == int(normalized[i - 1]) - 1
            for i in range(1, len(normalized))
        )
        if is_ascending or is_descending:
            return False

    # Check for 2-char repeating pattern
    if len(normalized) >= 4:
        pattern2 = normalized[:2]
        if pattern2 * (len(normalized) // 2) == normalized[
            : len(pattern2) * (len(normalized) // 2)
        ]:
            if (
                len(normalized) % 2 == 0
                or normalized[-(len(normalized) % 2) :] == pattern2[: len(normalized) % 2]
            ):
                return False

    # Check for 3-char repeating pattern
    if len(normalized) >= 6:
        pattern3 = normalized[:3]
        if pattern3 * (len(normalized) // 3) == normalized[
            : len(pattern3) * (len(normalized) // 3)
        ]:
            if (
                len(normalized) % 3 == 0
                or normalized[-(len(normalized) % 3) :] == pattern3[: len(normalized) % 3]
            ):
                return False

    return True


def credit_card_bin_valid(value: str) -> bool:
    """
    Verify credit card number has valid BIN (Bank Identification Number) prefix.

    Checks if the first 1-6 digits match known card network ranges:
    - Visa: 4
    - Mastercard: 51-55, 2221-2720
    - American Express: 34, 37
    - Discover: 6011, 622126-622925, 644-649, 65
    - JCB: 3528-3589
    - UnionPay: 62
    - Diners Club: 36, 38, 300-305

    Also applies Luhn check.

    Args:
        value: Credit card number string

    Returns:
        True if valid BIN and Luhn, False otherwise
    """
    # Remove non-digits
    digits = "".join(c for c in value if c.isdigit())

    if len(digits) < 13 or len(digits) > 19:
        return False

    # Check BIN ranges
    valid_bin = False

    # Visa: starts with 4
    if digits[0] == "4":
        valid_bin = True

    # Mastercard: 51-55 or 2221-2720
    elif len(digits) >= 2:
        prefix2 = int(digits[:2])
        if 51 <= prefix2 <= 55:
            valid_bin = True
        elif len(digits) >= 4:
            prefix4 = int(digits[:4])
            if 2221 <= prefix4 <= 2720:
                valid_bin = True

    # American Express: 34 or 37
    if not valid_bin and len(digits) >= 2:
        prefix2 = int(digits[:2])
        if prefix2 in (34, 37):
            valid_bin = True

    # Discover: 6011, 622126-622925, 644-649, 65
    if not valid_bin:
        if digits.startswith("6011"):
            valid_bin = True
        elif digits.startswith("65"):
            valid_bin = True
        elif len(digits) >= 3:
            prefix3 = int(digits[:3])
            if 644 <= prefix3 <= 649:
                valid_bin = True
        if not valid_bin and len(digits) >= 6:
            prefix6 = int(digits[:6])
            if 622126 <= prefix6 <= 622925:
                valid_bin = True

    # JCB: 3528-3589
    if not valid_bin and len(digits) >= 4:
        prefix4 = int(digits[:4])
        if 3528 <= prefix4 <= 3589:
            valid_bin = True

    # UnionPay: 62
    if not valid_bin and digits.startswith("62"):
        valid_bin = True

    # Diners Club: 36, 38, 300-305
    if not valid_bin and len(digits) >= 2:
        prefix2 = int(digits[:2])
        if prefix2 in (36, 38):
            valid_bin = True
        elif len(digits) >= 3:
            prefix3 = int(digits[:3])
            if 300 <= prefix3 <= 305:
                valid_bin = True

    if not valid_bin:
        return False

    # Also verify Luhn checksum
    return luhn(digits)


def _is_valid_date(year: int, month: int, day: int) -> bool:
    """
    Helper function to validate a date.

    Args:
        year: Full year (e.g., 1990, 2005)
        month: Month (1-12)
        day: Day (1-31)

    Returns:
        True if valid date, False otherwise
    """
    if month < 1 or month > 12:
        return False
    if day < 1 or day > 31:
        return False

    # Days per month (index 0 unused, Feb assumes leap year for simplicity)
    days_in_month = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    if day > days_in_month[month]:
        return False

    # More precise Feb check for non-leap years
    if month == 2 and day == 29:
        is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
        if not is_leap:
            return False

    return True


def kr_rrn_valid(value: str) -> bool:
    """
    Verify Korean Resident Registration Number (주민등록번호).

    Format: YYMMDD-NXXXXXX (13 digits)
    - YY: Year (00-99)
    - MM: Month (01-12)
    - DD: Day (01-31, validated per month)
    - N: Gender/Century indicator
        - 1: Male born 1900-1999
        - 2: Female born 1900-1999
        - 3: Male born 2000-2099
        - 4: Female born 2000-2099
    - XXXXXX: Serial number + checksum

    Args:
        value: RRN string (e.g., "900101-1234567" or "9001011234567")

    Returns:
        True if valid RRN format, False otherwise
    """
    # Remove hyphen
    digits = "".join(c for c in value if c.isdigit())

    if len(digits) != 13:
        return False

    # Parse date components
    try:
        yy = int(digits[0:2])
        month = int(digits[2:4])
        day = int(digits[4:6])
        gender_century = int(digits[6])
    except ValueError:
        return False

    # Validate gender/century indicator (1-4 for Korean citizens)
    if gender_century < 1 or gender_century > 4:
        return False

    # Determine full year from gender/century indicator
    if gender_century in (1, 2):  # 1900s
        year = 1900 + yy
    else:  # 3, 4 = 2000s
        year = 2000 + yy

    # Validate date
    if not _is_valid_date(year, month, day):
        return False

    # Reject obviously fake patterns
    if len(set(digits)) == 1:  # All same digits
        return False

    # Optional: Verify checksum (RRN has a weighted checksum)
    # Weights: 2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5
    weights = [2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5]
    total = sum(int(digits[i]) * weights[i] for i in range(12))
    check_digit = (11 - (total % 11)) % 10

    return int(digits[12]) == check_digit


def kr_alien_registration_valid(value: str) -> bool:
    """
    Verify Korean Alien Registration Number (외국인등록번호).

    Format: YYMMDD-NXXXXXX (13 digits)
    - YY: Year (00-99)
    - MM: Month (01-12)
    - DD: Day (01-31, validated per month)
    - N: Gender/Century indicator for foreigners
        - 5: Male born 1900-1999
        - 6: Female born 1900-1999
        - 7: Male born 2000-2099
        - 8: Female born 2000-2099

    Args:
        value: Alien registration number string

    Returns:
        True if valid format, False otherwise
    """
    # Remove hyphen
    digits = "".join(c for c in value if c.isdigit())

    if len(digits) != 13:
        return False

    # Parse date components
    try:
        yy = int(digits[0:2])
        month = int(digits[2:4])
        day = int(digits[4:6])
        gender_century = int(digits[6])
    except ValueError:
        return False

    # Validate gender/century indicator (5-8 for foreigners)
    if gender_century < 5 or gender_century > 8:
        return False

    # Determine full year from gender/century indicator
    if gender_century in (5, 6):  # 1900s
        year = 1900 + yy
    else:  # 7, 8 = 2000s
        year = 2000 + yy

    # Validate date
    if not _is_valid_date(year, month, day):
        return False

    # Reject obviously fake patterns
    if len(set(digits)) == 1:
        return False

    # Checksum: Similar to RRN but with a +2 offset
    # Weights: 2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5
    weights = [2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5]
    total = sum(int(digits[i]) * weights[i] for i in range(12))
    check_digit = (11 - (total % 11)) % 10
    check_digit = (check_digit + 2) % 10

    return int(digits[12]) == check_digit


def jp_driver_license_valid(value: str) -> bool:
    """
    Verify Japanese Driver's License Number (運転免許証番号).

    Format: 12 digits
    - Digits 1-2: Region code (10-99)
    - Digits 3-4: Last 2 digits of the year of first issuance
    - Digits 5-10: Serial number
    - Digit 11: Check digit (Modulus 11)
    - Digit 12: Re-issuance count

    Args:
        value: Driver's license number string

    Returns:
        True if valid, False otherwise
    """
    # Remove hyphens/spaces
    digits = "".join(c for c in value if c.isdigit())

    if len(digits) != 12:
        return False

    # Region code (10-99)
    region_code = int(digits[0:2])
    if region_code < 10:
        return False

    # Check digit (11th digit) calculation
    # Weights for first 10 digits
    weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(digits[i]) * weights[i] for i in range(10))
    remainder = total % 11

    if remainder <= 1:
        expected_check = 0
    else:
        expected_check = 11 - remainder

    return int(digits[10]) == expected_check


def jp_my_number_valid(value: str) -> bool:
    """
    Verify Japanese My Number (マイナンバー) checksum.

    Format: 12 digits with the last digit being a check digit.

    Checksum algorithm:
    - Weights for positions 1-11: [6,5,4,3,2,7,6,5,4,3,2]
    - Sum = Σ(digit[i] * weight[i])
    - Remainder = Sum % 11
    - Check digit = 0 if remainder <= 1, else (11 - remainder)

    Args:
        value: My Number string (12 digits, may have hyphens)

    Returns:
        True if valid checksum, False otherwise
    """
    # Remove separators
    digits = "".join(c for c in value if c.isdigit())

    if len(digits) != 12:
        return False

    # Reject all same digits
    if len(set(digits)) == 1:
        return False

    # Reject sequential patterns
    if digits in ("123456789012", "012345678901"):
        return False

    # Calculate checksum
    # Weights for positions 0-10 (first 11 digits)
    weights = [6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 2]

    total = sum(int(digits[i]) * weights[i] for i in range(11))
    remainder = total % 11

    if remainder <= 1:
        expected_check = 0
    else:
        expected_check = 11 - remainder

    return int(digits[11]) == expected_check


def kr_corporate_registration_valid(value: str) -> bool:
    """
    Verify Korean Corporate Registration Number (법인등록번호) checksum.

    Format: XXXXXX-XXXXXXX (13 digits)

    Args:
        value: Corporate registration number string

    Returns:
        True if valid, False otherwise
    """
    # Remove hyphen
    digits = "".join(c for c in value if c.isdigit())

    if len(digits) != 13:
        return False

    # Checksum calculation
    weights = [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2]
    total = 0

    for i in range(12):
        total += int(digits[i]) * weights[i]

    check_digit = (10 - (total % 10)) % 10
    return int(digits[12]) == check_digit

    return int(digits[12]) == check_digit


def spain_dni_valid(value: str) -> bool:
    """
    Verify Spanish DNI (Documento Nacional de Identidad) checksum.

    Format: 8 digits + 1 letter
    The letter is calculated as: number % 23 -> letter from sequence

    Letter sequence: TRWAGMYFPDXBNJZSQVHLCKE

    Args:
        value: DNI string (e.g., "12345678Z")

    Returns:
        True if valid, False otherwise
    """
    # Remove spaces
    dni = value.replace(" ", "").upper()

    if len(dni) != 9:
        return False

    # First 8 must be digits, last must be letter
    if not dni[:8].isdigit() or not dni[8].isalpha():
        return False

    # Letter sequence for checksum
    letters = "TRWAGMYFPDXBNJZSQVHLCKE"

    number = int(dni[:8])
    expected_letter = letters[number % 23]

    return dni[8] == expected_letter


def spain_nie_valid(value: str) -> bool:
    """
    Verify Spanish NIE (Número de Identidad de Extranjero) checksum.

    Format: X/Y/Z + 7 digits + 1 letter
    - X is replaced with 0
    - Y is replaced with 1
    - Z is replaced with 2
    Then same checksum as DNI.

    Args:
        value: NIE string (e.g., "X1234567L")

    Returns:
        True if valid, False otherwise
    """
    # Remove spaces
    nie = value.replace(" ", "").upper()

    if len(nie) != 9:
        return False

    # First char must be X, Y, or Z
    if nie[0] not in ("X", "Y", "Z"):
        return False

    # Middle 7 must be digits
    if not nie[1:8].isdigit():
        return False

    # Last must be letter
    if not nie[8].isalpha():
        return False

    # Replace first letter with number
    replacements = {"X": "0", "Y": "1", "Z": "2"}
    number_str = replacements[nie[0]] + nie[1:8]

    # Letter sequence for checksum (same as DNI)
    letters = "TRWAGMYFPDXBNJZSQVHLCKE"

    number = int(number_str)
    expected_letter = letters[number % 23]

    return nie[8] == expected_letter


def netherlands_bsn_valid(value: str) -> bool:
    """
    Verify Dutch BSN (Burgerservicenummer) using 11-proof algorithm.

    Format: 8 or 9 digits

    Algorithm (for 9 digits):
    - Multiply digits by weights [9, 8, 7, 6, 5, 4, 3, 2, -1]
    - Sum must be divisible by 11

    For 8 digits, prepend 0 and use same algorithm.

    Args:
        value: BSN string (8 or 9 digits)

    Returns:
        True if valid 11-proof, False otherwise
    """
    digits = "".join(c for c in value if c.isdigit())

    if len(digits) == 8:
        digits = "0" + digits
    elif len(digits) != 9:
        return False

    # Reject all same digits
    if len(set(digits)) == 1:
        return False

    # 11-proof check
    weights = [9, 8, 7, 6, 5, 4, 3, 2, -1]
    total = sum(int(digits[i]) * weights[i] for i in range(9))

    return total % 11 == 0


def poland_pesel_valid(value: str) -> bool:
    """
    Verify Polish PESEL checksum.

    Format: 11 digits (YYMMDDXXXXY)
    - YY: Year
    - MM: Month (special encoding for century)
    - DD: Day
    - XXXX: Serial + gender
    - Y: Check digit

    Month encoding:
    - 1900s: 01-12
    - 2000s: 21-32 (add 20)
    - 2100s: 41-52 (add 40)
    - 2200s: 61-72 (add 60)
    - 1800s: 81-92 (add 80)

    Checksum: weights [1,3,7,9,1,3,7,9,1,3], sum % 10 = 0

    Args:
        value: PESEL string (11 digits)

    Returns:
        True if valid, False otherwise
    """
    digits = "".join(c for c in value if c.isdigit())

    if len(digits) != 11:
        return False

    # Reject all same digits
    if len(set(digits)) == 1:
        return False

    # Parse and validate date
    try:
        yy = int(digits[0:2])
        mm = int(digits[2:4])
        dd = int(digits[4:6])
    except ValueError:
        return False

    # Decode month and century
    if 1 <= mm <= 12:
        year = 1900 + yy
        month = mm
    elif 21 <= mm <= 32:
        year = 2000 + yy
        month = mm - 20
    elif 41 <= mm <= 52:
        year = 2100 + yy
        month = mm - 40
    elif 61 <= mm <= 72:
        year = 2200 + yy
        month = mm - 60
    elif 81 <= mm <= 92:
        year = 1800 + yy
        month = mm - 80
    else:
        return False

    # Validate date
    if not _is_valid_date(year, month, dd):
        return False

    # Checksum verification
    weights = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3]
    total = sum(int(digits[i]) * weights[i] for i in range(10))
    check_digit = (10 - (total % 10)) % 10

    return int(digits[10]) == check_digit


def sweden_personnummer_valid(value: str) -> bool:
    """
    Verify Swedish Personnummer using Luhn algorithm.

    Format: YYYYMMDD-XXXX or YYMMDD-XXXX (10 or 12 digits)
    The last 4 digits include a Luhn check digit.

    For Luhn, only the last 10 digits (YYMMDDXXXX) are used.

    Args:
        value: Personnummer string

    Returns:
        True if valid Luhn checksum, False otherwise
    """
    # Remove separators
    digits = "".join(c for c in value if c.isdigit())

    if len(digits) == 12:
        # Full format YYYYMMDDXXXX - use last 10 digits
        digits = digits[2:]
    elif len(digits) != 10:
        return False

    # Parse and validate date
    try:
        mm = int(digits[2:4])
        dd = int(digits[4:6])
    except ValueError:
        return False

    # Basic date validation (assume 1900s or 2000s)
    if mm < 1 or mm > 12:
        return False
    if dd < 1 or dd > 31:
        return False

    # Luhn algorithm on all 10 digits
    return luhn(digits)


def france_insee_valid(value: str) -> bool:
    """
    Verify French INSEE/NIR number (Numéro de Sécurité Sociale).

    Format: 15 digits
    - 1: Sex (1=male, 2=female)
    - 2-3: Year of birth
    - 4-5: Month of birth (01-12)
    - 6-7: Department (01-95, 2A, 2B for Corsica, 97-99 for overseas)
    - 8-10: Commune code
    - 11-13: Order number
    - 14-15: Check digits (97 - (first 13 digits % 97))

    Args:
        value: INSEE number string (15 digits, may have spaces)

    Returns:
        True if valid, False otherwise
    """
    # Remove spaces
    cleaned = value.replace(" ", "")

    if len(cleaned) != 15:
        return False

    # Handle Corsica (2A, 2B)
    # For checksum calculation, 2A -> 19, 2B -> 18
    if cleaned[5:7].upper() == "2A":
        calc_str = cleaned[:5] + "19" + cleaned[7:]
    elif cleaned[5:7].upper() == "2B":
        calc_str = cleaned[:5] + "18" + cleaned[7:]
    else:
        calc_str = cleaned

    # Verify all digits
    if not calc_str.isdigit():
        return False

    # Sex must be 1 or 2
    sex = int(calc_str[0])
    if sex not in (1, 2):
        return False

    # Month validation (01-12)
    month = int(calc_str[3:5])
    if month < 1 or month > 12:
        return False

    # Calculate checksum
    # Check digits = 97 - (first 13 digits % 97)
    base_number = int(calc_str[:13])
    expected_check = 97 - (base_number % 97)
    actual_check = int(calc_str[13:15])

    return actual_check == expected_check


def belgium_rrn_valid(value: str) -> bool:
    """
    Verify Belgian Rijksregisternummer (National Register Number).

    Format: YYMMDD-XXX-CC (11 digits)
    - YYMMDD: Birth date
    - XXX: Counter (odd for male, even for female)
    - CC: Check digits = 97 - ((YYMMDDXXX) % 97)

    For people born in 2000+, prepend "2" to the number for checksum.

    Args:
        value: Belgian RRN string

    Returns:
        True if valid, False otherwise
    """
    # Remove separators
    digits = "".join(c for c in value if c.isdigit())

    if len(digits) != 11:
        return False

    # Parse date
    try:
        mm = int(digits[2:4])
        dd = int(digits[4:6])
    except ValueError:
        return False

    # Basic date validation
    if mm < 1 or mm > 12:
        return False
    if dd < 1 or dd > 31:
        return False

    # Get the base number and check digits
    base_9 = int(digits[:9])
    check_digits = int(digits[9:11])

    # Try 1900s calculation first
    expected_check_1900 = 97 - (base_9 % 97)

    if check_digits == expected_check_1900:
        return True

    # Try 2000s calculation (prepend "2")
    base_9_2000 = int("2" + digits[:9])
    expected_check_2000 = 97 - (base_9_2000 % 97)

    return check_digits == expected_check_2000


def finland_hetu_valid(value: str) -> bool:
    """
    Verify Finnish HETU (Henkilötunnus).

    Format: DDMMYYCZZZQ
    - DDMMYY: Birth date
    - C: Century sign (+ for 1800s, - for 1900s, A for 2000s)
    - ZZZ: Individual number (odd for male, even for female)
    - Q: Check character

    Check character: (DDMMYYZZZ as number) % 31 -> character from sequence
    Sequence: 0123456789ABCDEFHJKLMNPRSTUVWXY (excludes G, I, O, Q, Z)

    Args:
        value: HETU string (e.g., "010190-123A")

    Returns:
        True if valid, False otherwise
    """
    hetu = value.replace(" ", "").upper()

    if len(hetu) != 11:
        return False

    # Parse components
    try:
        dd = int(hetu[0:2])
        mm = int(hetu[2:4])
        yy = int(hetu[4:6])
        century_sign = hetu[6]
        individual = hetu[7:10]
        check_char = hetu[10]
    except (ValueError, IndexError):
        return False

    # Validate century sign
    if century_sign not in ("+", "-", "A"):
        return False

    # Validate individual number is digits
    if not individual.isdigit():
        return False

    # Determine year
    if century_sign == "+":
        year = 1800 + yy
    elif century_sign == "-":
        year = 1900 + yy
    else:  # 'A'
        year = 2000 + yy

    # Validate date
    if not _is_valid_date(year, mm, dd):
        return False

    # Check character calculation
    check_sequence = "0123456789ABCDEFHJKLMNPRSTUVWXY"

    # Combine DDMMYYZZZ as a single number
    number_str = hetu[0:6] + individual
    number = int(number_str)
    expected_check = check_sequence[number % 31]

    return check_char == expected_check


def jp_corporate_number_valid(value: str) -> bool:
    """
    Verify Japanese Corporate Number (法人番号) checksum.
    13 digits, the 1st digit is the check digit.
    Weights 1-2-1-2... for positions 1-12 of the base number.
    Check digit = 9 - (sum % 9).
    """
    digits = "".join(c for c in value if c.isdigit())
    if len(digits) != 13:
        return False

    check_digit = int(digits[0])
    base_digits = [int(d) for d in digits[1:]]

    # Weights: leftmost of base is weight 2, then 1, 2, 1...
    # index 11 (rightmost) weight 1, index 10 weight 2...
    total = 0
    for i in range(12):
        weight = 2 if (12 - i) % 2 == 0 else 1
        total += base_digits[i] * weight

    remainder = total % 9
    expected_check = 9 - remainder
    return check_digit == expected_check


def tw_ubn_valid(value: str) -> bool:
    """
    Verify Taiwan Unified Business Number (UBN).
    8 digits, checksum weights: 1,2,1,2,1,2,4,1.
    """
    digits = "".join(c for c in value if c.isdigit())
    if len(digits) != 8:
        return False

    weights = [1, 2, 1, 2, 1, 2, 4, 1]
    total = 0
    for i in range(8):
        prod = int(digits[i]) * weights[i]
        total += (prod // 10) + (prod % 10)

    if total % 10 == 0:
        return True

    # Special case: if 7th digit is 7 and check fails
    if digits[6] == "7" and (total + 1) % 10 == 0:
        return True

    return False


def us_npi_valid(value: str) -> bool:
    """
    Verify US National Provider Identifier (NPI).
    10 digits, Luhn check on '80840' + first 9 digits.
    """
    digits = "".join(c for c in value if c.isdigit())
    if len(digits) != 10:
        return False

    # Prefix 80840 + first 9 digits
    full_str = "80840" + digits[:9]

    # Luhn calculation for first 14 digits (80840 + 9 digits)
    luhn_total = 0
    rev_digits = [int(d) for d in full_str[::-1]]
    for i, d in enumerate(rev_digits):
        # Even positions from right (0-indexed) are doubled because
        # the check digit at position -1 would be the first.
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        luhn_total += d

    expected_check = (10 - (luhn_total % 10)) % 10
    return int(digits[9]) == expected_check


def uk_nino_valid(value: str) -> bool:
    """
    Verify UK National Insurance Number (NINO).
    Format: 2 letters, 6 digits, 1 letter.
    """
    import re

    # Standard NINO regex
    pattern = r"^[A-CEGHJ-PR-TW-Z][A-CEGHJ-NPR-TW-Z]\d{6}[A-D]$"
    if not re.match(pattern, value.upper()):
        return False

    # Exclude certain prefixes
    prefix = value[:2].upper()
    if prefix in ("BG", "GB", "KN", "NK", "NT", "TN", "ZZ"):
        return False

    return True


def swift_bic_valid(value: str) -> bool:
    """Verify SWIFT/BIC code (8 or 11 chars)."""
    val = value.replace(" ", "").upper()
    if len(val) not in (8, 11):
        return False

    import re

    return bool(re.match(r"^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$", val))


def aws_access_key_valid(value: str) -> bool:
    """Verify AWS Access Key (Starts with AKIA/ASIA, length 20)."""
    if len(value) != 20:
        return False
    if not (value.startswith("AKIA") or value.startswith("ASIA")):
        return False
    return all(c.isalnum() for c in value)


def google_api_key_valid(value: str) -> bool:
    """Verify Google API Key (Starts with AIza, length 39)."""
    if len(value) != 39:
        return False
    if not value.startswith("AIza"):
        return False
    import re

    return bool(re.match(r"^[A-Za-z0-9_-]{39}$", value))


def crypto_btc_valid(value: str) -> bool:
    """Verify Bitcoin address (Base58, length 26-35)."""
    if not (26 <= len(value) <= 35):
        return False

    # Base58 character set: no 0, O, I, l
    base58_chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    return all(c in base58_chars for c in value)


def crypto_eth_valid(value: str) -> bool:
    """Verify Ethereum address (Starts with 0x, 40 hex chars)."""
    if len(value) != 42:
        return False
    if not value.startswith("0x"):
        return False

    import re

    return bool(re.match(r"^0x[0-9a-fA-F]{40}$", value))


def imei_valid(value: str) -> bool:
    """
    Verify 15-digit IMEI using Luhn algorithm.

    Args:
        value: IMEI string

    Returns:
        True if valid 15-digit IMEI, False otherwise
    """
    digits_only = "".join(c for c in value if c.isdigit())
    if len(digits_only) != 15:
        return False

    # Check for all zeros or obvious test patterns
    if len(set(digits_only)) == 1:
        return False

    return luhn(digits_only)


def mac_address_valid(value: str) -> bool:
    """
    Verify MAC address format and common exclusion rules.

    Args:
        value: MAC address string

    Returns:
        True if likely a valid hardware MAC address, False otherwise
    """
    # Normalize: remove separators
    mac = value.replace(":", "").replace("-", "").replace(" ", "").upper()

    if len(mac) != 12:
        return False

    # Reject broadcast and null MACs
    if mac == "FFFFFFFFFFFF" or mac == "000000000000":
        return False

    return True


def kr_vehicle_registration_valid(value: str) -> bool:
    """
    Verify Korean vehicle registration plate format.

    Supports:
    - New format: 123가 4567 (3 digits + Hangul + 4 digits)
    - Old format: 12가 3456 (2 digits + Hangul + 4 digits)

    Valid Hangul characters for private vehicles:
    가, 나, 다, 라, 마, 거, 너, 더, 러, 머, 버, 서, 어, 저, 고, 노, 도, 로, 모, 보, 소, 오, 조, 구, 누, 두, 루, 무, 부, 수, 우, 주
    """
    import re

    # Remove spaces
    val = value.replace(" ", "")

    # Private vehicle Hangul set
    valid_hangul = "가나다라마거너더러머버서어저고노도로모보소오조구누두루무부수우주"
    # Commercial/Special: 하, 허, 호 (Rental), 바, 사, 아, 자 (Taxi/Bus), 배 (Delivery)
    valid_hangul += "하허호바사아자배"

    # Use regex to validate parts
    # Pattern: 2-3 digits + 1 Hangul + 4 digits
    pattern = rf"^(\d{{2,3}})([{valid_hangul}])(\d{{4}})$"
    if re.match(pattern, val):
        return True

    return False


def kr_pccc_valid(value: str) -> bool:
    """
    Verify Korean Personal Customs Clearance Code (PCCC).
    Format: P + 12 digits.
    The last digit is a checksum (currently simplified check).
    """
    if not value or len(value) != 13:
        return False

    if value[0].upper() != "P":
        return False

    if not value[1:].isdigit():
        return False

    return True


def kr_driver_license_valid(value: str) -> bool:
    """
    Verify Korean Driver's License Number.
    Supports both formats:
    - New (12 digits): XX-XX-XXXXXX-XX
    - Old (10 digits): XX-XXXXXX-XX
    The first 2 digits are region codes (11-28).
    """
    digits_only = "".join(c for c in value if c.isdigit())
    if len(digits_only) not in (10, 12):
        return False

    # Reject all same digits
    if len(set(digits_only)) == 1:
        return False

    region_code = int(digits_only[:2])
    valid_regions = {11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28}

    if region_code not in valid_regions:
        return False

    return True


def latitude_valid(value: str) -> bool:
    """Verify decimal latitude is within -90 to 90 range."""
    try:
        lat = float(value)
        return -90.0 <= lat <= 90.0
    except ValueError:
        return False


def longitude_valid(value: str) -> bool:
    """Verify decimal longitude is within -180 to 180 range."""
    try:
        lon = float(value)
        return -180.0 <= lon <= 180.0
    except ValueError:
        return False


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
    "contains_letter": contains_letter,
    "us_ssn_valid": us_ssn_valid,
    "cjk_name_standalone": cjk_name_standalone,
    # CJK name verification with surname checking
    "chinese_name_valid": chinese_name_valid,
    "korean_name_valid": korean_name_valid,
    "japanese_name_kanji_valid": japanese_name_kanji_valid,
    # National ID verification functions
    "cn_national_id_valid": cn_national_id_valid,
    "tw_national_id_valid": tw_national_id_valid,
    "india_aadhaar_valid": india_aadhaar_valid,
    "india_pan_valid": india_pan_valid,
    "kr_business_registration_valid": kr_business_registration_valid,
    "ipv4_public": ipv4_public,
    "not_repeating_pattern": not_repeating_pattern,
    "credit_card_bin_valid": credit_card_bin_valid,
    # Korean RRN and related
    "kr_rrn_valid": kr_rrn_valid,
    "kr_alien_registration_valid": kr_alien_registration_valid,
    "kr_corporate_registration_valid": kr_corporate_registration_valid,
    "jp_driver_license_valid": jp_driver_license_valid,
    # Zipcode verification (JP, CN, TW, IN)
    "jp_zipcode_valid": jp_zipcode_valid,
    "cn_zipcode_valid": cn_zipcode_valid,
    "tw_zipcode_valid": tw_zipcode_valid,
    "in_pincode_valid": in_pincode_valid,
    # Japanese
    "jp_my_number_valid": jp_my_number_valid,
    "jp_corporate_number_valid": jp_corporate_number_valid,
    "tw_ubn_valid": tw_ubn_valid,
    "us_npi_valid": us_npi_valid,
    "uk_nino_valid": uk_nino_valid,
    "swift_bic_valid": swift_bic_valid,
    "aws_access_key_valid": aws_access_key_valid,
    "google_api_key_valid": google_api_key_valid,
    "crypto_btc_valid": crypto_btc_valid,
    "crypto_eth_valid": crypto_eth_valid,
    "imei_valid": imei_valid,
    "mac_address_valid": mac_address_valid,
    "kr_vehicle_registration_valid": kr_vehicle_registration_valid,
    "kr_pccc_valid": kr_pccc_valid,
    "kr_driver_license_valid": kr_driver_license_valid,
    "latitude_valid": latitude_valid,
    "longitude_valid": longitude_valid,
    # European IDs
    "spain_dni_valid": spain_dni_valid,
    "spain_nie_valid": spain_nie_valid,
    "netherlands_bsn_valid": netherlands_bsn_valid,
    "poland_pesel_valid": poland_pesel_valid,
    "sweden_personnummer_valid": sweden_personnummer_valid,
    "france_insee_valid": france_insee_valid,
    "belgium_rrn_valid": belgium_rrn_valid,
    "finland_hetu_valid": finland_hetu_valid,
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
