# Hush Hunt v3.10.13 (build 76)

## Implemented in this build

### Home screen refresh
- Reworked the home screen to follow the more colourful mockup direction.
- Added 4 vibrant rotating wildlife themes:
  - Twilight fox
  - Mountain deer
  - Meadow rabbit
  - Waterfall kingfisher
- Theme picker is available from the home screen and profile screen.
- Dynamic mode rotates scenes on app reopen.
- Static mode keeps the selected scene.
- Live Capture and AR Safari cards now use richer photo-backed artwork with stronger contrast and clearer readability.
- Removed the extra mini action block from the hero area so the layout is cleaner and closer to the mockup style.

### Live Capture fixes
- Reworked Live Capture into a more compact camera layout so controls fit on screen better.
- Moved the animal selector into a compact overlay instead of a tall stacked block.
- Repositioned the status panel, zoom controls, shutter button, and game toggle.
- Shutter button is now anchored much lower and centred so it should remain visible.
- Reduced vertical crowding and overlap in the camera UI.
- Tightened top / bottom safe-area handling for Android to reduce wasted space.

### 0.6× wide lens improvements
- Improved rear-camera lens detection.
- Added a more aggressive fallback so the 0.6× option can appear when the device exposes multiple rear cameras even if labels are inconsistent.
- Retained 1× / 2× / 3× controls and pinch-to-zoom support.

## Updated files
- BrowserPreview/app_v75.js
- BrowserPreview/style_v75.css
- BrowserPreview/themes_v76/*
- BrowserPreview/button_scenes_v76/*
- WhiskerHunt/Resources/Raw/app_v75.js
- WhiskerHunt/Resources/Raw/style_v75.css
- WhiskerHunt/Resources/Raw/themes_v76/*
- WhiskerHunt/Resources/Raw/button_scenes_v76/*
- WhiskerHunt/WhiskerHunt.csproj

## Package version
- ApplicationDisplayVersion: 3.10.13
- ApplicationVersion: 76
