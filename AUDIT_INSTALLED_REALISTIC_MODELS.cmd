@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
 py -3 "tools\hush_realistic_models.py" audit
) else (
 python "tools\hush_realistic_models.py" audit
)
echo.
pause
