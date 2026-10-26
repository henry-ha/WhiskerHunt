# Hush Hunt v3.10.36 · Build 99 — Verified Repack

This release fixes the app-entry mismatch discovered in the earlier v3.10.35/Build 98 source delivery.

## Fixes compared with the previous package
- The Android WebView now opens `index_v99.html` (instead of stale `index_v97.html`).
- Legacy default profile names now display as **Wildlife Explorer** when loaded from Android saved state.
- Version numbers match across `MainPage.xaml`, `WhiskerHunt.csproj`, `index_v99.html` and `app_v99.js`.
- Uses prior v3.10.35 model, Safari worm artwork, profile label, shutter and Ginger Tabby patches, which were inadvertently bypassed by the old entry point.
- Includes an actual `WhiskerHunt.sln` for Visual Studio along with the `.csproj`.
- Removed old duplicate JS/CSS/html bundles and unused legacy artwork directories, reducing download size. The current active v99 app assets remain included: all 23 packaged GLB wildlife files, current Safari cutouts, field guide, themes and UI scene art.
- Preserves Android ApplicationId `uk.whiskerhunt.mobile`, local collection filename and backup schema. Deploy over the existing app, with the same signing certificate, to preserve data; export backup beforehand.

## Validation and limitations
- JS syntax, active HTML/resource links and packaged wildlife model manifest were validated.
- ZIP integrity is checked for every deliverable.
- Android .NET SDK isn't available in this environment; this is updated source, **not a compiled APK**, and device-level AR/shutter testing remains necessary.
- Native animals are still stylised meshes, not photo-real fur renders or full skeletal animation.

## GitHub upload
Unzip the full source to your GitHub repository root (so `WhiskerHunt/WhiskerHunt.csproj` and `.github/workflows/hush-hunt-apk.yml` exist in the expected paths) and commit the changes. GitHub build errors require inspecting the actual failed step logs, not only the deprecation warnings.
