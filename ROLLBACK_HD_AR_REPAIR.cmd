@echo off
setlocal
title Hush Hunt B99 - Restore previous renderer
pushd "%~dp0." || (echo ERROR: Cannot open installer directory.& pause & exit /b 1)
where py >nul 2>&1
if %errorlevel%==0 (py -3 "install_hd_ar_repair.py" --rollback) else (python "install_hd_ar_repair.py" --rollback)
if errorlevel 1 goto error
echo.
echo ROLLBACK FINISHED. Clean and Rebuild Solution, then redeploy.
popd
pause
exit /b 0
:error
echo ROLLBACK FAILED. Backup must exist from a previous INSTALL.
popd
pause
exit /b 1
