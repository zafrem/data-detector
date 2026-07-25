"""Tests for verification functions."""

from datadetector.verification import (
    get_verification_function,
    high_entropy_token,
    iban_mod97,
    luhn,
    register_verification_function,
    unregister_verification_function,
)


class TestIbanMod97:
    """Test IBAN Mod-97 verification."""

    def test_valid_ibans(self):
        """Test valid IBAN numbers."""
        valid_ibans = [
            "GB82WEST12345698765432",
            "DE89370400440532013000",
            "FR1420041010050500013M02606",
            "IT60X0542811101000000123456",
            "ES9121000418450200051332",
            "NL91ABNA0417164300",
            "BE68539007547034",
        ]
        for iban in valid_ibans:
            assert iban_mod97(iban), f"IBAN {iban} should be valid"

    def test_valid_ibans_with_spaces(self):
        """Test valid IBANs with spaces."""
        assert iban_mod97("GB82 WEST 1234 5698 7654 32")
        assert iban_mod97("DE89 3704 0044 0532 0130 00")

    def test_invalid_ibans(self):
        """Test invalid IBAN numbers."""
        invalid_ibans = [
            "GB82WEST12345698765433",  # Wrong check digit
            "DE89370400440532013001",  # Wrong check digit
            "ABCD1234567890123456",  # Invalid check digits
            "GB00WEST12345698765432",  # Invalid check digits
        ]
        for iban in invalid_ibans:
            assert not iban_mod97(iban), f"IBAN {iban} should be invalid"

    def test_invalid_format(self):
        """Test invalid IBAN formats."""
        assert not iban_mod97("1234567890")
        assert not iban_mod97("AB")
        assert not iban_mod97("")
        assert not iban_mod97("GB82!")  # Invalid character

    def test_case_insensitive(self):
        """Test that IBAN verification is case insensitive."""
        assert iban_mod97("gb82west12345698765432")
        assert iban_mod97("Gb82WeSt12345698765432")


class TestLuhn:
    """Test Luhn algorithm verification."""

    def test_valid_numbers(self):
        """Test valid Luhn numbers."""
        valid_numbers = [
            "79927398713",  # Valid Luhn
            "4532015112830366",  # Valid Visa card
            "5425233430109903",  # Valid Mastercard
        ]
        for number in valid_numbers:
            assert luhn(number), f"Number {number} should be valid"

    def test_invalid_numbers(self):
        """Test invalid Luhn numbers."""
        invalid_numbers = [
            "79927398714",  # Invalid check digit
            "4532015112830367",  # Invalid check digit
            "1234567890",  # Invalid
        ]
        for number in invalid_numbers:
            assert not luhn(number), f"Number {number} should be invalid"

    def test_invalid_format(self):
        """Test invalid formats."""
        assert not luhn("")
        assert not luhn("abcd")

    def test_with_spaces_and_dashes(self):
        """Test Luhn with spaces and dashes (should ignore non-digits)."""
        assert luhn("4532-0151-1283-0366")
        assert luhn("5425 2334 3010 9903")


class TestHighEntropyToken:
    """Test high entropy token verification."""

    def test_valid_tokens(self):
        """Test valid high-entropy tokens."""
        valid_tokens = [
            "rk_test_EXAMPLEKEY1234567890abcdefgh12345678",  # Stripe-like key (FAKE)
            "ghp_EXAMPLE1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P",  # GitHub token (FAKE)
            "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",  # AWS secret (40 chars)
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0",  # JWT
            "aBcD3fGh1JkLmN0pQrStUvW2xY4zA5bC6dE7fG8hI9j",  # Generic high-entropy
        ]
        for token in valid_tokens:
            assert high_entropy_token(token), f"Token {token} should be valid"

    def test_too_short(self):
        """Test tokens that are too short (<20 chars)."""
        short_tokens = [
            "short_token_here",
            "abc123xyz",
            "",
            "a" * 19,
        ]
        for token in short_tokens:
            assert not high_entropy_token(token), f"Token {token} should be invalid (too short)"

    def test_low_entropy_repetitive(self):
        """Test repetitive patterns with low entropy."""
        low_entropy_tokens = [
            "aaaaaaaaaaaaaaaaaaaaaa",  # All same character
            "aaaaaaaaaaaaaaaaaaaabbbbbbbbbbbbbbbbbbbb",  # Two characters
            "12345678901234567890",  # Sequential
            "abcabcabcabcabcabcabcabc",  # Repeating pattern
        ]
        for token in low_entropy_tokens:
            assert not high_entropy_token(token), f"Token {token} should be invalid (low entropy)"

    def test_with_spaces(self):
        """Test tokens with spaces (should be invalid)."""
        assert not high_entropy_token("rk_test_EXAMPLE1234 567890abcdefgh12345678")
        assert not high_entropy_token("token with spaces here and more content")

    def test_with_newlines(self):
        """Test tokens with newlines (should be invalid)."""
        assert not high_entropy_token("rk_test_EXAMPLE\n1234567890abcdefgh12345678")
        assert not high_entropy_token("token\nwith\nnewlines\nand\nmore")

    def test_invalid_characters(self):
        """Test tokens with invalid characters."""
        assert not high_entropy_token("rk_test_EXAMPLE@1234567890abcdefgh12345678")
        assert not high_entropy_token("token#with$special%chars&more*content!")

    def test_edge_case_exactly_20_chars(self):
        """Test token with exactly 20 characters."""
        # High entropy token with exactly 20 chars
        assert high_entropy_token("aBcD3fGh1JkLmN0pQrSt")
        # Low entropy token with exactly 20 chars
        assert not high_entropy_token("aaaaaaaaaaaaaaaaaaaa")


