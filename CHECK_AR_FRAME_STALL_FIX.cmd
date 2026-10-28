@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0hush_ar_frame_stall_fix.py" --check
) else (
  python "%~dp0hush_ar_frame_stall_fix.py" --check
)
echo.
pause
