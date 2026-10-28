HUSH HUNT v3.10.36 / Build 99
3D SAFARI - AR camera walk-around latency fix
28 October 2026

WHY THE ANIMALS APPEAR STATIC / LAG BEHIND THE PHONE
The Java Filament overlay draws in a TextureView, while ARCore's camera
background is shown by a separate GLSurfaceView. The app also added its
own extra frame throttle for larger 3D assets: GLBs over 24MB were limited
to about 33 FPS (30 milliseconds between Filament frames); 12-24MB models
to about 45 FPS (22 milliseconds). This can make the model visibly lag the
live camera as the phone moves, even when the ARCore world anchor is valid.
Separate layers can still have some inherent compositor latency.

THIS REPAIR
- Removes the unnecessary secondary large-GLB frame throttle. 3D model
  updates can now attempt every display VSYNC when ARCore has new matrices.
- Lets Filament's native renderer decide whether to skip if the GPU is
  actually behind, rather than assuming large files are slow.
- Passes the Choreographer VSYNC timestamp to renderer.beginFrame(...).
- Reuses 3 camera / model matrix scratch arrays rather than allocating new
  arrays each rendered frame, reducing GC and main-thread work.
- Does NOT change the ARCore camera, world anchors, walking path, animal
  rotations, existing animations, petting frame-sync channel, textures, GLBs,
  model assets, photo capture, or the 2D Safari.

INSTALL
1. Close Visual Studio. Back up the full Hush Hunt solution.
2. Extract the ZIP directly into E:\inetpub\wwwroot\WhiskerHunt\
   (the folder containing WhiskerHunt.sln, not the inner WhiskerHunt project).
3. Run CHECK_AR_SMOOTH_FIX.cmd. It must say CHECK PASSED.
4. Run INSTALL_AR_SMOOTH_FIX.cmd. It must say INSTALLED.
5. Open Visual Studio > Build > Clean Solution > Rebuild Solution.
6. Deploy to the phone over the existing app. DO NOT uninstall it, because
   uninstalling may delete private saved collections/captures.
7. Test: place Jack Russell on the carpet. Walk sideways slowly with the
   model in view. Repeat with Phoenix and larger Cat in Motion. Pet and
   rotate/zoom. Confirm the model stays fixed relative to the carpet.

IF PERFORMANCE WORSE OR APP CRASHES
Run ROLLBACK_AR_SMOOTH_FIX.cmd, then Clean/Rebuild and redeploy.
Every install creates a timestamped source backup inside
  HushHunt_AR_Performance_Backups\LowLatency_YYYYMMDD_...
The installer refuses to apply if expected code anchors differ; it is
safe to rerun after successful installation.

LIMITATIONS / HONEST TEST STATUS
- The update was regression-tested against reconstructed B99 HD colour,
  earlier petting and latest petting crash hotfix source patterns. On-device
  AR smoothness/latency has NOT been measured here.
- Dual-layer TextureView + GLSurfaceView composition still exists. If
  the phone continues to show an animal sliding or trailing as you orbit it,
  a deeper single-renderer / synchronised composition change is required.
- For high-polygon/high-texture models, 60 FPS is a *target*, never a
  guarantee: the GPU or Filament native frame pacing may drop frames.
- These changes aim to improve temporal alignment; they do not add new
  geometry, eyes, textures, or lighting.

FILE CHANGED
  WhiskerHunt/Platforms/Android/Java/com/hushhunt/filament/HushFilamentOverlay.java

LAUNCHER FIX (2026-10-28): Batch scripts no longer pass a quoted path ending in a backslash to Python, fixing WinError 123 and --check being treated as path text. All three commands use pushd into the solution directory and let Python use Path.cwd(). Rollback now selects most recent LowLatency backup directly in Python. The existing Java source patch content is unchanged.
