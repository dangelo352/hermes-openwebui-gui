#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v python3 >/dev/null 2>&1; then
  exec python3 launcher.py start-webui --no-browser
elif command -v python >/dev/null 2>&1; then
  exec python launcher.py start-webui --no-browser
else
  echo "Python 3 is required but was not found." >&2
  exit 1
fi
