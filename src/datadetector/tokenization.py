"""Reversible PII tokenization for RAG storage layer."""

import hashlib
import logging
from typing import Dict, List, Optional, Tuple

from datadetector.engine import Engine
from datadetector.rag_models import TokenMap

logger = logging.getLogger(__name__)


class SecureTokenizer:
    """
    Reversible PII tokenization for secure storage.

    Allows PII to be masked in vector stores while maintaining
    the ability to unmask for authorized access.
    """

    def __init__(
        self,
        engine: Engine,
        token_prefix: str = "TOKEN",
        use_stable_tokens: bool = False,
    ) -> None:
        """
        Initialize tokenizer.

        Args:
            engine: Engine instance for PII detection
            token_prefix: Prefix for generated tokens
            use_stable_tokens: If True, same PII always gets same token
                             (deterministic but less secure)
        """
        self.engine = engine
        self.token_prefix = token_prefix
        self.use_stable_tokens = use_stable_tokens
        self._token_counter = 0

    def tokenize_with_map(
        self,
        text: str,
        namespaces: Optional[List[str]] = None,
    ) -> Tuple[str, TokenMap]:
        """
        Tokenize PII and return mapping for reversal.

        Args:
            text: Text to tokenize
            namespaces: Pattern namespaces to search

        Returns:
            Tuple of (sanitized_text, token_map)

        Example:
            >>> tokenizer = SecureTokenizer(engine)
            >>> sanitized, token_map = tokenizer.tokenize_with_map(
            ...     "Email john@example.com, SSN 123-45-6789"
            ... )
            >>> print(sanitized)
            "Email [TOKEN:comm:email:0], SSN [TOKEN:us:ssn:1]"
            >>> token_map.tokens
            {'[TOKEN:comm:email:0]': 'john@example.com',
             '[TOKEN:us:ssn:1]': '123-45-6789'}
        """
        # Find all PII matches
        result = self.engine.find(
            text,
            namespaces=namespaces,
            include_matched_text=True,
        )

        if not result.has_matches:
            return text, TokenMap()

        # Build token map
        token_map = TokenMap()
        sanitized = text

        # Process matches in reverse order to preserve positions
        for match in reversed(result.matches):
            original_value = text[match.start : match.end]

            # Generate token
            token = self._generate_token(
                category=match.category,
                namespace=match.namespace,
                value=original_value,
            )

            # Add to map
            token_map.add(token, original_value)

            # Replace in text
            sanitized = sanitized[: match.start] + token + sanitized[match.end :]

        # Generate hash for secure storage
        token_map.hash = self._hash_token_map(token_map.tokens)

        return sanitized, token_map

    def detokenize(
        self,
        text: str,
        token_map: TokenMap,
        partial: bool = False,
    ) -> str:
        """
        Reverse tokenization using token map.

        Args:
            text: Tokenized text
            token_map: Token mapping to use
            partial: If True, only detokenize tokens present in map

        Returns:
            Detokenized text

        Example:
            >>> detokenized = tokenizer.detokenize(
            ...     "Email [TOKEN:comm:email:0]",
            ...     token_map
            ... )
            >>> print(detokenized)
            "Email john@example.com"
        """
        result = text

        for token, original in token_map.tokens.items():
            if token in result:
                result = result.replace(token, original)
            elif not partial:
                logger.warning(f"Token not found in text: {token}")

        return result

    def _generate_token(
        self,
        category: str,
        namespace: str,
        value: str,
    ) -> str:
        """
        Generate token for PII value.

        Args:
            category: PII category (email, ssn, etc.)
            namespace: Pattern namespace
            value: Original PII value

        Returns:
            Generated token string
        """
        if self.use_stable_tokens:
            # Deterministic token based on value hash
            value_hash = hashlib.sha256(value.encode()).hexdigest()[:8]
            return f"[{self.token_prefix}:{namespace}:{category}:{value_hash}]"
        else:
            # Random token
            token_id = self._token_counter
            self._token_counter += 1
            return f"[{self.token_prefix}:{namespace}:{category}:{token_id}]"

    def _hash_token_map(self, tokens: Dict[str, str]) -> str:
        """
        Generate hash of token map for verification.

        Args:
            tokens: Token mapping dict

        Returns:
            SHA256 hash of token map
        """
        # Sort for deterministic hash
        sorted_items = sorted(tokens.items())
        content = str(sorted_items).encode()
        return hashlib.sha256(content).hexdigest()

    def encrypt_token_map(
        self,
        token_map: TokenMap,
        encryption_key: Optional[bytes] = None,
    ) -> bytes:
        """
        Encrypt token map for secure storage.

        Args:
            token_map: Token map to encrypt
            encryption_key: Encryption key (generates if None)

        Returns:
            Encrypted token map bytes

        Note:
            Requires cryptography library for production use.
            This is a placeholder implementation.
        """
        # TODO: Implement proper encryption using cryptography library
        # For now, just return JSON bytes
        import json

        data = json.dumps(token_map.tokens).encode()

        logger.warning(
            "Token map encryption not implemented. "
            "Install cryptography library for production use."
        )

        return data

    def decrypt_token_map(
        self,
        encrypted_data: bytes,
        encryption_key: bytes,
    ) -> TokenMap:
        """
        Decrypt token map from storage.

        Args:
            encrypted_data: Encrypted token map
            encryption_key: Decryption key

        Returns:
            Decrypted TokenMap

        Note:
            Requires cryptography library for production use.
        """
        # TODO: Implement proper decryption
        import json

        tokens = json.loads(encrypted_data.decode())
        token_map = TokenMap(tokens=tokens)
        token_map.hash = self._hash_token_map(tokens)

        return token_map
