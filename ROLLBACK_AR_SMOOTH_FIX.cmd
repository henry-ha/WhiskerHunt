@echo off
setlocal EnableExtensions DisableDelayedExpansion
pushd "%~dp0"
if errorlevel 1 goto :bad_directory
echo Hush Hunt: restore the last AR source backup (launcher fix)
where py >nul 2>&1
if not errorlevel 1 goto :use_py
where python >nul 2>&1
if not errorlevel 1 goto :use_python
echo ERROR: Python 3 not found. Install Python 3 or add it to PATH.
set "RC=9009"
goto :finish
:use_py
py -3 "install_ar_smooth_fix.py" --restore-latest
goto :after_run
:use_python
python "install_ar_smooth_fix.py" --restore-latest
:after_run
set "RC=%errorlevel%"
if not "%RC%"=="0" echo ROLLBACK FAILED - inspect the error above.
:finish
popd
pause
exit /b %RC%
:bad_directory
echo ERROR: Cannot open the folder containing this installer.
pause
exit /b 1
