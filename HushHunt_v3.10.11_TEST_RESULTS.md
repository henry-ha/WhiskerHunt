# Hush Hunt v3.10.11 test results

Static/source verifications passed:
- Android version: 3.10.11 / build 74
- Android startup: `index_v74.html` pointing to `app_v74.js` and `style_v74.css`
- Matching browser and Android JS/CSS bytes
- JavaScript syntax using `node --check` on both packages
- Six WebP themes and 149 reference images exist in each asset pack
- The frog images and 6 theme images can be decoded
- No stale v73 entry point/source references in the live bundle
- ARCore source contains real plane search and labelled screen-locked preview fallback

Not verified:
- Actual APK compilation (Android / .NET SDK unavailable)
- Browser UI exercise (local Chromium blocked by container environment)
- Device camera, optical ultrawide availability, native plane tracking

Do not interpret static verification as passing phone/device tests.
