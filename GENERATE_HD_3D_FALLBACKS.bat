@echo off
setlocal
cd /d "%~dp0"
echo Hush Hunt - creating geometry fallbacks without changing the HD wildlife GLBs
where py >nul 2>nul
if errorlevel 1 (
 echo Python launcher not found. Install Python and use: python tools\make_hd_fallbacks.py
 goto :end
)
py tools\make_hd_fallbacks.py
if errorlevel 1 (
 echo If Trimesh is missing, run: py -m pip install trimesh Pillow numpy
)
echo.
echo Now rebuild WhiskerHunt in Visual Studio to include newly created ar_fallback files.
:end
echo.
pause
