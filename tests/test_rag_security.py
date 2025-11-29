"""Tests for RAG security middleware."""

import pytest

from datadetector import Engine, load_registry
from datadetector.rag_middleware import RAGSecurityMiddleware
from datadetector.rag_models import SecurityAction, SecurityLayer, SecurityPolicy, SeverityLevel
from datadetector.tokenization import SecureTokenizer


@pytest.fixture
def engine():
    """Create engine fixture."""
    registry = load_registry()
    return Engine(registry)


@pytest.fixture
def middleware(engine):
    """Create middleware fixture."""
    return RAGSecurityMiddleware(engine)


@pytest.fixture
def tokenizer(engine):
    """Create tokenizer fixture."""
    return SecureTokenizer(engine)


class TestInputLayerScanning:
    """Tests for Layer 1: Input scanning."""

    @pytest.mark.asyncio
    async def test_scan_query_with_email(self, middleware):
        """Test scanning query containing email."""
        query = "What's the email for john@example.com?"
        result = await middleware.scan_query(query, namespaces=["comm"])

        assert result.has_pii
        assert result.match_count > 0
        assert result.action_taken == SecurityAction.SANITIZE
        assert "john@example.com" not in result.sanitized_text

    @pytest.mark.asyncio
    async def test_scan_query_blocking_policy(self, middleware):
        """Test query blocking with strict policy."""
        policy = SecurityPolicy(
            layer=SecurityLayer.INPUT,
            action=SecurityAction.BLOCK,
            severity_threshold=SeverityLevel.HIGH,
        )

        query = "Process SSN 123-45-6789"
        result = await middleware.scan_query(query, namespaces=["us"], policy=policy)

        assert result.blocked
        assert result.action_taken == SecurityAction.BLOCK
        assert result.reason is not None

    @pytest.mark.asyncio
    async def test_scan_query_no_pii(self, middleware):
        """Test scanning query without PII."""
        query = "What are your business hours?"
        result = await middleware.scan_query(query)

        assert not result.has_pii
        assert result.match_count == 0
        assert not result.blocked
        assert result.sanitized_text == query


class TestStorageLayerScanning:
    """Tests for Layer 2: Storage scanning."""

    @pytest.mark.asyncio
    async def test_scan_document_with_tokenization(self, middleware):
        """Test document scanning with tokenization."""
        document = "Customer email: john@example.com, phone: 555-0123"
        result = await middleware.scan_document(document, namespaces=["comm"])

        assert result.has_pii
        assert result.match_count > 0
        assert result.action_taken == SecurityAction.SANITIZE
        assert result.token_map is not None
        assert len(result.token_map.tokens) > 0
        # Original values should be masked
        assert "john@example.com" not in result.sanitized_text
        # Tokens should be present
        assert "TOKEN" in result.sanitized_text

    @pytest.mark.asyncio
    async def test_scan_document_blocking(self, middleware):
        """Test document blocking."""
        policy = SecurityPolicy(
            layer=SecurityLayer.STORAGE,
            action=SecurityAction.BLOCK,
            severity_threshold=SeverityLevel.LOW,
        )

        document = "Confidential: SSN 123-45-6789"
        result = await middleware.scan_document(
            document, namespaces=["us"], policy=policy
        )

        assert result.blocked
        assert result.action_taken == SecurityAction.BLOCK


class TestOutputLayerScanning:
    """Tests for Layer 3: Output scanning."""

    @pytest.mark.asyncio
    async def test_scan_response_blocks_pii(self, middleware):
        """Test response blocking when PII detected."""
        response = "The customer SSN is 123-45-6789"
        result = await middleware.scan_response(response, namespaces=["us"])

        assert result.has_pii
        assert result.blocked
        assert result.action_taken == SecurityAction.BLOCK
        assert "BLOCKED" in result.sanitized_text

    @pytest.mark.asyncio
    async def test_scan_response_sanitize_mode(self, middleware):
        """Test response sanitization instead of blocking."""
        policy = SecurityPolicy(
            layer=SecurityLayer.OUTPUT,
            action=SecurityAction.SANITIZE,
            severity_threshold=SeverityLevel.HIGH,
        )

        response = "Contact email: support@example.com"
        result = await middleware.scan_response(
            response, namespaces=["comm"], policy=policy
        )

        assert result.has_pii
        assert not result.blocked
        assert result.action_taken == SecurityAction.SANITIZE
        assert "support@example.com" not in result.sanitized_text


