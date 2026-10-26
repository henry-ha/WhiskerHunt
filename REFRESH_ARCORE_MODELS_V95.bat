@echo off
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"
if not exist "WhiskerHunt\WhiskerHunt.csproj" (
  echo Put this batch file alongside the WhiskerHunt and tools folders.
  pause
  exit /b 1
)
py tools\import_cc0_wildlife.py
if errorlevel 1 (
  echo Could not refresh the local ARCore 3D choices.
  pause
  exit /b 1
)
echo Species picker refreshed without downloading any animal again.
echo Rebuild WhiskerHunt\WhiskerHunt.csproj in Visual Studio.
pause
