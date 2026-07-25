#!/bin/bash
# Example script for CI/CD integration
# Scans only the files changed in the current git branch/PR against main

TARGET_BRANCH="main"

echo "🔍 Starting PII Scan on changed files..."

# Ensure data-detector is installed
if ! command -v data-detector &> /dev/null; then
    echo "Error: data-detector is not installed. Run 'pip install data-detector'"
    exit 1
fi

# Get list of changed files (added or modified)
# Uses git diff to find changes between current HEAD and target branch
files=$(git diff --name-only --diff-filter=AM origin/$TARGET_BRANCH...HEAD 2>/dev/null)

if [ -z "$files" ]; then
    echo "No changed files found to scan."
    exit 0
fi

has_error=0

for file in $files; do
    if [ -f "$file" ]; then
        # Skip binary files or specific extensions if needed
        # if [[ "$file" == *.png ]]; then continue; fi
        
        echo "Scanning $file..."
        
        # Run data-detector
        # --on-match exit: Fails command if matches found
        # --first-only: Stops at first match for speed
        data-detector find --file "$file" --on-match exit --first-only
        
        if [ $? -ne 0 ]; then
            echo "❌ CRITICAL: PII detected in $file"
            has_error=1
        fi
    fi
done

if [ $has_error -ne 0 ]; then
    echo "🚫 Scan failed! Sensitive data detected."
    exit 1
else
    echo "✅ Scan passed! No PII detected in changed files."
    exit 0
fi
