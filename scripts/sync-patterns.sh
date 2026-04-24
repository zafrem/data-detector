#!/usr/bin/env bash
# Sync pii-pattern-engine submodule contents to api/pii-pattern-engine for Vercel deployment.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cp -r "$REPO_ROOT/pii-pattern-engine/regex" "$REPO_ROOT/api/pii-pattern-engine/"
cp -r "$REPO_ROOT/pii-pattern-engine/verification" "$REPO_ROOT/api/pii-pattern-engine/"

echo "api/pii-pattern-engine synced with submodule."
