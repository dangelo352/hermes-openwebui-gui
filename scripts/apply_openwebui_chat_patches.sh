#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 /path/to/open-webui" >&2
  exit 1
fi

TARGET="$(cd "$1" && pwd)"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PATCH_ROOT="$ROOT/openwebui-patches/src"

if [ ! -d "$TARGET/src" ]; then
  echo "Target does not look like an Open WebUI source checkout: $TARGET" >&2
  exit 1
fi

rsync -av "$PATCH_ROOT/" "$TARGET/src/"

echo "Applied Hermes chat UI patches into: $TARGET"
echo "Patched files include slash command overlay components for chat input."
