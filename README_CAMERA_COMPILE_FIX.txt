HUSH HUNT v3.10.36 - Build 99 - CAMERA COMPILE FIX
=================================================

FIX
The 15 compiler errors shown in Visual Studio were caused by the ambiguous
ImageButton class name between Microsoft.Maui.Controls.ImageButton and
Android.Widget.ImageButton in:
  WhiskerHunt/Platforms/Android/HushWideCameraActivity.cs

Updated both declarations to use Android.Widget.ImageButton explicitly:
  private Android.Widget.ImageButton? _shutter;
  _shutter = new Android.Widget.ImageButton(this)

This resolves the ImageButton type ambiguity and related cascading errors
with Android native UI methods (SetImageResource, SetPadding, Click, Enabled,
etc.).

IMPORTANT
- This is the corrected source, not a prebuilt APK.
- On Windows, open WhiskerHunt.sln in Visual Studio and choose Build >
  Rebuild Solution with the Android device/target selected.
- For the patch ZIP, extract its contents into the ROOT of your current
  Hush Hunt solution folder and replace files when prompted. Do not nest
  an extra folder inside WhiskerHunt.
- If Visual Studio still displays stale errors, run Build > Clean Solution,
  then Build > Rebuild Solution.
- The previous 8 warnings may remain; they are not the 15 ImageButton
  compilation errors reported in the screenshot.
- The full ZIP retains the v3.10.36 / Build 99 version and current app data
  compatibility; avoid uninstalling the existing phone installation.
- To update an installed app via GitHub APK, sign with the same keystore.

CHECKS PERFORMED
- Both changed lines inspected in source.
- ZIP integrity tested after repackaging.
- Actual MAUI Android build not run in this environment (.NET Android SDK
  and workload unavailable), so no successful compilation is claimed.
