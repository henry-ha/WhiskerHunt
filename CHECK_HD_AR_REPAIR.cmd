@echo off
setlocal
set "TITLE=Hush Hunt B99 - Check smoother AR + animal-shaped shadow"
title %TITLE%
pushd "%~dp0." || (echo ERROR: Cannot open installer directory.& pause & exit /b 1)
if not exist "WhiskerHunt.sln" (
  echo ERROR: Extract these files into the folder containing WhiskerHunt.sln.
  goto error
)
where py >nul 2>&1
if %errorlevel%==0 (py -3 "install_hd_ar_repair.py" --check) else (python "install_hd_ar_repair.py" --check)
if errorlevel 1 goto error
echo.
echo CHECK FINISHED. No source files changed.
popd
pause
exit /b 0
:error
echo.
echo CHECK FAILED. No source files changed.
popd
pause
exit /b 1
