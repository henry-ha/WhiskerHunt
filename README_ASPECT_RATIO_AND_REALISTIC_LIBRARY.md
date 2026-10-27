# Hush Hunt — Live Capture aspect-ratio repair + 23-slot realistic wildlife importer

**Based on v3.10.36, build 99.** Keep your app package ID, signing key, and installed data.

## Live Capture

- The old native Camera2 `SurfaceView` filled the entire screen regardless of its camera buffer ratio. That can distort faces, furniture and wildlife vertically, even at 1×.
- This source selects an actual supported Camera2 preview buffer, sets the `SurfaceHolder` buffer size, and lays the preview out using **uniform scale to fill, centred and cropped**. The sensor output is never stretched independently in X/Y.
- It retains the current 0.6×/1×/2×/3× buttons, capture, shutter icon and previous UI fixes. The photograph is still captured by the independent JPEG stream.
- On devices with a preview ratio different from the screen, the edges will crop. Cropping is normal; stretching is not.
- Preview geometry is logged as `HushCamera` for verification. Try showing a round object at 1×; it should remain circular.

## Realistic animal sourcing

Your full current native AR pack has **23 named 3D model files**, not one high-detail model for every animal in the 2D field guide. The included GLBs still remain the existing low-detail originals in this ZIP. This package **does not claim** to bundle 23 realistic replacements.

- `INSTALL_REALISTIC_WILDLIFE.bat` now checks all 23 available AR model slots, instead of four.
- Exact species and CC0 licence checks protect against a red squirrel pretending to be a grey squirrel or a fox pretending to be a Ginger Tabby.
- Filament compatibility: embedded WebP texture images are converted to embedded PNG, while mesh geometry, PBR material bindings, skins and animation data are retained.
- An image-texture quality gate rejects completely flat, material-only models. Triangle count alone does not prove realism. Every accepted animal must still be visually inspected before release.
- Each replaced model has a backup in `RealisticAssetBackups` and provenance in `realistic_asset_provenance.json`. Previously installed HD Deer and Labrador files are **not included in the patch**, so applying the patch will not erase your local upgrades.

### Windows instructions

1. Unzip the **small patch** into the root of the existing `WhiskerHunt` Visual Studio solution. Overwrite matching files; don't overwrite `Resources/Raw/ar_models` with older models.
2. Use Visual Studio: **Clean Solution → Rebuild Solution**. Deploy to OnePlus 11, keeping existing installation.
3. Check the camera preview using a circular object at 1× and 2×.
4. For realistic animal sourcing, from the project root run `INSTALL_REALISTIC_WILDLIFE.bat` on an internet-connected PC. The installer uses the 3DAssets.dev CC0 catalogue and installs exact verified matches only.
5. Run `py tools\audit_wildlife_library.py` and inspect the created `wildlife_quality_audit.json` to see which species are textured and which are still placeholders.
6. Rebuild and test every installed animal in AR Safari. Roll back any mismatched asset using `py tools\upgrade_realistic_wildlife.py --restore animal-key` (see `--list` for keys).

### Source selection

- **Poly Haven** (<https://polyhaven.com/>) is reputable, genuinely curated, and CC0, but does not cover each animal species.
- **Sketchfab** (<https://sketchfab.com/>) offers community comments and appreciation counts but licenses differ and authenticated download is generally required; do **not** automatically copy model files into a redistribution-ready app without validating the precise licence and attribution.
- **3DAssets.dev** (<https://3dassets.dev/assets?category=animals&style=realistic>) provides machine-readable CC0 and direct GLBs suitable for an automatic importer. Its catalogue can include AI-created models: inspect their anatomy and coats; catalogue metadata is **not** verified user review quality.

### Limitations

- The authoring environment cannot download the external CDN model bytes or compile an Android APK, so a fully replaced, tested realistic collection cannot be certified here. Existing GLB files in this source remain placeholders until your importer successfully replaces them.
- Static GLBs have no skeletal walk/pet animations. Filament lighting does not invent eyes, ears, legs, whiskers or fur textures.
- Surface sizing is grounded in Android Camera2 documentation but needs a device test on the OnePlus 11. If preview fails, filter Logcat by `HushCamera` and attach it with the Visual Studio Error List.
