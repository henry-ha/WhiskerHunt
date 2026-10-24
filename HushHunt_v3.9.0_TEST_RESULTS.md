# Hush Hunt v3.9.0 · Test results

**PASS:** `tests/test_v54_art_icon_arcore.py` — 128 distinct subtype images; matching offline Android/browser assets; approved launcher icon; Android manifest and existing package ID; Safari ARCore button enabled; browser-only explanatory fallback; versioned assets and Visual Studio solution.

**PASS:** `tests/test_v54_species_dice_burst.py` — all 17 animal groups have appropriate name/memory dice; recent frame buffer and five-shot chooser; only chosen shot saved; old collection data unaffected.

**PASS:** `tests/test_v54_live_only_compat.py` — new real-world discoveries remain live-camera-only; gallery/normal-camera imports do not create new catches; snail and dog savings and older backup compatibility.

**PASS reported by the test before test-runner hang:** `tests/test_v54_preferences_safari.py` — unit settings, remembered street-map consent, species tools and existing data. Playwright/Chromium process did not exit cleanly after printing the passing summary; this test should be considered a successful assertion run with incomplete process cleanup.

**PASS:** `tests/test_v54_arcore_compiler_hotfix.py` — static check of known ARCore type ambiguity fixes, bridge and resources. This is not an Android compile.

**PASS:** `node --check` on current JavaScript source. All images decoded and checked at 240 × 240; all 128 varieties had unique file hashes; native/browser resource parity verified.

**NOT VERIFIED:** Compiling the native Android APK, launching native ARCore on a physical OnePlus 11, real-world plane detection/anchor stability, launcher presentation on Android. Android dependencies could not be restored or built in this environment because the .NET Android SDK is unavailable.
