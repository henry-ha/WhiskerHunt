@echo off
setlocal
cd /d "%~dp0"
echo Hush Hunt B99 - CHECK compatible pose sync V5
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0pose_sync_v5.py" --check
) else (
  python "%~dp0pose_sync_v5.py" --check
)
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" echo CHECK FAILED - no changes made. Do not install.
if "%RC%"=="0" echo Check finished. Review the update and skipped lines above.
pause
exit /b %RC%
