#!/usr/bin/env bash
set -euo pipefail

# Convenience script to run the API or run ingestion locally.
# Usage:
#   ./scripts/run_local.sh           # starts API (with MOCK_GRAPH default true)
#   ./scripts/run_local.sh ingest    # runs the RAG ingestion script and exits

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Load .env if present (simple key=val lines)
if [ -f .env ]; then
  echo "Loading .env"
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

if [ "${1:-}" = "ingest" ]; then
  echo "Running RAG ingestion..."
  poetry run python scripts/ingest_data.py
  exit 0
fi

: "${MOCK_GRAPH:=true}"
export MOCK_GRAPH

echo "Starting API (MOCK_GRAPH=${MOCK_GRAPH})"
poetry run uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
