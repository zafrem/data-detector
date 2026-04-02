"""HTTP REST server for data-detector."""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
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


# ── Resource Scanning Models ──


class ResourceRequest(BaseModel):
    """Request model for registering a data resource."""

    name: str
    resource_type: str  # database, kafka, api, file_storage
    uri: str
    params: Optional[Dict[str, Any]] = None
    description: str = ""
    owner: Optional[str] = None
    tags: Optional[List[str]] = None


class ScanRequest(BaseModel):
    """Request model for scanning a resource."""

    strategy: str = "sample"  # metadata_only, sample, full
    containers: Optional[List[str]] = None
    namespaces: Optional[List[str]] = None
    sample_limit: int = 100


class ScanResultResponse(BaseModel):
    """Response model for a scan result."""

    scan_id: str
    resource_name: str
    status: str
    scan_started_at: Optional[str] = None
    scan_finished_at: Optional[str] = None
    scan_duration_ms: float = 0.0
    total_fields: int = 0
    pii_fields: int = 0
    pii_containers: int = 0
    errors: List[str] = []
    container_results: List[Dict[str, Any]] = []


class InventoryGenerateRequest(BaseModel):
    """Request model for inventory generation."""

    scan_ids: Optional[List[str]] = None  # None = all scans


class InventoryExportRequest(BaseModel):
    """Request model for inventory export."""

    format: str = "json"  # json, csv, yaml, html


class InventoryDiffRequest(BaseModel):
    """Request model for inventory diff."""

    old_inventory_json: str
    new_scan_ids: Optional[List[str]] = None


class LineageBuildRequest(BaseModel):
    """Request model for building lineage."""

    scan_ids: Optional[List[str]] = None
    cross_resource_links: Optional[List[Dict[str, str]]] = None


class LineageTraceRequest(BaseModel):
    """Request model for tracing a field."""

    field_path: str  # e.g., "my-db.users.email"
    direction: str = "both"  # upstream, downstream, both
    max_depth: int = 10


