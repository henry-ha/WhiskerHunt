# Whisker Hunt v2.7 test results

Passed in this run:
- `tests/test_v27.py`: Android asset paths/version, thumbnail selection, selected-photo CatDex save, no temporary shot carry-over.
- `tests/test_browser.py`: browser CatDex smoke test including creation, reunions, journal and backup safety.
- `tests/test_v19_subject.py`: focus-aware photo ranking and cancellation safety.
- `node --check BrowserPreview/app.js`: syntax validation.

Legacy test limitations:
- `tests/test_v26_native_photo.py` expects Android package version 2.6.0, so that exact version assertion no longer applies to v2.7.
- `tests/test_v22.py` references an older capture visual element and is not a valid current-UI test.
- `tests/test_v18_live.py` was not verified; its timed browser execution did not complete here. The live camera remains unverified on Android hardware.

Android APK: not compiled. Physical camera, touch and gallery behaviour must be checked on a connected Android device in Visual Studio.
