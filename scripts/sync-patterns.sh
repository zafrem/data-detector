#!/usr/bin/env bash
# Sync pii-pattern-engine submodule contents to api/pii-pattern-engine for Vercel deployment.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Ensure submodule is initialized and updated
if [ -d "$REPO_ROOT/.git" ]; then
    echo "Checking pii-pattern-engine submodule..."
    git -C "$REPO_ROOT" submodule update --init --recursive pii-pattern-engine
fi

cp -r "$REPO_ROOT/pii-pattern-engine/regex" "$REPO_ROOT/api/pii-pattern-engine/"
cp -r "$REPO_ROOT/pii-pattern-engine/verification" "$REPO_ROOT/api/pii-pattern-engine/"

echo "api/pii-pattern-engine synced with submodule."
