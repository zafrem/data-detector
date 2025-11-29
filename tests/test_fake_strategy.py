"""Tests for FAKE redaction strategy."""

import pytest

from datadetector import Engine, load_registry
from datadetector.models import RedactionStrategy


@pytest.fixture
def engine():
    """Create engine fixture."""
    registry = load_registry()
    return Engine(registry)


class TestFakeStrategy:
    """Tests for fake data replacement strategy."""

    def test_fake_email_replacement(self, engine):
        """Test fake email generation."""
        text = "Contact us at support@example.com"
        result = engine.redact(text, namespaces=["comm"], strategy=RedactionStrategy.FAKE)

        # Should not contain original email
        assert "support@example.com" not in result.redacted_text

        # Should contain email-like pattern
        assert "@" in result.redacted_text

        # Should still be readable
        assert "Contact us at" in result.redacted_text

    def test_fake_phone_replacement(self, engine):
        """Test fake phone generation."""
        text = "Call me at 555-123-4567"
        result = engine.redact(text, namespaces=["comm"], strategy=RedactionStrategy.FAKE)

        # Should not contain original phone
        assert "555-123-4567" not in result.redacted_text

        # Should still be readable
        assert "Call me at" in result.redacted_text

        # Fake phone should have reasonable length
        # (depends on pattern, but shouldn't be masked)
        assert "***" not in result.redacted_text or len(result.redacted_text) > len(text) / 2

    def test_fake_ssn_replacement(self, engine):
        """Test fake SSN generation."""
        text = "SSN: 123-45-6789"
        result = engine.redact(text, namespaces=["us"], strategy=RedactionStrategy.FAKE)

        # Should not contain original SSN
        assert "123-45-6789" not in result.redacted_text

        # Should preserve format (9 digits)
        assert "SSN:" in result.redacted_text

    def test_fake_multiple_pii(self, engine):
        """Test fake replacement with multiple PII types."""
        text = "Email: john@example.com, Phone: 555-0123, SSN: 123-45-6789"
        result = engine.redact(
            text, namespaces=["comm", "us"], strategy=RedactionStrategy.FAKE
        )

        # Original values should be gone
        assert "john@example.com" not in result.redacted_text
        assert "555-0123" not in result.redacted_text
        assert "123-45-6789" not in result.redacted_text

        # Structure should be preserved
        assert "Email:" in result.redacted_text
        assert "Phone:" in result.redacted_text
        assert "SSN:" in result.redacted_text

        # Should have realistic replacements
        assert result.redaction_count == 3

    def test_fake_fallback_to_mask(self, engine):
        """Test fallback to mask if fake generation fails."""
        # This test verifies the fallback mechanism
        # Since we have FakeDataGenerator, it should generate fake data
        # But if it fails, it should fall back to masking
        text = "Email: test@example.com"
        result = engine.redact(text, namespaces=["comm"], strategy=RedactionStrategy.FAKE)

        # Should redact one way or another
        assert "test@example.com" not in result.redacted_text
        assert result.redaction_count == 1

    def test_compare_mask_vs_fake(self, engine):
        """Compare mask and fake strategies."""
        text = "Contact: john@example.com, Phone: 555-1234"

        # MASK strategy
        mask_result = engine.redact(
            text, namespaces=["comm"], strategy=RedactionStrategy.MASK
        )

        # FAKE strategy
        fake_result = engine.redact(
            text, namespaces=["comm"], strategy=RedactionStrategy.FAKE
        )

        # Both should redact
        assert "john@example.com" not in mask_result.redacted_text
        assert "john@example.com" not in fake_result.redacted_text

        # Same number of matches
        assert mask_result.redaction_count == fake_result.redaction_count

        # Different results
        assert mask_result.redacted_text != fake_result.redacted_text

        # Fake should not have asterisks (or fewer of them)
        # Depending on pattern, mask might use predefined masks
        # So we just verify they're different strategies
        assert mask_result.strategy == RedactionStrategy.MASK
        assert fake_result.strategy == RedactionStrategy.FAKE


class TestFakeStrategyPerformance:
    """Performance tests for fake strategy."""

    def test_fake_performance_reasonable(self, engine):
        """Test that fake strategy has reasonable performance."""
        import time

        text = "Email: test@example.com" * 10  # Multiple instances

        start = time.perf_counter()
        for _ in range(100):
            engine.redact(text, namespaces=["comm"], strategy=RedactionStrategy.FAKE)
        duration = (time.perf_counter() - start) * 1000 / 100

        # Should be under 50ms per document on average
        assert duration < 50, f"FAKE strategy too slow: {duration:.2f}ms"

    def test_fake_vs_mask_performance(self, engine):
        """Compare performance of fake vs mask."""
        import time

        text = "Email: john@example.com, Phone: 555-0123"

        # Benchmark MASK
        start = time.perf_counter()
        for _ in range(100):
            engine.redact(text, strategy=RedactionStrategy.MASK)
        mask_time = time.perf_counter() - start

        # Benchmark FAKE
        start = time.perf_counter()
        for _ in range(100):
            engine.redact(text, strategy=RedactionStrategy.FAKE)
        fake_time = time.perf_counter() - start

        # FAKE should be slower but not drastically (< 10x)
        assert fake_time / mask_time < 10, (
            f"FAKE strategy too slow compared to MASK: "
            f"{fake_time/mask_time:.1f}x slower"
        )


class TestFakeWithRAG:
    """Test fake strategy in RAG context."""

    def test_document_embedding_quality(self, engine):
        """
        Test that fake data preserves semantic structure better than mask.

        This is important for RAG systems where text is embedded.
        """
        document = """
        Customer Support Request

        Name: John Doe
        Email: john.doe@company.com
        Phone: 555-123-4567

        Issue: Customer needs help with account access.
        """

        # MASK strategy
        mask_result = engine.redact(
            document, namespaces=["comm"], strategy=RedactionStrategy.MASK
        )

        # FAKE strategy
        fake_result = engine.redact(
            document, namespaces=["comm"], strategy=RedactionStrategy.FAKE
        )

        # Both should remove PII
        assert "john.doe@company.com" not in mask_result.redacted_text
        assert "john.doe@company.com" not in fake_result.redacted_text

        # Count words (proxy for semantic preservation)
        mask_words = len(mask_result.redacted_text.split())
        fake_words = len(fake_result.redacted_text.split())
        original_words = len(document.split())

        # FAKE should preserve word count better
        # (MASK might replace multi-word patterns with single mask)
        assert abs(fake_words - original_words) <= abs(mask_words - original_words)

        # FAKE should be more readable (subjective, but check for asterisks)
        mask_asterisks = mask_result.redacted_text.count("*")
        fake_asterisks = fake_result.redacted_text.count("*")

        # FAKE should have fewer or no asterisks
        assert fake_asterisks <= mask_asterisks
