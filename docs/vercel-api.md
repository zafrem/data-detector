# Data Detector Vercel API

A serverless PII detection, validation, masking, and fake-replacement API deployed on Vercel.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api` | No | Health check / service info |
| `POST` | `/api/auth/issue` | Admin token | Issue a new API key |
| `POST` | `/api/detect` | API key | Detect PII in text |
| `POST` | `/api/validate` | API key | Validate text against a specific pattern |
| `POST` | `/api/mask` | API key | Mask (redact) PII in text |
| `POST` | `/api/fake` | API key | Replace PII with realistic fake data |
| `GET` | `/api/logs` | API key | Retrieve usage logs |

## Authentication

The API uses HMAC-based stateless API keys with embedded system identification.

### Issuing an API Key

Send your admin token along with a **system name** identifying the calling service:

```bash
curl -X POST https://your-app.vercel.app/api/auth/issue \
  -H "Content-Type: application/json" \
  -d '{"token": "<ADMIN_TOKEN>", "system": "billing-service"}'
```

Response:
```json
{
  "api_key": "dd_abc123...",
  "system": "billing-service",
  "message": "Store this key securely. It cannot be retrieved again."
}
```

The `system` name is embedded in the signed key. Every API call made with this key is logged with the system name for usage tracking.

### Using an API Key

Pass the key in the `Authorization` header:

```bash
curl -X POST https://your-app.vercel.app/api/mask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dd_abc123..." \
  -d '{"text": "Call me at 010-1234-5678"}'
```

## Endpoint Details

### POST /api/detect

Detect PII in text and return match details.

**Request:**
```json
{
  "text": "Email test@example.com, SSN 123-45-6789",
  "namespaces": ["us", "comm"]
}
```

**Response:**
```json
{
  "text": "Email test@example.com, SSN 123-45-6789",
  "pii_found": true,
  "match_count": 2,
  "matches": [
    {
      "ns_id": "comm/email_01",
      "category": "email",
      "start": 6,
      "end": 22,
      "matched_text": null,
      "severity": "medium"
    }
  ]
}
```

### POST /api/validate

Validate text against a specific pattern.

**Request:**
```json
{
  "text": "010-1234-5678",
  "ns_id": "kr/mobile_01"
}
```

**Response:**
```json
{
  "ok": true,
  "ns_id": "kr/mobile_01"
}
```

### POST /api/mask

Mask PII in text. Returns the masked text and the number of changes.

**Request:**
```json
{
  "text": "Contact: test@example.com",
  "namespaces": ["comm"]
}
```

**Response:**
```json
{
  "original": "Contact: test@example.com",
  "masked": "Contact: ***@***.***",
  "change_count": 1,
  "changes": [
    {
      "ns_id": "comm/email_01",
      "category": "email",
      "start": 9,
      "end": 25,
      "original_fragment": "test@example.com",
      "severity": "medium"
    }
  ]
}
```

### POST /api/fake

Replace PII with realistic fake data using Faker.

**Request:**
```json
{
  "text": "SSN: 123-45-6789",
  "namespaces": ["us"]
}
```

**Response:**
```json
{
  "original": "SSN: 123-45-6789",
  "replaced": "SSN: 018-15-8567",
  "change_count": 1,
  "changes": [...]
}
```

### GET /api/logs

Retrieve usage logs (requires `API_LOG_FILE` env var to be set).

**Query Parameters:**
- `system` — filter by system name
- `event` — filter by event type (`token_issued` or `api_call`)
- `limit` — max entries to return (default: 100)

**Example:**
```bash
curl "https://your-app.vercel.app/api/logs?system=billing-service&limit=10" \
  -H "Authorization: Bearer dd_abc123..."
```

**Response:**
```json
{
  "logs": [
    {
      "event": "api_call",
      "system": "billing-service",
      "endpoint": "/api/mask",
      "key_prefix": "dd_abc123...",
      "detail": {"change_count": 3, "text_length": 70},
      "timestamp": "2026-02-21T05:47:04.200272+00:00"
    }
  ],
  "total": 1
}
```

## Usage Logging

Every API call and token issuance is logged with:

| Field | Description |
|-------|-------------|
| `event` | `token_issued` or `api_call` |
| `system` | System name embedded in the API key |
| `endpoint` | The API endpoint called |
| `key_prefix` | First 20 chars of the API key (for identification) |
| `detail` | Endpoint-specific data (match count, text length, etc.) |
| `timestamp` | ISO 8601 UTC timestamp |

Logs are written to:
1. **stdout** (structured JSON) — always available, visible in Vercel's log viewer
2. **JSON-lines file** — when `API_LOG_FILE` env var is set (for local use)

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ADMIN_TOKEN` | Yes | The designated token used to issue API keys |
| `API_SECRET` | Yes (prod) | Secret for HMAC key signing. Auto-generated if absent (not persistent across restarts) |
| `API_LOG_FILE` | No | Path to a JSON-lines log file. Enables the `/api/logs` endpoint |

## Local Development

### Start the server

```bash
ADMIN_TOKEN=mysecret API_SECRET=testsecret API_LOG_FILE=/tmp/dd_api.log \
  python3 -m uvicorn api.index:app --reload --port 8000
```

### Run the test suite

```bash
python3 scripts/test_vercel_api.py \
  --admin-token mysecret \
  --system my-test-app
```

### Test against deployed Vercel

```bash
python3 scripts/test_vercel_api.py \
  --base-url https://your-app.vercel.app \
  --admin-token <your-admin-token> \
  --system qa-testing
```

### Use an existing API key

```bash
python3 scripts/test_vercel_api.py \
  --base-url https://your-app.vercel.app \
  --api-key dd_abc123...
```

## Vercel Deployment

### Prerequisites

1. Install Vercel CLI: `npm install -g vercel`
2. Link your project: `vercel link`
3. Note the Org ID and Project ID from `.vercel/project.json`

### GitHub Actions (Automatic)

Add these secrets to your GitHub repository (Settings > Secrets):

| Secret | Source |
|--------|--------|
| `VERCEL_TOKEN` | [Vercel Account Settings > Tokens](https://vercel.com/account/tokens) |
| `VERCEL_ORG_ID` | `.vercel/project.json` after `vercel link` |
| `VERCEL_PROJECT_ID` | `.vercel/project.json` after `vercel link` |

Set environment variables in Vercel dashboard:
- `ADMIN_TOKEN` — your admin token
- `API_SECRET` — a stable secret (generate with `python3 -c "import secrets; print(secrets.token_hex(32))"`)

Once configured:
- **Push to `main`** → auto-deploys to production
- **Pull request** → deploys a preview and comments the URL

### Manual Deploy

```bash
vercel --prod
```
