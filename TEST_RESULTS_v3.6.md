# v3.6.0 test report

Passed:
- `node --check BrowserPreview/app_v38.js` — JavaScript syntax.
- `python3 tests/test_v38_gps_recovery.py` — simulated Android GPS no-fix error, retry, successful opt-in save, rounded coordinates in a virtual-cat sighting, visibility under **Saved locations (1)**, GPS-free backup removes coordinates, and stale GPS callbacks ignored.
- `python3 tests/test_browser.py` — existing CatDex browser smoke test (new/repeat cat, edits, journal, backups and safe merge).
- Checked versioned Android WebView assets and project metadata (v3.6.0, build 38).

Known limits:
- No Android SDK / .NET MAUI build tools available in this container; **APK not built**.
- Native permission and provider behaviour are not device-tested. The browser integration test simulates Android bridge callbacks and validates JavaScript saving, not Android's physical GPS services.
- `tests/test_v33_safety.py` is tied to an earlier, untagged native callback format and fails its static historical assertion; newer token-safe tests supersede that particular assertion.
