# Hush Hunt v3.8.4 — Build 48

## What's new

- **Coloured ant cards:** distinct darker/warmer colours for Black Garden, Red, Wood, Yellow Meadow, Pavement, Other ants and the group illustration. Illustration labels and offline file paths remain unchanged.
- **Capture tools:** butterflies and moths now use a drawn virtual Photo Net; rabbits use a Carrot Token. The small alternative tools remain focus aids. Main capture items and alternate icons animate gently; device reduced-motion preference is respected.
- **Live species switching:** during a real-wildlife live encounter, choose another wildlife group without restarting the camera. The primary and alternate tools, status and finishing species change together. The original live-only rule continues to apply; gallery uploads cannot create new discoveries.
- **Virtual wildlife Safari:** the 16 non-cat animal groups from the Field Guide join the existing AR cats, with 17 total groups, each with multiple illustrated variants. Virtual animal species and variety are recorded in the existing backup fields; older virtual cats still load. As before, these are stylised camera overlays, not ARCore tracked creatures or AI species recognition.
- **Wildlife Bingo:** 17 illustrated species-group tiles and per-group discovery progress, backed by existing real animal observations. Existing Cat Bingo remains a separate bonus and retains its old progress. Variety albums remain available on species filters.
- **Optional in-app street map:** tap Street map, read the location/privacy explanation and opt in before any OpenStreetMap tiles load. Pan, zoom and select named species pins. Turn back to Private plot whenever desired. Map access is not persisted across app launches. The original private plot and external OpenStreetMap button still work.
- **Distances:** tap a pin to see approximate straight-line distances to up to 12 other saved sightings, derived only from existing *rounded* locations. Not walking distances or precise GPS measurements. No location data is added to backups.
- **Polish:** new versioned Android and browser assets, `INTERNET` manifest permission for opt-in street tiles, native WebView action bridge preserved.

## Compatibility and privacy

- Android package/application ID **unchanged**: `uk.whiskerhunt.mobile`.
- Browser IndexedDB database key **unchanged**; native JSON storage file/backup format **unchanged**.
- No user photo, animal, location or XP database migration. v1 backups remain supported.
- Street tiles use OpenStreetMap's online tile endpoint *only after consent*. The tile service can see the requesting IP address and approximate area/viewport. Hush Hunt does not upload the collection/photo database.
- Approximate location distances should not be interpreted as exact animal locations.
- When offline or remote tiles cannot load, use the offline private plot.

## Limitations

- Real Android compilation and device camera/remote tile behaviour not verified: .NET Android SDK unavailable in this environment.
- Native ARCore surface tracking, online animal image recognition, and photo-realistic 3D creatures are not part of this build.
- Broad legacy browser smoke test did not finish because its Playwright driver stalled; the five focused regression suites passed.
