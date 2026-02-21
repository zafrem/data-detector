"""Vercel serverless API for data-detector PII detection and redaction."""

import sys
from pathlib import Path

# Ensure the src/ directory is on sys.path for Vercel deployments
_project_root = Path(__file__).resolve().parent.parent
_src_dir = _project_root / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

logger = logging.getLogger("datadetector.api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="data-detector API",
    description="PII detection, validation, masking, and fake-replacement API",
    version="0.0.3",
)

# ---------------------------------------------------------------------------
# Auth helpers  (stateless HMAC-based API keys)
# ---------------------------------------------------------------------------
# ADMIN_TOKEN  – the "designated token" used to issue API keys
# API_SECRET   – secret used to sign API keys (auto-generated if absent)
ADMIN_TOKEN: str = os.environ.get("ADMIN_TOKEN", "")
API_SECRET: str = os.environ.get("API_SECRET", os.urandom(32).hex())
LOG_FILE: str = os.environ.get("API_LOG_FILE", "")  # optional JSON log file path

security = HTTPBearer()


# ---------------------------------------------------------------------------
# Structured logging helpers
# ---------------------------------------------------------------------------
def _write_log(entry: Dict[str, Any]) -> None:
    """Write a structured log entry to logger and optionally to a JSON-lines file."""
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    logger.info(json.dumps(entry, ensure_ascii=False))

    if LOG_FILE:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.warning("Failed to write log file %s: %s", LOG_FILE, exc)


def _log_issuance(system: str, key_prefix: str) -> None:
    """Record a token issuance event."""
    _write_log({
        "event": "token_issued",
        "system": system,
        "key_prefix": key_prefix,
    })


def _log_usage(system: str, endpoint: str, key_prefix: str, detail: Optional[Dict[str, Any]] = None) -> None:
    """Record an API usage event."""
    entry: Dict[str, Any] = {
        "event": "api_call",
        "system": system,
        "endpoint": endpoint,
        "key_prefix": key_prefix,
    }
    if detail:
        entry["detail"] = detail
    _write_log(entry)


# ---------------------------------------------------------------------------
# Auth helpers  (stateless HMAC-based API keys with embedded system name)
# ---------------------------------------------------------------------------
def _sign(payload: str) -> str:
    """Create HMAC-SHA256 signature for *payload*."""
    return hmac.new(API_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _encode_system(system: str) -> str:
    """Base64url-encode the system name (no padding) for safe embedding in keys."""
    return base64.urlsafe_b64encode(system.encode()).rstrip(b"=").decode()


def _decode_system(encoded: str) -> str:
    """Decode a base64url-encoded system name."""
    padded = encoded + "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(padded).decode()


def _generate_api_key(system: str) -> str:
    """Generate a verifiable API key: ``dd_<random>:<ts>:<system_b64>.<signature>``."""
    rand = secrets.token_hex(16)
    ts = str(int(time.time()))
    sys_enc = _encode_system(system)
    payload = f"{rand}:{ts}:{sys_enc}"
    sig = _sign(payload)
    return f"dd_{payload}.{sig}"


def _verify_api_key(key: str) -> Optional[str]:
    """Verify an API key. Returns the embedded system name or None if invalid."""
    if not key.startswith("dd_"):
        return None
    try:
        body = key[3:]  # strip "dd_"
        payload, sig = body.rsplit(".", 1)
        if not hmac.compare_digest(sig, _sign(payload)):
            return None
        parts = payload.split(":")
        if len(parts) >= 3:
            return _decode_system(parts[2])
        return "unknown"
    except (ValueError, IndexError):
        return None


def _key_prefix(key: str) -> str:
    """Return a safe-to-log prefix of an API key."""
    return key[:20] + "..." if len(key) > 20 else key


def require_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """FastAPI dependency – reject requests without a valid API key. Logs usage."""
    token = credentials.credentials
    system = _verify_api_key(token)
    if system is None:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    # Store system name for endpoint handlers to use
    request.state.system = system
    request.state.key_prefix = _key_prefix(token)
    return token


# ---------------------------------------------------------------------------
# Engine singleton (lazy-loaded)
# ---------------------------------------------------------------------------
_engine_instance = None


def _get_engine():
    global _engine_instance
    if _engine_instance is None:
        from datadetector.engine import Engine
        from datadetector.models import RedactionStrategy  # noqa: F401
        from datadetector.registry import load_registry

        registry = load_registry()
        _engine_instance = Engine(registry)
    return _engine_instance


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class AuthIssueRequest(BaseModel):
    """Request body for issuing a new API key."""

    token: str
    system: str  # e.g. "billing-service", "crm-app", "internal-tool"


class AuthIssueResponse(BaseModel):
    api_key: str
    system: str
    message: str


class ValidateRequest(BaseModel):
    text: str
    ns_id: str


class ValidateResponse(BaseModel):
    ok: bool
    ns_id: str


class MaskRequest(BaseModel):
    text: str
    namespaces: Optional[List[str]] = None


class MaskResponse(BaseModel):
    original: str
    masked: str
    change_count: int
    changes: List[Dict[str, Any]]


class FakeRequest(BaseModel):
    text: str
    namespaces: Optional[List[str]] = None


class FakeResponse(BaseModel):
    original: str
    replaced: str
    change_count: int
    changes: List[Dict[str, Any]]


class DetectRequest(BaseModel):
    text: str
    namespaces: Optional[List[str]] = None


class DetectResponse(BaseModel):
    text: str
    pii_found: bool
    match_count: int
    matches: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def homepage():
    """Serve the API guide page."""
    html_path = Path(__file__).resolve().parent.parent / "public" / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    # Fallback if file not found
    return HTMLResponse("<h1>data-detector API</h1><p>Visit <a href='/api'>/api</a></p>")


@app.get("/api")
async def api_info():
    """Health / info endpoint (no auth required)."""
    return {
        "service": "data-detector",
        "version": "0.0.3",
        "endpoints": [
            "POST /api/auth/issue",
            "POST /api/detect",
            "POST /api/validate",
            "POST /api/mask",
            "POST /api/fake",
        ],
    }


@app.post("/api/auth/issue", response_model=AuthIssueResponse)
async def auth_issue(body: AuthIssueRequest):
    """Issue a new API key. Requires the designated admin token and a system name."""
    if not ADMIN_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_TOKEN is not configured on the server",
        )
    if not hmac.compare_digest(body.token, ADMIN_TOKEN):
        raise HTTPException(status_code=403, detail="Invalid admin token")

    system = body.system.strip()
    if not system:
        raise HTTPException(status_code=422, detail="system name is required")

    api_key = _generate_api_key(system)
    _log_issuance(system, _key_prefix(api_key))

    return AuthIssueResponse(
        api_key=api_key,
        system=system,
        message="Store this key securely. It cannot be retrieved again.",
    )


