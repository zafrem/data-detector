"""Verification functions for additional validation after regex matching.

This module re-exports verification functions from the centralized
verification library located in pattern-engine/verification/python/.

For the actual implementation and documentation, see:
pattern-engine/verification/python/verification.py
"""

import sys
from pathlib import Path

# Add pattern-engine to path if running from source (not installed package)
# This handles both Unix (with symlink) and Windows (without symlink support)
_pattern_engine_dir = Path(__file__).parent.parent.parent / "pattern-engine"
if _pattern_engine_dir.exists() and str(_pattern_engine_dir) not in sys.path:
    sys.path.insert(0, str(_pattern_engine_dir))

# Import all verification functions from the centralized location
from verification.python.verification import (  # noqa: E402
    contains_letter,
    dms_coordinate,
    generic_number_not_timestamp,
    get_verification_function,
    high_entropy_token,
    iban_mod97,
    korean_bank_account_valid,
    korean_zipcode_valid,
    luhn,
    not_timestamp,
    register_verification_function,
    unregister_verification_function,
    us_ssn_valid,
    us_zipcode_valid,
)

# Re-export all the imported functions for convenience
__all__ = [
    "iban_mod97",
    "luhn",
    "dms_coordinate",
    "high_entropy_token",
    "not_timestamp",
    "korean_zipcode_valid",
    "us_zipcode_valid",
    "korean_bank_account_valid",
    "generic_number_not_timestamp",
    "contains_letter",
    "us_ssn_valid",
    "get_verification_function",
    "register_verification_function",
    "unregister_verification_function",
]
