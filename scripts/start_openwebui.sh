#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .open-webui-venv/bin/activate
set -a
source .env.openwebui
set +a
exec open-webui serve
