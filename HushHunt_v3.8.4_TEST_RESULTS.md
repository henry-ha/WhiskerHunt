# Hush Hunt v3.8.4 — test results

**Static checks:** JavaScript syntax (`node --check`) passed; zipped asset set/integrity to be verified at release. Versioned Android/browser source and `uk.whiskerhunt.mobile` checked. New Android `index_v48.html` retains the native bridge flag.

**PASSED focused browser regression suites (Chromium/Playwright with mocked camera/storage):**

1. `tests/test_v48_new_features.py`: 17-group Bingo with a preserved Cat Bingo, butterfly Photo Net and rabbit Carrot Token changed within a live encounter, distinct ant recolours, online street map opt-in with zero map-tile requests before consent, zoom, interactive pins, straight-line distances, optional map disable, virtual-snail save, existing-real-animal preservation and compatible backup.
2. `tests/test_v48_legacy_visual_guide.py`: offline images, 128 varieties, visual species selection, cat and snail saves, edits, older photo compatibility, original v1 backup round trip.
3. `tests/test_v48_legacy_map_compat.py`: existing private map pin/card, individual external map consent, Android external browser action, data unchanged.
4. `tests/test_v48_legacy_virtual_compat.py`: original virtual cat gameplay and backup unaffected by live-only real-wildlife restrictions.
5. `tests/test_v48_legacy_live_only.py`: gallery/normal-camera input cannot create new real catches, successful real snail/dog live captures, old photos retained.

**INCOMPLETE:** `tests/test_browser.py` broad legacy suite: Playwright/Node process stalled and was interrupted by timeout. No full-suite pass claimed.

**NOT TESTED:** Compiled Android APK / direct OnePlus camera / actual OpenStreetMap HTTPS tile download in Android WebView. Test network was deliberately blocked; map tested for constructing requests and consent behaviour rather than real downloaded map tiles.
