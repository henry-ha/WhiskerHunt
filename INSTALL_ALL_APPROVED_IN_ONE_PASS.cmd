@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (set "PY=py -3") else (set "PY=python")
echo INSTALL APPROVED MODELS ONLY - all 61 slots assessed.
echo Each installed model has a timestamped SHA256-verified backup.
echo Edit each review.json approved=true ONLY after checking eyes, limbs,
echo texture, license, scene props, Android geometry and animations.
echo.
set /p SURE=Type INSTALL to proceed: 
if /I not "%SURE%"=="INSTALL" goto finish
%PY% tools\hush_one_sweep.py --install-approved --yes
:finish
pause
endlocal
