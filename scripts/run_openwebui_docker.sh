#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

python3 scripts/build_patched_openwebui.py
python3 launcher.py restart --no-browser

echo "Open WebUI container started."
echo "URL: http://127.0.0.1:8080"
echo "Workspace tool installed: Hermes Control"
