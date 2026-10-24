# Hush Hunt v3.10.6 · Build 69 — Release Entry-Point Fix

## Root cause
The previous project delivered updated code in `app.js` and `style.css`, but the Android shell still launched `index_v66.html`, which referenced old `app_v66.js` and `style_v66.css`. The Android project metadata was also still on 3.10.3 build 66.

## Fixed
- `WhiskerHunt.csproj`: `ApplicationDisplayVersion=3.10.6`, `ApplicationVersion=69`
- `MainPage.xaml`: now loads `index_v69.html`.
- `index_v69.html` (BrowserPreview and Android): references *new* `app_v69.js` and `style_v69.css`.
- Both v69 JavaScript/CSS files are exact copies of the latest edited app.js/style.css, with current version strings.
- Browser service worker shell cache bumped to v69; Android now retires legacy shell service workers using its native bridge flag, without touching user data.
- Same Android ApplicationId `uk.whiskerhunt.mobile` and existing storage schema.
- Includes the storyboard-style Home, full-screen Live Capture controls, and the updated Identified UI from v3.10.5, plus the v3.10.4 field-guide artwork work.

## INSTALL: Visual Studio
1. **Back up your collection** from the currently installed Hush Hunt if possible.
2. Extract the Android ZIP and open `WhiskerHunt.sln` in Visual Studio.
3. Select the `net10.0-android` project and **Clean**, **Rebuild**, then **Deploy** to your phone.
4. Launch Hush Hunt and check version: `3.10.6 · build 69`.
5. Do not uninstall the app or use **Clear storage**: those actions can remove locally saved sightings.

## Testing limits
JavaScript and zip integrity checks were performed; full Android compilation and hardware camera/ultrawide testing require your Visual Studio/OnePlus 11 environment. Zoom levels are shown only when the platform exposes native support; do not assume every Android WebView exposes its ultrawide lens. This is a SOURCE release, not an installable APK.
