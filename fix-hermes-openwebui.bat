@echo off
setlocal
cd /d "%~dp0"

echo ==============================================
echo Hermes OpenWebUI - Full Repair / Rebuild
echo ==============================================
echo.
echo This will:
echo   1. pull latest repo changes
echo   2. rebuild the patched Open WebUI image
echo   3. restart the adapter and GUI
echo   4. reinstall workspace assets
echo.

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 launcher.py update
  set EXIT_CODE=%errorlevel%
  goto done
)

where python >nul 2>nul
if %errorlevel%==0 (
  python launcher.py update
  set EXIT_CODE=%errorlevel%
  goto done
)

echo ERROR: Python 3 was not found on PATH.
echo Install Python 3, then re-run this file.
set EXIT_CODE=1

:done
echo.
if "%EXIT_CODE%"=="0" (
  echo Repair / rebuild completed successfully.
  echo Open WebUI should be available at http://127.0.0.1:8080
) else (
  echo Repair / rebuild failed with exit code %EXIT_CODE%.
)
echo.
pause
exit /b %EXIT_CODE%
