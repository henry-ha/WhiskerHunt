# Hush Hunt v3.8.3 · Build 47 — Test Results

- **PASS** JavaScript syntax `node --check BrowserPreview/app.js`.
- **PASS** `python tests/test_v47_visual_guide.py`: rebrand, 17 groups and 128 varieties, offline bundled images, Garden Snail saved, Cat Tuxedo saved using old `coat` field, all 17 groups render image cards, edit Snail to Grove Snail preserving sighting, FieldDex filtered album counts and unlocked status, backup v1, legacy cat preserved.
- **PASS** `python tests/test_v47_live_only.py`: real live-only save, gallery/normal camera cannot mint catches, snail and dog, prior photos and backup compatibility.
- **PASS** `python tests/test_v47_map_compat.py`: private map pin, name/photo card, explicit external map consent, Android route and immutable collection data.
- **PASS** `python tests/test_v47_virtual_compat.py`: AR Safari virtual cats work and remain separate from real wildlife; backups compatible.
- **PASS** Versioned source parity between BrowserPreview and Android bundled assets.
- **PASS** 146 bundled WebP illustrations (128 varieties + 17 group cards + 1 Not sure), with matching files under each Android/Browser resource directory; versioned HTML points to app_v47.js/style_v47.css.
- **PASS** ZIP CRC integrity for complete, Android and browser source packages.
- **NOT VERIFIED** Native Android compilation, MAUI UI, GPS interaction and camera operation on a physical phone: dotnet SDK not available.
- **NOT COMPLETED** Legacy `tests/test_browser.py` full-suite run hung in this sandbox's Chromium/browser environment. The dedicated field guide and three compatibility suites above did pass.

These tests simulate supported workflows in Chromium; they are not proof of correct on-device Android deployment.
