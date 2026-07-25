#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test CLI for the data-detector Vercel API.

Usage:
  # Start local server first (in another terminal):
  #   cd <project-root>
  #   ADMIN_TOKEN=mysecret API_SECRET=testsecret uvicorn api.index:app --reload --port 8000

  # Then run tests:
  python scripts/test_vercel_api.py                          # test against localhost:8000
  python scripts/test_vercel_api.py --base-url https://your-app.vercel.app
  python scripts/test_vercel_api.py --admin-token mysecret   # custom admin token
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_BASE = "http://localhost:8000"
DEFAULT_ADMIN_TOKEN = "mysecret"

# Sample texts for testing
SAMPLES = {
    "en": "Contact me at test@example.com or call 010-1234-5678. SSN: 123-45-6789",
    "kr": "전화번호는 010-9876-5432이고 이메일은 user@test.co.kr 입니다",
    "mixed": "My card 4111-1111-1111-1111 and email admin@corp.com",
}


# ---------------------------------------------------------------------------
# HTTP helpers (stdlib only – no external deps required)
# ---------------------------------------------------------------------------
def _request(method, url, data=None, headers=None, timeout=30):
    """Make an HTTP request and return (status, json_body)."""
    body = json.dumps(data).encode() if data else None
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)

    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            err_body = json.loads(exc.read().decode())
        except Exception:
            err_body = {"detail": str(exc)}
        return exc.code, err_body


def _post(url, data, headers=None):
    return _request("POST", url, data, headers)


def _get(url, headers=None):
    return _request("GET", url, headers=headers)


# ---------------------------------------------------------------------------
# Pretty printing
# ---------------------------------------------------------------------------
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def header(title):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")


def ok(msg):
    print(f"  {GREEN}[OK]{RESET} {msg}")


def fail(msg):
    print(f"  {RED}[FAIL]{RESET} {msg}")


def info(msg):
    print(f"  {YELLOW}[INFO]{RESET} {msg}")


def dump(label, obj):
    print(f"  {BOLD}{label}:{RESET}")
    for line in json.dumps(obj, indent=2, ensure_ascii=False).split("\n"):
        print(f"    {line}")


# ---------------------------------------------------------------------------
# Test functions
# ---------------------------------------------------------------------------
def test_health(base):
    header("1. Health Check  (GET /api)")
    status, body = _get(f"{base}/api")
    if status == 200 and body.get("service") == "data-detector":
        ok(f"Service is up — v{body.get('version')}")
        info(f"Endpoints: {body.get('endpoints')}")
    else:
        fail(f"Unexpected response: {status} {body}")
    return status == 200


def test_auth_issue(base, admin_token, system="test-cli"):
    header("2. Issue API Key  (POST /api/auth/issue)")

    # Test with wrong token
    status, body = _post(
        f"{base}/api/auth/issue",
        {"token": "wrong_token", "system": "test-cli"},
    )
    if status == 403:
        ok("Correctly rejected invalid admin token")
    else:
        fail(f"Expected 403, got {status}: {body}")

    # Test missing system name
    status, body = _post(
        f"{base}/api/auth/issue",
        {"token": admin_token, "system": ""},
    )
    if status == 422:
        ok("Correctly rejected empty system name")
    else:
        info(f"Empty system check: {status} {body}")

    # Test with correct token + system
    status, body = _post(
        f"{base}/api/auth/issue",
        {"token": admin_token, "system": system},
    )
    if status == 200 and "api_key" in body:
        api_key = body["api_key"]
        ok(f"API key issued for system '{body['system']}': {api_key[:20]}...")
        info(body["message"])
        return api_key
    else:
        fail(f"Failed to issue key: {status} {body}")
        return None


def test_no_auth(base):
    header("3. Auth Required Check")
    status, body = _post(f"{base}/api/detect", {"text": "test"})
    if status in (401, 403):
        ok("Correctly rejected request without API key")
    else:
        fail(f"Expected 401/403, got {status}")


def test_detect(base, api_key, text, label=""):
    header(f"4. Detect PII  (POST /api/detect) {label}")
    auth = {"Authorization": f"Bearer {api_key}"}
    status, body = _post(f"{base}/api/detect", {"text": text}, headers=auth)
    if status == 200:
        ok(f"PII found: {body['pii_found']}, matches: {body['match_count']}")
        dump("Result", body)
    else:
        fail(f"Error {status}: {body}")
    return status == 200


def test_validate(base, api_key):
    header("5. Validate  (POST /api/validate)")
    auth = {"Authorization": f"Bearer {api_key}"}

    # Valid Korean mobile
    status, body = _post(
        f"{base}/api/validate",
        {"text": "010-1234-5678", "ns_id": "kr/mobile_01"},
        headers=auth,
    )
    if status == 200:
        result = "VALID" if body["ok"] else "INVALID"
        ok(f"010-1234-5678 against kr/mobile_01 -> {result}")
    else:
        fail(f"Error {status}: {body}")

    # Invalid pattern ID
    status, body = _post(
        f"{base}/api/validate",
        {"text": "test", "ns_id": "xx/nonexistent_99"},
        headers=auth,
    )
    if status == 404:
        ok("Correctly returned 404 for unknown pattern")
    else:
        info(f"Got {status}: {body}")


