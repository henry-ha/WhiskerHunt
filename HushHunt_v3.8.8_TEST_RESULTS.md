# Hush Hunt v3.8.8 test results

Environment: headless Chromium Playwright and static project checks. **No .NET SDK or Android emulator/physical device used.**

- **PASS** `test_v52_species_dice_burst.py`: builds 52, browser/Android resource parity, 17 animal name pools, species-aware name and memory dice for a live snail then butterfly, 12-frame rolling buffer / 260ms interval, five-shot review, no frame arrays in the backup.
- **PASS** `test_v52_preferences_safari.py`: persistent imperial/metric and online-map consent, Safari hedgehog/butterfly/cat tools and text, legacy collection retained.
- **PASS** `test_v52_live_only_compat.py`: live-only real sightings, gallery/normal-camera still restricted, snail/dog saving and prior backup restoration.
- **PASS** `test_v52_arcore_compiler_hotfix.py`: known ARCore source hotfix patterns, Android/WebView entry resources and stable storage identifiers.
- **PASS** `node --check` on bundled JavaScript, ZIP integrity check on deliverables.

Not verified: Android APK compilation, camera permission/stream operation on user's OnePlus, actual 260ms capture performance, ARCore tracking or external-map loading on device.
