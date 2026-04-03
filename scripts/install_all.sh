#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required but not installed. Install uv first: https://docs.astral.sh/uv/" >&2
  exit 1
fi

if [ ! -x /root/.hermes/hermes-agent/venv/bin/hermes ]; then
  echo "Hermes CLI not found at /root/.hermes/hermes-agent/venv/bin/hermes" >&2
  echo "Install/configure Hermes first, then rerun this script." >&2
  exit 1
fi

mkdir -p state open-webui-data

if [ ! -d .venv ]; then
  uv venv --python 3.11 .venv
fi

source .venv/bin/activate
uv pip install -r requirements.txt

echo
echo "Adapter environment ready."
echo "Next steps:"
echo "  1. Start adapter: ./scripts/start_adapter.sh"
echo "  2. Start Open WebUI in Docker: ./scripts/run_openwebui_docker.sh"
echo "  3. Open http://127.0.0.1:8080"
