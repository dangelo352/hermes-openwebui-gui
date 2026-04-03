#!/usr/bin/env bash
set -euo pipefail

if ! command -v cmd.exe >/dev/null 2>&1; then
  echo "This script must run inside WSL with access to Windows via cmd.exe" >&2
  exit 1
fi

USERPROFILE_WIN="$(cmd.exe /c echo %USERPROFILE% | tr -d '\r')"
if [ -z "$USERPROFILE_WIN" ]; then
  echo "Could not determine Windows user profile" >&2
  exit 1
fi

TARGET_DIR="$(wslpath "${USERPROFILE_WIN}\\Desktop")/hermes-openwebui-gui"
mkdir -p "$TARGET_DIR"

rsync -av --delete \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude '.open-webui-venv/' \
  --exclude 'open-webui-data/' \
  --exclude 'state/' \
  --exclude '__pycache__/' \
  ./ "$TARGET_DIR/"

echo "Synced project to $TARGET_DIR"
