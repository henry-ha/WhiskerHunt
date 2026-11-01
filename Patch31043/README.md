# Hush Hunt v3.10.43 — Wildlife Colour, Animation & Catalogue Repair

This is a **Windows source/asset installer**, not a compiled APK. Target: the *inner* `WhiskerHunt` folder containing `WhiskerHunt.csproj`, with **v3.10.42 / build 105 source patch already applied**. Keep the installed app on your phone to preserve local data. You can test changes after a Visual Studio Clean → Rebuild → Deploy.

## Concrete findings from your original 88 GLBs

- Original `Animated/Elephant.glb`: **zero embedded images**, one glTF material with `emissiveFactor=[1,1,1]`, `KHR_materials_specular.specularColorFactor=[2,2,2]`; that explains a glowing white appearance. It has one animation and must NOT be labelled a realistic textured model.
- A large subset of the other animals have extreme emission and/or overly high specular reflectivity, so changing the global AR lights will not uniformly fix their colour. The patch **normalises 52 GLB materials** (as validated on the original archive) while preserving embedded original texture images, vertex data, mesh geometry, rigs and animations.
- `Kangaroo Mouse` and `Kangaroo Mouse (Alternate)` in the original archive are byte-identical. Only the first is kept.
- The new **Lion** entry displays the former **Lion (Alternate)** animated GLB; the lower-quality original Lion entry is removed.
- The first app's Java animation loop deliberately slowed the only Meshy clip to **0.4×**, and refused to advance animation when the ARCore frame generation was unchanged. Both are addressed. The 41ms heavy-animal cadence also landed on ~20fps on 60Hz screens; the patch uses a common ~30fps target and adds stall diagnostics.

**Important:** This repair cannot invent a detailed elephant texture that was not exported with the original model. The elephant is now a non-glowing neutral grey with existing sculpted geometry. Creating a genuinely textured elephant requires a correctly textured source GLB. Overall frame rate on your OnePlus 11 is not verified here.

## Install steps

1. Extract this ZIP to:
   `E:\inetpub\wwwroot\WhiskerHunt\Patch31043`
2. Open **Windows PowerShell**.
3. Run the **read-only dry-run**:

```powershell
py "E:\inetpub\wwwroot\WhiskerHunt\Patch31043\apply_v31043.py" --project-root "E:\inetpub\wwwroot\WhiskerHunt\WhiskerHunt"
```

4. Only if it prints **DRY RUN SUCCESS**, close Visual Studio builds and apply:

```powershell
py "E:\inetpub\wwwroot\WhiskerHunt\Patch31043\apply_v31043.py" --project-root "E:\inetpub\wwwroot\WhiskerHunt\WhiskerHunt" --apply
```

5. **Backups:** The installer prints a dated folder next to the inner project, under `.hush_v31043_backup`. It preserves originals of changed source files, all changed GLBs, and the two removed duplicate GLBs. Budget about **1 GB of free disk space** for the backups.
6. In Visual Studio: **Build → Clean Solution → Rebuild Solution**, then deploy to your OnePlus 11.
7. Launch **3D Safari**, test the elephant, Lion, Ragdoll Cat, Corgi animation and several static animals. The model count should be **86** and the menu should show `Hush Hunt v3.10.43 · build 106`.

## Logs to diagnose remaining lag

In Visual Studio Logcat or Android Studio Logcat, filter `HushFilament` and `HushHuntAR`.

- `AR_OVERLAY_FPS=` tells how many 3D overlay frames reached the renderer in 5 seconds. Low FPS here while ARCore remains smooth implies Filament/GPU or model workload.
- `AR_OVERLAY_STALL_MS=` flags a renderer gap over 180ms.
- `ARCORE_UPDATE_STALL_MS=` flags `Session.Update()` taking over 90ms on the ARCore GL thread; this would affect even static animals.

If the still camera and static models continue to stutter, capture 20–30 seconds of these logs. Two composited GL renderers plus phone thermal throttling/driver synchronisation may require a larger renderer refactor; further tweaks to lighting or zoom won't solve that.

## Roll back

Use the **exact backup folder printed by the installer**:

```powershell
py "E:\inetpub\wwwroot\WhiskerHunt\Patch31043\restore_v31043.py" --project-root "E:\inetpub\wwwroot\WhiskerHunt\WhiskerHunt" --backup "<full printed backup folder>"
```

If the restore dry-run succeeds, add `--restore` to the command. Rollback refuses to overwrite modifications made after the patch. Then clean, rebuild and redeploy.

## Validation performed here

- Reconstructed a v3.10.42 project from the archived v3.10.38 project plus v3.10.39–42 update scripts.
- Extracted the actual 88 GLBs from your original three-part archive and ran dry-run, apply, repeat dry-run, rollback dry-run, full rollback, reapply.
- All 86 resulting files pass GLB 2.0 header/JSON length checks; the source and UI menus both report 86 animals; the elephant and Lion's uncompressed binary payloads (meshes, animation, textures) remain **byte-identical** to the originals.
- Checked source transformations and Python syntax; JavaScript syntax checked with Node.js.
- **Not performed:** Android build (SDK unavailable here), actual GPU profiling on your OnePlus, or a rendered 3D visual test. No APK is included.

## Included files

- `apply_v31043.py` — dry-run / apply installer. Python standard library only.
- `model_materials.py` — GLB material normaliser, no mesh or texture re-encoding.
- `restore_v31043.py` — safe backup restore.
- `elephant_matte_gray_repaired.glb` — repaired original elephant for external preview. Installer also repairs the elephant in the project, so manually copying this file is unnecessary.
