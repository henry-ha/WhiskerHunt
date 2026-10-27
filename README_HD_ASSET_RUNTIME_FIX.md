# Hush Hunt v3.10.36 Build 99 — HD loader + vector camera correction

**Do not overwrite your installed HD Deer/Labrador assets.** The recommended SMALL PATCH has no files in `Resources/Raw/ar_models/` and does not undo the two models already downloaded by `INSTALL_REALISTIC_WILDLIFE.bat`.

## What actually failed

- `InvalidDataException` was being raised by the old static OpenGL GLB parser. The new HD models include glTF features (such as quantised attributes and PBR textures) that this older parser cannot handle.
- Before this fix, if the Filament Java bridge was not installed and the old parser rejected the model, AR Safari immediately showed **3D wildlife not ready**.
- This package includes separate lightweight backup meshes for Deer and Labrador at `ar_fallback/` so the old renderer can show something without changing the original downloaded HD GLBs.
- Filament still receives the primary HD model (`ar_models/`). If it initializes, the app switches to HD materials and shows `HD / Filament ready` in the Safari header. If it cannot initialize, the standard preview remains; look for `HushFilament` in Visual Studio Android Logcat. This is a fallback, not a claim that the HD renderer works on every phone.

## Camera icon

- Replaced the old Android system bitmap camera glyph (which was blurry at 46dp) with `Platforms/Android/Resources/drawable/hush_camera_vector.xml`.
- The fixed white shutter circle stays the same size. The vector has crisp edges at any phone density.

## Patch installation (recommended)

1. Make a backup of your project and your `WhiskerHunt/Resources/Raw/ar_models/` folder.
2. Extract `HushHunt_v3.10.36_Build99_HD_Load_Fix_PATCH.zip` into your existing project root (for example `E:\inetpub\wwwroot\WhiskerHunt\`). Let files with matching paths be replaced. Do **not** overwrite `ar_models/` if Windows asks; the patch intentionally contains none.
3. Run `py tools\check_installed_hd_assets.py` from the project root. Your previously installed Red Deer Stag and Labrador should still show >10,000 triangles and usually embedded textures. The Ginger Tabby and Grey Squirrel are still old placeholder GLBs unless you have separately installed better licensed models.
4. In Visual Studio, Clean, then Rebuild, and deploy to your phone under the **same application ID and signing key**. Do not uninstall Hush Hunt because your wildlife collection is stored locally.
5. Test Deer and Labrador again. If you see `HD / Filament ready`, that confirms the Filament overlay is active. If you see `standard graphics`, open Android Logcat, filter by `HushFilament`, and share the *first exception* (especially any `ClassNotFoundException`, `UnsatisfiedLinkError`, or graphics error). This distinguishes a JNI bridge problem from a GLB parsing issue.

## What is *not* included

- The source ZIP cannot include the new HD GLBs that were downloaded into your Windows `E:` folder, because they are not available in this sandbox. The full source ZIP contains the older original models as its primary assets. **Do not extract the full ZIP over your installed HD model folder without first backing those two GLBs up.**
- There is no new realistic Ginger Tabby or Grey Squirrel asset included, so their appearance will not materially change.
- A high triangle count by itself does not prove realistic fur, anatomy, or coat markings. Actual textures and model quality matter.
- No fully compiled/tested Android APK could be produced in this environment. The fix is source-only and should be tested on your OnePlus 11.

## Included changed files

- `WhiskerHunt/Platforms/Android/HushGlbAnimal3D.cs`
- `WhiskerHunt/Platforms/Android/HushArCoreActivity.cs`
- `WhiskerHunt/Platforms/Android/HushFilamentBridge.cs`
- `WhiskerHunt/Platforms/Android/HushWideCameraActivity.cs`
- `WhiskerHunt/Platforms/Android/Resources/drawable/hush_camera_vector.xml`
- `WhiskerHunt/Resources/Raw/ar_fallback/other-deer.glb`
- `WhiskerHunt/Resources/Raw/ar_fallback/dog-labrador.glb`
- `WhiskerHunt/WhiskerHunt.csproj`
- `tools/check_installed_hd_assets.py`
