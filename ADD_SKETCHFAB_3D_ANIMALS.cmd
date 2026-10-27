@echo off
setlocal
cd /d "%~dp0"
echo Hush Hunt - Add 5 Sketchfab GLBs to AR Safari
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 "%~dp0install_sketchfab_five.py"
) else (
  python "%~dp0install_sketchfab_five.py"
)
if errorlevel 1 (
  echo.
  echo Install failed. Your existing animals should remain intact. Check the error above.
) else (
  echo.
  echo Success! Rebuild and deploy from Visual Studio.
)
pause
