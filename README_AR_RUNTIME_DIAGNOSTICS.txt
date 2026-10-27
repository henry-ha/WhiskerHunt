Hush Hunt v3.10.36 Build 99 - Domestic Shorthair runtime diagnostics patch

What this patch changes
- HushGlbAnimal3D.cs checks whether a GLB is suitable for the old OpenGL parser
  BEFORE parsing. Modern quantized / animated / extended GLBs are passed intact
  to Filament, avoiding expected InvalidDataException first-chance messages.
- Compatible ar_fallback/ models are preferred for the legacy renderer.
- HushFilamentOverlay.java logs each Filament startup stage to Android Logcat.
- Java performs a basic GLB container header check before passing bytes to gltfio.
- CAPTURE_AR_CRASH_LOG.bat collects the real native crash reason after reproducing.

Install
1. Back up your source and close Visual Studio.
2. Extract into E:\inetpub\wwwroot\WhiskerHunt, preserving paths, and overwrite.
3. Clean/Rebuild and deploy the app without uninstalling (keep existing signing key).
4. Test Domestic Shorthair in 3D Safari.
5. If Android still aborts, run CAPTURE_AR_CRASH_LOG.bat while USB debugging is on.
   Open Domestic Shorthair, allow crash, return to the command window,
   and share HushHunt_AR_Log_Filtered.txt after reviewing it for private data.

CAUTION: The screenshot shows System.IO.InvalidDataException followed by native
SIGABRT. The first-chance exception is addressed by skipping unsupported legacy
parsing. A native crash cannot be conclusively fixed without its full Logcat
abort reason / native backtrace, so the new stage logging is essential.

No GLB assets, species manifest, saved animal data, camera code, or application
ID are altered by this patch.

Checks performed: source inspection, Python GLB format tests, ZIP integrity.
Not performed: full .NET MAUI Android compile or testing on a physical phone.
