HUSH HUNT v3.10.36 Build 99 — PRIMARY GLB LOADING & ROTATION GLYPH FIX

ROOT CAUSE
The prior HushGlbAnimal3D.TryLoad() searched ar_fallback/<file> before
ar_models/<file>. Thus a simplified backup replaced an available repaired
wildlife model, causing missing eyes, lost coat textures and wrong anatomy.

CHANGES
- ar_models always first, ar_fallback only if primary is missing/incompatible.
- Android Logcat now reports "MODEL SOURCE: ar_models/... [PRIMARY]" or
  "MODEL SOURCE: ar_fallback/... [FALLBACK]" for each animal.
- Rotation glyphs centred and nudged about 3dp up inside the same 48dp circles.
- HD/Filament still available for non-legacy-compatible GLBs; 61 repaired
  float32 GLBs can use the direct GL renderer when supported.

INSTALLATION
1. BACK UP the entire solution and Resources/Raw/ar_models directory.
2. Extract this ZIP into E:\inetpub\wwwroot\WhiskerHunt.
   Its root contains WhiskerHunt/Platforms/Android/.
3. If using the all-in-one ZIP, the repaired ar_models GLBs will also be copied
   into WhiskerHunt/Resources/Raw/ar_models. They replace only matching .glb
   files. This is intentional: older or quantised GLBs must not be repackaged.
4. CLOSE Visual Studio; delete WhiskerHunt/bin and WhiskerHunt/obj (build
   artifacts ONLY; never delete the source or wildlife directories).
5. Open the solution, rebuild, and DEPLOY over the existing installation.
   Do NOT uninstall the existing app (saved collection).
6. Check Android Logcat filter HushHuntAR: MODEL SOURCE should say [PRIMARY].
   If it says [FALLBACK], check your packaged Resources/Raw/ar_models file.

VERIFIED OFF-DEVICE
- All 61 shipped GLBs: GLB header, JSON and primary float attributes checked.
- Archive integrity verified after creation.
- Source patches verified textually; Android compilation and on-device
  rendering are NOT verified here.

The original artwork can still have anatomy/texture imperfections. This
fix ensures the app does not silently use an inferior fallback when a
repaired, compatible primary GLB is available.
