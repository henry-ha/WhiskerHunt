# Hush Hunt v3.10.0 — Test results

Passed:
- JavaScript syntax checks for BrowserPreview and Android bundled app runtime.
- Playwright browser smoke: app boots, two Safari choices appear, and Safari images resolve to the transparent folder while Collection images continue to resolve to the original card folder.
- v63 branding/cutout integration test: 146 RGBA PNG cutouts in both Android and browser, identical bytes; cutouts contain transparent regions.
- v63 species dice / collection compatibility browser tests: 17 groups, live-only species captures, 12-frame sampling, five-shot review, species-specific dice, Collection labels and backup compatibility.
- Launcher and splash checks: approved bunny art in MAUI icon + all five Android density mipmaps, manifest references retained; approved art in OS splash and browser header.

Limitations:
- Android app wasn't compiled or tested on your OnePlus in this environment; ARCore plane tracking and camera capture require on-device confirmation.
- Wildlife alpha masks are generated automatically from illustrated cards; some tiny pale wings/fur details or paper remnants may need later individual polishing. They are genuine PNG alpha masks, not CSS square crops.
- The app package identifier and stored collection data format were not changed.