class DataDetectorServer:
    """Server wrapper for managing state."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize server with configuration."""
        self.config = config or {}
        self.registry: Optional[PatternRegistry] = None
        self.engine: Optional[Engine] = None
        self.rag_middleware: Optional[RAGSecurityMiddleware] = None
        # Resource scanning state
        self._resources: Dict[str, Any] = {}  # name -> DataResource
        self._scan_results: Dict[str, Any] = {}  # scan_id -> ResourceScanResult
        self._inventories: Dict[str, Any] = {}  # inventory_id -> DataInventory
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
        version="0.0.5",
    )

    # Create server instance
    server = DataDetectorServer(config)

    # CORS middleware
    cors_config = (config or {}).get("cors", {})
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config.get("allow_origins", ["*"]),
        allow_credentials=cors_config.get("allow_credentials", True),
        allow_methods=cors_config.get("allow_methods", ["*"]),
        allow_headers=cors_config.get("allow_headers", ["*"]),
    )

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
            version="0.0.5",
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

    # ── Resource Scanning Endpoints ──

    @app.post("/resources", tags=["resource-scanning"])
    async def register_resource(request: ResourceRequest) -> Dict[str, Any]:
        """Register a data resource for scanning."""
        from datadetector.resource_models import (
            ConnectionConfig,
            DataResource,
            ResourceType,
        )

        try:
            resource = DataResource(
                name=request.name,
                resource_type=ResourceType(request.resource_type),
                connection=ConnectionConfig(uri=request.uri, params=request.params or {}),
                description=request.description,
                owner=request.owner,
                tags=request.tags or [],
            )
            server._resources[request.name] = resource
            return {
                "status": "registered",
                "name": request.name,
                "resource_type": request.resource_type,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/resources", tags=["resource-scanning"])
    async def list_resources() -> List[Dict[str, Any]]:
        """List all registered resources."""
        return [
            {
                "name": r.name,
                "resource_type": r.resource_type.value,
                "description": r.description,
                "owner": r.owner,
                "tags": r.tags,
            }
            for r in server._resources.values()
        ]

    @app.delete("/resources/{name}", tags=["resource-scanning"])
    async def delete_resource(name: str) -> Dict[str, str]:
        """Delete a registered resource."""
        if name not in server._resources:
            raise HTTPException(status_code=404, detail=f"Resource '{name}' not found")
        del server._resources[name]
        return {"status": "deleted", "name": name}

    @app.post(
        "/resources/{name}/scan",
        response_model=ScanResultResponse,
        tags=["resource-scanning"],
    )
    async def scan_resource(name: str, request: ScanRequest) -> ScanResultResponse:
        """Stage 1: Scan a resource for PII."""
        if server.engine is None:
            raise HTTPException(status_code=500, detail="Engine not initialized")
        if name not in server._resources:
            raise HTTPException(status_code=404, detail=f"Resource '{name}' not found")

        from datadetector.adapters import get_adapter_class
        from datadetector.data_explorer import DataExplorer
        from datadetector.resource_models import ScanStrategy

        resource = server._resources[name]

        try:
            adapter_cls = get_adapter_class(resource.resource_type)
        except (ImportError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))

        explorer = DataExplorer(
            server.engine,
            sample_limit=request.sample_limit,
            namespaces=request.namespaces,
        )

        try:
            adapter = adapter_cls(resource)
            adapter.connect()
            try:
                result = explorer.scan(
                    adapter,
                    strategy=ScanStrategy(request.strategy),
                    containers=request.containers,
                )
            finally:
                adapter.close()
        except Exception as e:
            logger.error(f"Scan error for '{name}': {e}")
            raise HTTPException(status_code=500, detail=f"Scan failed: {e}")

        scan_id = str(uuid.uuid4())[:8]
        server._scan_results[scan_id] = result

        return ScanResultResponse(
            scan_id=scan_id,
            resource_name=name,
            status=result.status.value,
            scan_started_at=result.scan_started_at,
            scan_finished_at=result.scan_finished_at,
            scan_duration_ms=result.scan_duration_ms,
            total_fields=result.total_fields,
            pii_fields=result.pii_fields,
            pii_containers=result.pii_containers,
            errors=result.errors,
            container_results=_scan_result_to_containers(result),
        )

    @app.get("/scans", tags=["resource-scanning"])
    async def list_scans() -> List[Dict[str, Any]]:
        """List all scan results."""
        return [
            {
                "scan_id": sid,
                "resource_name": r.resource.name,
                "status": r.status.value,
                "scan_started_at": r.scan_started_at,
                "scan_finished_at": r.scan_finished_at,
                "pii_fields": r.pii_fields,
                "total_fields": r.total_fields,
            }
            for sid, r in server._scan_results.items()
        ]

    @app.get("/scans/{scan_id}", response_model=ScanResultResponse, tags=["resource-scanning"])
    async def get_scan(scan_id: str) -> ScanResultResponse:
        """Get a specific scan result."""
        if scan_id not in server._scan_results:
            raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found")

        result = server._scan_results[scan_id]
        return ScanResultResponse(
            scan_id=scan_id,
            resource_name=result.resource.name,
            status=result.status.value,
            scan_started_at=result.scan_started_at,
            scan_finished_at=result.scan_finished_at,
            scan_duration_ms=result.scan_duration_ms,
            total_fields=result.total_fields,
            pii_fields=result.pii_fields,
            pii_containers=result.pii_containers,
            errors=result.errors,
            container_results=_scan_result_to_containers(result),
        )

    @app.post("/inventory/generate", tags=["resource-scanning"])
    async def generate_inventory(request: InventoryGenerateRequest) -> Dict[str, Any]:
        """Stage 2: Generate PII inventory from scan results."""
        from datadetector.data_inventory import DataInventoryGenerator

        gen = DataInventoryGenerator()

        scan_ids = request.scan_ids or list(server._scan_results.keys())
        for sid in scan_ids:
            if sid not in server._scan_results:
                raise HTTPException(status_code=404, detail=f"Scan '{sid}' not found")
            gen.add_scan_result(server._scan_results[sid])

        inventory = gen.generate()
        inventory_id = str(uuid.uuid4())[:8]
        server._inventories[inventory_id] = inventory

        summary = DataInventoryGenerator.summary(inventory)
        summary["inventory_id"] = inventory_id
        summary["scan_ids"] = scan_ids

        return summary

    @app.get("/inventory/{inventory_id}/export", tags=["resource-scanning"])
    async def export_inventory(inventory_id: str, format: str = "json") -> Response:
        """Export inventory in the specified format."""
        if inventory_id not in server._inventories:
            raise HTTPException(status_code=404, detail=f"Inventory '{inventory_id}' not found")

        from datadetector.data_inventory import DataInventoryGenerator
        from datadetector.resource_models import InventoryFormat

        inventory = server._inventories[inventory_id]
        gen = DataInventoryGenerator()

        try:
            fmt = InventoryFormat(format)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid format: {format}")

        result = gen.export(inventory, fmt)

        media_types = {
            "json": "application/json",
            "csv": "text/csv",
            "yaml": "text/yaml",
            "html": "text/html",
        }
        return Response(content=result, media_type=media_types.get(format, "text/plain"))

    @app.post("/inventory/diff", tags=["resource-scanning"])
    async def diff_inventory(request: InventoryDiffRequest) -> Dict[str, Any]:
        """Compare old inventory JSON with current scan results."""
        from datadetector.data_inventory import DataInventoryGenerator

        try:
            old_inv = DataInventoryGenerator.load_json_str(request.old_inventory_json)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid old inventory: {e}")

        gen = DataInventoryGenerator()
        scan_ids = request.new_scan_ids or list(server._scan_results.keys())
        for sid in scan_ids:
            if sid not in server._scan_results:
                raise HTTPException(status_code=404, detail=f"Scan '{sid}' not found")
            gen.add_scan_result(server._scan_results[sid])

        new_inv = gen.generate()
        diff = DataInventoryGenerator.diff(old_inv, new_inv)

        return {
            "added": len(diff.added),
            "removed": len(diff.removed),
            "changed": len(diff.changed),
            "unchanged": diff.unchanged_count,
            "timestamp": diff.timestamp,
        }

    @app.post("/lineage/build", tags=["resource-scanning"])
    async def build_lineage(request: LineageBuildRequest) -> Dict[str, Any]:
        """Stage 3: Build PII lineage graph from scan results."""
        from datadetector.data_lineage import DataLineageTracer

        tracer = DataLineageTracer()

        scan_ids = request.scan_ids or list(server._scan_results.keys())
        for sid in scan_ids:
            if sid not in server._scan_results:
                raise HTTPException(status_code=404, detail=f"Scan '{sid}' not found")
            tracer.add_scan_result(server._scan_results[sid])

        if request.cross_resource_links:
            for link in request.cross_resource_links:
                tracer.add_cross_resource_link(
                    link["src_resource"],
                    link["src_field"],
                    link["tgt_resource"],
                    link["tgt_field"],
                )

        tracer.build_graph()

        data = tracer.to_dict()
        data["pii_flow_summary"] = tracer.get_pii_flow_summary()
        data["sources"] = [n.full_path for n in tracer.find_pii_sources()]
        data["sinks"] = [n.full_path for n in tracer.find_pii_sinks()]

        return data

    @app.post("/lineage/trace", tags=["resource-scanning"])
    async def trace_lineage(request: LineageTraceRequest) -> Dict[str, Any]:
        """Trace PII flow from a specific field."""
        from datadetector.data_lineage import DataLineageTracer

        tracer = DataLineageTracer()
        for result in server._scan_results.values():
            tracer.add_scan_result(result)

        tracer.build_graph()
        subgraph = tracer.trace(
            request.field_path,
            direction=request.direction,
            max_depth=request.max_depth,
        )

        return {
            "field": request.field_path,
            "direction": request.direction,
            "nodes": [
                {
                    "id": n.full_path,
                    "resource": n.resource_name,
                    "field": n.field_qualified_name,
                    "categories": [c.value for c in n.categories],
                    "has_pii": bool(n.categories),
                }
                for n in subgraph.nodes
            ],
            "edges": [
                {
                    "source": e.source.full_path,
                    "target": e.target.full_path,
                    "type": e.relationship_type.value,
                }
                for e in subgraph.edges
            ],
        }

    @app.get("/lineage/mermaid", tags=["resource-scanning"])
    async def lineage_mermaid() -> Response:
        """Get Mermaid diagram of PII lineage."""
        from datadetector.data_lineage import DataLineageTracer

        tracer = DataLineageTracer()
        for result in server._scan_results.values():
            tracer.add_scan_result(result)

        tracer.build_graph()
        mermaid = tracer.to_mermaid()
        return Response(content=mermaid, media_type="text/plain")

    @app.get("/metrics")
    async def metrics() -> Response:
        """Prometheus metrics endpoint."""
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


