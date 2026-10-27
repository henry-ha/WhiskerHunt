# Hush Hunt v3.10.36 Build 99 — Filament / ARCore Environmental HDR integration (source preview)

This is an **Android source integration**, not a precompiled APK or a device-validated release. It keeps the original app package ID and Android version code. Do not uninstall your current Hush Hunt app; preserve your wildlife collection.

## What has changed

1. `WhiskerHunt.csproj` includes official Google Filament Android and gltfio dependencies (v1.78.1). Restore needs internet access. A native Java Filament renderer lives under `Platforms/Android/Java/com/hushhunt/filament/HushFilamentOverlay.java`; a small JNI bridge lives in `HushFilamentBridge.cs`.
2. `HushArCoreActivity.cs` retains the existing ARCore session, camera preview, plane placement, photo and pet controls. It passes each tracked camera pose, projection, anchored model position and selected scale into Filament.
3. ARCore Environmental HDR is requested. When a compatible device supplies a valid light estimate, the scene uses its dominant-light direction/intensity and ambient spherical-harmonic coefficients. Otherwise, neutral lighting remains. This is a **diffuse-light first pass**, not full ARCore environment-cubemap reflections.
4. Google Filament gltfio loads the original `.glb` with PBR materials, textures, nodes and existing glTF skeletal/morph animations when present. It does *not* create walking, eye movement, ear twitching or fur details absent from an asset.
5. A transparent Filament layer sits above ARCore's camera rendering. The legacy OpenGL GLB renderer stays available as a fallback if Filament cannot initialise; the soft-ground shadow remains for old models, while the new `HushFloorShadow.cs` draws an ARCore-anchored contact shadow under HD models unsupported by the old parser. Photo capture uses a window-level GPU copy when the Filament overlay is active (which may include visible controls and needs handset testing).
6. `tools/upgrade_realistic_wildlife.py` keeps a source GLB unchanged after verifying its license, exact intended species and mobile-friendly size/mesh limits. It backs up a previous GLB before a successful replacement; no existing animal is replaced when download or validation fails.

## Install and test in Visual Studio on Windows

1. Unzip the **full source** to a new working folder. Open `WhiskerHunt.sln` with Visual Studio and .NET 10 MAUI Android tools.
2. Restore NuGet/Maven dependencies on the computer while connected to the internet. For the first Filament build, run **Clean Solution** and **Rebuild Solution** rather than mixing stale Android build outputs.
3. Deploy to your OnePlus 11 using the same application ID and signing key. Do not uninstall: saved collections are stored on device.
4. AR Safari > select an installed GLB > scan a tracked floor and place the animal. Check the scene, scale and exposure under bright and dim light. Check that tapping the animal, the petting text, capture photo, moving and pinch-scale still work. If Filament fails, check Android Logcat for `HushFilament` and confirm the old fallback renderer appears for legacy GLBs.
5. For higher-detail models, run `INSTALL_REALISTIC_WILDLIFE.bat` on an internet-connected Windows computer. **Only exact licensed matches will install**. Some matches can remain unavailable; this is intentionally not a fabricated bundled HD collection. Alternatively place a verified, licensed GLB using:

   `py tools\upgrade_realistic_wildlife.py --local deer C:\path\red-deer.glb`

   Supported keys: `deer`, `labrador`, `ginger-tabby`, `grey-squirrel`. Verify your file's distribution rights. Rebuild/deploy after the installer reports INSTALLED.
6. Verify Filament and model quality on the device; turn to low-poly fallback or restore backups with `py tools\upgrade_realistic_wildlife.py --restore deer` for any incompatible asset.

## Honest status / limitations

- The environment that produced this ZIP has **no .NET Android/MAUI SDK or Android emulator**. Java sources, project structure, GLB installer syntax and archive consistency were inspected, but no Visual Studio compilation, APK signing, ARCore Environmental HDR reading or GPU compositing could be tested here. Treat it as a provisional integration branch; Java interop or AAR dependencies might still need device-specific corrections.
- The **original 23 low-poly animals** are bundled in this ZIP. It includes *no newly licensed external HD meshes*: Filament cannot make the old low-poly geometry photorealistic. Install verified third-party HD assets separately.
- Real shadows **on the actual camera floor**, contact occlusion and realistic limb movement require further AR depth / shadow receiver meshes / glTF animation authoring, respectively. This integration retains a soft ground-shadow pass for both old and HD models but is not full real-world occlusion.
- Some advanced glTF compression extensions (Draco / meshopt) are deliberately rejected by the installer until their decoder compatibility is established. External texture links must be embedded in GLB.
- For Filament overlays, PixelCopy photo framing can include the on-screen controls; verify in tests before release.

## Files of interest

- `WhiskerHunt/Platforms/Android/Java/com/hushhunt/filament/HushFilamentOverlay.java`
- `WhiskerHunt/Platforms/Android/HushFilamentBridge.cs`
- `WhiskerHunt/Platforms/Android/HushArCoreActivity.cs`
- `WhiskerHunt/Platforms/Android/HushGlbAnimal3D.cs`
- `WhiskerHunt/Platforms/Android/HushFloorShadow.cs`
- `WhiskerHunt/WhiskerHunt.csproj`
- `tools/upgrade_realistic_wildlife.py`
- `INSTALL_REALISTIC_WILDLIFE.bat`

Filament upstream: https://github.com/google/filament — ARCore HDR: https://developers.google.com/ar/develop/java/lighting-estimation/developer-guide
