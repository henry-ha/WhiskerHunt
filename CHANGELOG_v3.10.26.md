# Hush Hunt v3.10.26 — Build 89

## Android Live Capture
- Android Home > Live Capture now starts a unified native Camera2 preview with 0.6×/1×/2×/3× controls already on-screen. Tapping 0.6× changes the active Camera2 repeating request; it no longer opens an intermediate confirmation dialog or another camera view. The WebView-based camera remains for browser use.
- When a genuine rear 0.6× ratio is unavailable to third-party apps, its native zoom button is disabled and the 1× rear view is retained. This release never digitally shrinks 1× while pretending it is ultrawide.
- Added pinch gestures to the native camera preview, alongside fixed zoom buttons.
- JPEG frames are normalized into physically upright portrait bitmap pixels before passing to the existing species/collection flow, addressing the 90° anticlockwise photo issue. Does not modify saved collection records.
- Camera cancellation returns to the prior screen without restarting a broken WebView video preview.

## ARCore
- Replaced generic fallback ellipsoid blobs for new recognized species families with procedural 3D anatomy for spiders (eight jointed legs), ants, beetles, ladybirds, bees, wasps, dragonflies, fish, lizards, tortoises and foxes.
- Unsupported categories no longer create a misleading generic model and offer 2D Safari instead.
- **Artwork limitation:** These remain stylized procedural 3D prototypes. This package does not contain photorealistic, textured or species-accurate 3D scans/GLB models. Genuine realistic 360° models require properly licensed production 3D art and integration into ARCore.

## Home
- Lowered the Settings and WILDLIFE EXPLORER top controls by 14 CSS pixels without moving the approved Home wallpapers or the primary launch cards.

## Retained
- ApplicationId uk.whiskerhunt.mobile; same local Collection schema and backups.
- Existing 20 high-quality wildlife Home themes and 2D Safari art untouched.

## Device testing still required
- There is no dotnet/Android workload in this execution environment. This is a source patch, **not a compiled or device-verified APK**.
- On OnePlus 11: open Live Capture, tap all zoom values in the same view, verify 0.6× shows more scene than 1×, verify photo orientation and collection capture, try back/cancel and reopen, then test ARCore Spider and other families.
