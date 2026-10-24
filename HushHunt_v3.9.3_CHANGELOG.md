# Hush Hunt v3.9.3 · Build 57

## Compilation hotfix

- Corrected `HasTrackablePlaneAt` in `HushArCoreActivity.cs` to explicitly accept `Google.AR.Core.Frame`, removing its ambiguity with `Microsoft.Maui.Controls.Frame`.
- Resolves the two **CS0104** and **CS1503** errors shown by Visual Studio in v3.9.2.
- Bumped the app to 3.9.3 / build 57, with matching WebView assets (`index_v57.html`, `app_v57.js`, `style_v57.css`).
- Android application ID remains `uk.whiskerhunt.mobile`, and collection data storage/backup files are unchanged.

No other ARCore geometry or species artwork changed in this hotfix.

The Android project must still be rebuilt in Visual Studio; this environment does not have the .NET Android workload.
