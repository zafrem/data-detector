"""RAG security middleware for three-layer PII protection."""

import logging
from typing import List, Optional

from datadetector.engine import Engine
from datadetector.rag_models import (
    DocumentScanResult,
    QueryScanResult,
    ResponseScanResult,
    SecurityAction,
    SecurityLayer,
    SecurityPolicy,
    SeverityLevel,
    TokenMap,
)
from datadetector.tokenization import SecureTokenizer

logger = logging.getLogger(__name__)


class RAGSecurityMiddleware:
    """
    Three-layer security middleware for RAG systems.

    Provides:
    - Layer 1 (INPUT): Scan user queries before processing
    - Layer 2 (STORAGE): Scan documents before indexing
    - Layer 3 (OUTPUT): Scan LLM responses before returning
    """

    def __init__(
        self,
        engine: Engine,
        input_policy: Optional[SecurityPolicy] = None,
        storage_policy: Optional[SecurityPolicy] = None,
        output_policy: Optional[SecurityPolicy] = None,
    ) -> None:
        """
        Initialize RAG security middleware.

        Args:
            engine: Engine instance for PII detection
            input_policy: Policy for input layer (queries)
            storage_policy: Policy for storage layer (documents)
            output_policy: Policy for output layer (responses)
        """
        self.engine = engine
        self.tokenizer = SecureTokenizer(engine)

        # Default policies
        self.input_policy = input_policy or SecurityPolicy(
            layer=SecurityLayer.INPUT,
            action=SecurityAction.SANITIZE,
            severity_threshold=SeverityLevel.MEDIUM,
        )

        self.storage_policy = storage_policy or SecurityPolicy(
            layer=SecurityLayer.STORAGE,
            action=SecurityAction.SANITIZE,
            severity_threshold=SeverityLevel.LOW,
        )

        self.output_policy = output_policy or SecurityPolicy(
            layer=SecurityLayer.OUTPUT,
            action=SecurityAction.BLOCK,
            severity_threshold=SeverityLevel.HIGH,
        )

    async def scan_query(
        self,
        query: str,
        namespaces: Optional[List[str]] = None,
        policy: Optional[SecurityPolicy] = None,
    ) -> QueryScanResult:
        """
        Layer 1: Scan user query before processing.

        Args:
            query: User query text
            namespaces: Pattern namespaces to search
            policy: Override default input policy

        Returns:
            QueryScanResult with action taken

        Example:
            >>> result = await middleware.scan_query(
            ...     "What's the email for john@example.com?"
            ... )
            >>> if result.blocked:
            ...     raise ValueError("Query contains PII")
            >>> # Use result.sanitized_text for processing
        """
        policy = policy or self.input_policy

        # Find PII in query
        find_result = self.engine.find(
            query,
            namespaces=namespaces,
            include_matched_text=True,
        )

        # Apply policy
        sanitized_text = query
        action_taken = SecurityAction.ALLOW
        blocked = False
        reason = None
        token_map = None

        if find_result.has_matches:
            # Check severity thresholds
            high_severity_matches = [
                m for m in find_result.matches if policy.should_block(m.severity)
            ]

            if high_severity_matches and policy.action == SecurityAction.BLOCK:
                blocked = True
                action_taken = SecurityAction.BLOCK
                reason = f"Query contains {len(high_severity_matches)} high-severity PII matches"

            elif policy.action == SecurityAction.SANITIZE:
                # Sanitize based on strategy
                if policy.redaction_strategy.value == "tokenize":
                    sanitized_text, token_map = self.tokenizer.tokenize_with_map(query, namespaces)
                else:
                    redact_result = self.engine.redact(
                        query,
                        namespaces=namespaces,
                        strategy=policy.redaction_strategy,
                    )
                    sanitized_text = redact_result.redacted_text

                action_taken = SecurityAction.SANITIZE
                reason = f"Sanitized {len(find_result.matches)} PII matches"

            elif policy.action == SecurityAction.WARN:
                action_taken = SecurityAction.WARN
                reason = f"Warning: Query contains {len(find_result.matches)} PII matches"
                logger.warning(reason)

            if policy.log_matches:
                logger.info(
                    f"Input scan: {len(find_result.matches)} matches, "
                    f"action={action_taken.value}"
                )

        return QueryScanResult(
            original_text=query,
            sanitized_text=sanitized_text,
            matches=find_result.matches,
            action_taken=action_taken,
            blocked=blocked,
            layer=SecurityLayer.INPUT,
            reason=reason,
            token_map=token_map,
        )

    async def scan_document(
        self,
        document: str,
        namespaces: Optional[List[str]] = None,
        policy: Optional[SecurityPolicy] = None,
        chunk_id: Optional[int] = None,
        total_chunks: Optional[int] = None,
    ) -> DocumentScanResult:
        """
        Layer 2: Scan document before indexing in vector store.

        Args:
            document: Document text to scan
            namespaces: Pattern namespaces to search
            policy: Override default storage policy
            chunk_id: Chunk ID if processing in chunks
            total_chunks: Total number of chunks

        Returns:
            DocumentScanResult with sanitized text

        Example:
            >>> result = await middleware.scan_document(
            ...     "Customer SSN: 123-45-6789",
            ...     policy=SecurityPolicy(action="tokenize")
            ... )
            >>> # Store result.sanitized_text in vector DB
            >>> # Store result.token_map securely for later reversal
        """
        policy = policy or self.storage_policy

        # Find PII in document
        find_result = self.engine.find(
            document,
            namespaces=namespaces,
            include_matched_text=True,
        )

        sanitized_text = document
        action_taken = SecurityAction.ALLOW
        blocked = False
        reason = None
        token_map = None

        if find_result.has_matches:
            if policy.action == SecurityAction.BLOCK:
                # Block document from being indexed
                blocked = True
                action_taken = SecurityAction.BLOCK
                reason = f"Document contains {len(find_result.matches)} PII matches"

            elif policy.action == SecurityAction.SANITIZE:
                # Sanitize with tokenization for reversibility
                if policy.redaction_strategy.value == "tokenize" and policy.preserve_format:
                    sanitized_text, token_map = self.tokenizer.tokenize_with_map(
                        document, namespaces
                    )
                else:
                    redact_result = self.engine.redact(
                        document,
                        namespaces=namespaces,
                        strategy=policy.redaction_strategy,
                    )
                    sanitized_text = redact_result.redacted_text

                action_taken = SecurityAction.SANITIZE
                reason = f"Sanitized {len(find_result.matches)} PII matches"

            elif policy.action == SecurityAction.WARN:
                action_taken = SecurityAction.WARN
                reason = f"Warning: Document contains {len(find_result.matches)} PII matches"
                logger.warning(reason)

            if policy.log_matches:
                logger.info(
                    f"Storage scan: {len(find_result.matches)} matches, "
                    f"action={action_taken.value}"
                )

        return DocumentScanResult(
            original_text=document,
            sanitized_text=sanitized_text,
            matches=find_result.matches,
            action_taken=action_taken,
            blocked=blocked,
            layer=SecurityLayer.STORAGE,
            reason=reason,
            token_map=token_map,
            chunk_id=chunk_id,
            total_chunks=total_chunks,
        )

    async def scan_response(
        self,
        response: str,
        namespaces: Optional[List[str]] = None,
        policy: Optional[SecurityPolicy] = None,
        token_map: Optional[TokenMap] = None,
    ) -> ResponseScanResult:
        """
        Layer 3: Scan LLM response before returning to user.

        Args:
            response: LLM response text
            namespaces: Pattern namespaces to search
            policy: Override default output policy
            token_map: Token map for detokenization (if authorized)

        Returns:
            ResponseScanResult with action taken

        Example:
            >>> result = await middleware.scan_response(
            ...     "The customer SSN is 123-45-6789"
            ... )
            >>> if result.blocked:
            ...     return "[RESPONSE BLOCKED: Contains PII]"
            >>> return result.sanitized_text
        """
        policy = policy or self.output_policy

        # Detokenize if authorized and map provided
        processed_response = response
        if token_map and policy.allow_detokenization:
            processed_response = self.tokenizer.detokenize(response, token_map)

        # Find PII in response
        find_result = self.engine.find(
            processed_response,
            namespaces=namespaces,
            include_matched_text=True,
        )

        sanitized_text = processed_response
        action_taken = SecurityAction.ALLOW
        blocked = False
        reason = None

        if find_result.has_matches:
            # Check severity thresholds
            high_severity_matches = [
                m for m in find_result.matches if policy.should_block(m.severity)
            ]

            if high_severity_matches and policy.action == SecurityAction.BLOCK:
                blocked = True
                action_taken = SecurityAction.BLOCK
                reason = (
                    f"Response contains {len(high_severity_matches)} " "high-severity PII matches"
                )
                sanitized_text = "[RESPONSE BLOCKED: Contains sensitive information]"

            elif policy.action == SecurityAction.SANITIZE:
                redact_result = self.engine.redact(
                    processed_response,
                    namespaces=namespaces,
                    strategy=policy.redaction_strategy,
                )
                sanitized_text = redact_result.redacted_text
                action_taken = SecurityAction.SANITIZE
                reason = f"Sanitized {len(find_result.matches)} PII matches"

            elif policy.action == SecurityAction.WARN:
                action_taken = SecurityAction.WARN
                reason = f"Warning: Response contains {len(find_result.matches)} PII matches"
                logger.warning(reason)

            if policy.log_matches:
                logger.info(
                    f"Output scan: {len(find_result.matches)} matches, "
                    f"action={action_taken.value}"
                )

        return ResponseScanResult(
            original_text=response,
            sanitized_text=sanitized_text,
            matches=find_result.matches,
            action_taken=action_taken,
            blocked=blocked,
            layer=SecurityLayer.OUTPUT,
            reason=reason,
        )

    def update_policy(
        self,
        layer: SecurityLayer,
        policy: SecurityPolicy,
    ) -> None:
        """
        Update security policy for a layer.

        Args:
            layer: Security layer to update
            policy: New policy configuration
        """
        if layer == SecurityLayer.INPUT:
            self.input_policy = policy
        elif layer == SecurityLayer.STORAGE:
            self.storage_policy = policy
        elif layer == SecurityLayer.OUTPUT:
            self.output_policy = policy

        logger.info(f"Updated {layer.value} layer policy: {policy.action.value}")
