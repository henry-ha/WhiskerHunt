@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "LAST_COLOR_FIX_BACKUP.txt" (
 echo No previous backup recorded.
 pause
 exit /b 1
)
set /p "BACKUP=" <"LAST_COLOR_FIX_BACKUP.txt"
set "TARGET=%~dp0WhiskerHunt"
set "RELJAVA=Platforms\Android\Java\com\hushhunt\filament\HushFilamentOverlay.java"
set "RELMODELS=Resources\Raw\ar_models"
for %%F in ("%BACKUP%\%RELJAVA%" "%BACKUP%\%RELMODELS%\cat-cat-in-motion.glb" "%BACKUP%\%RELMODELS%\fantasy-phoenix-bird.glb") do if not exist "%%~fF" (
 echo Missing backup item: %%~fF
 pause
 exit /b 1
)
copy /B /Y "%BACKUP%\%RELJAVA%" "%TARGET%\%RELJAVA%" >nul || goto :FAIL
copy /B /Y "%BACKUP%\%RELMODELS%\cat-cat-in-motion.glb" "%TARGET%\%RELMODELS%\cat-cat-in-motion.glb" >nul || goto :FAIL
copy /B /Y "%BACKUP%\%RELMODELS%\fantasy-phoenix-bird.glb" "%TARGET%\%RELMODELS%\fantasy-phoenix-bird.glb" >nul || goto :FAIL
echo Previous Java and GLBs restored. Clean/Rebuild/Deploy.
pause
exit /b 0
:FAIL
echo RESTORE FAILED. Inspect: %BACKUP%
pause
exit /b 1
