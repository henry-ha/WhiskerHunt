# Hush Hunt 3.8.6 (build 50) — Profile units, remembered street map, wildlife Safari corrections

Based on 3.8.5 (build 49). This is a source release, not a verified compiled Android APK.

## Profile / map

- Added Explorer Profile → **My map preferences**, placed above discovery insights for visibility.
- Distance units are **Miles & yards (UK)** by default or **Kilometres & metres**. Switch any time; street-map labels update accordingly.
- Added a remembered **street-map choice**; the existing opt-in consent panel remains mandatory the first time street tiles are requested. A choice to show streets persists across launches and is stored in the existing private profile snapshot. A choice to stay private persists too.
- Turning the setting off removes the interactive street-map view; the private discovery plot remains offline.
- Distances continue to use roughly 1 km-rounded coordinates, so results are **approximate straight-line estimates**, not accurate walking distances or exact species positions. Yards and metres are deliberately rounded.
- The private-plot text no longer incorrectly says the currently visible street-map area is “not a street map.”
- Enabling online tiles shares the viewed area and device IP with the external OpenStreetMap tile provider; there is no automatic map request while online maps are disabled.

## AR Safari / collection language

- Fixed the captured-orb **cat paw** that appeared during non-cat encounters even after the draggable tool had changed.
- Hedgehog uses a leaf badge in both stages, butterfly and moth use an illustrated virtual net, rabbits use carrots, and the original whisker claw is still used for cats.
- Alternating tools also update correctly, including the accessibility labels and illustrated icons.
- Continue/save actions now say **Keep this [species]**; the virtual naming form uses the current animal group.
- Updated the virtual encounter guidance, habitat/variety description, post-capture animation and species-specific success text (instead of cat/paw/meow messages for every species).
- Virtual entries remain explicitly distinguished from real wildlife sightings.
- Renamed some leftover general collection, profile, journal and recovery labels to use wildlife terminology. Cat-specific challenges remain cat-specific.
- Added top safe-area clearance to full-screen Safari so Android system status icons do not overlap the heading.
- New installations use **Hush Explorer** as the default displayed profile name, but existing saved profile names are never overwritten.
- Expanded the Profile insight tile from only cat coats to worldwide wildlife varieties; Cat Bingo remains in FieldDex.

## Compatibility

- `ApplicationId`: `uk.whiskerhunt.mobile` unchanged.
- Native storage: `whisker-hunt-state.json` and `.bak` unchanged.
- Browser IndexedDB: `whiskerhunt_local_v1`, schema v1, unchanged.
- Backup format continues to use `{app:"Whisker Hunt",version:1,...}`; the visible name **Hush Hunt** does not rename existing saved data or lose old photos.
- New profile preferences are an optional, validated `profile.viewSettings` object inside the current profile, compatible with old backups.
- Offline 2D Safari is still available; the experimental native ARCore implementation from 3.8.5 is unchanged.

## Build/verification

- `node --check` passed.
- Playwright v50 regression passed: persisted Imperial/Metric & street opt-in on simulated native reload, no OSM network request before consent, species-specific hedgehog/butterfly/cat capture tools and naming.
- Playwright legacy wildlife/FieldDex/Bingo/virtual save tests passed.
- Playwright live-only and virtual-cat compatibility tests passed.
- JavaScript/CSS and native MAUI bundled raw assets matched byte for byte. ZIP integrity verified.
- **No .NET/Android SDK was available here; no Android compile or physical ARCore device verification was performed.**
