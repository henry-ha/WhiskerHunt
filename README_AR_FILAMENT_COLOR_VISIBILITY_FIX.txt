HUSH HUNT v3.10.36 build 99 — SKETCHFAB 3D AR RENDERER HOTFIX
27 October 2026

PURPOSE
Fix confirmed >24 MiB Filament GLB size cap that hid Cat in Motion and Jack Russell.
Reduce extreme exposure of light textures (Phoenix, white cat, kangaroo).
Reduce judder by synchronising Filament frames with fresh ARCore matrix snapshots.
Remove 1-second recurring TextureView bitmap readbacks once animal pixels are verified.
Use adjustable render budget depending on file size (16, 22 or 30ms).

INSTALL
1. Back up your E:\inetpub\wwwroot\WhiskerHunt project.
2. Close Visual Studio.
3. Extract this zip into E:\inetpub\wwwroot\WhiskerHunt.
4. Let it overwrite ONLY the Java renderer file at
   WhiskerHunt\Platforms\Android\Java\com\hushhunt\filament\HushFilamentOverlay.java
5. Run VERIFY_SKETCHFAB_3D_MODELS.cmd (Python 3 required).
6. In Visual Studio use Build > Clean Solution, then Rebuild Solution.
7. Deploy over the installed Hush Hunt app; DO NOT uninstall/clear storage.
8. Test Phoenix -> Sumpitueslag Cat -> Cat in Motion -> Bald Eagle -> Jack Russell.

SAFETY
- Original five Sketchfab GLBs are NOT overwritten. The update uses those already installed.
- Saved discoveries, app settings and your 61 other wildlife GLBs are unchanged.
- Backups are YOUR existing project copy; this zip is a source patch, not an APK.
- No new animation clips are introduced; Cat in Motion's label is not proof of animation.
- The older OpenGL loader retains its separate 24MiB fallback cap. Filament can now
  open the larger files directly; very heavy models may still be slow or fail on-device.
- The AR renderer is two GPU layers (ARCore GLSurfaceView + Filament TextureView);
  eliminating all latency requires a more substantial single-surface renderer refactor.
- Lighting is calibrated conservatively, but device testing is required.

DEBUG
Android Logcat tags to filter: HushFilament, HushHuntAR, AndroidRuntime.
A missing cat: look for 'GLB exceeds mobile 64 MiB safety limit' or a renderer exception.
A model can load without its embedded textures appearing properly; check the log.
The supplied audit validates GLB structure and embedded image counts, not appearance.

BUILD STATUS
Source patch and GLB audit validated. No Android SDK was available here to compile
or deploy; on-device output has NOT been visually verified.
