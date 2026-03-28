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
    # src/datadetector/verification.py -> src/datadetector -> src -> root
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
    # Base/Common
    contains_letter,
    dms_coordinate,
    generic_number_not_timestamp,
    get_verification_function,
    high_entropy_token,
    iban_mod97,
    luhn,
    not_timestamp,
    register_verification_function,
    unregister_verification_function,
    # US
    us_ssn_valid,
    us_zipcode_valid,
    us_npi_valid,
    # KR
    korean_bank_account_valid,
    korean_zipcode_valid,
    kr_rrn_valid,
    kr_business_registration_valid,
    kr_corporate_registration_valid,
    kr_alien_registration_valid,
    # JP
    jp_zipcode_valid,
    jp_my_number_valid,
    jp_corporate_number_valid,
    # CN
    cn_national_id_valid,
    cn_zipcode_valid,
    # TW
    tw_national_id_valid,
    tw_zipcode_valid,
    tw_ubn_valid,
    # IN
    india_aadhaar_valid,
    india_pan_valid,
    in_pincode_valid,
    # EU
    france_insee_valid,
    spain_dni_valid,
    spain_nie_valid,
    netherlands_bsn_valid,
    poland_pesel_valid,
    sweden_personnummer_valid,
    belgium_rrn_valid,
    finland_hetu_valid,
    uk_nino_valid,
    # Names
    chinese_name_valid,
    korean_name_valid,
    japanese_name_kanji_valid,
    cjk_name_standalone,
    # Others
    ipv4_public,
    not_repeating_pattern,
    credit_card_bin_valid,
    swift_bic_valid,
    aws_access_key_valid,
    google_api_key_valid,
    crypto_btc_valid,
    crypto_eth_valid,
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
    "jp_zipcode_valid",
    "cn_zipcode_valid",
    "tw_zipcode_valid",
    "in_pincode_valid",
    "korean_bank_account_valid",
    "generic_number_not_timestamp",
    "contains_letter",
    "us_ssn_valid",
    "us_npi_valid",
    "cn_national_id_valid",
    "tw_national_id_valid",
    "india_aadhaar_valid",
    "india_pan_valid",
    "kr_business_registration_valid",
    "kr_rrn_valid",
    "kr_corporate_registration_valid",
    "kr_alien_registration_valid",
    "jp_my_number_valid",
    "jp_corporate_number_valid",
    "tw_ubn_valid",
    "france_insee_valid",
    "spain_dni_valid",
    "spain_nie_valid",
    "netherlands_bsn_valid",
    "poland_pesel_valid",
    "sweden_personnummer_valid",
    "belgium_rrn_valid",
    "finland_hetu_valid",
    "uk_nino_valid",
    "chinese_name_valid",
    "korean_name_valid",
    "japanese_name_kanji_valid",
    "cjk_name_standalone",
    "ipv4_public",
    "not_repeating_pattern",
    "credit_card_bin_valid",
    "swift_bic_valid",
    "aws_access_key_valid",
    "google_api_key_valid",
    "crypto_btc_valid",
    "crypto_eth_valid",
    "get_verification_function",
    "register_verification_function",
    "unregister_verification_function",
]
