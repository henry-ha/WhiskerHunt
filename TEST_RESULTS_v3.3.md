# Whisker Hunt v3.3 test report

**Passed** `python3 tests/test_v35.py`: checks consistent version 3.3.0/build 35 references, matching Android/browser assets, alternative-only tool selector in both directions, tool animation class, claw SVG, simplified AR HUD, native recovery routing, simulated read-only snapshot preview, decline-to-merge (no changes), confirm-to-merge (preserved XP), and no browser exceptions.

**Passed** `python3 tests/test_browser.py`: normal capture, editing, repeat sightings, export/restore, journal, safe merge and ID validation.

**Passed** `node --check BrowserPreview/app_v35.js`: JavaScript syntax.

**Source check:** The recovery wizard export path avoids calling the native save/rotation function; the Android entry point references versioned v35 files and the same application ID.

**Not tested:** Android APK compilation or on-device native backup inspection/restore, physical camera latency, Android sharing and permissions. No Android SDK/.NET compiler was available in this environment.
