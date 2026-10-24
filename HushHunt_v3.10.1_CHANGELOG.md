# Hush Hunt v3.10.1 · Android build 64

- Two **direct home-screen actions**: Live Capture opens real-wildlife camera without the chooser; AR Safari opens the existing ARCore/2D mode chooser directly.
- **Faster first preview**: live encounter UI paints immediately from the first actual camera frame, without waiting for offline photo quality analysis. Existing capture game and photo ranking remain available.
- **Quick photo** button on the live stage snapshots the current camera immediately, then uses the existing live-only provenance and save form. No external camera/gallery bypass.
- **Zoom out**: full-frame `object-fit: contain`; prefer a named ultrawide camera when offered by Android WebView; native zoom-out to 0.5 if track supports it. 0.5x/1x/2x controls are only shown where supported, never simulated by CSS.
- Camera stops on modal close/background; zoom switching keeps the old camera preview until the requested replacement opens. No new storage or backup fields.
- Existing app ID `uk.whiskerhunt.mobile`, private cat and wildlife photos, locations, XP and backup format unchanged. Do not uninstall app before updating.

**Limits:** Physical ultrawide camera exposure depends on Android WebView's camera device list. If the WebView does not expose the 0.5x sensor, only supported controls display. ARCore remains separate from the live camera. Android build/real camera require Visual Studio + supported device.
