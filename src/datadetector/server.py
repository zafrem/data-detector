"""HTTP REST server for data-detector."""

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel
from starlette.responses import Response

from datadetector.engine import Engine
from datadetector.models import RedactionStrategy
from datadetector.rag_middleware import RAGSecurityMiddleware
from datadetector.rag_models import SecurityAction, SecurityLayer, SeverityLevel
from datadetector.registry import PatternRegistry, load_registry

logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "datadetector_requests_total",
    "Total requests",
    ["endpoint", "status"],
)
REQUEST_DURATION = Histogram(
    "datadetector_request_duration_seconds",
    "Request duration in seconds",
    ["endpoint"],
)
PATTERN_MATCHES = Counter(
    "datadetector_pattern_matches_total",
    "Total pattern matches",
    ["namespace", "pattern_id"],
)

# Error messages
ERROR_RAG_NOT_INITIALIZED = "RAG middleware not initialized"


# Request/Response models
class FindRequest(BaseModel):
    """Request model for /find endpoint."""

    text: str
    namespaces: Optional[List[str]] = None
    options: Optional[Dict[str, Any]] = None


class ValidateRequest(BaseModel):
    """Request model for /validate endpoint."""

    text: str
    ns_id: str


class RedactRequest(BaseModel):
    """Request model for /redact endpoint."""

    text: str
    namespaces: Optional[List[str]] = None
    strategy: Optional[str] = "mask"


class FindResponse(BaseModel):
    """Response model for /find endpoint."""

    hits: List[Dict[str, Any]]
    count: int
    namespaces_searched: List[str]


class ValidateResponse(BaseModel):
    """Response model for /validate endpoint."""

    ok: bool
    ns_id: str


class RedactResponse(BaseModel):
    """Response model for /redact endpoint."""

    text: str
    redaction_count: int
    strategy: str


class HealthResponse(BaseModel):
    """Response model for /health endpoint."""

    status: str
    version: str
    patterns_loaded: int
    namespaces: List[str]


class ReloadResponse(BaseModel):
    """Response model for /reload endpoint."""

    status: str
    version: int
    patterns_loaded: int


# RAG-specific models
class RAGQueryRequest(BaseModel):
    """Request model for RAG query scanning."""

    query: str
    namespaces: Optional[List[str]] = None
    action: Optional[str] = "sanitize"  # block, warn, sanitize, allow
    severity_threshold: Optional[str] = "medium"


class RAGDocumentRequest(BaseModel):
    """Request model for RAG document scanning."""

    document: str
    namespaces: Optional[List[str]] = None
    action: Optional[str] = "sanitize"
    use_tokenization: Optional[bool] = True


class RAGResponseRequest(BaseModel):
    """Request model for RAG response scanning."""

    response: str
    namespaces: Optional[List[str]] = None
    action: Optional[str] = "block"
    severity_threshold: Optional[str] = "high"
    token_map: Optional[Dict[str, str]] = None


class RAGScanResponse(BaseModel):
    """Response model for RAG scanning."""

    sanitized_text: str
    blocked: bool
    pii_detected: bool
    match_count: int
    action_taken: str
    reason: Optional[str] = None
    token_map: Optional[Dict[str, str]] = None


class DataDetectorServer:
    """Server wrapper for managing state."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize server with configuration."""
        self.config = config or {}
        self.registry: Optional[PatternRegistry] = None
        self.engine: Optional[Engine] = None
        self.rag_middleware: Optional[RAGSecurityMiddleware] = None
        self._load_patterns()

    def _load_patterns(self) -> None:
        """Load patterns from configuration."""
        registry_config = self.config.get("registry", {})
        paths = registry_config.get("paths")

        logger.info(f"Loading patterns from: {paths}")
        self.registry = load_registry(paths=paths)
        self.engine = Engine(
            self.registry,
            default_mask_char=self.config.get("redaction", {}).get("mask_char", "*"),
            hash_algorithm=self.config.get("redaction", {}).get("hash_algorithm", "sha256"),
        )
        self.rag_middleware = RAGSecurityMiddleware(self.engine)
        logger.info(f"Loaded {len(self.registry)} patterns")

    def reload_patterns(self) -> Dict[str, Any]:
        """Reload patterns from files."""
        try:
            old_version = self.registry.version if self.registry else 0
            self._load_patterns()
            new_version = self.registry.version if self.registry else 0
            return {
                "status": "ok",
                "version": new_version,
                "patterns_loaded": len(self.registry) if self.registry else 0,
                "message": f"Reloaded successfully (v{old_version} -> v{new_version})",
            }
        except Exception as e:
            logger.error(f"Failed to reload patterns: {e}")
            raise HTTPException(status_code=500, detail=f"Reload failed: {str(e)}")


