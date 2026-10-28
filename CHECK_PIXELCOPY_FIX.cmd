@echo off
setlocal EnableExtensions
REM V2: never pass a quoted directory ending in backslash as a Python argument.
pushd "%~dp0"
if errorlevel 1 goto :badfolder
if not exist "install_hush_pixelcopy_fix.py" goto :missingscript
echo Hush Hunt B99 - CHECK SurfaceView PixelCopy hotfix (Windows path V2)
where py >nul 2>&1
if not errorlevel 1 goto :pyl
where python >nul 2>&1
if errorlevel 1 goto :missingpython
python "install_hush_pixelcopy_fix.py" --check
goto :done
:pyl
py -3 "install_hush_pixelcopy_fix.py" --check
goto :done
:missingscript
echo ERROR: extract all files together into the WhiskerHunt solution directory.
goto :fail
:missingpython
echo ERROR: Python 3 is needed. Install Python 3 and try again.
goto :fail
:badfolder
echo ERROR: could not open installer folder.
goto :failnoshell
:fail
set "RESULT=1"
goto :finish
:done
set "RESULT=%errorlevel%"
if not "%RESULT%"=="0" echo CHECK FAILED - see diagnostic above.
:finish
popd
:failnoshell
if not defined RESULT set "RESULT=1"
echo.
pause
exit /b %RESULT%
