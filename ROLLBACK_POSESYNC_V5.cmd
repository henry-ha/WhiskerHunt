@echo off
setlocal
cd /d "%~dp0"
echo Hush Hunt B99 - ROLLBACK pose sync V5
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0pose_sync_v5.py" --rollback
) else (
  python "%~dp0pose_sync_v5.py" --rollback
)
set "RC=%ERRORLEVEL%"
pause
exit /b %RC%
