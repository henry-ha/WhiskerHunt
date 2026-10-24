# Hush Hunt v3.10.4 — UI refinement pass

## Implemented in this update

### Field Guide / identification cards
- Replaced the **Peacock butterfly** card artwork with a **realistic field-guide illustration**.
- Simplified the fallback choice so the guide uses **one clear option: `Not sure`** instead of duplicating `Not sure`, `Other`, and `My own description` on the same grid.
- Increased the **artwork square size** and tile height so species images fit more cleanly inside the cards.
- Updated the image sizing so guide art is shown **fully inside the square** using a contained fit.
- Kept edit-mode identification grids in sync with the same simplified behaviour.

### Home screen
- **Live Capture** and **AR Safari** home buttons are now **centre aligned**.

### Live Capture
- Live encounter now applies a **full-screen camera presentation** for the real-camera flow.
- Kept the existing **quick shutter / zoom controls** path and made the full-screen layout place them more prominently.
- Preserved existing AR Safari behaviour while avoiding live-camera layout regressions.

### Assets / versioning
- Added new asset pack **`field_art_v67`**.
- Bumped app version stamp to **v3.10.4 · build 67**.

## Key UX decision taken
- Chosen approach: **single fallback tile = `Not sure`**.
  - Reason: simplest for children, least cluttered, and still lets the user continue without knowing the species type.
