#!/usr/bin/env bash
#
# MLOps / CI PII gate example.
#
# Each `data-detector gate` command reads a file or stdin, writes a JSON report,
# and exits non-zero when PII meets the --fail-on severity threshold. Drop these
# into any pipeline step (GitHub Actions, GitLab CI, Airflow/KFP task, pre-commit).
#
# Exit codes:  0 = clean/passed   1 = PII gate triggered   2 = error (bad input)
#
# Runs fully offline for text and JSONL inputs (no external services required).

set -euo pipefail

NS=("--ns" "comm" "--ns" "us" "--ns" "kr")

echo "==> 1. Gate plain text (file or stdin)"
echo "Reach me at alice.kim@gmail.com" | data-detector gate text "${NS[@]}" --fail-on medium

echo "==> 2. Gate a batch of RAG records (JSONL: query/document/response/messages)"
data-detector gate rag rag_records.jsonl "${NS[@]}" --report rag_report.json

echo "==> 3. Gate AI training data before fine-tuning (JSONL dir or HuggingFace id)"
data-detector gate training-data ./training_data/ "${NS[@]}" --report training_report.json

# In CI, the non-zero exit from any step above fails the job automatically
# (because of `set -e`). To inspect instead of failing, capture the code:
#
#   set +e
#   data-detector gate training-data ./training_data/ "${NS[@]}" --report report.json
#   code=$?
#   set -e
#   [ "$code" -eq 1 ] && echo "PII found — see report.json" && exit 1
