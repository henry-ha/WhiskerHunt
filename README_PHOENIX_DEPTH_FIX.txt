HUSH HUNT — PHOENIX GLB DEPTH-SORT REPAIR (2026-10-28)

OBSERVED PROBLEM
The imported fantasy-phoenix-bird.glb has both materials set to alphaMode=BLEND,
with RGBA textures containing mostly opaque pixels. Transparent-material sorting
can make wings and head overlap incorrectly as the AR viewing direction changes.
At 3x scale, large portions of this oversized phoenix also leave the camera view.

WHAT CHANGES
Both material alphaMode settings BLEND -> MASK, alphaCutoff=0.38.
No mesh vertices, UVs, textures, skeleton, animations, or environment are replaced.
This is a reasonable targeted experiment, not a guarantee of solving all occlusion.
A backup is created, and the repair can be rolled back.

INSTALL
1. Extract this ZIP anywhere on your Windows PC.
2. Run CHECK_PHOENIX_DEPTH_FIX.bat, then INSTALL_PHOENIX_DEPTH_FIX.bat.
3. In Visual Studio: Clean Solution, Rebuild Solution, deploy the updated app.
4. Test Phoenix at 1x before increasing to 2x or 3x, keeping its entire body in view.
5. If feather edges look jagged, run RESTORE_PHOENIX_ORIGINAL.bat and let us know.

PROJECT LOCATION
Default: E:\inetpub\wwwroot\WhiskerHunt
If your solution is elsewhere, edit the --root argument in the BAT files or run
  py -3 patch_phoenix_glb.py --check --root "D:\YourProjectFolder"
  py -3 patch_phoenix_glb.py --install --root "D:\YourProjectFolder"

The pre-made reference file HushHunt_Phoenix_DepthSort_Repaired.glb is included
for inspecting in Blender or a GLB viewer, but the script is preferred because
it patches your CURRENT model without overwriting any other recent adjustments.

IMPORTANT
The screenshot shows clipping at high zoom as well. A model-specific AR scale
clamp / auto-fit might be necessary in HushArCoreActivity.cs as a separate step.
The script does NOT touch the Filament render loop or AR tracking performance.