def test_mask(base, api_key, text, label=""):
    header(f"6. Mask (Redact)  (POST /api/mask) {label}")
    auth = {"Authorization": f"Bearer {api_key}"}
    status, body = _post(f"{base}/api/mask", {"text": text}, headers=auth)
    if status == 200:
        ok(f"Changes: {body['change_count']}")
        info(f"Original: {body['original']}")
        info(f"Masked:   {body['masked']}")
        if body["changes"]:
            dump("Change details", body["changes"])
    else:
        fail(f"Error {status}: {body}")
    return status == 200


def test_fake(base, api_key, text, label=""):
    header(f"7. Fake Replace  (POST /api/fake) {label}")
    auth = {"Authorization": f"Bearer {api_key}"}
    status, body = _post(f"{base}/api/fake", {"text": text}, headers=auth)
    if status == 200:
        ok(f"Changes: {body['change_count']}")
        info(f"Original: {body['original']}")
        info(f"Replaced: {body['replaced']}")
        if body["changes"]:
            dump("Change details", body["changes"])
    else:
        fail(f"Error {status}: {body}")
    return status == 200


def test_logs(base, api_key, system):
    header("8. Usage Logs  (GET /api/logs)")
    auth = {"Authorization": f"Bearer {api_key}"}

    # All logs
    status, body = _get(f"{base}/api/logs?limit=5", headers=auth)
    if status == 200:
        ok(f"Retrieved {body['total']} log entries")
        if body["logs"]:
            for entry in body["logs"][:3]:
                info(
                    f"  [{entry.get('event')}] system={entry.get('system')} "
                    f"endpoint={entry.get('endpoint', '-')} "
                    f"@ {entry.get('timestamp', '?')}"
                )
    elif status == 404:
        info("Log file not enabled (set API_LOG_FILE to enable)")
    else:
        info(f"Logs response: {status} {body}")

    # Filter by system
    status, body = _get(f"{base}/api/logs?system={system}&limit=3", headers=auth)
    if status == 200:
        ok(f"Filtered by system='{system}': {body['total']} entries")
    elif status != 404:
        info(f"Filter response: {status}")

    # Filter by event type
    status, body = _get(f"{base}/api/logs?event=token_issued&limit=3", headers=auth)
    if status == 200:
        ok(f"Filtered by event='token_issued': {body['total']} entries")
    elif status != 404:
        info(f"Filter response: {status}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Test CLI for data-detector Vercel API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Local testing (start server first with uvicorn)
  ADMIN_TOKEN=mysecret API_SECRET=testsecret uvicorn api.index:app --reload --port 8000
  python scripts/test_vercel_api.py

  # Test deployed Vercel API
  python scripts/test_vercel_api.py --base-url https://your-app.vercel.app --admin-token <token>

  # Use existing API key (skip auth issuance)
  python scripts/test_vercel_api.py --api-key dd_abc123...
        """,
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE,
        help=f"API base URL (default: {DEFAULT_BASE})",
    )
    parser.add_argument(
        "--admin-token",
        default=DEFAULT_ADMIN_TOKEN,
        help="Admin token for issuing API keys",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Use an existing API key instead of issuing a new one",
    )
    parser.add_argument(
        "--system",
        default="test-cli",
        help="System name to embed in the API key (default: test-cli)",
    )
    parser.add_argument(
        "--text",
        default=None,
        help="Custom text to test with (in addition to built-in samples)",
    )
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    passed = 0
    failed = 0

    print(f"{BOLD}data-detector API Test Suite{RESET}")
    print(f"Target: {base}")

    # 1. Health
    if test_health(base):
        passed += 1
    else:
        failed += 1

    # 2. Auth
    api_key = args.api_key
    if not api_key:
        api_key = test_auth_issue(base, args.admin_token, args.system)
        if api_key:
            passed += 1
        else:
            fail("Cannot continue without API key")
            sys.exit(1)

    # 3. No-auth rejection
    test_no_auth(base)

    # 4-7. Test each endpoint with sample texts
    test_text = args.text or SAMPLES["en"]

    if test_detect(base, api_key, test_text, "[EN]"):
        passed += 1
    else:
        failed += 1

    test_validate(base, api_key)
    passed += 1

    if test_mask(base, api_key, test_text, "[EN]"):
        passed += 1
    else:
        failed += 1

    if test_fake(base, api_key, test_text, "[EN]"):
        passed += 1
    else:
        failed += 1

    # Test with Korean sample
    if test_mask(base, api_key, SAMPLES["kr"], "[KR]"):
        passed += 1
    else:
        failed += 1

    # 8. Logs
    test_logs(base, api_key, args.system)

    # Summary
    header("SUMMARY")
    total = passed + failed
    print(f"  {GREEN}Passed: {passed}{RESET} / {total}")
    if failed:
        print(f"  {RED}Failed: {failed}{RESET}")
    print()

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
