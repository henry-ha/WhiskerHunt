# Hush Hunt v3.10.23 · build 86

## Home screen
- Changed the active wallpaper to a non-cropping `object-fit: contain` presentation (centered, no blur/filter/transform).
- Kept Home card sizing and bottom-navigation safe spacing from build 85.
- Matching button scene images also use non-cropping fit to avoid enlarging the subject.
- Existing artwork is still based on lower-resolution source illustrations; this patch does not create true native 4K source details.

## Wide capture (Android)
- Added `HushWideCameraActivity`, a dedicated **in-app** rear-camera capture screen instead of launching the generic external phone camera app.
- The camera scans accessible rear camera streams and only uses one whose reported field of view is materially wider than the regular rear stream. Never fabricates 0.6× with 1× digital scaling.
- New `whiskerhunt://wide-camera` bridge and `hushNativeWideResult` callbacks deliver captured JPGs to the existing species-confirmation flow.
- Cancellation, errors and unsupported lenses restart the WebView's Live Capture stream to avoid the grey play-button/abandoned video problem.
- OEM limitation: the implementation uses Android's legacy camera enumeration, which often hides the ultrawide physical camera on modern multi-camera devices. Thus actual 0.6× on a OnePlus 11 is **not confirmed**; if hidden, the UI explicitly reports the unavailable lens and resumes 1×.

## Distinct AR modes
- Native ARCore requires a genuinely tracked surface and anchor before a creature can be placed and collected.
- Removed native ARCore's substitute screen-locked-preview placement; that behaviour is reserved for the separate 2D Safari mode.
- 2D Safari identifies itself as `2D · VIRTUAL`, reducing confusion with native ARCore.
- Neither mode promises volumetric 3D character assets: both use illustrated 2D wildlife artwork, while native ARCore provides 3D world anchoring.

## Project
- Version and build bumped to 3.10.23 / 86.
- Android launch now points to `index_v86.html` which loads `app_v86.js` and `style_v86.css`.
- No change to ApplicationId or collection storage schema; deploy in-place to keep collections.

## Limitations and testing
- Syntax/static checks and archive-integrity checks only. Android compilation, real 0.6× rear field of view, and ARCore tracking need on-device verification.
