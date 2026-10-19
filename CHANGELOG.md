# Whisker Hunt v3.7.4 (Build 43)

## Cat Map improvements
- **Fixed the Android external-map handoff in source**: `View map` used a WebView URL that could fail silently. The native `open` bridge now launches a verified OpenStreetMap HTTPS URL using Android's external `ACTION_VIEW` intent, and sends a success/failure result to the app.
- **No more raw `file://` confirmation dialogue**: Whisker Hunt shows its own clear "Open a street map?" confirmation. Only pressing **Open street map** shares the selected location with OpenStreetMap.
- **Visible private location plot**: existing saved places appear as larger, bright paw markers, labelled with each cat's name. A pinned cat photo/name card appears even with only one discovery.
- **Interactive saved-location list**: **Show pin** highlights the chosen marker in the private plot; **Street map** opens the external-map consent screen.
- Added slight visual separation for duplicate pins in the same rounded area, without changing the coordinates.
- No network access is necessary to view the private plot. It remains a **coordinate plot, not a street-tile map**.

## Preserved
- Existing CatDex cats, photos, sightings, location coordinates, XP, quests, and version 1 JSON backup format.
- No storage migration or automatic upload.

## Testing
- `tests/test_v43_map.py` passed (map UI, multiple pins, consent, native route simulation, data preservation).
- `tests/test_browser.py` passed (CatDex smoke test).
- `node --check BrowserPreview/app.js` passed.
- Android build/APK not compiled in this environment (no .NET SDK installed); device verification required.
