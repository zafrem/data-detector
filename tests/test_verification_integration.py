"""Integration tests for verification with engine."""

import pytest

from datadetector import Engine, load_registry
from datadetector.verification import (
    register_verification_function,
    unregister_verification_function,
)


class TestVerificationIntegration:
    """Test verification integration with engine."""

    @pytest.fixture
    def engine(self):
        """Load engine with IBAN patterns."""
        registry = load_registry(paths=["pattern-engine/regex/pii/iban.yml"])
        return Engine(registry)

    def test_iban_validation_with_verification(self, engine):
        """Test IBAN validation with Mod-97 verification."""
        # Valid IBAN - should pass both regex and verification
        result = engine.validate("GB82WEST12345698765432", "co/iban_01")
        assert result.is_valid

        # Invalid IBAN - passes regex but fails verification
        result = engine.validate("GB82WEST12345698765433", "co/iban_01")
        assert not result.is_valid

    def test_iban_find_with_verification(self, engine):
        """Test finding IBANs with verification."""
        text = "Valid: GB82WEST12345698765432 Invalid: GB82WEST12345698765433"

        result = engine.find(text, namespaces=["co"])

        # Should only find the valid IBAN
        assert result.match_count == 1
        assert result.matches[0].matched_text is None  # store_raw is false
        assert result.matches[0].start == 7  # Position of valid IBAN
        assert result.matches[0].end == 29

    def test_iban_redact_with_verification(self, engine):
        """Test redacting IBANs with verification."""
        text = "Account: GB82WEST12345698765432 and GB82WEST12345698765433"

        result = engine.redact(text, namespaces=["co"])

        # Should only redact the valid IBAN
        assert result.redaction_count == 1
        assert "GB82WEST12345698765432" not in result.redacted_text
        assert "GB82WEST12345698765433" in result.redacted_text  # Invalid one remains

    def test_pattern_without_verification(self):
        """Test that patterns without verification work normally."""
        # Email pattern doesn't have verification
        registry = load_registry(paths=["pattern-engine/regex/pii/common"])
        engine = Engine(registry)
        result = engine.validate("user@example.com", "comm/email_01")
        assert result.is_valid

    def test_country_specific_iban_with_verification(self, engine):
        """Test country-specific IBAN patterns with verification."""
        # Valid German IBAN
        result = engine.validate("DE89370400440532013000", "co/iban_de_01")
        assert result.is_valid

        # Invalid German IBAN (wrong check digit)
        result = engine.validate("DE89370400440532013001", "co/iban_de_01")
        assert not result.is_valid

    def test_multiple_ibans_in_text(self, engine):
        """Test finding multiple IBANs with mixed validity."""
        text = """
        Account 1: GB82WEST12345698765432
        Account 2: DE89370400440532013000
        Account 3: GB82WEST12345698765433
        Account 4: FR1420041010050500013M02606
        Account 5: DE89370400440532013001
        """

        result = engine.find(text, namespaces=["co"])

        # Should find only valid IBANs (3 valid ones)
        valid_ibans = [m for m in result.matches if m.category.value == "iban"]
        assert len(valid_ibans) == 3

    def test_iban_with_spaces(self, engine):
        """Test IBAN validation with spaces."""
        # Note: The regex pattern doesn't include spaces, so this won't match the pattern
        # This is expected behavior - the pattern defines the format
        result = engine.validate("GB82 WEST 1234 5698 7654 32", "co/iban_01")
        assert not result.is_valid  # Won't match regex pattern


class TestCustomVerification:
    """Test custom verification functions."""

    @pytest.fixture
    def custom_engine(self, tmp_path):
        """Create engine with custom verification pattern."""
        # Create a custom pattern file with verification
        pattern_file = tmp_path / "custom.yml"
        pattern_content = """
namespace: cu
description: Custom patterns with verification

patterns:
  - id: custom_01
    location: cust
    category: other
    description: Custom ID with checksum
    pattern: 'CID-\\d{4}'
    verification: custom_checksum
    examples:
      match:
        - "CID-1234"
      nomatch:
        - "CID-12345"
    policy:
      store_raw: false
      action_on_match: redact
      severity: medium
"""
        pattern_file.write_text(pattern_content)

        # Register custom verification function
        def custom_checksum(value: str) -> bool:
            """Custom checksum: sum of digits must be even."""
            digits = [int(c) for c in value if c.isdigit()]
            return sum(digits) % 2 == 0

        register_verification_function("custom_checksum", custom_checksum)

        # Load registry and create engine
        registry = load_registry(paths=[str(pattern_file)])
        engine = Engine(registry)

        yield engine

        # Cleanup
        unregister_verification_function("custom_checksum")

    def test_custom_verification_function(self, custom_engine):
        """Test custom verification function."""
        # CID-1234: 1+2+3+4 = 10 (even) -> valid
        result = custom_engine.validate("CID-1234", "cu/custom_01")
        assert result.is_valid

        # CID-1235: 1+2+3+5 = 11 (odd) -> invalid
        result = custom_engine.validate("CID-1235", "cu/custom_01")
        assert not result.is_valid

    def test_custom_verification_in_find(self, custom_engine):
        """Test custom verification in find operation."""
        text = "IDs: CID-1234 CID-1235 CID-2468"

        result = custom_engine.find(text, namespaces=["cu"])

        # Should find CID-1234 (1+2+3+4=10, even) and CID-2468 (2+4+6+8=20, even)
        # Should NOT find CID-1235 (1+2+3+5=11, odd)
        assert result.match_count == 2


class TestVerificationErrors:
    """Test error handling in verification."""

    @pytest.fixture
    def engine_with_missing_verification(self, tmp_path):
        """Create engine with pattern referencing non-existent verification."""
        pattern_file = tmp_path / "invalid.yml"
        pattern_content = """
namespace: iv
description: Pattern with invalid verification

patterns:
  - id: invalid_01
    location: test
    category: other
    description: Pattern with non-existent verification
    pattern: 'TEST-\\d{4}'
    verification: nonexistent_function
    policy:
      store_raw: false
      action_on_match: redact
      severity: medium
"""
        pattern_file.write_text(pattern_content)
        registry = load_registry(paths=[str(pattern_file)])
        return Engine(registry)

    def test_missing_verification_function(self, engine_with_missing_verification):
        """Test pattern with missing verification function."""
        # Pattern should still work, but without verification
        result = engine_with_missing_verification.validate("TEST-1234", "iv/invalid_01")
        # Should match regex (verification function is None, so skipped)
        assert result.is_valid
