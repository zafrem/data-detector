"""Streaming engine for real-time PII scanning in RAG pipelines."""

import asyncio
import logging
import sys
from typing import Any, AsyncIterator, Callable, List, Optional

from datadetector.engine import Engine
from datadetector.models import FindResult, RedactionStrategy

# Compatibility for Python 3.8 (asyncio.to_thread added in 3.9)
if sys.version_info >= (3, 9):
    to_thread = asyncio.to_thread
else:

    async def to_thread(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Compatibility function for asyncio.to_thread (Python 3.9+)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


logger = logging.getLogger(__name__)


class StreamEngine:
    """
    High-performance streaming engine for real-time PII detection.

    Optimized for RAG pipelines where sub-10ms latency is critical.
    """

    def __init__(
        self,
        engine: Engine,
        buffer_size: int = 1024,
        max_concurrent: int = 10,
    ) -> None:
        """
        Initialize streaming engine.

        Args:
            engine: Base Engine instance for pattern matching
            buffer_size: Buffer size for streaming chunks (bytes)
            max_concurrent: Maximum concurrent scan operations
        """
        self.engine = engine
        self.buffer_size = buffer_size
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def scan_stream(
        self,
        text_stream: AsyncIterator[str],
        namespaces: Optional[List[str]] = None,
        stop_on_first: bool = False,
    ) -> AsyncIterator[FindResult]:
        """
        Scan streaming text for PII.

        Args:
            text_stream: Async iterator of text chunks
            namespaces: Pattern namespaces to search
            stop_on_first: Stop on first PII match (faster)

        Yields:
            FindResult for each chunk
        """
        async for chunk in text_stream:
            async with self._semaphore:
                result = await to_thread(
                    self.engine.find,
                    chunk,
                    namespaces=namespaces,
                    stop_on_first_match=stop_on_first,
                )
                yield result

    async def scan_batch(
        self,
        texts: List[str],
        namespaces: Optional[List[str]] = None,
        stop_on_first: bool = False,
    ) -> List[FindResult]:
        """
        Scan multiple texts concurrently.

        Args:
            texts: List of texts to scan
            namespaces: Pattern namespaces to search
            stop_on_first: Stop on first PII match per text

        Returns:
            List of FindResult objects
        """

        async def scan_one(text: str) -> FindResult:
            async with self._semaphore:
                return await to_thread(
                    self.engine.find,
                    text,
                    namespaces=namespaces,
                    stop_on_first_match=stop_on_first,
                )

        tasks = [scan_one(text) for text in texts]
        return await asyncio.gather(*tasks)

    async def redact_stream(
        self,
        text_stream: AsyncIterator[str],
        namespaces: Optional[List[str]] = None,
        strategy: Optional[RedactionStrategy] = None,
    ) -> AsyncIterator[str]:
        """
        Redact PII from streaming text.

        Args:
            text_stream: Async iterator of text chunks
            namespaces: Pattern namespaces to search
            strategy: Redaction strategy (mask/hash/tokenize)

        Yields:
            Redacted text chunks
        """
        async for chunk in text_stream:
            async with self._semaphore:
                result = await to_thread(
                    self.engine.redact,
                    chunk,
                    namespaces=namespaces,
                    strategy=strategy,
                )
                yield result.redacted_text

    async def process_documents(
        self,
        documents: List[str],
        chunk_size: int = 512,  # Reserved for future chunking implementation
        chunk_overlap: int = 50,  # Reserved for future chunking implementation
        namespaces: Optional[List[str]] = None,
    ) -> List[FindResult]:
        """
        Process documents with chunk-aware scanning.

        Splits documents into chunks while preserving PII context
        at boundaries.

        Args:
            documents: List of documents to process
            chunk_size: Characters per chunk (reserved for future implementation)
            chunk_overlap: Overlap between chunks to catch boundary PII (reserved for future implementation)
            namespaces: Pattern namespaces to search

        Returns:
            List of FindResult objects per document

        Note:
            Chunking parameters are currently reserved for future implementation.
            Documents are processed as a whole.
        """
        # Note: chunk_size and chunk_overlap are reserved for future chunking feature
        _ = chunk_size  # Suppress unused parameter warning
        _ = chunk_overlap  # Suppress unused parameter warning

        async def process_one(doc: str) -> FindResult:
            # For now, scan full document
            # TODO: Implement proper chunking with boundary awareness
            async with self._semaphore:
                return await to_thread(
                    self.engine.find,
                    doc,
                    namespaces=namespaces,
                )

        tasks = [process_one(doc) for doc in documents]
        return await asyncio.gather(*tasks)
