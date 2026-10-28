@echo off
setlocal
cd /d "%~dp0"
echo Hush Hunt B99 - INSTALL compatible pose sync V5
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0pose_sync_v5.py" --install
) else (
  python "%~dp0pose_sync_v5.py" --install
)
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" echo INSTALL FAILED - source either unchanged or automatically restored.
pause
exit /b %RC%
