Hush Hunt v3.10.36 / Build 99 - Camera compilation fix

Corrects the remaining CS1061 error in HushWideCameraActivity.cs (line 166).
BEFORE: _shutter.SetBackground(ShutterBackground());
AFTER:  _shutter.Background = ShutterBackground();

This full-source archive also retains the earlier Android.Widget.ImageButton
namespace qualification fix for the former 14 compile errors.

Open WhiskerHunt.sln in Visual Studio, Clean Solution, Rebuild Solution.
Android .NET MAUI runtime/compiler testing was not available here.
Keep the existing app installed (and back up saved captures) to avoid data loss.
