# v3.8.1 test report

## Passed (Playwright/Chromium browser simulations)

- `tests/test_v45_live_only.py`: confirms camera/gallery import options disappear, an unverified image cannot open a collectible form, a session-sourced still can save a snail and dog, late gallery replacement is rejected, old cat photograph survives, and existing v1 JSON backup restoration retains all three records.
- `tests/test_v45_virtual_compat.py`: verifies virtual AR Safari captures still save separately and do not become real FieldDex records.
- `tests/test_v45_map_compat.py`: verifies saved location pins, cat labels, explicit OpenStreetMap permission, external-link callback path, and no data mutation.
- `node --check BrowserPreview/app_v45.js`: JavaScript syntax passed.

## Not tested

- Physical-device live camera latency, camera permission behaviour and screenshot quality on Android.
- Native .NET MAUI APK compilation: .NET SDK not available in this execution environment.

Older gallery-import tests target intentionally removed behaviour and should not be treated as regressions for the live-only flow.
