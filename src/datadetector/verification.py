"""Verification functions for additional validation after regex matching.

This module re-exports verification functions from the centralized
verification library located in pattern-engine/verification/python/.

For the actual implementation and documentation, see:
pattern-engine/verification/python/verification.py
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Add pattern-engine directory to path so we can import verification module
_PATTERN_ENGINE_DIR = Path(__file__).parent.parent.parent / "pattern-engine"
if str(_PATTERN_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PATTERN_ENGINE_DIR))

# Import all verification functions from the centralized location
try:
    from verification.python.verification import (
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
except ImportError as e:
    logger.error(f"Failed to import verification functions from centralized location: {e}")
    logger.info("Falling back to local implementations")
    # If import fails, we need to provide fallback implementations
    # For now, we'll raise the error to make it clear something is wrong
    raise


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
