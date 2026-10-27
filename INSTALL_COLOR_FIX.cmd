@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "ROOT=%~dp0"
set "TARGET=%ROOT%WhiskerHunt"
if not exist "%TARGET%\WhiskerHunt.csproj" (
 echo ERROR: Extract ZIP into the solution folder containing WhiskerHunt\WhiskerHunt.csproj
 echo Example: E:\inetpub\wwwroot\WhiskerHunt\
 pause
 exit /b 1
)
set "STAGING=%ROOT%PATCH_FILES\WhiskerHunt"
set "RELJAVA=Platforms\Android\Java\com\hushhunt\filament\HushFilamentOverlay.java"
set "RELMODELS=Resources\Raw\ar_models"
for %%F in ("%STAGING%\%RELJAVA%" "%STAGING%\%RELMODELS%\cat-cat-in-motion.glb" "%STAGING%\%RELMODELS%\fantasy-phoenix-bird.glb") do if not exist "%%~fF" (
 echo Missing patch source: %%~fF
 pause
 exit /b 1
)
for %%F in ("%TARGET%\%RELJAVA%" "%TARGET%\%RELMODELS%\cat-cat-in-motion.glb" "%TARGET%\%RELMODELS%\fantasy-phoenix-bird.glb") do if not exist "%%~fF" (
 echo Missing installed original: %%~fF
 echo Stopping to avoid altering a different Hush Hunt project.
 pause
 exit /b 1
)
set "BACKUP=%ROOT%ColorFix_Backup_%RANDOM%_%RANDOM%"
mkdir "%BACKUP%\%RELMODELS%" 2>nul
mkdir "%BACKUP%\Platforms\Android\Java\com\hushhunt\filament" 2>nul
copy /B /Y "%TARGET%\%RELJAVA%" "%BACKUP%\%RELJAVA%" >nul || goto :FAIL
copy /B /Y "%TARGET%\%RELMODELS%\cat-cat-in-motion.glb" "%BACKUP%\%RELMODELS%\cat-cat-in-motion.glb" >nul || goto :FAIL
copy /B /Y "%TARGET%\%RELMODELS%\fantasy-phoenix-bird.glb" "%BACKUP%\%RELMODELS%\fantasy-phoenix-bird.glb" >nul || goto :FAIL
>"%ROOT%LAST_COLOR_FIX_BACKUP.txt" echo %BACKUP%
copy /B /Y "%STAGING%\%RELJAVA%" "%TARGET%\%RELJAVA%" >nul || goto :FAIL
copy /B /Y "%STAGING%\%RELMODELS%\cat-cat-in-motion.glb" "%TARGET%\%RELMODELS%\cat-cat-in-motion.glb" >nul || goto :FAIL
copy /B /Y "%STAGING%\%RELMODELS%\fantasy-phoenix-bird.glb" "%TARGET%\%RELMODELS%\fantasy-phoenix-bird.glb" >nul || goto :FAIL
echo.
echo COLOR FIX INSTALLED. Original files backed up to:
echo %BACKUP%
echo Next: Clean Solution, Rebuild Solution, deploy without uninstalling.
pause
exit /b 0
:FAIL
echo ERROR copying one or more files. Your last backup is in %BACKUP%.
echo Run RESTORE_COLOR_FIX.cmd before rebuilding.
pause
exit /b 1
