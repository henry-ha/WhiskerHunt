@echo off
setlocal EnableExtensions
cd /d "%~dp0" || (echo Could not locate patch folder.& pause & exit /b 1)
echo Hush Hunt 3D Safari - HD model petting reaction fix
echo Project folder: %CD%
where py >nul 2>&1
if not errorlevel 1 (
    py -3 "%CD%\apply_hush_petting_fix.py" --project "%CD%"
) else (
    where python >nul 2>&1
    if errorlevel 1 (echo Python 3 was not found. Install Python 3 or the Windows Python launcher.& pause & exit /b 1)
    python "%CD%\apply_hush_petting_fix.py" --project "%CD%"
)
set "STATUS=%ERRORLEVEL%"
if not "%STATUS%"=="0" echo INSTALL FAILED. Read the exact error above.
if "%STATUS%"=="0" echo FINISHED. Clean and Rebuild the solution, then deploy without uninstalling.
echo.
pause
exit /b %STATUS%
