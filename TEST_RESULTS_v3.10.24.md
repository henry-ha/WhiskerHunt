# v3.10.24 release validation

- JavaScript syntax: `node --check` on both Android Raw and BrowserPreview app_v87.js
- Android entrypoint: MainPage.xaml Source="index_v87.html"
- HTML: both index_v87.html files reference app_v87.js and style_v87.css
- Themes: 20 new wallpapers, 20 preview images, 40 full-width button background images in both Android and browser bundles
- New source dimensions: 1080×1920 wallpaper export (not source-native 4K); 720×620 button image export
- Camera code: Camera2 zoom range + sub-1x capture path present, no Camera1 enumeration
- ZIP integrity and file fingerprints checked
- Android compile: NOT completed (Android MAUI .NET SDK unavailable)
- Device camera: NOT tested (OnePlus 11 access unavailable)
- Browser screenshot: blocked by navigation restrictions, so layout not verified on real WebView
