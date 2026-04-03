#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 launcher.py rebuild-webui
python3 launcher.py start
python3 scripts/install_openwebui_workspace_assets.py
printf '\nAll fixes/rebuild steps completed.\nGUI: http://127.0.0.1:8080\n'
