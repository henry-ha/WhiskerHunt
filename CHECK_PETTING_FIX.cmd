@echo off
setlocal EnableExtensions
cd /d "%~dp0" || (echo Could not locate patch folder.& pause & exit /b 1)
echo Checking Hush Hunt petting fix without modifying the project...
where py >nul 2>&1
if not errorlevel 1 (
    py -3 "%CD%\apply_hush_petting_fix.py" --project "%CD%" --check
) else (
    where python >nul 2>&1
    if errorlevel 1 (echo Python 3 was not found. Install Python 3 or the Windows Python launcher.& pause & exit /b 1)
    python "%CD%\apply_hush_petting_fix.py" --project "%CD%" --check
)
set "STATUS=%ERRORLEVEL%"
if not "%STATUS%"=="0" echo CHECK FAILED. No project files changed.
if "%STATUS%"=="0" echo CHECK PASSED. You may now run INSTALL_PETTING_FIX.cmd
echo.
pause
exit /b %STATUS%
