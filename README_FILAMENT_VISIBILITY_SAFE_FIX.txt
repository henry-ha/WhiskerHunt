Hush Hunt v3.10.36 Build 99 — Rendering Recovery, Silverback Fallback & Controls

This is a SOURCE PATCH for the existing Visual Studio solution. It is not a compiled APK.
It does not overwrite your installed HD GLB files, 48-animal catalogue, icons or saved captures.

Corrections
-----------
1) Existing/legacy-compatible GLBs use the original, real 3D OpenGL renderer.
   This avoids the newer overlay making Garden Snail and other original animals black.
2) Filament's TextureView is composited at full alpha from creation; no
   pre-placement 2D animal is drawn because no model frame renders before an anchor.
3) Filament no longer calls a background GPU frame "HD ready". A small pixel
   sample verifies that visible, lit animal geometry actually appeared.
4) The legacy renderer stays visible when a usable fallback exists. When the
   only HD renderer is invisible, it no longer shows a misleading shadow alone.
5) ARCore's main-light direction is reversed for Filament's ray direction;
   ambient lighting is stabilized and contact shadows are much lighter.
6) Filament's frame loop is capped near 30 FPS to reduce duplicated GPU load.
7) Rotation has LEFT and RIGHT only. The confusing tilt controls are removed;
   yaw directions have been swapped as requested. Walking stays in place.
8) The status no longer says an invisible animal "arrived" just because its
   anchor reached a destination.

Silverback Gorilla / other invisible modern HD models
----------------------------------------------------
Modern GLBs sometimes cannot render through the Filament Android overlay on
some devices. The included OPTIONAL fallback generator converts your already-
installed HD mesh into a static, unquantised GLB for the old 3D renderer.
This is a genuine 3D mesh fallback, NOT a 2D sprite. Trimesh may drop
skeletal animation or unsupported material features. The HD source is retained.

A. Back up E:\inetpub\wwwroot\WhiskerHunt first.
B. Extract this ZIP into E:\inetpub\wwwroot\WhiskerHunt (overwrite source files).
C. Run in Command Prompt, only if missing Python dependencies:
       py -m pip install trimesh Pillow numpy
D. Run GENERATE_HD_3D_FALLBACKS.bat (uses your installed HD models, including
   Silverback Gorilla, if present). Read HushHunt_Fallback_Conversion_Report.json.
E. Clean Solution / Rebuild Solution in Visual Studio and deploy without
   uninstalling the existing app.
F. Test Garden Snail (normal appearance and rotation), Silverback Gorilla
   (full geometry visible and attached to the floor), and Walk/perspective.

Verification in this environment
--------------------------------
- GLB fallback converter tested with a simulated modern GLB of ~34,000 triangles;
  the source remained unmodified and a compatible 3D fallback was generated.
- Basic source checks and ZIP integrity checks passed.
- No on-device Android compilation or Silverback HD GLB test was possible here.
- If Gorilla conversion fails, share HushHunt_Fallback_Conversion_Report.json
  and Android Logcat lines filtered on HushFilament / HushHuntAR.
