"""Verification functions for additional validation after regex matching.

This module re-exports verification functions from the centralized
verification library located in pattern-engine/verification/python/.

For the actual implementation and documentation, see:
pattern-engine/verification/python/verification.py
"""

import logging
import sys
from pathlib import Path
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Add pattern-engine directory to path so we can import verification module
_PATTERN_ENGINE_DIR = Path(__file__).parent.parent.parent / "pattern-engine"
if str(_PATTERN_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PATTERN_ENGINE_DIR))

# Import all verification functions from the centralized location
try:
    from verification.python.verification import (
        VERIFICATION_FUNCTIONS,
        contains_letter,
        dms_coordinate,
        generic_number_not_timestamp,
        get_verification_function as _get_verification_function,
        high_entropy_token,
        iban_mod97,
        korean_bank_account_valid,
        korean_zipcode_valid,
        luhn,
        not_timestamp,
        register_verification_function as _register_verification_function,
        unregister_verification_function as _unregister_verification_function,
        us_ssn_valid,
        us_zipcode_valid,
    )
except ImportError as e:
    logger.error(f"Failed to import verification functions from centralized location: {e}")
    logger.info("Falling back to local implementations")
    # If import fails, we need to provide fallback implementations
    # For now, we'll raise the error to make it clear something is wrong
    raise


# Re-export the imported functions
def iban_mod97(value: str) -> bool:
    """Re-exported from centralized verification library."""
    from verification.python.verification import iban_mod97 as _impl
    return _impl(value)


def luhn(value: str) -> bool:
    """Re-exported from centralized verification library."""
    from verification.python.verification import luhn as _impl
    return _impl(value)


def dms_coordinate(value: str) -> bool:
    """Re-exported from centralized verification library."""
    from verification.python.verification import dms_coordinate as _impl
    return _impl(value)


def high_entropy_token(value: str) -> bool:
    """Re-exported from centralized verification library."""
    from verification.python.verification import high_entropy_token as _impl
    return _impl(value)


def not_timestamp(value: str) -> bool:
    """Re-exported from centralized verification library."""
    from verification.python.verification import not_timestamp as _impl
    return _impl(value)


def korean_zipcode_valid(value: str) -> bool:
    """Re-exported from centralized verification library."""
    from verification.python.verification import korean_zipcode_valid as _impl
    return _impl(value)


def us_zipcode_valid(value: str) -> bool:
    """Re-exported from centralized verification library."""
    from verification.python.verification import us_zipcode_valid as _impl
    return _impl(value)


def korean_bank_account_valid(value: str) -> bool:
    """Re-exported from centralized verification library."""
    from verification.python.verification import korean_bank_account_valid as _impl
    return _impl(value)


def generic_number_not_timestamp(value: str) -> bool:
    """Re-exported from centralized verification library."""
    from verification.python.verification import generic_number_not_timestamp as _impl
    return _impl(value)


def contains_letter(value: str) -> bool:
    """Re-exported from centralized verification library."""
    from verification.python.verification import contains_letter as _impl
    return _impl(value)


def us_ssn_valid(value: str) -> bool:
    """Re-exported from centralized verification library."""
    from verification.python.verification import us_ssn_valid as _impl
    return _impl(value)


def get_verification_function(name: str) -> Optional[Callable[[str], bool]]:
    """Get verification function by name from centralized registry."""
    return _get_verification_function(name)


def register_verification_function(name: str, func: Callable[[str], bool]) -> None:
    """Register a custom verification function in centralized registry."""
    _register_verification_function(name, func)


def unregister_verification_function(name: str) -> bool:
    """Unregister a verification function from centralized registry."""
    return _unregister_verification_function(name)