@app.post("/api/detect", response_model=DetectResponse)
async def detect(request: Request, body: DetectRequest, _key: str = Depends(require_api_key)):
    """Detect PII in text and return match details."""
    engine = _get_engine()
    result = engine.find(
        body.text,
        namespaces=body.namespaces,
        include_matched_text=True,
    )
    matches = [
        {
            "ns_id": m.ns_id,
            "category": m.category.value,
            "start": m.start,
            "end": m.end,
            "matched_text": m.matched_text,
            "severity": m.severity.value,
        }
        for m in result.matches
    ]
    _log_usage(request.state.system, "/api/detect", request.state.key_prefix, {
        "match_count": result.match_count,
        "text_length": len(body.text),
    })
    return DetectResponse(
        text=body.text,
        pii_found=result.has_matches,
        match_count=result.match_count,
        matches=matches,
    )


@app.post("/api/validate", response_model=ValidateResponse)
async def validate(request: Request, body: ValidateRequest, _key: str = Depends(require_api_key)):
    """Validate text against a specific pattern."""
    engine = _get_engine()
    try:
        result = engine.validate(body.text, body.ns_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    _log_usage(request.state.system, "/api/validate", request.state.key_prefix, {
        "ns_id": body.ns_id,
        "is_valid": result.is_valid,
    })
    return ValidateResponse(ok=result.is_valid, ns_id=body.ns_id)


@app.post("/api/mask", response_model=MaskResponse)
async def mask(request: Request, body: MaskRequest, _key: str = Depends(require_api_key)):
    """Mask (redact) PII in text. Returns masked text and change count."""
    from datadetector.models import RedactionStrategy

    engine = _get_engine()
    result = engine.redact(
        body.text,
        namespaces=body.namespaces,
        strategy=RedactionStrategy.MASK,
    )
    changes = [
        {
            "ns_id": m.ns_id,
            "category": m.category.value,
            "start": m.start,
            "end": m.end,
            "original_fragment": body.text[m.start : m.end],
            "severity": m.severity.value,
        }
        for m in result.matches
    ]
    _log_usage(request.state.system, "/api/mask", request.state.key_prefix, {
        "change_count": result.redaction_count,
        "text_length": len(body.text),
    })
    return MaskResponse(
        original=body.text,
        masked=result.redacted_text,
        change_count=result.redaction_count,
        changes=changes,
    )


@app.post("/api/fake", response_model=FakeResponse)
async def fake(request: Request, body: FakeRequest, _key: str = Depends(require_api_key)):
    """Replace PII with realistic fake data. Returns replaced text and change count."""
    from datadetector.models import RedactionStrategy

    engine = _get_engine()
    result = engine.redact(
        body.text,
        namespaces=body.namespaces,
        strategy=RedactionStrategy.FAKE,
    )
    changes = [
        {
            "ns_id": m.ns_id,
            "category": m.category.value,
            "start": m.start,
            "end": m.end,
            "original_fragment": body.text[m.start : m.end],
            "severity": m.severity.value,
        }
        for m in result.matches
    ]
    _log_usage(request.state.system, "/api/fake", request.state.key_prefix, {
        "change_count": result.redaction_count,
        "text_length": len(body.text),
    })
    return FakeResponse(
        original=body.text,
        replaced=result.redacted_text,
        change_count=result.redaction_count,
        changes=changes,
    )


@app.get("/api/logs")
async def get_logs(
    system: Optional[str] = None,
    event: Optional[str] = None,
    limit: int = 100,
    _key: str = Depends(require_api_key),
):
    """
    Retrieve usage logs. Requires API key.

    Query params:
        system: filter by system name
        event:  filter by event type (token_issued, api_call)
        limit:  max entries to return (default 100)

    Note: Only available when API_LOG_FILE is configured.
    """
    if not LOG_FILE:
        raise HTTPException(
            status_code=404,
            detail="Logging to file is not enabled. Set API_LOG_FILE env var.",
        )
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return {"logs": [], "total": 0}

    logs = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if system and entry.get("system") != system:
            continue
        if event and entry.get("event") != event:
            continue
        logs.append(entry)
        if len(logs) >= limit:
            break

    return {"logs": logs, "total": len(logs)}
