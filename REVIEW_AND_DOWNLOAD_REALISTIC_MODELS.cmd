@echo off
setlocal
cd /d "%~dp0"
echo HUSH HUNT - REALISTIC WILDLIFE CANDIDATES
echo ---------------------------------------
echo Downloads go to staging only. Existing animals are not replaced.
echo.
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
  py -3 "tools\hush_realistic_models.py" fetch all
) else (
  python "tools\hush_realistic_models.py" fetch all
)
echo.
echo Review models in HushHunt_Realistic_Model_Candidates before installing.
echo To compare them with current library, run AUDIT_INSTALLED_REALISTIC_MODELS.cmd.
pause
