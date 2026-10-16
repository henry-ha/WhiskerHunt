# Whisker Hunt v1.9

This is the Android-first .NET MAUI + WebView source project. **No Android APK was compiled here.**

## v1.9: Best frame around your selected cat
1. Open **Catch → Live encounter**.
2. Tap the cat in the preview to place the target ring.
3. Drag the Dangle Lure (optional), then drag the Whisker Pod onto the target.
4. Whisker Hunt chooses the best recent still using an offline quality estimate of the area you marked as the cat, plus whole-frame quality.
5. Review the selected photo, name the cat and save to CatDex.

The game does **not** automatically recognize cats or faces. The crop is based on your tap. It holds at most eight recent stills in memory; no video is recorded or uploaded. Normal camera/gallery fallback is still available.

## Compatibility
The existing CatDex database, native JSON snapshot schema, XP, quests, sightings, and backup/restore format have **not changed**. Back up your CatDex before installing a new development build; install over the existing app rather than uninstalling.

## Tests
Run `python3 tests/test_v19_subject.py`, `python3 tests/test_v18_live.py`, and `python3 tests/test_browser.py` with Playwright, Pillow and Chromium installed. The Android live camera and WebView permission bridge require device testing.

## Earlier features
# Whisker Hunt v1.8

An Android-first .NET MAUI app for photographing real cats and collecting sightings in a private offline CatDex. Its game-inspired capture UI is original and does not use Pokémon graphics or game assets.

## Build and test

1. **Back up your CatDex first.** Keep the existing app installed; do not clear app data.
2. Open `WhiskerHunt.sln` in Visual Studio with the **.NET 10 Android / MAUI workload** installed.
3. Select the `WhiskerHunt` project, target your Android device and deploy **over** the previous app. The Android package ID remains `uk.whiskerhunt.mobile`; version code is `18`.
4. Tap **Catch → Live encounter**. Approve Android camera permission if prompted. Tap the cat in the live preview to position the ring, drag **Dangle Lure** or **Whisker Pod** from the translucent dock on the right, and release over the target.
5. On success, the camera stops and the clearest-looking recent still is selected for the existing CatDex save form. Check the photo and save only when ready.
6. If live preview cannot start, use **Take a photo** (native camera) or **Choose a photo** (gallery). Both existing still-photo paths are preserved.

### Safety and privacy

- The live camera samples a maximum of **eight recent still frames** over approximately **three seconds**. All candidate frames remain in volatile memory and are discarded on exit; **only one selected still can be saved** to the CatDex. No video or audio is recorded.
- No cloud service, network cat detector, background location tracking or third-party API is used. Keep a respectful distance from real cats.
- Camera permission is only granted to the app's own local UI for video; microphone and unrelated web origins are rejected.
- Your existing CatDex database / native JSON snapshots, IDs, XP, quests and backups use the same format as v1.7. **Do not uninstall the existing app before updating.**

### Browser preview

`BrowserPreview` contains the same HTML, CSS and JavaScript as the MAUI raw assets. For live camera in a browser, serve the directory over **HTTPS or localhost** (browsers restrict `getUserMedia` on insecure origins). The browser demo can also use the gallery fallback.

Run `python3 tests/test_v18_live.py` with Playwright and Chromium to exercise a synthetic video stream without needing a physical camera. Run other `tests/test_*.py` scripts for regression coverage.

### Known limitations / build status

- The live camera/WebChromeClient path is **not yet Android device-verified**; actual camera access depends on Android WebView origin and permission support. If it fails, use the existing native camera picker.
- Cat detection is **manual targeting**; best-frame selection uses whole-frame exposure/detail heuristics rather than cat recognition.
- **No Android APK was compiled in this environment** because the .NET Android workload is unavailable. The deliverable is a versioned source ZIP.
