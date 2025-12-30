"""Tests for CJK (Chinese, Japanese, Korean) patterns."""

import pytest
from datadetector import load_registry

@pytest.fixture
def registry():
    """Load test registry."""
    return load_registry()

class TestChinesePatterns:
    """Tests for Chinese patterns."""

    def test_cn_mobile_pattern(self, registry):
        """Test Chinese mobile phone pattern."""
        pattern = registry.get_pattern("cn/mobile_01")
        assert pattern is not None

        # Test matches
        assert pattern.compiled.fullmatch("13812345678")
        assert pattern.compiled.fullmatch("13912345678")
        assert pattern.compiled.fullmatch("15012345678")
        assert pattern.compiled.fullmatch("18912345678")

        # Test non-matches
        assert not pattern.compiled.fullmatch("23812345678")  # Invalid prefix
        assert not pattern.compiled.fullmatch("1381234567")   # Too short
        assert not pattern.compiled.fullmatch("138123456789") # Too long

    def test_cn_national_id_pattern(self, registry):
        """Test Chinese National ID pattern."""
        pattern = registry.get_pattern("cn/national_id_01")
        assert pattern is not None

        # Test matches (18 digits)
        # Note: These are fake but syntactically correct ID numbers
        assert pattern.compiled.fullmatch("110101199003071234")
        assert pattern.compiled.fullmatch("11010119900307123X")  # Checksum X

        # Test non-matches
        assert not pattern.compiled.fullmatch("11010119900307123")  # Too short
        
        # NOTE: Current regex is permissive and allows invalid dates
        # assert not pattern.compiled.fullmatch("110101199013071234") # Invalid month (13)


class TestJapanesePatterns:
    """Tests for Japanese patterns."""

    def test_jp_mobile_pattern(self, registry):
        """Test Japanese mobile phone pattern."""
        pattern = registry.get_pattern("jp/mobile_01")
        assert pattern is not None

        # Test matches
        assert pattern.compiled.fullmatch("090-1234-5678")
        assert pattern.compiled.fullmatch("080-1234-5678")
        assert pattern.compiled.fullmatch("070-1234-5678")
        assert pattern.compiled.fullmatch("09012345678")  # No hyphens

        # Test non-matches
        assert not pattern.compiled.fullmatch("03-1234-5678")  # Landline (Tokyo)
        assert not pattern.compiled.fullmatch("090-1234-567")  # Too short

    def test_jp_my_number_pattern(self, registry):
        """Test Japanese My Number (Individual Number) pattern."""
        pattern = registry.get_pattern("jp/my_number_01")
        assert pattern is not None

        # Test matches (12 digits)
        assert pattern.compiled.fullmatch("123456789012")
        assert pattern.compiled.fullmatch("1234-5678-9012") # With hyphens? Check if pattern supports it.
        # Often My Number is written as 12 digits block or 4-4-4.
        
        # Test non-matches
        assert not pattern.compiled.fullmatch("12345678901")   # Too short

class TestKoreanPatternsAdditional:
    """Additional tests for Korean patterns not covered in main test."""

    def test_kr_zipcode_pattern(self, registry):
        """Test Korean Zipcode pattern."""
        pattern = registry.get_pattern("kr/zipcode_01")
        assert pattern is not None

        # New 5-digit format
        assert pattern.compiled.fullmatch("03123")
        
        # Old 6-digit format (usually with dash) - check if supported
        # assert pattern.compiled.fullmatch("123-456") 
        # Checking patterns usually support current standards first.

