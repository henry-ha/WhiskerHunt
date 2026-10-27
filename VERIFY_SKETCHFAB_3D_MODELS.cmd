@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (
  py -3 tools\verify_sketchfab_3d_assets.py "%CD%"
) else (
  python tools\verify_sketchfab_3d_assets.py "%CD%"
)
echo.
echo Audit complete. Keep this window open to read any errors.
pause
