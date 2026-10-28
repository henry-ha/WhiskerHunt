@echo off
setlocal EnableExtensions
cd /d "%~dp0" || (echo Cannot access solution folder.& pause & exit /b 1)
echo Hush Hunt - safe AR-frame pet reaction repair
where py >nul 2>&1
if not errorlevel 1 (py -3 "%CD%\repair_petting_crash.py" --project "%CD%") else (python "%CD%\repair_petting_crash.py" --project "%CD%")
set "STATUS=%ERRORLEVEL%"
echo.
if "%STATUS%"=="0" (echo INSTALLED. Clean/Rebuild/Deploy without uninstalling.) else (echo REPAIR FAILED. Existing project remains unchanged or was rolled back.)
pause
exit /b %STATUS%
