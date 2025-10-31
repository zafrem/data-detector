"""Tests for AsyncEngine."""

import asyncio

import pytest

from datadetector import AsyncEngine, load_registry
from datadetector.models import RedactionStrategy


@pytest.fixture
def registry():
    """Load test registry."""
    return load_registry()


@pytest.fixture
def async_engine(registry):
    """Create async engine."""
    return AsyncEngine(registry)


class TestAsyncFind:
    """Tests for async find operations."""

    @pytest.mark.asyncio
    async def test_find_basic(self, async_engine):
        """Test basic async find operation."""
        text = "Contact: user@example.com"
        result = await async_engine.find(text)

        assert result is not None
        assert result.text == text
        assert len(result.matches) > 0
        assert any(m.category.value == "email" for m in result.matches)

    @pytest.mark.asyncio
    async def test_find_with_tokens(self, async_engine):
        """Test finding tokens asynchronously."""
        text = "AWS_KEY=AKIAIOSFODNN7EXAMPLE"
        result = await async_engine.find(text)

        assert result.has_matches
        assert any(m.category.value == "token" for m in result.matches)
        assert any("aws" in m.ns_id.lower() for m in result.matches)

    @pytest.mark.asyncio
    async def test_find_stop_on_first_match(self, async_engine):
        """Test early termination."""
        text = "AWS_KEY=AKIAIOSFODNN7EXAMPLE and user@example.com"
        result = await async_engine.find(text, stop_on_first_match=True)

        assert result.has_matches
        assert len(result.matches) == 1

    @pytest.mark.asyncio
    async def test_find_no_matches(self, async_engine):
        """Test text with no PII."""
        text = "This is clean text with no PII"
        result = await async_engine.find(text)

        assert not result.has_matches
        assert len(result.matches) == 0

    @pytest.mark.asyncio
    async def test_find_with_namespace_filter(self, async_engine):
        """Test filtering by namespace."""
        text = "010-1234-5678 and user@example.com"
        result = await async_engine.find(text, namespaces=["kr"])

        assert result.has_matches
        # Should only find Korean patterns
        assert all(m.namespace == "kr" for m in result.matches)


class TestAsyncFindBatch:
    """Tests for batch async find operations."""

    @pytest.mark.asyncio
    async def test_find_batch_basic(self, async_engine):
        """Test batch find operation."""
        texts = [
            "Email: user@example.com",
            "Phone: 010-1234-5678",
            "Token: AKIAIOSFODNN7EXAMPLE",
        ]
        results = await async_engine.find_batch(texts)

        assert len(results) == 3
        assert all(isinstance(r.matches, list) for r in results)
        # Each text should have at least one match
        assert all(r.has_matches for r in results)

    @pytest.mark.asyncio
    async def test_find_batch_concurrent(self, async_engine):
        """Test that batch processing is concurrent."""
        import time

        # Create 10 texts to process
        texts = [f"Email{i}: user{i}@example.com" for i in range(10)]

        start_time = time.time()
        results = await async_engine.find_batch(texts)
        batch_time = time.time() - start_time

        assert len(results) == 10
        assert all(r.has_matches for r in results)

        # Batch should be reasonably fast (just a sanity check)
        assert batch_time < 5.0  # Should complete in less than 5 seconds

    @pytest.mark.asyncio
    async def test_find_batch_empty_list(self, async_engine):
        """Test batch with empty list."""
        results = await async_engine.find_batch([])
        assert len(results) == 0


class TestAsyncValidate:
    """Tests for async validate operations."""

    @pytest.mark.asyncio
    async def test_validate_valid_email(self, async_engine):
        """Test validating a valid email."""
        result = await async_engine.validate("user@example.com", "comm/email_01")

        assert result.is_valid
        assert result.match is not None
        assert result.match.category.value == "email"

    @pytest.mark.asyncio
    async def test_validate_invalid_email(self, async_engine):
        """Test validating an invalid email."""
        result = await async_engine.validate("not-an-email", "comm/email_01")

        assert not result.is_valid
        assert result.match is None

    @pytest.mark.asyncio
    async def test_validate_korean_mobile(self, async_engine):
        """Test validating Korean mobile number."""
        result = await async_engine.validate("010-1234-5678", "kr/mobile_01")

        assert result.is_valid
        assert result.match is not None
        assert result.match.namespace == "kr"

    @pytest.mark.asyncio
    async def test_validate_pattern_not_found(self, async_engine):
        """Test validation with non-existent pattern."""
        with pytest.raises(ValueError, match="Pattern not found"):
            await async_engine.validate("test", "invalid/pattern")


class TestAsyncValidateBatch:
    """Tests for batch async validate operations."""

    @pytest.mark.asyncio
    async def test_validate_batch_basic(self, async_engine):
        """Test batch validation."""
        emails = [
            "user1@example.com",
            "user2@example.com",
            "invalid-email",
            "user3@example.com",
        ]
        results = await async_engine.validate_batch(emails, "comm/email_01")

        assert len(results) == 4
        assert results[0].is_valid
        assert results[1].is_valid
        assert not results[2].is_valid
        assert results[3].is_valid

    @pytest.mark.asyncio
    async def test_validate_batch_all_valid(self, async_engine):
        """Test batch validation with all valid inputs."""
        phones = ["010-1234-5678", "011-123-4567", "016-9999-8888"]
        results = await async_engine.validate_batch(phones, "kr/mobile_01")

        assert len(results) == 3
        assert all(r.is_valid for r in results)


