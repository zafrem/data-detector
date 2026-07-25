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

## MLOps Gates (`gate` commands)

For ML pipelines, the `gate` commands provide a uniform PII gate over text, RAG
records, and training data. Each reads a **file or stdin**, writes a **JSON
report** (to stdout or `--report FILE`), and returns an exit code:

| Exit code | Meaning |
|:---------:|---------|
| `0` | Clean — no PII at/above the `--fail-on` severity |
| `1` | PII gate triggered |
| `2` | Error (e.g. malformed input, missing source) |

These run fully offline for text and JSONL inputs — suitable for isolated test
and CI runners with no external services.

```bash
# Gate plain text (stdin or file)
echo "Reach me at alice.kim@gmail.com" | data-detector gate text --ns comm --fail-on medium

# Gate a batch of RAG records (JSONL with query/document/response/messages fields)
data-detector gate rag rag_records.jsonl --ns comm --ns us --report rag_report.json

# Gate AI training data before fine-tuning (JSONL dir/file or HuggingFace dataset id)
data-detector gate training-data ./training_data/ --ns comm --report training_report.json
```

Common options: `--ns` (namespaces), `--fail-on {low,medium,high,critical}`
(default `low`), `--report FILE`, `--show-matches` (include raw values — off by
default for privacy), `-q/--quiet` (suppress the human summary; keep stdout pure
JSON). A runnable script is at [`examples/mlops_pii_gate.sh`](../../examples/mlops_pii_gate.sh).

### GitHub Actions: gate training data

```yaml
      - name: PII gate on training data
        run: |
          pip install data-detector
          data-detector gate training-data ./data/ --ns comm --ns us --report pii_report.json
      - name: Upload PII report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: pii-report
          path: pii_report.json
```
