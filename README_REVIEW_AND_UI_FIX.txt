Hush Hunt v3.10.36 B99 - controls refinement + non-destructive GLB checks

UI change:
- Existing four buttons remain 48dp in diameter.
- Rotate left and rotate right characters increased from 22sp to 29sp.
- All four buttons use a translucent neutral grey background and subtle border.
- No change to model scale, rotation logic, saved collection or other controls.

GLB check:
- Double-click REVIEW_HUSH_HUNT_HD_MODELS.cmd on the development PC.
- It checks the EXACT GLB files currently installed in Resources/Raw/ar_models.
- It compares any same-named files in Resources/Raw/ar_fallback for lost PBR textures,
  images and animations. Such damage can explain missing eyes / coat details.
- It also identifies binary glTF errors, missing external resources and incompatible
  WebP / KTX2 / mesh-compression extensions.
- WebP images can be losslessly migrated to PNG in a SEPARATE review-only GLB,
  without altering meshes, skinning, original files or active app assets.
- Requires Pillow if WebP images are found: py -m pip install Pillow
- The script does NOT replace an animal in the app, claim to fix absent geometry,
  or delete original or fallback models.

Install this ZIP over the EXISTING project (not over your installed HD asset folder).
Open Visual Studio, Clean Solution and Rebuild after installing the UI source.
Do NOT uninstall the app, and do not overwrite GLBs using the review copies until validated.

For actual anatomical restoration, we need the original corrupt/incompatible GLB bytes
(e.g. other-silverback-gorilla.glb) and the runtime Logcat HushFilament stage/error.
A Windows viewer failing to open a GLB does not prove the file is corrupt: it may
not support its glTF compression or texture extensions.
