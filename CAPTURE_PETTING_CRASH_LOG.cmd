@echo off
setlocal EnableExtensions
cd /d "%~dp0" || (echo Could not locate script folder.& pause & exit /b 1)
set "ADB="
if exist "%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" set "ADB=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"
if not defined ADB if exist "%ProgramFiles(x86)%\Android\android-sdk\platform-tools\adb.exe" set "ADB=%ProgramFiles(x86)%\Android\android-sdk\platform-tools\adb.exe"
if not defined ADB if defined ANDROID_HOME if exist "%ANDROID_HOME%\platform-tools\adb.exe" set "ADB=%ANDROID_HOME%\platform-tools\adb.exe"
if not defined ADB if defined ANDROID_SDK_ROOT if exist "%ANDROID_SDK_ROOT%\platform-tools\adb.exe" set "ADB=%ANDROID_SDK_ROOT%\platform-tools\adb.exe"
if not defined ADB for /f "delims=" %%I in ('where adb 2^>nul') do if not defined ADB set "ADB=%%I"
if not defined ADB (
 echo Android adb.exe was not found. In Visual Studio, open Android Logcat,
 echo reproduce the crash, and copy AndroidRuntime or SIGABRT errors.
 pause
 exit /b 1
)
echo Device list:
"%ADB%" devices
set "RAW=%CD%\HushHunt_Petting_Recent_Log_FULL.txt"
set "FILTER=%CD%\HushHunt_Petting_Recent_Log_FILTERED.txt"
echo.
echo Reproduce the crash FIRST, then run this script to collect recent Android logs.
echo Reading Android Logcat. Do not disconnect the device.
"%ADB%" logcat -d -v threadtime -t 8000 > "%RAW%"
if errorlevel 1 (echo Logcat failed. Check USB debugging and authorisation.& pause & exit /b 1)
findstr /I /C:"hushhunt" /C:"HushFilament" /C:"AndroidRuntime" /C:"SIGABRT" /C:"FATAL EXCEPTION" /C:"JNI DETECTED ERROR" /C:"art/runtime" /C:"libc" "%RAW%" > "%FILTER%"
echo.
echo Saved filtered log: "%FILTER%"
echo If empty, share FULL log instead: "%RAW%"
echo Note: logs may contain private device data. Review before sharing.
pause