class TestAsyncRedact:
    """Tests for async redact operations."""

    @pytest.mark.asyncio
    async def test_redact_basic(self, async_engine):
        """Test basic redaction."""
        text = "Contact: user@example.com"
        result = await async_engine.redact(text)

        assert result.original_text == text
        assert result.redacted_text != text
        assert "@" not in result.redacted_text or "***@***" in result.redacted_text
        assert result.redaction_count > 0

    @pytest.mark.asyncio
    async def test_redact_multiple_pii(self, async_engine):
        """Test redacting multiple PII items."""
        text = "Email: user@example.com, Phone: 010-1234-5678"
        result = await async_engine.redact(text)

        assert result.redaction_count >= 2
        assert "user@example.com" not in result.redacted_text
        assert "010-1234-5678" not in result.redacted_text

    @pytest.mark.asyncio
    async def test_redact_with_hash_strategy(self, async_engine):
        """Test redaction with hash strategy."""
        text = "Email: user@example.com"
        result = await async_engine.redact(text, strategy=RedactionStrategy.HASH)

        assert "[HASH:" in result.redacted_text
        assert "user@example.com" not in result.redacted_text

    @pytest.mark.asyncio
    async def test_redact_with_tokenize_strategy(self, async_engine):
        """Test redaction with tokenize strategy."""
        text = "Email: user@example.com"
        result = await async_engine.redact(text, strategy=RedactionStrategy.TOKENIZE)

        assert "[TOKEN:" in result.redacted_text
        assert "user@example.com" not in result.redacted_text

    @pytest.mark.asyncio
    async def test_redact_no_pii(self, async_engine):
        """Test redaction with no PII."""
        text = "Clean text with no PII"
        result = await async_engine.redact(text)

        assert result.redacted_text == text
        assert result.redaction_count == 0


class TestAsyncRedactBatch:
    """Tests for batch async redact operations."""

    @pytest.mark.asyncio
    async def test_redact_batch_basic(self, async_engine):
        """Test batch redaction."""
        texts = [
            "Email: user1@example.com",
            "Phone: 010-1234-5678",
            "Token: AKIAIOSFODNN7EXAMPLE",
        ]
        results = await async_engine.redact_batch(texts)

        assert len(results) == 3
        assert all(r.redaction_count > 0 for r in results)
        assert results[0].redacted_text != texts[0]
        assert results[1].redacted_text != texts[1]
        assert results[2].redacted_text != texts[2]

    @pytest.mark.asyncio
    async def test_redact_batch_with_strategy(self, async_engine):
        """Test batch redaction with custom strategy."""
        texts = ["user1@example.com", "user2@example.com"]
        results = await async_engine.redact_batch(texts, strategy=RedactionStrategy.HASH)

        assert len(results) == 2
        assert all("[HASH:" in r.redacted_text for r in results)

    @pytest.mark.asyncio
    async def test_redact_batch_concurrent(self, async_engine):
        """Test that batch redaction is concurrent."""
        import time

        texts = [f"Email: user{i}@example.com" for i in range(20)]

        start_time = time.time()
        results = await async_engine.redact_batch(texts)
        batch_time = time.time() - start_time

        assert len(results) == 20
        assert all(r.redaction_count > 0 for r in results)
        # Should complete reasonably quickly
        assert batch_time < 5.0


class TestAsyncEngineConfiguration:
    """Tests for async engine configuration."""

    @pytest.mark.asyncio
    async def test_custom_mask_char(self, registry):
        """Test custom mask character."""
        engine = AsyncEngine(registry, default_mask_char="X")
        text = "Email: user@example.com"
        result = await engine.redact(text)

        # Should use X instead of * for patterns without custom masks
        assert "X" in result.redacted_text or "***@***" in result.redacted_text

    @pytest.mark.asyncio
    async def test_custom_hash_algorithm(self, registry):
        """Test custom hash algorithm."""
        engine = AsyncEngine(registry, hash_algorithm="sha512")
        text = "Email: user@example.com"
        result = await engine.redact(text, strategy=RedactionStrategy.HASH)

        assert "[HASH:" in result.redacted_text


class TestAsyncPerformance:
    """Performance-related tests for async engine."""

    @pytest.mark.asyncio
    async def test_concurrent_find_operations(self, async_engine):
        """Test multiple concurrent find operations."""
        texts = [
            "Email: user@example.com",
            "Phone: 010-1234-5678",
            "Token: AKIAIOSFODNN7EXAMPLE",
            "SSN: 123-45-6789",
        ]

        # Create concurrent tasks manually
        tasks = [async_engine.find(text) for text in texts]
        results = await asyncio.gather(*tasks)

        assert len(results) == 4
        assert all(r.has_matches for r in results)

    @pytest.mark.asyncio
    async def test_mixed_operations_concurrent(self, async_engine):
        """Test mixing different operations concurrently."""
        # Create different types of operations
        find_task = async_engine.find("Email: user@example.com")
        validate_task = async_engine.validate("010-1234-5678", "kr/mobile_01")
        redact_task = async_engine.redact("Token: AKIAIOSFODNN7EXAMPLE")

        # Run them concurrently
        find_result, validate_result, redact_result = await asyncio.gather(
            find_task, validate_task, redact_task
        )

        assert find_result.has_matches
        assert validate_result.is_valid
        assert redact_result.redaction_count > 0
