# Hush Hunt v3.10.31 · build 94

## Added
- Legal CC0 3D asset sourcing and exact species mapping for 22 candidates from 3DAssets.dev packs.
- Offline source importer/normalizer that translates glTF quantized/WebP GLBs into this native renderer's supported GLB variant using Trimesh/Pillow, with validation and explicit failure handling.
- Dynamic ARCore picker generated from verified installed GLB files, never from an invented count of remote models.
- Added scrollable animal picker for more than five options and adjusted native AR object size presets for larger wildlife families.
- Windows one-click `INSTALL_CC0_WILDLIFE.bat` helper.

## Not yet complete
- 22 candidates are NOT bundled animal models. Five existing GLBs are included. The importer needs to run on an internet-enabled Windows development machine, and not every candidate may be available or pass quality checks.
- Professional photo scans and 239 accurate species variants require real licensed assets. The existing shader isn't yet a physically based glTF renderer and animations aren't supported.

## Verified in current environment
- 5 bundled GLBs pass static format checks.
- One bundled GLB successfully round-trip normalized via Trimesh and passed the native validator.
- AR picker changes to 6 when a compatible 6th GLB is installed, and goes back to 5 when removed.
- `node --check` succeeds on app_v94.js; Python importer compiles, XML references inspected.
- ZIP file integrity verified.
- No .NET MAUI Android build or device tests (SDK not installed here).
