@echo off
setlocal EnableExtensions
REM Hush Hunt: Clean rebuild, then install and launch on the connected Android device.
REM Place this file next to WhiskerHunt.csproj (inside the inner WhiskerHunt folder).
set "PROJECT=%~dp0WhiskerHunt.csproj"
if not exist "%PROJECT%" (
  echo ERROR: WhiskerHunt.csproj was not found next to this script.
  echo Copy CLEAN_REBUILD_DEPLOY.cmd into the folder containing WhiskerHunt.csproj.
  pause
  exit /b 2
)
where dotnet >nul 2>nul
if errorlevel 1 (
  echo ERROR: dotnet command not found. Open a Developer Command Prompt or install the .NET SDK.
  pause
  exit /b 3
)
set "DEVICE_ARG="
if not "%~1"=="" set "DEVICE_ARG=-p:Device=%~1"
pushd "%~dp0"
echo.
echo ===== STEP 1/2: CLEAN + REBUILD HUSH HUNT [Debug, net10.0-android] =====
dotnet build "%PROJECT%" -t:Rebuild -f net10.0-android -c Debug
if errorlevel 1 goto :failed

echo.
echo ===== STEP 2/2: DEPLOY + LAUNCH ON ANDROID =====
dotnet build "%PROJECT%" -t:Run -f net10.0-android -c Debug %DEVICE_ARG%
if errorlevel 1 goto :failed

echo.
echo SUCCESS: Build completed and Android run command returned successfully.
popd
exit /b 0
:failed
echo.
echo FAILED: See the build/deployment error above. No forced uninstall was performed.
popd
pause
exit /b 1