class TestTokenization:
    """Tests for tokenization system."""

    def test_tokenize_with_map(self, tokenizer):
        """Test tokenization with mapping."""
        text = "Email: john@example.com, Phone: 555-0123"
        sanitized, token_map = tokenizer.tokenize_with_map(text, namespaces=["comm"])

        assert "john@example.com" not in sanitized
        assert "555-0123" not in sanitized
        assert "TOKEN" in sanitized
        assert len(token_map.tokens) >= 2
        assert token_map.hash is not None

    def test_detokenize(self, tokenizer):
        """Test token reversal."""
        original = "Email: john@example.com"
        sanitized, token_map = tokenizer.tokenize_with_map(original, namespaces=["comm"])

        # Detokenize
        detokenized = tokenizer.detokenize(sanitized, token_map)

        # Should match original
        assert detokenized == original

    def test_stable_tokens(self, engine):
        """Test stable token generation."""
        tokenizer = SecureTokenizer(engine, use_stable_tokens=True)

        text = "Email: test@example.com"
        sanitized1, _ = tokenizer.tokenize_with_map(text, namespaces=["comm"])
        sanitized2, _ = tokenizer.tokenize_with_map(text, namespaces=["comm"])

        # Stable tokens should be identical
        assert sanitized1 == sanitized2


class TestPolicyManagement:
    """Tests for policy management."""

    def test_update_policy(self, middleware):
        """Test policy update."""
        new_policy = SecurityPolicy(
            layer=SecurityLayer.INPUT,
            action=SecurityAction.BLOCK,
            severity_threshold=SeverityLevel.CRITICAL,
        )

        middleware.update_policy(SecurityLayer.INPUT, new_policy)

        assert middleware.input_policy.action == SecurityAction.BLOCK
        assert middleware.input_policy.severity_threshold == SeverityLevel.CRITICAL

    def test_severity_threshold_logic(self):
        """Test severity threshold logic."""
        policy = SecurityPolicy(
            layer=SecurityLayer.OUTPUT,
            action=SecurityAction.BLOCK,
            severity_threshold=SeverityLevel.HIGH,
        )

        # Should block high and critical
        assert policy.should_block("high")
        assert policy.should_block("critical")

        # Should not block medium and low
        assert not policy.should_block("medium")
        assert not policy.should_block("low")


class TestEndToEndRAGWorkflow:
    """End-to-end RAG workflow tests."""

    @pytest.mark.asyncio
    async def test_complete_rag_pipeline(self, middleware, tokenizer):
        """Test complete RAG pipeline with all three layers."""
        # Layer 1: Input scanning
        query = "What's the status for customer john@example.com?"
        input_result = await middleware.scan_query(query, namespaces=["comm"])
        assert not input_result.blocked
        sanitized_query = input_result.sanitized_text

        # Layer 2: Storage scanning (document indexing)
        document = "Customer john@example.com has account 12345"
        storage_result = await middleware.scan_document(document, namespaces=["comm"])
        assert storage_result.token_map is not None
        sanitized_doc = storage_result.sanitized_text

        # Simulate RAG processing (would retrieve and use LLM here)
        # For test, just create a mock response
        llm_response = "The account status is active"

        # Layer 3: Output scanning
        output_result = await middleware.scan_response(
            llm_response, namespaces=["comm"]
        )
        assert not output_result.blocked  # No PII in this response
        assert output_result.sanitized_text == llm_response

    @pytest.mark.asyncio
    async def test_tokenization_roundtrip_in_pipeline(self, middleware, tokenizer):
        """Test tokenization and detokenization in pipeline."""
        # Original document with PII
        document = "Customer: john@example.com, SSN: 123-45-6789"

        # Tokenize for storage
        sanitized, token_map = tokenizer.tokenize_with_map(
            document, namespaces=["comm", "us"]
        )

        # Store sanitized version (no PII)
        assert "john@example.com" not in sanitized
        assert "123-45-6789" not in sanitized

        # Later, detokenize if authorized
        detokenized = tokenizer.detokenize(sanitized, token_map)

        # Should match original
        assert detokenized == document
