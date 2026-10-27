Hush Hunt v3.10.36 Build 99 - ADB Crash Logger Repair

Why this patch exists:
- The previous CAPTURE_AR_CRASH_LOG.bat only looked in PATH and %LOCALAPPDATA%\Android\Sdk.
- The Visual Studio .NET MAUI SDK is often at C:\Program Files (x86)\Android\android-sdk.
- Hush Hunt still stops with Android native SIGABRT. The screenshot lacks the abort message and triggering backtrace; neither Filament nor JNI can yet be confirmed as root cause.

What this diagnostic-only patch does:
- Searches common Windows / Visual Studio Android SDK locations for adb.exe.
- Checks device connectivity and USB debugging authorisation.
- Captures *existing* crash logs BEFORE clearing the buffer (important).
- Optionally clears the log then captures a clean, newly reproduced crash.
- Includes context around HushFilament STAGE, Android runtime abort, JNI, Filament and native crash messages.
- Writes readable filtered logs and full logs into the folder containing CAPTURE_AR_CRASH_LOG.bat.

How to install:
1. Extract this ZIP into E:\inetpub\wwwroot\WhiskerHunt (your solution folder).
2. Replace CAPTURE_AR_CRASH_LOG.bat and add tools\extract_ar_crash.ps1.
3. Keep OnePlus connected via USB debugging, double-click CAPTURE_AR_CRASH_LOG.bat.
4. It saves HushHunt_AR_Log_Existing_Filtered.txt immediately; inspect it before creating a new crash.
5. To reproduce, follow the script and open Domestic Shorthair in 3D Safari.
6. After the crash, return to the script and press a key.
7. Review HushHunt_AR_Log_Filtered.txt for private information before sharing.

This patch DOES NOT modify the app, 3D models, camera, AR renderer or collection data.
A new app build is neither required nor useful for this diagnostic-only repair.
