# Hush Hunt 3.10.8 (build 71) — live Android entry-point repair

## Confirmed cause of the v3.10.7 deployment defect
The Android project had version 3.10.7 but its `MainPage.xaml` opened `index_v69.html`; that HTML imported `app_v69.js` and `style_v69.css`, which still contained the v3.10.6 UI. Updating `app.js` and `style.css` alone had no effect.

## Changes
- `MainPage.xaml` now opens **index_v71.html**.
- `index.html` and `index_v71.html` now import **app_v71.js** and **style_v71.css**.
- `app_v71.js` and `style_v71.css` are exact copies of the latest corrected sources.
- Removed unused older index/script/stylesheet versions to prevent accidental launches.
- App display version updated to **3.10.8**, Android build to **71**.
- Updated offline browser service worker to the new release assets.
- Extra CSS fixes to compact animal cards, home hero space, live controls and safe-area spacing.
- Kept Android application ID and saved collection database unchanged.

## Testing limitations
Validated launch dependency chain, static resource existence, JavaScript syntax and browser UI. Android APK compilation and native camera lens/zoom hardware still need testing on a phone.
