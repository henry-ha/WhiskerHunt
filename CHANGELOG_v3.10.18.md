# Hush Hunt v3.10.18 · Build 81

- **Fixed missing home background**: an older `!important` CSS shorthand overrode the selected theme. The home scene now has a full-bleed image layer and a higher-priority fallback background; theme scenes and action card artwork use the same selected theme.
- **Fixed misleading 0.6× UI**: previous code assumed an ultrawide camera whenever multiple cameras existed (or on a OnePlus UA). 0.6× now only changes the in-app view when WebView exposes an explicit ultrawide device or hardware zoom below 1×.
- **Native camera fallback**: where the WebView does not expose ultrawide video, tap `0.6× ↗` and select `Open phone camera`, choose 0.6× in the phone camera, and return the photo to Hush Hunt. No digitally shrunk 1× image is presented as a wide photo.
- Saved collection schema and package ID are unchanged.
- Android startup now loads `index_v81.html`, `app_v81.js` and `style_v81.css`.

Note: true seamless 0.6× in the WebView still depends on the device's actual camera exposure to WebView. The fallback needs manual lens selection in the Android camera app. This is source code, not a compiled APK.
