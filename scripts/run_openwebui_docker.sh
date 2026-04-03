#!/usr/bin/env bash
set -euo pipefail

IMAGE="ghcr.io/open-webui/open-webui:main"
CONTAINER="hermes-open-webui"
DATA_VOLUME="hermes-open-webui-data"
ADAPTER_URL="${OPENAI_API_BASE_URL:-http://host.docker.internal:8001/v1}"
API_KEY="${OPENAI_API_KEY:-hermes-local}"
WEBUI_AUTH_VALUE="${WEBUI_AUTH:-False}"

if ! command -v cmd.exe >/dev/null 2>&1; then
  echo "This helper expects to run from WSL with access to Windows Docker Desktop via cmd.exe." >&2
  exit 1
fi

cmd.exe /c start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe" >/dev/null 2>&1 || true

echo "Waiting for Docker Desktop..."
until cmd.exe /c docker info >/dev/null 2>&1; do
  sleep 3
done

cmd.exe /c "docker rm -f ${CONTAINER}" >/dev/null 2>&1 || true
cmd.exe /c "docker run -d -p 8080:8080 -e ENABLE_OPENAI_API=True -e ENABLE_FORWARD_USER_INFO_HEADERS=True -e OPENAI_API_BASE_URL=${ADAPTER_URL} -e OPENAI_API_KEY=${API_KEY} -e WEBUI_AUTH=${WEBUI_AUTH_VALUE} -v ${DATA_VOLUME}:/app/backend/data --name ${CONTAINER} --restart unless-stopped ${IMAGE}"

echo "Waiting for Open WebUI HTTP health..."
until curl -fsS http://127.0.0.1:8080/health >/dev/null 2>&1; do
  sleep 3
done

echo "Installing Hermes workspace assets into Open WebUI..."
python3 "$(dirname "$0")/install_openwebui_workspace_assets.py"

echo "Open WebUI container started."
echo "URL: http://127.0.0.1:8080"
echo "Workspace tool installed: Hermes Control"
