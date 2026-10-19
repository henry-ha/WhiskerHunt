# Whisker Hunt v3.4.0 — build 36

## What changed

### 1) Whisker Paw claw animation
- Updated the Whisker Paw SVG to use sharper cat-like claws.
- Added claw motion during the grab animation so the claws now retract/extend with the paw instead of staying static.
- Added reduced-motion safety fallback.

### 2) Safer location permission flow
- Added inline location-help panels for both:
  - real-cat save flow
  - virtual cat save flow
- New actions:
  - **Allow location**
  - **Open app settings**
  - **Retry**
- Added younger-audience-friendly wording: users are reminded to ask a parent or trusted adult if unsure.
- Native MAUI bridge now handles `app-settings` and opens the app settings screen.
- Approximate map-pin locations are rounded and cached briefly to improve save reliability.

### 3) More realistic virtual cats
- Reworked AR/virtual cat rendering with more natural body proportions, ears, eyes, whiskers, shading, fur accents and tail styling.
- The procedural upgrade applies across the full generated catalogue.

### 4) Rarity system improvements
- Expanded the AR catalogue to **128 cat types**.
- Added weighted rarity spawning:
  - common
  - uncommon
  - rare
  - epic
  - legendary
- Rarer cats now appear less often.
- Rarity is shown in encounter and gallery UI.

### 5) Versioning / shell updates
- App version bumped to **3.4.0 (36)**.
- Added `index_v36.html`, `app_v36.js`, `style_v36.css`.
- Updated service-worker cache to v36.
- MAUI shell now points to `index_v36.html`.
