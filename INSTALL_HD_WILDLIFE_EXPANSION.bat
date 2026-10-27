@echo off
cd /d "%~dp0"
echo ============================================
echo HUSH HUNT - High Detail Wildlife Expansion
echo ============================================
echo.
echo This installer keeps saved collections and original 23 models.
echo Models are CC0 candidates until you inspect them on device.
echo.
py -m pip install --disable-pip-version-check Pillow
if errorlevel 1 (
 echo Python or Pillow install failed. Install Python 3 and try again.
 pause
 exit /b 1
)
echo.
echo Updating original 23 species when exact high-detail CC0 matches exist...
py tools\upgrade_realistic_wildlife.py --download
if errorlevel 1 echo Some original species had no validated candidate and were preserved.
echo.
echo Adding new CC0 animal species from curated packs...
py tools\expand_realistic_wildlife.py --download-extras
if errorlevel 1 echo Some extras could not be imported. Check the messages above.
echo.
py tools\audit_wildlife_library.py
py tools\expand_realistic_wildlife.py --report

echo.
echo IMPORTANT: Open Visual Studio and Rebuild after new models install.
echo IMPORTANT: DO NOT uninstall the phone app. Inspect species in AR Safari.
pause
