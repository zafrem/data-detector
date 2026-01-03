# CI/CD Integration Guide

Data Detector can be integrated into your CI/CD pipeline (GitHub Actions, GitLab CI, Jenkins) to automatically block code containing sensitive information (PII) from being merged.

## The `--on-match` Flag

The key to CI/CD integration is the `--on-match` flag in the `find` command.

*   `--on-match exit`: If PII is found, the command exits with **Code 1** (Error), causing the pipeline to fail.
*   `--on-match skip`: (Default) If PII is found, the command reports it but exits with **Code 0** (Success).

## GitHub Actions Example

Create a file named `.github/workflows/pii-scan.yml` in your repository:

```yaml
name: PII Scan

on: [pull_request]

jobs:
  pii-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.9"

      - name: Install Data Detector
        run: pip install data-detector

      - name: Scan Codebase
        # Scans all files in the repository
        # Fails the build if any PII is found
        run: |
          # Find all text files (exclude git, venv, etc.)
          find . -type f -not -path '*/.*' -not -path '*/__pycache__/*' | while read file; do
            data-detector find --file "$file" --on-match exit
          done
```

## Performance Optimization

For large repositories, scanning every file sequentially can be slow. We recommend:

1.  **Scan only changed files**: Use `git diff` to get the list of modified files in a PR.
2.  **Use `grep` first**: Use a fast tool like `grep` or `ripgrep` to find potential matches, then verify with Data Detector.

### Optimized Script (Scan Changed Files)

```bash
#!/bin/bash
# Get list of changed files
files=$(git diff --name-only origin/main...HEAD)

for file in $files; do
  if [ -f "$file" ]; then
    echo "Scanning $file..."
    data-detector find --file "$file" --on-match exit
    if [ $? -ne 0 ]; then
      echo "❌ PII detected in $file!"
      exit 1
    fi
  fi
done
echo "✅ No PII detected."
```

## GitLab CI Example

```yaml
pii_scan:
  stage: test
  script:
    - pip install data-detector
    - find . -name "*.py" -o -name "*.js" | xargs -I {} data-detector find --file {} --on-match exit
```
