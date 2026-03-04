"""Verification functions for additional validation after regex matching.

This module re-exports verification functions from the centralized
verification library located in pattern-engine/verification/python/.

For the actual implementation and documentation, see:
pattern-engine/verification/python/verification.py
"""

import sys
from pathlib import Path
from typing import Optional

# Add pattern-engine to path if running from source (not installed package)
# This handles both Unix (with symlink) and Windows (without symlink support)
def _find_pattern_engine() -> Optional[Path]:
    # 1. Try relative to this file
    rel_path = Path(__file__).resolve().parent.parent.parent / "pattern-engine"
    if rel_path.exists():
        return rel_path
    
    # 2. Try relative to project root (CWD)
    cwd_path = Path.cwd() / "pattern-engine"
    if cwd_path.exists():
        return cwd_path
        
    # 3. Try common deployment paths (/var/task for Vercel)
    vercel_path = Path("/var/task/pattern-engine")
    if vercel_path.exists():
        return vercel_path
        
    return None

_pattern_engine_dir = _find_pattern_engine()
if _pattern_engine_dir and str(_pattern_engine_dir) not in sys.path:
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
