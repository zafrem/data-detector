"""Vercel serverless API for data-detector PII detection and redaction."""

import sys
from pathlib import Path

# Ensure the src/ directory is on sys.path for Vercel deployments
_project_root = Path(__file__).resolve().parent.parent
_src_dir = _project_root / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

import base64  # noqa: E402
import hashlib  # noqa: E402
import hmac  # noqa: E402
import json  # noqa: E402
import logging  # noqa: E402
import os  # noqa: E402
import secrets  # noqa: E402
import time  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from typing import Any, Dict, List, Optional  # noqa: E402

from fastapi import Depends, FastAPI, HTTPException, Request, Response  # noqa: E402
from fastapi.responses import HTMLResponse, PlainTextResponse  # noqa: E402
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer  # noqa: E402
from pydantic import BaseModel  # noqa: E402

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
    version="0.0.5",
)

# ---------------------------------------------------------------------------
# Embedded guide HTML (fallback when public/index.html is not found on Vercel)
# ---------------------------------------------------------------------------
_GUIDE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="google-site-verification" content="google736311ca6ba1b7ad.html" />
<title>Data Detector API</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0a0b;--surface:#111113;--border:#1e1e22;
  --text:#e8e6e3;--dim:#6b6966;--accent:#d4f34a;
  --danger:#ff4d4d;--mono:'IBM Plex Mono',monospace;
  --serif:'Instrument Serif',Georgia,serif;
}
html{font-size:15px;scroll-behavior:smooth}
body{
  background:var(--bg);color:var(--text);
  font-family:var(--mono);line-height:1.7;
  min-height:100vh;overflow-x:hidden;
}
body::before{
  content:'';position:fixed;inset:0;
  background:
    radial-gradient(ellipse 60% 40% at 20% 10%,rgba(212,243,74,.04),transparent),
    radial-gradient(ellipse 50% 50% at 80% 80%,rgba(212,243,74,.02),transparent);
  pointer-events:none;z-index:0;
}
.wrap{max-width:820px;margin:0 auto;padding:0 2rem;position:relative;z-index:1}
header{padding:5rem 0 3rem;border-bottom:1px solid var(--border)}
header .tag{
  display:inline-block;font-size:.65rem;letter-spacing:.12em;text-transform:uppercase;
  color:var(--bg);background:var(--accent);padding:.2rem .7rem;border-radius:2px;
  margin-bottom:1.4rem;font-weight:600;
}
header h1{
  font-family:var(--serif);font-weight:400;font-size:3.2rem;
  line-height:1.1;letter-spacing:-.02em;margin-bottom:.8rem;
}
header h1 em{font-style:italic;color:var(--accent)}
header p{color:var(--dim);font-size:.85rem;max-width:520px}
header .base-url{
  margin-top:1.4rem;padding:.6rem 1rem;
  background:var(--surface);border:1px solid var(--border);border-radius:4px;
  font-size:.8rem;display:inline-flex;align-items:center;gap:.6rem;
  cursor:pointer;transition:border-color .2s;
}
header .base-url:hover{border-color:var(--accent)}
header .base-url .label{color:var(--dim);font-size:.65rem;text-transform:uppercase;letter-spacing:.08em}
header .base-url code{color:var(--accent)}
header .base-url .copy{color:var(--dim);font-size:.65rem;opacity:0;transition:opacity .2s}
header .base-url:hover .copy{opacity:1}
section{padding:3rem 0;border-bottom:1px solid var(--border)}
section:last-of-type{border-bottom:none;padding-bottom:5rem}
.section-label{
  font-size:.6rem;letter-spacing:.14em;text-transform:uppercase;
  color:var(--dim);margin-bottom:1.6rem;font-weight:600;
}
.auth-flow{display:grid;gap:1rem}
.auth-step{
  display:grid;grid-template-columns:2rem 1fr;gap:1rem;
  padding:1.2rem 1.4rem;background:var(--surface);
  border:1px solid var(--border);border-radius:6px;
}
.auth-step .num{font-family:var(--serif);font-size:1.6rem;color:var(--accent);line-height:1}
.auth-step h3{font-size:.8rem;font-weight:600;margin-bottom:.3rem}
.auth-step p{font-size:.75rem;color:var(--dim);line-height:1.6}
.endpoints{display:grid;gap:1.2rem}
.ep{border:1px solid var(--border);border-radius:6px;overflow:hidden;transition:border-color .25s}
.ep:hover{border-color:#2a2a30}
.ep-header{
  display:flex;align-items:center;gap:.8rem;
  padding:1rem 1.4rem;cursor:pointer;
  background:var(--surface);user-select:none;
}
.ep-header .method{
  font-size:.6rem;font-weight:600;letter-spacing:.06em;
  padding:.15rem .5rem;border-radius:2px;flex-shrink:0;
}
.ep-header .method.post{background:rgba(212,243,74,.15);color:var(--accent)}
.ep-header .method.get{background:rgba(74,180,243,.15);color:#4ab4f3}
.ep-header .path{font-size:.8rem;font-weight:500}
.ep-header .desc{margin-left:auto;font-size:.7rem;color:var(--dim);text-align:right}
.ep-header .chevron{color:var(--dim);font-size:.7rem;transition:transform .25s;margin-left:.6rem}
.ep.open .ep-header .chevron{transform:rotate(90deg)}
.ep-body{max-height:0;overflow:hidden;transition:max-height .35s ease}
.ep.open .ep-body{max-height:800px}
.ep-content{padding:1.2rem 1.4rem;border-top:1px solid var(--border)}
.ep-content .sub{
  font-size:.6rem;text-transform:uppercase;letter-spacing:.1em;
  color:var(--dim);margin-bottom:.5rem;font-weight:600;
}
.ep-content .sub+.sub{margin-top:1.2rem}
pre{
  background:var(--bg);border:1px solid var(--border);border-radius:4px;
  padding:1rem 1.2rem;overflow-x:auto;font-size:.75rem;
  line-height:1.8;margin-top:.4rem;
  scrollbar-width:thin;scrollbar-color:var(--border) transparent;
}
pre code{font-family:var(--mono)}
.k{color:var(--accent)}.s{color:#8bdb6a}.n{color:#e09956}.d{color:var(--dim)}
.try-it{padding:3rem 0}
.try-grid{display:grid;grid-template-columns:1fr 1fr;gap:1.4rem}
@media(max-width:680px){.try-grid{grid-template-columns:1fr}}
.try-input,.try-output{display:flex;flex-direction:column;gap:.6rem}
.try-input label,.try-output label{
  font-size:.6rem;text-transform:uppercase;letter-spacing:.1em;
  color:var(--dim);font-weight:600;
}
textarea{
  background:var(--surface);border:1px solid var(--border);border-radius:4px;
  padding:.8rem 1rem;font-family:var(--mono);font-size:.8rem;
  color:var(--text);resize:vertical;min-height:120px;
  outline:none;transition:border-color .2s;
}
textarea:focus{border-color:var(--accent)}
select,button.run{
  font-family:var(--mono);font-size:.75rem;
  padding:.5rem .8rem;border-radius:4px;cursor:pointer;
}
select{background:var(--surface);border:1px solid var(--border);color:var(--text);outline:none}
button.run{
  background:var(--accent);color:var(--bg);border:none;
  font-weight:600;letter-spacing:.04em;transition:opacity .2s;
  align-self:flex-start;
}
button.run:hover{opacity:.85}
button.run:disabled{opacity:.4;cursor:not-allowed}
.try-output pre{min-height:120px;margin:0;border-color:var(--border)}
.try-controls{display:flex;gap:.6rem;align-items:center;flex-wrap:wrap}
.try-controls .status{font-size:.7rem;color:var(--dim)}
.try-controls .status.err{color:var(--danger)}
footer{padding:2rem 0 3rem;text-align:center;font-size:.7rem;color:var(--dim)}
footer a{color:var(--dim);text-decoration:underline;text-underline-offset:3px}
footer a:hover{color:var(--text)}
@keyframes fadeUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
header,.section-label,.auth-step,.ep,.try-grid,footer{animation:fadeUp .5s ease both}
header{animation-delay:.05s}
section:nth-of-type(1) .section-label{animation-delay:.15s}
section:nth-of-type(1) .auth-step:nth-child(1){animation-delay:.2s}
section:nth-of-type(1) .auth-step:nth-child(2){animation-delay:.25s}
section:nth-of-type(1) .auth-step:nth-child(3){animation-delay:.3s}
section:nth-of-type(2) .section-label{animation-delay:.35s}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="tag">v0.0.5</div>
  <h1>Data <em>Detector</em> API</h1>
  <p>PII detection, validation, masking, and fake-replacement. Detect personal information across Korean, Chinese, Japanese, and English text.</p>
  <div class="base-url" onclick="navigator.clipboard.writeText(location.origin+'/api');this.querySelector('.copy').textContent='copied!'">
    <div>
      <div class="label">Base URL</div>
      <code id="baseUrl"></code>
    </div>
    <span class="copy">click to copy</span>
  </div>
</header>

<section>
  <div class="section-label">Authentication</div>
  <div class="auth-flow">
    <div class="auth-step">
      <div class="num">1</div>
      <div>
        <h3>Get an API key</h3>
        <p>POST to <code>/api/auth/issue</code> with your admin token and a system name identifying your service.</p>
      </div>
    </div>
    <div class="auth-step">
      <div class="num">2</div>
      <div>
        <h3>Store the key</h3>
        <p>The response contains a signed API key (<code>dd_...</code>). Store it securely &mdash; it cannot be retrieved again.</p>
      </div>
    </div>
    <div class="auth-step">
      <div class="num">3</div>
      <div>
        <h3>Authenticate requests</h3>
        <p>Pass the key in every request: <code>Authorization: Bearer dd_...</code></p>
      </div>
    </div>
  </div>
</section>

<section>
  <div class="section-label">Endpoints</div>
  <div class="endpoints">

    <div class="ep">
      <div class="ep-header" onclick="this.parentElement.classList.toggle('open')">
        <span class="method post">POST</span>
        <span class="path">/api/auth/issue</span>
        <span class="desc">Issue API key</span>
        <span class="chevron">&#9654;</span>
      </div>
      <div class="ep-body"><div class="ep-content">
        <div class="sub">Request</div>
<pre><code>{
  <span class="k">"token"</span>: <span class="s">"your-admin-token"</span>,
  <span class="k">"system"</span>: <span class="s">"billing-service"</span>
}</code></pre>
        <div class="sub">Response</div>
<pre><code>{
  <span class="k">"api_key"</span>: <span class="s">"dd_c2eca8ea..."</span>,
  <span class="k">"system"</span>: <span class="s">"billing-service"</span>,
  <span class="k">"message"</span>: <span class="s">"Store this key securely."</span>
}</code></pre>
      </div></div>
    </div>

    <div class="ep">
      <div class="ep-header" onclick="this.parentElement.classList.toggle('open')">
        <span class="method post">POST</span>
        <span class="path">/api/detect</span>
        <span class="desc">Detect PII</span>
        <span class="chevron">&#9654;</span>
      </div>
      <div class="ep-body"><div class="ep-content">
        <div class="sub">Request</div>
<pre><code>{
  <span class="k">"text"</span>: <span class="s">"Email me at test@example.com"</span>,
  <span class="k">"namespaces"</span>: [<span class="s">"comm"</span>, <span class="s">"us"</span>]  <span class="d">// optional</span>
}</code></pre>
        <div class="sub">Response</div>
<pre><code>{
  <span class="k">"pii_found"</span>: <span class="n">true</span>,
  <span class="k">"match_count"</span>: <span class="n">1</span>,
  <span class="k">"matches"</span>: [
    { <span class="k">"ns_id"</span>: <span class="s">"comm/email_01"</span>, <span class="k">"category"</span>: <span class="s">"email"</span>,
      <span class="k">"start"</span>: <span class="n">12</span>, <span class="k">"end"</span>: <span class="n">28</span>, <span class="k">"severity"</span>: <span class="s">"medium"</span> }
  ]
}</code></pre>
      </div></div>
    </div>

    <div class="ep">
      <div class="ep-header" onclick="this.parentElement.classList.toggle('open')">
        <span class="method post">POST</span>
        <span class="path">/api/validate</span>
        <span class="desc">Validate against pattern</span>
        <span class="chevron">&#9654;</span>
      </div>
      <div class="ep-body"><div class="ep-content">
        <div class="sub">Request</div>
<pre><code>{
  <span class="k">"text"</span>: <span class="s">"010-1234-5678"</span>,
  <span class="k">"ns_id"</span>: <span class="s">"kr/mobile_01"</span>
}</code></pre>
        <div class="sub">Response</div>
<pre><code>{
  <span class="k">"ok"</span>: <span class="n">true</span>,
  <span class="k">"ns_id"</span>: <span class="s">"kr/mobile_01"</span>
}</code></pre>
      </div></div>
    </div>

    <div class="ep">
      <div class="ep-header" onclick="this.parentElement.classList.toggle('open')">
        <span class="method post">POST</span>
        <span class="path">/api/mask</span>
        <span class="desc">Mask PII</span>
        <span class="chevron">&#9654;</span>
      </div>
      <div class="ep-body"><div class="ep-content">
        <div class="sub">Request</div>
<pre><code>{
  <span class="k">"text"</span>: <span class="s">"Call 010-1234-5678 or test@example.com"</span>
}</code></pre>
        <div class="sub">Response</div>
<pre><code>{
  <span class="k">"original"</span>: <span class="s">"Call 010-1234-5678 or test@example.com"</span>,
  <span class="k">"masked"</span>:   <span class="s">"Call **-****-**** or ***@***.***"</span>,
  <span class="k">"change_count"</span>: <span class="n">2</span>,
  <span class="k">"changes"</span>: [ <span class="d">... detail per match</span> ]
}</code></pre>
      </div></div>
    </div>

    <div class="ep">
      <div class="ep-header" onclick="this.parentElement.classList.toggle('open')">
        <span class="method post">POST</span>
        <span class="path">/api/fake</span>
        <span class="desc">Replace with fake data</span>
        <span class="chevron">&#9654;</span>
      </div>
      <div class="ep-body"><div class="ep-content">
        <div class="sub">Request</div>
<pre><code>{
  <span class="k">"text"</span>: <span class="s">"SSN: 123-45-6789"</span>,
  <span class="k">"namespaces"</span>: [<span class="s">"us"</span>]
}</code></pre>
        <div class="sub">Response</div>
<pre><code>{
  <span class="k">"original"</span>: <span class="s">"SSN: 123-45-6789"</span>,
  <span class="k">"replaced"</span>: <span class="s">"SSN: 018-15-8567"</span>,
  <span class="k">"change_count"</span>: <span class="n">1</span>,
  <span class="k">"changes"</span>: [ <span class="d">... detail per match</span> ]
}</code></pre>
      </div></div>
    </div>

    <div class="ep">
      <div class="ep-header" onclick="this.parentElement.classList.toggle('open')">
        <span class="method get">GET</span>
        <span class="path">/api/logs</span>
        <span class="desc">Usage logs</span>
        <span class="chevron">&#9654;</span>
      </div>
      <div class="ep-body"><div class="ep-content">
        <div class="sub">Query Parameters</div>
<pre><code><span class="k">system</span>=billing-service  <span class="d">// filter by system</span>
<span class="k">event</span>=api_call          <span class="d">// token_issued | api_call</span>
<span class="k">limit</span>=50                <span class="d">// max entries (default 100)</span></code></pre>
        <div class="sub">Response</div>
<pre><code>{
  <span class="k">"logs"</span>: [
    { <span class="k">"event"</span>: <span class="s">"api_call"</span>, <span class="k">"system"</span>: <span class="s">"billing-service"</span>,
      <span class="k">"endpoint"</span>: <span class="s">"/api/mask"</span>,
      <span class="k">"detail"</span>: { <span class="k">"change_count"</span>: <span class="n">3</span> },
      <span class="k">"timestamp"</span>: <span class="s">"2026-02-21T05:47:04Z"</span> }
  ],
  <span class="k">"total"</span>: <span class="n">1</span>
}</code></pre>
      </div></div>
    </div>

  </div>
</section>

<section class="try-it">
  <div class="section-label">Try It</div>
  <div class="try-grid">
    <div class="try-input">
      <label>Input text</label>
      <textarea id="tryText" placeholder="Enter text with PII...">Contact me at test@example.com or call 010-1234-5678. SSN: 123-45-6789</textarea>
      <div class="try-controls">
        <select id="tryEndpoint">
          <option value="detect">Detect</option>
          <option value="mask" selected>Mask</option>
          <option value="fake">Fake</option>
        </select>
        <input type="password" id="tryKey" placeholder="API key (dd_...)" style="
          font-family:var(--mono);font-size:.75rem;padding:.5rem .8rem;
          background:var(--surface);border:1px solid var(--border);border-radius:4px;
          color:var(--text);outline:none;flex:1;min-width:140px;
        ">
        <button class="run" id="tryRun" onclick="runTry()">Run</button>
        <span class="status" id="tryStatus"></span>
      </div>
    </div>
    <div class="try-output">
      <label>Response</label>
      <pre id="tryResult"><code class="d">Response will appear here...</code></pre>
    </div>
  </div>
</section>

</div>
<footer>
  <a href="https://github.com/zafrem/data-detector" target="_blank">GitHub</a>
  &nbsp;&middot;&nbsp; Apache License 2.0
</footer>
<script>
document.getElementById('baseUrl').textContent = location.origin + '/api';
let _demoAvailable = false;
(async function checkDemo() {
  try {
    const res = await fetch('/api/demo-key');
    if (res.ok) {
      _demoAvailable = true;
      document.getElementById('tryKey').placeholder = 'Using demo key (or enter your own)';
    }
  } catch (e) { /* demo key not available */ }
})();
async function runTry() {
  const text = document.getElementById('tryText').value;
  const endpoint = document.getElementById('tryEndpoint').value;
  const userKey = document.getElementById('tryKey').value.trim();
  const useDemo = !userKey && _demoAvailable;
  const status = document.getElementById('tryStatus');
  const result = document.getElementById('tryResult');
  const btn = document.getElementById('tryRun');
  if (!userKey && !useDemo) { status.textContent = 'API key required'; status.className = 'status err'; return; }
  if (!text) { status.textContent = 'Enter some text'; status.className = 'status err'; return; }
  btn.disabled = true;
  status.textContent = 'sending...';
  status.className = 'status';
  try {
    const url = useDemo ? '/api/demo/' + endpoint : '/api/' + endpoint;
    const headers = { 'Content-Type': 'application/json' };
    if (!useDemo) headers['Authorization'] = 'Bearer ' + userKey;
    const res = await fetch(url, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({ text })
    });
    const data = await res.json();
    result.innerHTML = '<code>' + syntaxHighlight(JSON.stringify(data, null, 2)) + '</code>';
    status.textContent = res.status + ' \\u00b7 ' + res.statusText;
    status.className = res.ok ? 'status' : 'status err';
  } catch (e) {
    result.innerHTML = '<code class="d">' + e.message + '</code>';
    status.textContent = 'error';
    status.className = 'status err';
  }
  btn.disabled = false;
}
function syntaxHighlight(json) {
  return json.replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/"([^"]+)":/g, '<span class="k">"$1"</span>:')
    .replace(/: "([^"]*)"/g, ': <span class="s">"$1"</span>')
    .replace(/: (\\d+)/g, ': <span class="n">$1</span>')
    .replace(/: (true|false|null)/g, ': <span class="n">$1</span>');
}
</script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Auth helpers  (stateless HMAC-based API keys)
# ---------------------------------------------------------------------------
# ADMIN_TOKEN  – the "designated token" used to issue API keys
# API_SECRET   – secret used to sign API keys (auto-generated if absent)
def _get_admin_token() -> str:
    return os.environ.get("ADMIN_TOKEN", "")


