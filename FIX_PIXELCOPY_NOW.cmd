@echo off
setlocal EnableExtensions
pushd "%~dp0"
if errorlevel 1 goto :badfolder
if not exist "install_hush_pixelcopy_fix.py" goto :missing
echo Hush Hunt B99 - Windows path corrected V2
echo Checking Java source first...
where py >nul 2>&1
if not errorlevel 1 goto :withpy
where python >nul 2>&1
if errorlevel 1 goto :nopython
python "install_hush_pixelcopy_fix.py" --check
if errorlevel 1 goto :failure
python "install_hush_pixelcopy_fix.py" --install
if errorlevel 1 goto :failure
goto :success
:withpy
py -3 "install_hush_pixelcopy_fix.py" --check
if errorlevel 1 goto :failure
py -3 "install_hush_pixelcopy_fix.py" --install
if errorlevel 1 goto :failure
goto :success
:missing
echo ERROR: Please extract ALL zip files into your WhiskerHunt solution root.
goto :failure
:nopython
echo ERROR: Python 3 not found.
goto :failure
:badfolder
echo ERROR: Could not open launcher folder.
goto :failure_no_pop
:failure
echo.
echo FIX FAILED. No new source edit was made unless install reports completion.
popd
:failure_no_pop
pause
exit /b 1
:success
echo.
echo SUCCESS. Open Visual Studio - Clean Solution - Rebuild Solution.
popd
pause
exit /b 0
