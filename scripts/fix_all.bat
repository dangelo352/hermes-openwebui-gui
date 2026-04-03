@echo off
setlocal
python launcher.py rebuild-webui
if errorlevel 1 exit /b %errorlevel%
python launcher.py start
if errorlevel 1 exit /b %errorlevel%
python scripts\install_openwebui_workspace_assets.py
echo.
echo All fixes/rebuild steps completed.
echo GUI: http://127.0.0.1:8080
