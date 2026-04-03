@echo off
setlocal
cd /d "%~dp0"
call update-webui-easy.bat
exit /b %errorlevel%