def _get_api_secret() -> str:
    # Use a cached secret if one was auto-generated to maintain consistency
    # but allow environment override at any time.
    env_secret = os.environ.get("API_SECRET")
    if env_secret:
        return env_secret
    
    global _AUTO_API_SECRET
    if "_AUTO_API_SECRET" not in globals():
        globals()["_AUTO_API_SECRET"] = os.urandom(32).hex()
    return globals()["_AUTO_API_SECRET"]


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


def _log_usage(
    system: str,
    endpoint: str,
    key_prefix: str,
    detail: Optional[Dict[str, Any]] = None,
) -> None:
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
    secret = _get_api_secret()
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


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

        registry = load_registry(validate_examples=False)
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


_HOMEPAGE_HTML: Optional[str] = None


def _load_static_file(filename: str) -> Optional[str]:
    """Load a file from the public directory, trying multiple paths for Vercel compatibility."""
    candidates = [
        _project_root / "public" / filename,
        Path(__file__).resolve().parent.parent / "public" / filename,
        Path(__file__).resolve().parent / "public" / filename,
        Path(f"/var/task/public/{filename}"),
        Path(f"/var/task/api/../public/{filename}"),
        _project_root / filename,  # Also check root as fallback
    ]
    for p in candidates:
        try:
            if p.exists():
                logger.info(f"Successfully loaded {filename} from {p}")
                return p.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning(f"Error checking path {p}: {e}")
            continue
    logger.error(f"Failed to find {filename} in any of the candidate paths.")
    return None


