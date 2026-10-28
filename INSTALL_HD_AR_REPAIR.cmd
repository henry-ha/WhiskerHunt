@echo off
setlocal
title Hush Hunt B99 - Install smoother AR and species shadows
pushd "%~dp0." || (echo ERROR: Cannot open installer directory.& pause & exit /b 1)
if not exist "WhiskerHunt.sln" (
  echo ERROR: Place files in the folder containing WhiskerHunt.sln.
  goto error
)
where py >nul 2>&1
if %errorlevel%==0 (py -3 "install_hd_ar_repair.py") else (python "install_hd_ar_repair.py")
if errorlevel 1 goto error
echo.
echo INSTALL FINISHED. Clean and Rebuild Solution, then deploy OVER existing app.
popd
pause
exit /b 0
:error
echo.
echo INSTALL FAILED. Read the reason above. Do NOT force replacement files.
popd
pause
exit /b 1
