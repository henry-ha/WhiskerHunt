# Hush Hunt v3.8.8 — Build 52

## Wildlife memories & the live burst camera

- **Wildlife-aware dice:** added independent name pools for all 17 animal groups (plus 24 cross-species names), and tailored little-memory suggestions alongside an extensive universal set. Snails no longer receive whisker/kitty wording; species selection is read at the instant the dice are tapped. All suggestions remain editable; no automatic recognition is claimed.
- **Virtual Safari:** automatically suggested names/memories now match the chosen virtual species, rather than defaulting to cat descriptions. Existing virtual friends keep their saved names.
- **Live burst capture:** rolling photo buffer increases from four to twelve recent frames. Live sampling interval changes from 900ms to 260ms, and sampling continues while the player drags a capture tool. The final still has a 960px maximum side. The chooser shows the top five ranked images instead of three, with horizontal scrolling on smaller displays. Captured frames are ephemeral and are never exported to collection backups or saved as videos.
- **Terminology:** the main nav, real-capture continuation, and collection header use **Collection**. Replaced the 'Cat area' and 'Cat target' labels with species-neutral target-area wording. Real-photo form footnotes and live-only fallback now match the wildlife identity.
- **No gallery/video uploads:** new real-animal discoveries still require the existing in-session live-camera source check; legacy imported photos can still be browsed and restored. Video files cannot be imported for new captures.
- **Data continuity:** retains `uk.whiskerhunt.mobile`, `whiskerhunt_local_v1`, the Android private CatDex JSON storage format and the existing backup format; no schema migration or automatic deletion. App version `3.8.8`, Android version code `52`, entry `index_v52.html`.

## Limitations

- A quality heuristic scores the user-selected target region for exposure/detail, **not whether a species is truly present**. Repeated or very similar frames may appear in the five suggestions.
- Faster sampling may increase CPU use on some phones; test for heat, battery consumption, lag and dropped frames. Timing is best-effort on Android WebView, not a guaranteed 260ms camera shutter or 12 high-resolution photographs.
- The native Android/ARCore code has not been compiled or device-tested in this environment. A successful browser regression is not a device guarantee.
