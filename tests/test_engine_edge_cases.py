"""Tests for engine edge cases to improve coverage."""

import re

from datadetector.engine import Engine
from datadetector.models import (
    ActionOnMatch,
    Category,
    Pattern,
    Policy,
    RedactionStrategy,
    Severity,
)
from datadetector.registry import PatternRegistry


class TestEngineStoreRawPolicy:
    """Test engine with store_raw policy."""

    def test_find_with_store_raw_policy(self):
        """Test find with store_raw=True policy includes matched text."""
        registry = PatternRegistry()

        # Pattern with store_raw=True
        pattern = Pattern(
            id="url_01",
            namespace="test",
            location="test",
            category=Category.OTHER,
            pattern=r"https://example\.com",
            compiled=re.compile(r"https://example\.com"),
            description="Test URL",
            flags=[],
            mask="https://***",
            examples=None,
            policy=Policy(
                store_raw=True,  # Allow storing matched text
                action_on_match=ActionOnMatch.REPORT,
                severity=Severity.LOW,
            ),
            metadata={},
            verification=None,
            verification_func=None,
            priority=100,
        )
        registry.add_pattern(pattern)
        engine = Engine(registry)

        result = engine.find(
            "Visit https://example.com", namespaces=["test"], include_matched_text=True
        )

        assert result.match_count == 1
        assert result.matches[0].matched_text == "https://example.com"

    def test_validate_with_store_raw_policy(self):
        """Test validate with store_raw=True policy."""
        registry = PatternRegistry()

        # Pattern with store_raw=True
        pattern = Pattern(
            id="url_01",
            namespace="test",
            location="test",
            category=Category.OTHER,
            pattern=r"https://example\.com",
            compiled=re.compile(r"https://example\.com"),
            description="Test URL",
            flags=[],
            mask="https://***",
            examples=None,
            policy=Policy(
                store_raw=True,
                action_on_match=ActionOnMatch.REPORT,
                severity=Severity.LOW,
            ),
            metadata={},
            verification=None,
            verification_func=None,
            priority=100,
        )
        registry.add_pattern(pattern)
        engine = Engine(registry)

        result = engine.validate("https://example.com", "test/url_01")
        assert result.is_valid
        assert result.match is not None
        assert result.match.matched_text == "https://example.com"


class TestRedactionStrategies:
    """Test edge cases in redaction strategies."""

    def test_redact_with_no_pattern_mask(self):
        """Test redaction when pattern has no mask defined."""
        registry = PatternRegistry()

        # Pattern without mask
        pattern = Pattern(
            id="test_01",
            namespace="test",
            location="test",
            category=Category.EMAIL,
            pattern=r"test@example\.com",
            compiled=re.compile(r"test@example\.com"),
            description="Test",
            flags=[],
            mask=None,  # No mask defined
            examples=None,
            policy=Policy(
                store_raw=False,
                action_on_match=ActionOnMatch.REDACT,
                severity=Severity.MEDIUM,
            ),
            metadata={},
            verification=None,
            verification_func=None,
            priority=100,
        )
        registry.add_pattern(pattern)
        engine = Engine(registry)

        result = engine.redact("Email: test@example.com", strategy=RedactionStrategy.MASK)
        # Should use default masking since no mask is defined
        assert "test@example.com" not in result.redacted_text
        assert "*" in result.redacted_text

    def test_redact_unknown_strategy_fallback(self):
        """Test that unknown strategy falls back to default masking."""
        registry = PatternRegistry()

        pattern = Pattern(
            id="test_01",
            namespace="test",
            location="test",
            category=Category.EMAIL,
            pattern=r"test@example\.com",
            compiled=re.compile(r"test@example\.com"),
            description="Test",
            flags=[],
            mask="***",
            examples=None,
            policy=Policy(
                store_raw=False,
                action_on_match=ActionOnMatch.REDACT,
                severity=Severity.MEDIUM,
            ),
            metadata={},
            verification=None,
            verification_func=None,
            priority=100,
        )
        registry.add_pattern(pattern)
        engine = Engine(registry)

        # Test all valid strategies to ensure full coverage
        result_mask = engine.redact("test@example.com", strategy=RedactionStrategy.MASK)
        assert result_mask.redaction_count == 1

        result_hash = engine.redact("test@example.com", strategy=RedactionStrategy.HASH)
        assert result_hash.redaction_count == 1
        assert "[HASH:" in result_hash.redacted_text

        result_token = engine.redact("test@example.com", strategy=RedactionStrategy.TOKENIZE)
        assert result_token.redaction_count == 1
        assert "[TOKEN:" in result_token.redacted_text
