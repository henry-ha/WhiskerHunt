# Hush Hunt v3.10.24 — build 87

## Theme and Home fixes
- Replaced the previous theme pack with 20 new clean wildlife landscape compositions, without baked-in bands, borders or labels.
- Bundled matching portrait wallpapers (1080 × 1920 exported pixels), per-theme previews and 40 full-width scene images for Live Capture and AR Safari cards.
- Updated the active theme registry to `themes_v87`, `theme_previews_v87`, and `button_scenes_v87`.
- Added v87-specific Home layout overrides: explicit image cover/cropping rules, image spans the full card width, no dark side strips, button shadows overlaid rather than separate vertical panels, Home sized to phone viewport.
- Rotating themes and Static selection still use the existing storage keys with a new v87 namespace and a v82 migration fallback.
- Bumped service worker shell cache, Android WebView entry point and MAUI app version to 3.10.24 / 87.

## Live 0.6× capture
- Replaced legacy Camera1 rear-lens enumeration with a Camera2 capture activity that checks `CameraCharacteristics.ControlZoomRatioRange` on logical rear cameras (Android 11+).
- If a rear Camera2 zoom range covers 0.6×, preview and JPEG capture explicitly request `CaptureRequest.ControlZoomRatio=0.6f`.
- Does not offer simulated 0.6× if the phone does not expose it, and no longer routes to an external camera.
- Uses supported JPEG output dimensions and returns a photo to the existing species-selection flow with a 2048px limit instead of 1280px.
- Still entirely contingent on OnePlus/OEM camera access; Android build and device tests are pending.

## Important quality limitation
- These are **new original scenic compositions** exported at phone-resolution, NOT source-native 4K photographs or 4K renders. The original image generation produced smaller source tiles. Pixel upscaling is not presented as restoring 4K detail.
- For genuine 4K detail at 2160 × 3840 per wallpaper, each theme needs a new full-resolution individual master image.

## Compatibility
- MAUI application ID unchanged. Collection storage serialization and app-state schema unchanged. Deploy over existing app; do not uninstall.
