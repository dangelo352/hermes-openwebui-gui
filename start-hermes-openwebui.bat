@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 launcher.py start
  exit /b %errorlevel%
)

where python >nul 2>nul
if %errorlevel%==0 (
  python launcher.py start
  exit /b %errorlevel%
)

echo Python 3 is required but was not found.
pause
exit /b 1
