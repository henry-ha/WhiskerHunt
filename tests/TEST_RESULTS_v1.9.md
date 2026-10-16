# Whisker Hunt v1.9 test results

Tested with headless Chromium + Playwright in this environment.

- PASS `tests/test_v19_subject.py`: focus-aware ranking vs misleading background, moving focus changes selected still, stale asynchronous selection cannot overwrite photo after camera stop.
- PASS `tests/test_v18_live.py`: simulated real MediaStream, rolling frame buffer, lure + pod drag, best-frame freeze, CatDex save, retake and camera fallback.
- PASS `tests/test_browser.py`: new cat, repeat sighting, CatDex edit, journal, backups, XP, duplicate rejection.
- PASS `tests/test_v16.py`: drag aim guide, minimum movement, miss, lure, pod and saved XP.
- PASS `tests/test_v17.py`: right-side floating tools and Whisker Pod encounter.
- PASS `tests/test_v15.py`: photo quality, retake cancellation and photo replacement.
- PASS `tests/test_v14.py`: portrait/landscape target mapping and resize.
- PASS `node --check BrowserPreview/app.js`: JavaScript syntax.

The complete suite was not run to completion; some parallel browser runs timed out. Real Android camera and WebView permissions are **not** verified. No Android APK was compiled.
