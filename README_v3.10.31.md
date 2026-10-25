# Hush Hunt v3.10.31 — build 94

## Installation
Open `WhiskerHunt.sln` in Visual Studio 2022 with the compatible .NET 10 Android MAUI workload, select your attached Android phone, and build/deploy. **Install over the currently installed Hush Hunt app. Do not uninstall or clear app data** or you could lose locally saved collection items/photos. Export a full collection backup first as a precaution.

This download is **source code, not an APK**. The .NET Android SDK and OnePlus 11 were not available in the generation environment, so Android compilation and real-device ARCore/Camera2 validation could not be completed.

## New
- Child-friendly AR instructions; compact controls with 2D Safari, camera, Place/Move and ± animal-size adjustment plus pinch-to-resize.
- Live Capture has a coral shutter, mint ring, flash symbol, and a larger unclipped button holder above the nav bar. The momentary screen flash animation still works when tapped.
- 2D Safari red close is aligned right; virtual creature images/names and capture ring stay away from the bottom instructions, including on smaller screens.

## Compatibility
- Android ApplicationId `uk.whiskerhunt.mobile` retained.
- Existing JSON save/backup schema and animal/photo collection storage retained.
- Existing five textured ARCore GLB models retained.

See `RELEASE_NOTES_v3.10.31.md` and `tests/verify_v94.py`.