def create_app(config: Optional[Dict[str, Any]] = None) -> FastAPI:
    """
    Create FastAPI application.

    Args:
        config: Server configuration dictionary

    Returns:
        FastAPI application instance
    """
    app = FastAPI(
        title="data-detector",
        description="PII detection and redaction service",
        version="0.0.2",
    )

    # Create server instance
    server = DataDetectorServer(config)

    # Middleware for metrics and timing
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next: Any) -> Any:
        """Record metrics for each request."""
        start_time = time.time()
        endpoint = request.url.path

        response = await call_next(request)

        duration = time.time() - start_time
        REQUEST_COUNT.labels(endpoint=endpoint, status=response.status_code).inc()
        REQUEST_DURATION.labels(endpoint=endpoint).observe(duration)

        return response

    @app.post("/find", response_model=FindResponse)
    async def find(request: FindRequest) -> FindResponse:
        """Find PII in text."""
        if server.engine is None:
            raise HTTPException(status_code=500, detail="Engine not initialized")

        try:
            options = request.options or {}
            result = server.engine.find(
                request.text,
                namespaces=request.namespaces,
                allow_overlaps=options.get("allow_overlaps", False),
                include_matched_text=options.get("include_matched_text", False),
            )

            # Record pattern matches
            for match in result.matches:
                PATTERN_MATCHES.labels(
                    namespace=match.namespace,
                    pattern_id=match.pattern_id,
                ).inc()

            hits = [
                {
                    "ns_id": m.ns_id,
                    "pattern_id": m.pattern_id,
                    "namespace": m.namespace,
                    "category": m.category.value,
                    "span": m.span,
                    "match": m.matched_text,
                    "severity": m.severity.value,
                }
                for m in result.matches
            ]

            return FindResponse(
                hits=hits,
                count=result.match_count,
                namespaces_searched=result.namespaces_searched,
            )
        except Exception as e:
            logger.error(f"Find error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/validate", response_model=ValidateResponse)
    async def validate(request: ValidateRequest) -> ValidateResponse:
        """Validate text against pattern."""
        if server.engine is None:
            raise HTTPException(status_code=500, detail="Engine not initialized")

        try:
            result = server.engine.validate(request.text, request.ns_id)
            return ValidateResponse(
                ok=result.is_valid,
                ns_id=request.ns_id,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Validate error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/redact", response_model=RedactResponse)
    async def redact(request: RedactRequest) -> RedactResponse:
        """Redact PII from text."""
        if server.engine is None:
            raise HTTPException(status_code=500, detail="Engine not initialized")

        try:
            strategy = RedactionStrategy(request.strategy or "mask")
            result = server.engine.redact(
                request.text,
                namespaces=request.namespaces,
                strategy=strategy,
            )

            return RedactResponse(
                text=result.redacted_text,
                redaction_count=result.redaction_count,
                strategy=result.strategy.value,
            )
        except Exception as e:
            logger.error(f"Redact error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        """Health check endpoint."""
        if server.registry is None:
            raise HTTPException(status_code=503, detail="Registry not initialized")

        return HealthResponse(
            status="healthy",
            version="0.0.1",
            patterns_loaded=len(server.registry),
            namespaces=list(server.registry.namespaces.keys()),
        )

    @app.post("/reload", response_model=ReloadResponse)
    async def reload() -> ReloadResponse:
        """Reload patterns from files."""
        result = server.reload_patterns()
        return ReloadResponse(**result)

    # RAG-specific endpoints
    @app.post("/rag/scan-query", response_model=RAGScanResponse)
    async def rag_scan_query(request: RAGQueryRequest) -> RAGScanResponse:
        """
        Layer 1: Scan user query before RAG processing.

        Blocks or sanitizes queries containing PII before they enter
        the RAG pipeline.
        """
        if server.rag_middleware is None:
            raise HTTPException(status_code=500, detail=ERROR_RAG_NOT_INITIALIZED)

        try:
            from datadetector.rag_models import SecurityPolicy

            # Create policy from request
            policy = SecurityPolicy(
                layer=SecurityLayer.INPUT,
                action=SecurityAction(request.action or "sanitize"),
                severity_threshold=SeverityLevel(request.severity_threshold or "medium"),
            )

            result = await server.rag_middleware.scan_query(
                request.query,
                namespaces=request.namespaces,
                policy=policy,
            )

            return RAGScanResponse(
                sanitized_text=result.sanitized_text,
                blocked=result.blocked,
                pii_detected=result.has_pii,
                match_count=result.match_count,
                action_taken=result.action_taken.value,
                reason=result.reason,
                token_map=result.token_map.tokens if result.token_map else None,
            )
        except Exception as e:
            logger.error(f"RAG query scan error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/rag/scan-document", response_model=RAGScanResponse)
    async def rag_scan_document(request: RAGDocumentRequest) -> RAGScanResponse:
        """
        Layer 2: Scan document before indexing in vector store.

        Sanitizes or tokenizes PII in documents before they are
        embedded and stored.
        """
        if server.rag_middleware is None:
            raise HTTPException(status_code=500, detail=ERROR_RAG_NOT_INITIALIZED)

        try:
            from datadetector.rag_models import SecurityPolicy

            # Create policy with tokenization support
            policy = SecurityPolicy(
                layer=SecurityLayer.STORAGE,
                action=SecurityAction(request.action or "sanitize"),
                redaction_strategy=(
                    RedactionStrategy.TOKENIZE
                    if request.use_tokenization
                    else RedactionStrategy.MASK
                ),
                preserve_format=True,
            )

            result = await server.rag_middleware.scan_document(
                request.document,
                namespaces=request.namespaces,
                policy=policy,
            )

            return RAGScanResponse(
                sanitized_text=result.sanitized_text,
                blocked=result.blocked,
                pii_detected=result.has_pii,
                match_count=result.match_count,
                action_taken=result.action_taken.value,
                reason=result.reason,
                token_map=result.token_map.tokens if result.token_map else None,
            )
        except Exception as e:
            logger.error(f"RAG document scan error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/rag/scan-response", response_model=RAGScanResponse)
    async def rag_scan_response(request: RAGResponseRequest) -> RAGScanResponse:
        """
        Layer 3: Scan LLM response before returning to user.

        Blocks or sanitizes LLM responses that contain leaked PII.
        """
        if server.rag_middleware is None:
            raise HTTPException(status_code=500, detail=ERROR_RAG_NOT_INITIALIZED)

        try:
            from datadetector.rag_models import SecurityPolicy, TokenMap

            # Create policy for output
            policy = SecurityPolicy(
                layer=SecurityLayer.OUTPUT,
                action=SecurityAction(request.action or "block"),
                severity_threshold=SeverityLevel(request.severity_threshold or "high"),
            )

            # Build token map if provided
            token_map = None
            if request.token_map:
                token_map = TokenMap(tokens=request.token_map)

            result = await server.rag_middleware.scan_response(
                request.response,
                namespaces=request.namespaces,
                policy=policy,
                token_map=token_map,
            )

            return RAGScanResponse(
                sanitized_text=result.sanitized_text,
                blocked=result.blocked,
                pii_detected=result.has_pii,
                match_count=result.match_count,
                action_taken=result.action_taken.value,
                reason=result.reason,
            )
        except Exception as e:
            logger.error(f"RAG response scan error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/metrics")
    async def metrics() -> Response:
        """Prometheus metrics endpoint."""
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


# For running directly with uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
