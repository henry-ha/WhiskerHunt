# Hush Hunt v3.9.5 · test results

## Passed
- `tests/test_v59_release.py` — versioned app entrypoint; native/JS/Android artwork path agreement; 146 Android/browser artwork assets with matching bytes; correct app ID; ARCore selection enabled in a browser smoke test.
- `tests/test_v59_live_only_compat.py` — live-camera-only real wildlife captures; legacy collection and backup compatibility; snail and dog saving; no gallery bypass.
- `tests/test_v59_preferences_safari.py` — imperial/metric settings, remembered opt-in map preferences, 2D Safari wildlife tools and labels, collection preservation.
- `tests/test_v59_species_dice_burst.py` — 17 wildlife groups, species-appropriate name and memory suggestions, 12-frame buffer, five-frame chooser and private backup behaviour.
- `node --check` on both versioned browser and bundled Android JavaScript runtimes.

## Not verified
- Android APK compilation: .NET/Android SDK not available in this environment.
- Real device ARCore launch, surface tracking, Collect/PixelCopy capture and launcher icon: require deployment on a supported Android phone.
- Scientific/photographic likeness of every illustrated variety: art is educationally inspired and intentionally stylised, not an identification system.
