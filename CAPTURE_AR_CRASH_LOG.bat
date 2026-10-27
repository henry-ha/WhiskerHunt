@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title Hush Hunt AR Crash Logger - stays open
color 0F
echo ================================================================
echo   HUSH HUNT - ANDROID AR NATIVE CRASH LOGGER
 echo   This window stays open even if ADB cannot be found.
echo ================================================================
echo.
if not exist "%~dp0HushHunt_AR_Capture.ps1" (
  echo ERROR: HushHunt_AR_Capture.ps1 is missing.
  echo Extract BOTH files from the ZIP to the SAME folder.
  echo.
  pause
  exit /b 10
)
where powershell.exe >nul 2>&1
if errorlevel 1 (
  echo ERROR: Windows PowerShell is not available.
  echo.
  pause
  exit /b 11
)
set "HUSH_LOG_SCRIPT=%~dp0HushHunt_AR_Capture.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%HUSH_LOG_SCRIPT%"
set "LOG_RESULT=%ERRORLEVEL%"
echo.
echo ---------------------------------------------------------------
echo Capture tool exit code: %LOG_RESULT%
echo Look for HushHunt_AR_Log_Filtered.txt and HushHunt_Logger_Status.txt
 echo in this folder: %~dp0
 echo This window should remain visible until you press a key.
echo ---------------------------------------------------------------
pause
exit /b %LOG_RESULT%
