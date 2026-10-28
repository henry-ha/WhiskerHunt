HUSH HUNT B99 — FILAMENT AR FRAME STALL REDUCTION (2026-10-28)

PURPOSE
The phoenix GLB transparency/depth repair is preserved. This is a conservative
source-only patch to reduce avoidable rendering work in the *separate* Filament
animal overlay. Intended for the reported lag when walking around anchored animals.

CHANGES (depending on actual Java source; CHECK displays exact edits)
- Filament overlay extra post-processing OFF. PBR colour, textures and depth stay.
- Redundant Filament directional shadow-map pass OFF. Existing AR contact
  / silhouette shadow (from ARCore view) is left alone.
- In old renderer variants, limit repeated GPU->CPU visibility inspection to
  6 attempts per session (prevents endless readback stalls if it cannot pass).
- Does not edit anchor placement, rotation, petting, walking, GLB materials,
  wildlife meshes, ARCore exposure or storage. No reinstall/uninstall needed.

INSTALL (WINDOWS)
1. Back up/commit your WhiskerHunt source. Exit Visual Studio debugging.
2. EXTRACT ALL 4 FILES to E:\inetpub\wwwroot\WhiskerHunt\ (folder containing
   WhiskerHunt.sln and the inner WhiskerHunt folder).
3. Run CHECK_AR_FRAME_STALL_FIX.cmd. Proceed only if CHECK PASSED.
4. Run INSTALL_AR_FRAME_STALL_FIX.cmd. Confirm INSTALL PASSED.
5. Clean Solution, Rebuild Solution, deploy OVER the existing Android app.
6. Test Phoenix at 1x: place on floor, walk around SLOWLY (not just rotate).
   Then test Zebra and Fox in exactly the same location and lighting.
7. If anything is worse: ROLLBACK_AR_FRAME_STALL_FIX.cmd, rebuild, redeploy.

WHEN THIS IS NOT ENOUGH
This still uses separate ARCore-camera and Filament-animal rendering surfaces.
They are asynchronously composited. If ARCore camera motion outruns model frame
updates the animal can appear screen-locked then catch up. The proper longer-term
fix is a genuinely unified ARCore+Filament rendering path with shared presentation
timing and one surface, rather than more arbitrary FPS caps or frame readbacks.

VALIDATION
The patch script is local-source tested against known B99 Filament Java
variants. It is NOT compiled in Visual Studio and is NOT device-benchmarked.
No claims of a tested FPS increase. If CHECK says "No matching actions" or
an unexpected source revision, do not force replacements.

OPTIONAL CUSTOM LOCATION
  py -3 hush_ar_frame_stall_fix.py --check --root "D:\YourProject"
  py -3 hush_ar_frame_stall_fix.py --install --root "D:\YourProject"
