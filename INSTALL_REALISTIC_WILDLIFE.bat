@echo off
cd /d "%~dp0"
echo Hush Hunt: CC0 realistic wildlife importer for Filament glTF 2.0
echo All 23 bundled AR models are checked, originals backed up, exact CC0 licence required.
Models with unavailable exact HD matches will remain unchanged.
echo Internet access is needed for online model discovery.
py -m pip install Pillow
if errorlevel 1 (
  echo Pillow could not be installed. GLB WebP conversion needs Pillow.
  pause
  exit /b 1
)
py tools\upgrade_realistic_wildlife.py --download
if errorlevel 1 echo Some models were not available - originals were kept.
echo.
echo Review installer output, then CLEAN and REBUILD WhiskerHunt in Visual Studio.
pause
