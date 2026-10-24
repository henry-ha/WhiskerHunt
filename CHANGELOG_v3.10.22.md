# Hush Hunt v3.10.22 · build 85

- Home: shortened the layout to clear the fixed bottom navigation, reduced the giant action tiles, preserved wallpaper aspect ratio and removed scrolling on Home.
- ARCore: lifted the Place/Move/Capture tray 68 dp above Android's system navigation; top header now clears the status bar.
- ARCore: anchored and screen-locked animals are clamped inside the usable camera area.
- Safari art: rebuilt a full squirrel transparent sprite from the complete field-guide artwork, replacing the cropped-face squirrel; this is also used for the squirrel group fallback.
- All 148 Safari sprites are copied into versioned `safari_cutouts_v85` so stale WebView assets do not recur. Other original species silhouettes are not stretched; both 2D and native views use `FitCenter` / `object-fit: contain`.
- Rebased on v3.10.21 without touching native storage schema, app ID, collection records or backups.
- Source/tests only; native ARCore runtime requires physical-device verification.
