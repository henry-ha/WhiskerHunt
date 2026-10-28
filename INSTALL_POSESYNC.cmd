@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
REM The trailing dot prevents Windows from parsing a quoted trailing backslash incorrectly.
set "ROOT=%~dp0."
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0install_pose_sync_v3.py" --root "%ROOT%" --install
) else (
  python "%~dp0install_pose_sync_v3.py" --root "%ROOT%" --install
)
set "STATUS=%ERRORLEVEL%"
echo.
if "%STATUS%"=="0" (echo OPERATION SUCCEEDED.) else (echo OPERATION FAILED. See PATCH ABORTED above.)
pause
exit /b %STATUS%
