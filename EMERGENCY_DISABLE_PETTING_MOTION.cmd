@echo off
setlocal EnableExtensions
cd /d "%~dp0" || (echo Cannot access solution folder.& pause & exit /b 1)
echo Emergency stop: disable HD pet motion (retain touch feedback, wildlife colours, data)
where py >nul 2>&1
if not errorlevel 1 (py -3 "%CD%\repair_petting_crash.py" --project "%CD%" --disable) else (python "%CD%\repair_petting_crash.py" --project "%CD%" --disable)
set "STATUS=%ERRORLEVEL%"
echo.
if "%STATUS%"=="0" (echo HD pet motion disabled. Rebuild/deploy without uninstalling.) else (echo DISABLE FAILED - see above.)
pause
exit /b %STATUS%
