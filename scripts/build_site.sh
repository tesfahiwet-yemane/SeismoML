#!/usr/bin/env bash
# Preview the website locally, exactly as GitHub Actions builds it.
#
#   bash scripts/build_site.sh          # execute notebooks, then serve at http://127.0.0.1:8000
#   bash scripts/build_site.sh --fast   # reuse already executed notebooks (text edits only)
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p docs/notebooks
if [[ "${1:-}" != "--fast" ]]; then
  for nb in notebooks/0*.ipynb; do
    echo "Executing $nb"
    jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=7200 \
      --output-dir docs/notebooks "$nb"
  done
fi
mkdocs serve
