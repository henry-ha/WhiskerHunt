@echo off
setlocal
cd /d "%~dp0"
echo HUSH HUNT -- Repair AR Safari icons and keep all installed wildlife files
where py >nul 2>nul
if errorlevel 1 (
 echo Python 3 not found. Run: python tools\fix_ar_safari.py
 pause
 exit /b 1
)
py tools\fix_ar_safari.py
if errorlevel 1 (
 echo Repair failed. Your existing models and catalogue have not been deleted.
 pause
 exit /b 1
)
echo.
echo Close Visual Studio, delete WhiskerHunt\bin and WhiskerHunt\obj, then Rebuild and Deploy.
echo Verify the built APK: py tools\verify_filament_apk.py "path-to-built.apk"
pause
