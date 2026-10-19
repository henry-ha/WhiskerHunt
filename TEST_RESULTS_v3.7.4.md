# Whisker Hunt v3.7.4 test results

## Passed
- JavaScript syntax (`node --check BrowserPreview/app.js`).
- `python3 tests/test_v43_map.py`: existing cat preserved, private map pin visible and labelled, 56px marker, selection without third-party requests, nearby/duplicate pin placement, app-owned privacy consent, consent cancellation without sending coordinates, simulated native external map URL handoff, reporting no-browser errors, no CatDex data mutation.
- `python3 tests/test_browser.py`: existing browser CatDex, catches, edits, journal, backup/restore smoke test.
- Versioned WebView assets and Android project metadata consistent with version **3.7.4 / 43**.

## Not tested / limitations
- This environment lacks the .NET Android SDK, so there is **no compiled APK** or Windows Visual Studio build.
- Actual Android `ACTION_VIEW` behaviour on a OnePlus/Android 16 device remains to be tested.
- The private in-app plot is **not a street map**. Detailed street tiles are opened in an external browser only with consent.
