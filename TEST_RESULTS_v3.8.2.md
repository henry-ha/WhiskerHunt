# Faunigo / Whisker Hunt v3.8.2 — Test results

## Passed
- `node --check BrowserPreview/app_v46.js` — JavaScript syntax.
- `python3 tests/test_v46_species_tools.py` — app version, bridge and asset parity, provisional brand, strict live source, Snail Leaf Stamp + Macro Lens, Cat Claw + Lure, correct species in save form, legacy cats preserved, backup/restore preserved.
- `python3 tests/test_v46_live_only.py` — live-only wildlife capture, no camera/gallery import loophole, Snail and Dog records and old-photo backups.
- `python3 tests/test_v46_map_compat.py` — private map pin/selection, explicit permission before external OpenStreetMap navigation, no mutation of collection.
- `python3 tests/test_v46_virtual_compat.py` — AR virtual-cat flow and backup remains separate from real wildlife.

## Limitations
- Older `tests/test_browser.py` expects the obsolete gallery/photo-based encounter flow and times out at that step after the live-only rule. It was not counted as passing and should be refactored for the newer gameplay.
- No .NET/Android SDK in this environment, so **no APK compilation** or real-device camera validation.
- Browser preview screenshots use a mock camera and cannot demonstrate actual live video performance.
- Brand name **Faunigo** is provisional, not trademark-cleared.
