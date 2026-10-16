# Whisker Hunt v2.5 regression results

Executed in this run:

- **PASS** `tests/test_v25.py`: packaged Android v2.5 entrypoint and version metadata, versioned assets, live fallback with delayed camera resolution, native picker cancellation state, visual SVG paw, circular controls, visible build marker, capture flourish and no JS errors.
- **PASS** `tests/test_browser.py`: CatDex save/edit/reunion/quest/journal/backups smoke tests.
- **PASS** `tests/test_v19_subject.py`: focus-aware photo selection regression test.

Not verified:

- Android .NET MAUI compilation and installation (SDK unavailable).
- Device-specific camera cancellation and service-worker retirement on the actual phone.
- Historical v1.8 timing test (timing assumptions are not applicable to the current reduced-rate live sampling loop).
