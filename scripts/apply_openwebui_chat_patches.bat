@echo off
setlocal
if "%~1"=="" (
  echo Usage: %~nx0 C:\path\to\open-webui
  exit /b 1
)
wsl.exe -d Ubuntu bash -lc "cd /root/hermes-openwebui-gui && ./scripts/apply_openwebui_chat_patches.sh $(wslpath '%~1')"
