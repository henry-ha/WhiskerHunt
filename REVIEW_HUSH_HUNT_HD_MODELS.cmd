@echo off
setlocal
cd /d "%~dp0"
echo Hush Hunt - Checking installed GLB files without changing them.
echo.
where py >nul 2>&1
if %errorlevel% equ 0 (
    py tools\review_installed_wildlife_glbs.py --prepare-webp
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        python tools\review_installed_wildlife_glbs.py --prepare-webp
    ) else (
        echo Python 3 is not on PATH. Please install Python 3 and rerun.
    )
)
echo.
echo Reports are in the project root: HushHunt_GLB_Quality_Report.txt and .json
pause