class TestVerificationRegistry:
    """Test verification function registry."""

    def test_get_builtin_functions(self):
        """Test getting built-in verification functions."""
        # Functions are re-exported from centralized library
        # Check they're callable and work correctly
        func = get_verification_function("iban_mod97")
        assert func is not None
        assert callable(func)
        assert func == iban_mod97 or func.__name__ == "iban_mod97"

        func = get_verification_function("luhn")
        assert func is not None
        assert callable(func)

        func = get_verification_function("high_entropy_token")
        assert func is not None
        assert callable(func)

    def test_get_nonexistent_function(self):
        """Test getting non-existent function."""
        assert get_verification_function("nonexistent") is None

    def test_register_custom_function(self):
        """Test registering custom verification function."""

        def custom_verify(value: str) -> bool:
            return value.startswith("TEST")

        register_verification_function("custom", custom_verify)
        func = get_verification_function("custom")
        assert func is not None
        assert func("TEST123")
        assert not func("NOTTEST")

        # Cleanup
        unregister_verification_function("custom")

    def test_unregister_function(self):
        """Test unregistering verification function."""

        def temp_verify(value: str) -> bool:
            return True

        register_verification_function("temp", temp_verify)
        assert get_verification_function("temp") is not None

        result = unregister_verification_function("temp")
        assert result is True
        assert get_verification_function("temp") is None

    def test_unregister_nonexistent(self):
        """Test unregistering non-existent function."""
        result = unregister_verification_function("nonexistent")
        assert result is False

    def test_overwrite_function(self):
        """Test overwriting existing function."""

        def verify1(value: str) -> bool:
            return True

        def verify2(value: str) -> bool:
            return False

        register_verification_function("test_overwrite", verify1)
        func1 = get_verification_function("test_overwrite")
        assert func1("anything")

        register_verification_function("test_overwrite", verify2)
        func2 = get_verification_function("test_overwrite")
        assert not func2("anything")

        # Cleanup
        unregister_verification_function("test_overwrite")


class TestDMSCoordinate:
    """Test DMS coordinate verification."""

    def test_dms_invalid_format(self):
        """Test DMS coordinate with invalid format."""
        from datadetector.verification import dms_coordinate

        # Invalid format - should fail regex
        assert not dms_coordinate("invalid")
        assert not dms_coordinate("90")
        assert not dms_coordinate("90°30'")

    def test_dms_invalid_minutes(self):
        """Test DMS with invalid minutes (> 59)."""
        from datadetector.verification import dms_coordinate

        # Minutes > 59
        assert not dms_coordinate("37°60′0″N")
        assert not dms_coordinate("122°65′9″W")

    def test_dms_latitude_out_of_range(self):
        """Test DMS latitude > 90 degrees."""
        from datadetector.verification import dms_coordinate

        # Latitude > 90
        assert not dms_coordinate("91°0′0″N")
        assert not dms_coordinate("100°30′15″S")

    def test_dms_longitude_out_of_range(self):
        """Test DMS longitude > 180 degrees."""
        from datadetector.verification import dms_coordinate

        # Longitude > 180
        assert not dms_coordinate("181°0′0″E")
        assert not dms_coordinate("200°15′30″W")

    def test_dms_valid_coordinates(self):
        """Test valid DMS coordinates."""
        from datadetector.verification import dms_coordinate

        # Valid coordinates
        assert dms_coordinate("37°46′29.7″N")
        assert dms_coordinate("122°25′9.8″W")
        assert dms_coordinate("90°0′0″N")
        assert dms_coordinate("180°0′0″E")
        assert dms_coordinate("0°0′0″S")
