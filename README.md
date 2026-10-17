# Whisker Hunt v3.3.0 · Build 35

Android-first offline CatDex and AR Safari prototype, developed in .NET MAUI with a WebView frontend.

## Release highlights

- **Cleaner live capture:** Only the *other* tool appears in the tool dock. When Paw is active, the selector says **Switch to Lure**; when Lure is active, it says **Switch to Paw**.
- **Tool-change animation:** A small, short spring-pop signals tool changes. Reduced-motion preferences are respected.
- **Less AR Safari clutter:** Long camera instructions, quality box and extra launch instructions are hidden in AR Safari, keeping the camera and cat more prominent. Live-camera classic mode still provides detail.
- **Find missing cats:** A recovery wizard in Explorer profile checks the Android private `.bak` snapshot and previews possible missing cats, without modifying storage. Users explicitly confirm any merge. Users may also select a previously exported JSON backup. The recovery wizard's **Save my current CatDex first** action exports a cache copy *without rotating the recovery snapshot*.
- Same Android application ID and v1 CatDex schema: upgrading over the existing app should preserve data. Do **not** uninstall the app or clear app storage.

## Where to find recovery

**Explorer profile → Find missing cats**. On Android, it reads `whisker-hunt-state.json.bak` if present and valid. If unavailable, select a previously exported backup. No recovery is guaranteed when Android app storage has already been erased.

## Installation and testing

1. Make a full CatDex backup and keep the file somewhere safe before deploying.
2. Extract the complete source ZIP into a **new folder**, then open `WhiskerHunt.sln`.
3. Ensure your Android device and **Build + Deploy** are enabled in Visual Studio Configuration Manager.
4. Clean, rebuild and deploy **over** the existing installation. Do not uninstall.
5. Confirm the app shows **v3.3.0 · build 35**.

Browser tests pass. **No Android APK was compiled in this environment**; native recovery and live-camera performance still require a device test.
