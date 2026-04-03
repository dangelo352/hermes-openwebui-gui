#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
export HERMES_BIN="${HERMES_BIN:-/root/.hermes/hermes-agent/venv/bin/hermes}"
export HERMES_WORKDIR="${HERMES_WORKDIR:-/root/.hermes/hermes-agent}"
export HERMES_OPENAI_MODEL="${HERMES_OPENAI_MODEL:-hermes-gui}"
export HERMES_OPENAI_API_KEY="${HERMES_OPENAI_API_KEY:-hermes-local}"
exec uvicorn adapter.app:app --host 0.0.0.0 --port 8001
