V5.1 WINDOWS PATH FIX (2026-10-28)
=================================
This package corrects the WinError 123 command-line problem in V5.
The earlier launcher used: --root "%~dp0"
The trailing backslash in that quoted argument can escape its closing quote.
V5.1 does not pass --root; Python discovers the solution from its own file location.
The underlying pose-sync changes are unchanged from V5.

IMPORTANT: Extract all files. Replace any V5 .cmd files with these new ones.
Run CHECK_POSESYNC_V5.cmd FIRST. If it reports CHECK PASSED, then
run INSTALL_POSESYNC_V5.cmd. Do not run INSTALL if check fails.
If source layout does not match, the patch may safely skip some changes.
No APK is included. This does NOT prove the AR lag is resolved.

HUSH HUNT B99 - LOW LATENCY POSE SYNC V5 (2026-10-28)
====================================================

Why V4 failed
-------------
V4 required a single, exact continuous camera/model matrix-transform block.
Your source is a different revision, so V4 reported "0 matches" and safely
left your project untouched. This was not a missing GLB or a build failure.

What V5 changes
---------------
Instead of replacing a whole transform block, V5 independently recognises
and optimises the camera matrix, world matrix, projection, light updates,
frame generation acknowledgement and ARCore plane searches. Unrecognised
transform code stays untouched, and the patch reports what it SKIPPED.
The animal model's geometry, GLB textures, rotation, petting and controls
are not edited. Rollback backs up exact original source bytes.

INSTALL
-------
1. Close the running Visual Studio debug session. Keep your own backup too.
2. Extract ALL FOUR package files into your current solution root:
   E:\inetpub\wwwroot\WhiskerHunt\
   (the folder that contains WhiskerHunt.sln).
3. Run CHECK_POSESYNC_V5.cmd and review its output. Check does NOT edit source.
4. If CHECK PASSED, run INSTALL_POSESYNC_V5.cmd.
5. In Visual Studio: Clean Solution, Rebuild Solution, deploy to your phone.
   Do NOT uninstall your app; collections, captures and favourites are retained.
6. Compare an anchored zebra or fox while walking sideways at 1x, 2x and 3x.
7. If worse, stop debugging and run ROLLBACK_POSESYNC_V5.cmd.

REQUIRED
--------
Windows Python 3 ("py -3" or "python" on PATH).
No extra Python packages required.
Do not run V4 again after installing V5.

SAFETY / LIMITATIONS
--------------------
- Tested with CHECK / INSTALL / ROLLBACK on six local Hush Hunt source variants,
  including deliberately altered matrix-source layout.
- These are source-level checks only, not compiled Android/device benchmarks.
- An unknown matrix section is explicitly skipped, not blindly rewritten.
- The underlying TWO-SURFACE Filament + ARCore pipeline can still exhibit
  latency. A true same-frame composite requires architectural work.
- If CHECK reports "NO SOURCE UPDATES", do NOT rerun installers. Send the
  current HushFilamentOverlay.java and HushArCoreActivity.cs to tailor a fix.
- The script makes no changes to GLB assets, databases, Android package,
  or the user's installed application data.

CURRENT SOURCE FILES (if you need to share for tailoring):
WhiskerHunt\Platforms\Android\Java\com\hushhunt\filament\HushFilamentOverlay.java
WhiskerHunt\Platforms\Android\HushArCoreActivity.cs
