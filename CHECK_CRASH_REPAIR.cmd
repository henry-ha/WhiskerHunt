@echo off
setlocal EnableExtensions
cd /d "%~dp0" || (echo Cannot access solution folder.& pause & exit /b 1)
echo Checking Hush Hunt HD petting crash repair (no files changed)...
where py >nul 2>&1
if not errorlevel 1 (py -3 "%CD%\repair_petting_crash.py" --project "%CD%" --check) else (python "%CD%\repair_petting_crash.py" --project "%CD%" --check)
set "STATUS=%ERRORLEVEL%"
echo.
if "%STATUS%"=="0" (echo CHECK PASSED.) else (echo CHECK FAILED. No files modified.)
pause
exit /b %STATUS%
