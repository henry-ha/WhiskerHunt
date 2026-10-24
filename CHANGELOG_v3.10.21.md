# Hush Hunt v3.10.21 — Build 84

## Home layout — fixed
- Replaced multiple conflicting legacy height rules with one phone-viewport-sized Home hero.
- Animal artwork is displayed using `object-fit:cover`, with no CSS transform or stretched aspect ratio.
- Live Capture and AR Safari buttons remain visible above bottom navigation at ordinary phone sizes.
- Removed the extra Home stats and release-caption sections from the Home layout to avoid long vertical scrolling.
- Dynamic and Static continue to use the selected v83 majestic wildlife theme assets.

## Your Collection — simplified
- New order: Your Collection summary → six animal-family filters → search/sort → saved photograph grid.
- Wildlife bingo, cat-coat challenges and virtual wildlife gallery remain available inside one collapsed "More challenges & virtual wildlife" disclosure.
- Kept the saved collection schema, favorites, sort, filters, photos and location records unchanged.

## Ultrawide photo path — repaired
- Fixed the 0.6× phone-camera fallback being accidentally redirected to the old "live-only" chooser.
- In the installed Android app, the 0.6× option opens the native camera. Select 0.6× on that camera, capture the image and the result returns to the species confirmation form in Hush Hunt.
- The return path accepts only the native *capture* result and does not treat gallery imports as new captures.
- **Limit:** Android WebView still does not expose reliable direct control over a OnePlus 11 ultrawide lens. This is an external/native camera capture hand-off, NOT an in-WebView 0.6× stream. Camera lens selection needs an on-device check.

## Release
- App version 3.10.21, build 84
- Android MainPage now loads `index_v84.html` → `app_v84.js` and `style_v84.css`.
- Cache version advanced to shell-v84.
- No Android app-ID or collection storage-schema changes; deploy over current app without uninstalling.

## Validation
- JS syntax checks and matching Android/browser source digests passed.
- Browser simulation at 390×820 confirmed Home cards in viewport, Collection ordering, theme picker and family filters.
- Simulated Android photo callback successfully opened species form.
- Android/CameraX/Camera2 hardware tests could not be run in this environment.
