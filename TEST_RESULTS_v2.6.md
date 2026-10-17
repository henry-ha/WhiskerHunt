# Whisker Hunt v2.6.0 test results

Executed successfully in this run:

- **PASS** `tests/test_v26_native_photo.py`: request-token native picker bridge, stale camera result after modal close, out-of-order camera/gallery results, cancellation and late success, error and late success, switch to live, photo preparation, unchanged CatDex DB and backup version.
- **PASS** `tests/test_v26_ui.py`: Android version 2.6.0/code 26, versioned WebView entrypoint, live fallback chooser, late `getUserMedia` result, SVG cat paw, visible build marker and floating Meow effect.
- **PASS** `tests/test_browser.py`: cat collection, sightings, journal, reunion, safe merge, ID validation and backup smoke test.
- **PASS** `tests/test_v19_subject.py`: focus-aware best-frame selection, refocus and cancelled-camera guard.

Not verified:

- Android .NET MAUI compilation or physical-device camera behaviour: `dotnet` / Android SDK unavailable.
- `tests/test_v26_storage.py`: real IndexedDB reload test could not run because this execution environment blocks localhost and file-page navigation (`ERR_BLOCKED_BY_ADMINISTRATOR`).
- `tests/test_v22.py`: historical test references an element removed by the v2.5 paw redesign; fails with a missing-element DOM error. The current v2.6 UI test passes.

No database migration or CatDex deletion was performed.
