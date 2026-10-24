# Hush Hunt v3.10.19 · Build 82 — Verification

## Source integrity — passed
- Android project `<ApplicationDisplayVersion>3.10.19</ApplicationDisplayVersion>` and `<ApplicationVersion>82</ApplicationVersion>`.
- `MainPage.xaml` opens `index_v82.html`, which loads only `app_v82.js` and `style_v82.css`.
- Both Android and browser packages include identical theme source and matching 20 wallpaper assets, 20 previews and 40 themed button images.
- 20 distinct wallpaper SHA-256 hashes verified.
- Service-worker shell cache key updated to `whisker-hunt-shell-v82`.
- JavaScript passed `node --check`.
- App ID (`uk.whiskerhunt.mobile`) and local collection store (`whiskerhunt_local_v1`) unchanged.

## Phone-size UI test — passed with limits
- Browser JavaScript and CSS loaded into Chromium at 390×844 using inline document injection due the test environment blocking local navigation.
- Theme picker rendered 20 options.
- Choosing Red Panda Bamboo updated the actual Home image reference to `themes_v82/red-panda-bamboo.webp`, not just the theme name.
- Static choice stored `{"mode":"static","theme":"red-panda-bamboo","motion":false}` and Home still displayed that choice after Apply.
- No uncaught JavaScript errors during the test.
- The test used a temporary in-memory `localStorage` shim because sandboxed `about:blank` blocks access to persistent storage. True app restart and on-device rendering remain unverified.

## Artwork disclosure
- Images use the approved 20-scene illustrated gallery, compositionally extended for portrait Home use at 1200×2048. Their exported pixel dimensions are not equivalent to original 4K scene detail.
- This build is an Android MAUI **source** update, not a compiled APK. Device deployment must still be verified.
