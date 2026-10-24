# Hush Hunt v3.10.1 · build 64 test results

- **PASS** JavaScript syntax (`node --check`) in MAUI and browser source.
- **PASS** Chromium/Playwright synthetic video-stream test (`tests/test_v64_direct_capture.py`): direct home buttons, one-tap camera launch, un-cropped `object-fit: contain` video, quick shutter through live provenance into unchanged species save form, AR Safari separate chooser, no new saved entries before confirmation.
- **PASS** Native and browser JavaScript/styles/service-worker assets parity; app ID and source package version checks.
- **PASS** Browser preview screenshot generated.
- **NOT RUN** Full .NET MAUI Android compile (no .NET Android SDK in this environment).
- **NOT VERIFIED** OnePlus 11 ultrawide lens enumeration/zoom availability, Android WebView startup time, native ARCore runtime and real sensor performance.

### Deployment
Open `WhiskerHunt.sln` in Visual Studio, restore NuGet, and deploy over `uk.whiskerhunt.mobile` without uninstalling or clearing storage. Keep a full backup before upgrading.
