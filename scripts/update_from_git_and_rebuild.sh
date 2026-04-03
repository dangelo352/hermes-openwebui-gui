#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
LOG_DIR="state"
LOG_FILE="$LOG_DIR/update-rebuild.log"
mkdir -p "$LOG_DIR"
{
  echo "[$(date -Is)] Starting git update + rebuild"
  if [ "${HERMES_GUI_GIT_PULL:-1}" = "1" ]; then
    git pull --ff-only
  else
    echo "[$(date -Is)] Skipping git pull because HERMES_GUI_GIT_PULL=0"
  fi
  python3 launcher.py rebuild-webui
  python3 launcher.py start
  python3 scripts/install_openwebui_workspace_assets.py
  echo "[$(date -Is)] Update + rebuild completed successfully"
} >> "$LOG_FILE" 2>&1
