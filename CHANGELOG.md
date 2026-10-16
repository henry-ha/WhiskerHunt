# Whisker Hunt changelog

## v2.5.0 (Android build 25) — visible-update and live-camera recovery release

- Corrected Android application version metadata, which had remained `2.2.0` in the prior `v2.4` source package.
- Changed the Android WebView entrypoint to `index_v25.html`, loading `app_v25.js` and `style_v25.css` instead of reusing the previous asset URLs. Added a visible `Whisker Hunt v2.5.0 · build 25` marker to every encounter/other modal.
- Prevented the native Android shell from registering the browser demo's service worker. Unregisters any existing same-origin app-shell worker and deletes **only Whisker Hunt service-worker shell caches**; it does not touch CatDex snapshots, personal photos, IndexedDB, or any unrelated user data.
- Configured the native WebView to avoid stale HTTP cache entries. The Android package ID and existing native CatDex JSON format remain unchanged.
- Fixed the race where tapping **Use normal camera instead** during a pending live-camera startup and then cancelling the native camera could reveal **Starting live camera…** again. The old live startup is invalidated before opening a safe **Choose your camera** screen behind the native camera. Cancellation signals return to that chooser.
- Replaced the old ball/rounded-square artwork with a standalone vector cat-paw silhouette (four toes and a shaped central pad). The inactive drag handle has a circular dotted `DRAG` guide, which disappears when dragging; the Pod/Lure selection buttons remain circular.
- Added extra vertical room to keep the paw above capture instructions. Kept existing paw-grab and floating `Meow!` capture effects.
- Preserved CatDex entries, photos, sightings, XP, quests, and existing JSON backup/restore compatibility.

## Limitations

- No Android APK was compiled or tested on physical hardware in this environment.
- Browser tests simulate the native photo cancellation callback and delayed camera startup; the final behaviour must still be tested on the OnePlus.
- Camera preview and frame scoring are heuristics and do not perform automatic cat recognition.
