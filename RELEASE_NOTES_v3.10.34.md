# Hush Hunt v3.10.34 · Build 97 — 3D/2D Safari Labels, 23 Wildlife Models and Responsive Petting

Based on the latest pre-existing v3.10.33 / Build 96 source (petting v1), rather than on v3.10.32 shown in the screenshot.

## Implemented

- Native ARCore camera heading changed from **AR Safari ✨** to **3D Safari ✨**.
- 2D Safari camera/encounter sheet heading changed to **2D Safari ✨**. The mode chooser says **Choose a Safari ✨**.
- The installed 3D wildlife catalog contains **23 exact species/variety selections**, each mapping to an actual bundled GLB file. The catalog includes five prior starter slots, **18 new original static 3D meshes** (fox, deer, mouse, bat, tortoise, wild rabbit, grey squirrel, European hedgehog, frog, Labrador, Ginger Tabby, robin, owl, peacock butterfly, honeybee, stag beetle, emperor dragonfly and black garden ant). The previously exaggerated Seven-spot Ladybird has also been replaced by a remodelled anatomical silhouette.
- Added a search field for the larger 3D Safari catalog, and changed the 3D Safari chooser card to focus the choices instead of always launching the ladybird.
- Petting carries forward **tap + single-finger stroke on the projected animal** from v3.10.33. Visible green feedback, haptic feedback on compatible devices, bounce, sway and a subtle continuous idle movement are in the source. Two-finger animal zoom and move/photo controls remain.
- Fixed native selection default for cat models; they now load under `Cat` rather than the old `Snail` fallback.
- Bundled the new assets offline; no extra download at run time. Combined identical-colour geometry in each generated GLB to reduce OpenGL ES2 draw calls.
- No changes to Android application ID `uk.whiskerhunt.mobile`, existing saved collection schema, backup key, photos or persisted collection.

## Accurate limitations

- New models are **originally generated, low-poly, colour-material meshes**, rather than scanned, photogrammetric or photo-realistic models. Anatomy and silhouettes are more distinguishable but still stylised; no photorealistic texture maps or animal-specific bone rigging are included.
- Petting is a **touchscreen gesture**, not physical-hand tracking. The real-world hand does not physically occlude or deform the model; correct hand-over-animal layering will require a camera/ARCore Depth segmentation and occlusion integration.
- Idle and pet motions are whole-model transforms, **not wing flapping, walking or eye/blink skeletal animation**.
- The 2D Safari is not a native ARCore scene; its camera-overlay behavior is preserved.
- Source validations confirm GLB header, meshes, skin-free geometry, supported index types, catalog keys and matching assets. `node --check` passes. **No installed .NET Android SDK and no real-device ARCore validation** in the available environment, so compiled APK not produced; device testing is required.

## Deploy without losing collected animals

1. Export a Collection backup from your existing Hush Hunt installation.
2. Open `WhiskerHunt.sln` or `WhiskerHunt/WhiskerHunt.csproj` in Visual Studio with the .NET MAUI Android workload.
3. Build and install over the existing app, using the **same signing key**. Do not uninstall or clear app data.
4. Open AR Safari > 3D Safari > choose a new model. Place it on a tracked surface. Tap/stroke it on the **phone screen**: green pet reaction + soft motion, and try animal +/- and photo.
5. Switch to 2D Safari to confirm the screen heading is correctly labelled.

For users with **additional GLB imports** outside the 23 bundled selections, keep a backup of the custom `Resources/Raw/ar_models/` folder. A full source-folder replacement can overwrite your custom `installed_species.json`; use the included patch additively and merge extra JSON entries as needed.
