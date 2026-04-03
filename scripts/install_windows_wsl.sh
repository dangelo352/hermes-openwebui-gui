#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="/mnt/c/Users/DAngelo/Desktop/hermes-openwebui-gui"
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