def _load_homepage() -> str:
    """Load homepage HTML, trying multiple paths for Vercel compatibility."""
    global _HOMEPAGE_HTML
    if _HOMEPAGE_HTML is not None:
        return _HOMEPAGE_HTML

    content = _load_static_file("index.html")
    if content:
        _HOMEPAGE_HTML = content
        return _HOMEPAGE_HTML

    return _GUIDE_HTML


@app.get("/", response_class=HTMLResponse)
async def homepage():
    """Serve the API guide page."""
    return HTMLResponse(_load_homepage())


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    """Serve robots.txt."""
    content = _load_static_file("robots.txt")
    if content:
        return PlainTextResponse(content)
    # Fallback if file not found
    return PlainTextResponse("User-agent: *\nAllow: /\n")


@app.get("/sitemap.xml")
async def sitemap_xml(request: Request):
    """Serve sitemap.xml."""
    content = _load_static_file("sitemap.xml")
    if content:
        return Response(content=content, media_type="application/xml")
    
    # Fallback hardcoded sitemap
    host = request.base_url
    fallback_sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{host}</loc>
    <lastmod>2026-03-20</lastmod>
    <changefreq>monthly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
"""
    return Response(content=fallback_sitemap, media_type="application/xml")


@app.get("/google736311ca6ba1b7ad.html", response_class=HTMLResponse)
async def google_verification():
    """Serve Google search console verification file."""
    # Hardcoded string as a fail-safe since this is a static verification token
    verification_string = "google-site-verification: google736311ca6ba1b7ad.html"
    
    content = _load_static_file("google736311ca6ba1b7ad.html")
    if content:
        return HTMLResponse(content)
        
    # Fallback to hardcoded string
    return HTMLResponse(verification_string)


@app.get("/favicon.ico")
async def favicon():
    """Serve favicon.ico (optional)."""
    return Response(status_code=204)


@app.get("/api")
async def api_info():
    """Health / info endpoint (no auth required)."""
    return {
        "service": "data-detector",
        "version": "0.0.5",
        "endpoints": [
            "POST /api/auth/issue",
            "POST /api/detect",
            "POST /api/validate",
            "POST /api/mask",
            "POST /api/fake",
        ],
    }


@app.get("/api/demo-key")
async def demo_key():
    """Check whether a demo API key is configured (does not expose the key)."""
    key = os.getenv("DEMO_API_KEY", "")
    if not key:
        raise HTTPException(status_code=404, detail="Demo key not configured")
    return {"available": True}


@app.post("/api/demo/{endpoint}")
async def demo_proxy(endpoint: str, request: Request):
    """Proxy endpoint that uses the server-side DEMO_API_KEY so the key is never sent to the client."""
    demo = os.getenv("DEMO_API_KEY", "")
    if not demo:
        raise HTTPException(status_code=404, detail="Demo key not configured")
    if endpoint not in ("detect", "mask", "fake"):
        raise HTTPException(status_code=400, detail="Invalid demo endpoint")

    system = _verify_api_key(demo)
    if system is None:
        raise HTTPException(status_code=401, detail="Demo key is invalid for current API_SECRET")

    try:
        body = await request.json()
        text = body.get("text", "")
        namespaces = body.get("namespaces")
        engine = _get_engine()

        if endpoint == "detect":
            result = engine.find(text, namespaces=namespaces, include_matched_text=True)
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
            _log_usage(system, "/api/detect", "demo", {"match_count": result.match_count, "text_length": len(text)})
            return {"text": text, "pii_found": result.has_matches, "match_count": result.match_count, "matches": matches}

        from datadetector.models import RedactionStrategy

        if endpoint == "mask":
            result = engine.redact(text, namespaces=namespaces, strategy=RedactionStrategy.MASK)
            changes = [
                {"ns_id": m.ns_id, "category": m.category.value, "start": m.start, "end": m.end, "original_fragment": text[m.start:m.end], "severity": m.severity.value}
                for m in result.matches
            ]
            _log_usage(system, "/api/mask", "demo", {"change_count": result.redaction_count, "text_length": len(text)})
            return {"original": text, "masked": result.redacted_text, "change_count": result.redaction_count, "changes": changes}

        if endpoint == "fake":
            result = engine.redact(text, namespaces=namespaces, strategy=RedactionStrategy.FAKE)
            changes = [
                {"ns_id": m.ns_id, "category": m.category.value, "start": m.start, "end": m.end, "original_fragment": text[m.start:m.end], "severity": m.severity.value}
                for m in result.matches
            ]
            _log_usage(system, "/api/fake", "demo", {"change_count": result.redaction_count, "text_length": len(text)})
            return {"original": text, "replaced": result.redacted_text, "change_count": result.redaction_count, "changes": changes}

    except Exception as exc:
        logger.exception("Error in demo_proxy")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(exc)}")


@app.post("/api/auth/issue", response_model=AuthIssueResponse)
async def auth_issue(body: AuthIssueRequest):
    """Issue a new API key. Requires the designated admin token and a system name."""
    admin_token = _get_admin_token()
    if not admin_token:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_TOKEN is not configured on the server",
        )
    if not hmac.compare_digest(body.token, admin_token):
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
        with open(LOG_FILE, encoding="utf-8") as f:
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
