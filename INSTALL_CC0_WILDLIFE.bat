@echo off
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"
echo.
echo Hush Hunt - optional CC0 3D wildlife installer
 echo This downloads third-party animal models from 3DAssets.dev into source assets.
 echo It checks for CC0 licensing and converts to native ARCore-compatible GLB.
 echo Build and test the updated MAUI project after import.
echo.
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found. Install Python 3.11+ and run manually.
  pause
  exit /b 1
)
py -c "import trimesh, PIL, numpy" >nul 2>nul
if errorlevel 1 (
  echo Installing missing 3D import dependencies...
  py -m pip install --disable-pip-version-check trimesh Pillow numpy
  if errorlevel 1 (
    echo Required Python packages could not be installed.
    pause
    exit /b 1
  )
)
py tools\import_cc0_wildlife.py --download
if errorlevel 1 (
  echo Import failed. Check your connection and licence information.
  pause
  exit /b 1
)
echo.
echo Complete. Rebuild WhiskerHunt\WhiskerHunt.csproj in Visual Studio.
echo No existing collections are modified. Models are bundled into the APK on rebuild.
pause
