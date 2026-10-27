@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (set "PY=py -3") else (set "PY=python")
echo ===================================================
echo HUSH HUNT - ONE SWEEP: ALL 61 WILDLIFE ASSET SLOTS
echo ===================================================
echo This stages alternative models and reports shortages.
echo Original models are NOT overwritten.
echo.
%PY% tools\hush_one_sweep.py
set "STATUS=%ERRORLEVEL%"
echo.
if exist Wildlife_One_Sweep_Reports\OPEN_61_MODEL_REVIEW.html (
 start "" "Wildlife_One_Sweep_Reports\OPEN_61_MODEL_REVIEW.html"
)
echo Finish status: %STATUS%
echo Review Wildlife_One_Sweep_Reports before installing anything.
pause
endlocal
