# Whisker Hunt v2.9 test results

Passed locally in browser simulation:

- `tests/test_v29.py`: automatic AR cat spawn; no manual scene tapping; optional model selection; generated virtual-cat PNG; virtual save; existing real cat and XP preserved; separate Virtual Friends gallery; v2.9 asset and app metadata.
- `tests/test_v29_camera.py`: live MediaStream from simulated camera; automatic cat visible; no continuous background JPEG frame capture while AR Safari is active; camera track stops after catch.
- `tests/test_browser.py`: existing browser smoke tests covering real-cat capture/save, quest features, collection, journal, reunions, backup merge, input validation.
- `tests/test_v19_subject.py`: existing focus-aware photo-quality selection (when run).

Not verified:

- APK compilation (no .NET MAUI Android build tools available).
- Performance on a physical Android device.
- Actual native ARCore surface detection/anchor placement (not implemented in this release).