def _scan_result_to_containers(result: Any) -> List[Dict[str, Any]]:
    """Convert ResourceScanResult container data to JSON-serializable dicts."""
    containers = []
    for cr in result.container_results:
        fields = []
        for fr in cr.field_results:
            field_data: Dict[str, Any] = {
                "field_name": fr.field_info.name,
                "container_name": fr.field_info.container_name,
                "data_type": fr.field_info.data_type,
                "pii_detected": fr.pii_detected,
                "confidence": fr.confidence.value,
                "categories": [c.value for c in fr.categories],
                "severities": [s.value for s in fr.severities],
                "metadata_score": fr.metadata_score,
                "sample_score": fr.sample_score,
                "combined_score": fr.combined_score,
                "sample_count": fr.sample_count,
                "match_count": fr.match_count,
                "match_ratio": fr.match_ratio,
                "ns_ids": fr.ns_ids,
            }
            if fr.pii_detected and fr.max_severity:
                field_data["max_severity"] = fr.max_severity.value
            if hasattr(fr, "masking_policy") and fr.masking_policy:
                field_data["masking_policy"] = {
                    "strategy": fr.masking_policy.strategy.value,
                    "mask_pattern": fr.masking_policy.mask_pattern,
                }
            fields.append(field_data)

        containers.append(
            {
                "container_name": cr.container.name,
                "container_type": cr.container.container_type.value,
                "scan_duration_ms": cr.scan_duration_ms,
                "total_fields": len(cr.field_results),
                "pii_fields": cr.pii_field_count,
                "fields": fields,
            }
        )
    return containers


# For running directly with uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
