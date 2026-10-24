# Hush Hunt v3.9.8 verification

## Checks passed
- `node --check` for Android and browser `app_v61.js`.
- `tests/test_v61_art_refresh.py`: 146 matching updated WEBP images in new `field_art_v61` folders; native bridge, AR activity and JS URL validation agree; app ID and state storage unchanged.
- `tests/test_v61_release.py`: source checks and Playwright AR Safari launch UI.
- `tests/test_v61_species_dice_burst.py`: species names/memories, burst chooser, backups and collection compatibility.
- `tests/test_v61_preferences_safari.py`: map unit preferences/consent and species-specific capture tools.
- Release ZIP integrity validation.

## Not verified
- Android build/deployment (the .NET Android SDK isn't installed here).
- WebView rendering or cache behaviour on the user's physical OnePlus.

The fix changes asset paths and the launcher entry HTML; it doesn't modify stored collection schema, image data, or native ARCore plane detection.
