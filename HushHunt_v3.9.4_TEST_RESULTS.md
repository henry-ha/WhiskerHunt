# Hush Hunt v3.9.4 test report

## PASS — checks executed here
- `node --check` on the v58 Android and browser JavaScript.
- `tests/test_v58_art_arcore_release.py`: 146 Android/browser artwork assets matched, icon/manifest and versioning checks, `PixelCopy` native code path present, ARCore button selectable in browser with correct unsupported-browser message, no JavaScript page errors.
- `tests/test_v58_species_dice_burst.py`: all 17 species groups' name/memory dice, 12-frame burst and 5-shot chooser, Collection wording, backup compatibility.
- `tests/test_v58_preferences_safari.py`: imperial/metric units, persistent street-map opt-in across simulated reload, no tile requests without opt-in, species-specific Safari tools.
- `tests/test_v58_live_only_compat.py`: real wildlife requires verified live camera, no gallery import path for new catches, snail/dog saves, older records and backups.
- New asset folder `field_art_v58` matches between Android and Browser Preview; original `field_art` retained for legacy HTML assets.
- No change to `ApplicationId` and collection schema.

## Not verified here
- Actual Android compilation or deployment (dotnet Android SDK unavailable).
- PixelCopy on the OnePlus 11 and successful ARCore Collect photo handoff in a real camera session.
- Launcher icon refresh on OnePlus launcher and ARCore tracking stability on device.

When testing, make a full Collection backup first, deploy as an update without uninstalling, test ARCore Place → Collect, and check that a virtual animal is saved in Collection.
