# Whisker Hunt v2.2 regression results

## Passed in Chromium / Playwright

- `tests/test_v22.py` — actual canvas MediaStream, preview quality work deferred, 520 px periodic vs 720 px release frame, sampling pause/resume while dragging, circular tool icons and paw silhouette, live retake, capture and still selection, CatDex save, backup format, and stale-catch guard.
- `tests/test_browser.py` — catch and collection smoke test.
- `tests/test_v19_subject.py` — cat-focus-aware frame selection and stale shutdown protection.
- `tests/test_v21.py` — live retake and paw controls.
- `tests/test_v16.py`, `test_v17.py`, `test_v15.py`, `test_v14.py`, `test_v13.py`, `test_v12.py`, `test_v11.py`, `test_v10.py` — previous capture, drag, storage and UX regressions.
- `tests/test_v05.py`, `test_v06.py`, `test_v07.py`, `test_v08.py`, `test_v09.py` — restore, privacy, XP, native storage and compatibility.

17 browser suites passed. Historical cache-version-only assertions were updated to match v2.2; their feature assertions were retained. `tests/test_v18_live.py` is obsolete because it expects the removed photo-picker retake flow; v2.2 has a live-retake test instead. `tests/test_v20.py` is obsolete because it checks old live-sampling constants.

## Blocked by environment

- `tests/test_real_storage.py`: `ERR_BLOCKED_BY_ADMINISTRATOR` navigating to local HTTP server.
- `tests/test_v06_real_indexeddb.py`: `ERR_BLOCKED_BY_ADMINISTRATOR` navigating to `https://whisker.test/`.

## Not tested

- .NET MAUI Android compilation (no `dotnet` SDK available in the runtime).
- Physical Android camera frame rate and touch latency; improvements are code-level optimisations, not a measured device benchmark.
