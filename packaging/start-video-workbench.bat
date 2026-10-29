@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Starting Video Workbench...
echo.

if not exist "video-workbench.exe" (
  echo video-workbench.exe was not found in this folder.
  echo Please extract the whole zip package before starting.
  echo.
  pause
  exit /b 1
)

"%~dp0video-workbench.exe"
set EXIT_CODE=%ERRORLEVEL%

echo.
if not "%EXIT_CODE%"=="0" (
  echo Startup failed. Error code: %EXIT_CODE%
  echo If startup-error.log exists in this folder, send it to the developer.
) else (
  echo The workbench has exited.
)
echo.
pause
