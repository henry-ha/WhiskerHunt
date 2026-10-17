# Whisker Hunt v3.0 test results

## Passed
- `python tests/test_v30.py`: versioned Android references and matching assets; 30 cat types; multi-photo add/delete/Done; name and memory dice; AR camera composite preview; virtual save; separate real and virtual records; backup and restore retaining virtual status/model; opt-in location unchecked, opt-in virtual location rounded to 0.01 degrees, GPS-free export stripping coordinates; profile backup buttons.
- `python tests/test_browser.py`: established real CatDex workflow, journals, repeat sightings, safe merge, photo signature validation, existing stats.
- `python tests/test_v29_camera.py`: live virtual encounter starts with automatic appearance, avoids background frame processing and stops camera after capture.
- `node --check BrowserPreview/app.js`: JavaScript syntax valid.

## Not verified
- Actual Android APK compilation and installation.
- Physical-device system-camera batching (each shot uses the native MediaPicker).
- Location permission prompts on the user's OnePlus 11.
- ARCore surface detection (not included).
