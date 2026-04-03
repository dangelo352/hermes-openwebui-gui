@echo off
setlocal

echo Starting Docker Desktop...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"

echo Waiting for Docker engine...
:wait_docker
cmd /c docker info >nul 2>nul
if errorlevel 1 (
  timeout /t 3 /nobreak >nul
  goto wait_docker
)

echo Starting Hermes adapter inside WSL...
wsl.exe -d Ubuntu bash -lc "cd /root/hermes-openwebui-gui && ./scripts/install_all.sh && nohup ./scripts/start_adapter.sh >/tmp/hermes-openwebui-adapter.log 2>&1 &"

echo Recreating Open WebUI container with forwarded session headers enabled...
cmd /c docker rm -f hermes-open-webui >nul 2>nul
cmd /c docker run -d -p 8080:8080 -e ENABLE_OPENAI_API=True -e ENABLE_FORWARD_USER_INFO_HEADERS=True -e OPENAI_API_BASE_URL=http://host.docker.internal:8001/v1 -e OPENAI_API_KEY=hermes-local -e WEBUI_AUTH=False -v hermes-open-webui-data:/app/backend/data --name hermes-open-webui --restart unless-stopped ghcr.io/open-webui/open-webui:main

echo.
echo Hermes Open WebUI should be starting.
echo GUI: http://127.0.0.1:8080
echo Adapter health: http://127.0.0.1:8001/health
echo.
pause
