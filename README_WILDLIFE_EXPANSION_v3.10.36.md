# Hush Hunt — realistic wildlife expansion (developer update)

**Base: v3.10.36 build 99.** This project preserves the package ID and all saved collection data; do **not** uninstall the Android app.

## Status of included GLB meshes

- The source ZIP has the **original 23 3D models**. There are **no newly downloaded HD GLBs inside this ZIP**. The creation environment could not obtain third-party binary model downloads.
- The update adds a tested importer and model-picker integration for **28 curated additional species**. They appear in the picker **only after successful installation and validation on the development PC**.
- Existing previously installed HD deer and Labrador models are preserved when applying the **patch ZIP**; the full ZIP contains baseline models and must not be extracted over an upgraded ar_models directory.
- The older 23 animal slots are also checked for exact-name CC0 replacements. If a better exact match cannot be verified or its GLB has no PBR colour texture, the old model remains unchanged. **No false claims of 51 photorealistic models.**
- Generated models and online catalogue ratings are not a substitute for examining geometry, anatomical accuracy and coats on device.

## One-click installation on Windows

1. **Back up** `WhiskerHunt/Resources/Raw/ar_models/` and your whole project directory.
2. Extract the **small patch** to the solution root (not the `WhiskerHunt` subfolder).
3. Run `INSTALL_HD_WILDLIFE_EXPANSION.bat` on your internet-connected development computer.
4. It queries CC0 metadata, validates/downloads GLBs, converts embedded WebP textures to PNG while preserving mesh/animation records, and backs up originals before replacement.
5. It rebuilds the in-app 3D Safari picker using files actually installed, then writes `realistic_asset_provenance.json`, `wildlife_extra_sources.json` and `wildlife_quality_audit.json`.
6. **Clean Solution → Rebuild Solution** in Visual Studio. Do **not** uninstall the existing Android app.
7. Test each added/modified animal at 1× in 3D Safari. Check face, ears, legs, fur, texture orientation, ground contact, shadows, size and photo capture. Reject/roll back any failures.

For a list of additional targets and individual local files:

```powershell
py tools\expand_realistic_wildlife.py --report
py tools\expand_realistic_wildlife.py --import-local african-lion C:\models\lion.glb --license CC0 --source https://original-creator.example/model
py tools\expand_realistic_wildlife.py --refresh-picker
py tools\upgrade_realistic_wildlife.py --restore deer
```

Manual imports must be properly licensed; CC BY imports need creator attribution wherever used. **Do not redistribute CGTrader / asset-store downloaded model files separately**; check each vendor licence. Sketchfab downloads need authentication and item-specific licence checks; this source has no bypass or scraping mechanism.

## Collections reviewed

- [3DAssets.dev Realistic Wild Animals HD](https://3dassets.dev/packs/exotic-wildlife-hd) — **CC0**, many animal candidates with PBR textures; static poses.
- [3DAssets.dev Pets and Companions HD](https://3dassets.dev/packs/pets-and-companions-hd) — **CC0**, domestic animals; static and varying coat accuracy.
- [3DAssets.dev Reptiles, Amphibians and Insects](https://3dassets.dev/packs/reptiles-amphibians-and-minibeasts) — **CC0**, smaller creatures, inspect visual realism.
- [Sketchfab](https://sketchfab.com/developers/download-api) — community reviews; downloads require login/API authentication. Model rights vary.
- [CGTrader licensing](https://help.cgtrader.com/hc/en-us/articles/360015124437-Royalty-Free-License) — permissible use in an incorporated application differs from redistributing raw assets.
- [Poly Haven](https://polyhaven.com/) — curated CC0 materials/HDRIs, limited matching wildlife.

## Diagnostics and limitations

- Python syntax checks, JS `node --check`, manifest reconciliation, repeated picker generation, and ZIP integrity were tested locally.
- **Not verified**: third-party GLB binary downloads, exactness/realism of all online candidates, .NET/Android compilation, ARCore Filament runtime on your OnePlus 11.
- The HD packs' source materials are not necessarily fur photogrammetry; many are AI-generated. Each asset should be judged visually rather than by triangle count.
- Additional species are AR-only entries at present. They are not automatically inserted into the full 2D real-life sighting field guide.
- Older 3D animals remain visible if no verified better asset exists. Building a truly photorealistic 23-species collection requires individual artistic review and potentially licensed high-end game assets.
