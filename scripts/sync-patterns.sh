#!/usr/bin/env bash
# Sync pattern-engine submodule contents to api/pattern-engine for Vercel deployment.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cp -r "$REPO_ROOT/pattern-engine/regex" "$REPO_ROOT/api/pattern-engine/"
cp -r "$REPO_ROOT/pattern-engine/verification" "$REPO_ROOT/api/pattern-engine/"

echo "api/pattern-engine synced with submodule."
