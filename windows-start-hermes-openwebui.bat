@echo off
setlocal
cd /d "%~dp0"
call start-hermes-openwebui.bat
exit /b %errorlevel%
