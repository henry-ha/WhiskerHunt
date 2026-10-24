# Hush Hunt v3.10.15 · Build 78

This is the source-code update to Hush Hunt / Whisker Hunt for Android .NET MAUI, with a parallel browser preview. It is **not** a compiled APK.

## Changes
- Corrected Home theme picker: tapping a scene selects it and switches to Static so pressing Save actually applies that scene. Dynamic remains a separate rotation mode, with working persisted preferences. The Save area has additional Android navigation clearance.
- Updated native MAUI WebView-to-ARCore detection: the host marks the installed native AR bridge ready after WebView navigation; previously AR Safari incorrectly reported that the Android app was required. The original wildlife collection storage flags, keys and app ID have not been changed.
- Prevented old duplicate home-screen listeners from initiating competing Live Capture or AR Safari launches.
- Rebuilt the frog sprite cutouts using species artwork and corrected transparency. The tree frog no longer loses the head while retaining the eyes; the revised sprite pack is `safari_cutouts_v78`.
- Normalized the highlighted new-capture choice to **New discovery** for every species, including cats.
- Corrected native AR Safari result messaging to distinguish screen-locked preview from a tracked surface anchor.
- Replaced all live startup references with `index_v78.html` -> `app_v78.js` + `style_v78.css`; Android and browser have matching current assets. Removed old launch JS/CSS copies to prevent accidental stale builds.

## Installation
1. Back up your existing collection in the installed app if possible.
2. Extract the Android MAUI ZIP to a **new directory**.
3. Open `WhiskerHunt/WhiskerHunt.csproj` in a .NET MAUI-capable Visual Studio installation (or open the solution if Visual Studio generates one).
4. Clean and rebuild. Deploy **over the installed app**, preserving its Android package ID `uk.whiskerhunt.mobile`. Do not uninstall or clear app storage.
5. Confirm version v3.10.15 / build 78.

## Important verification limit
JavaScript syntax, theme behavior and assets were checked in the available environment. Physical Android build, Google Play Services for AR, real tracked-plane behavior and camera capture must still be verified on the target phone. ARCore still depends on Android camera permission, ARCore support and well-lit textured surfaces.
