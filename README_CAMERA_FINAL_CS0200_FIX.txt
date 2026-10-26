Hush Hunt v3.10.36 Build 99 — Camera compilation hotfix (CS0200)

Changes:
- Removed unsupported assignment to FrameLayout.ForegroundGravity in
  WhiskerHunt/Platforms/Android/HushWideCameraActivity.cs.
- The shutter camera icon remains centered using LayoutParams with
  GravityFlags.Center.
- Keeps previous camera button layout and ground-shadow renderer changes.

To install: extract the patch at your WhiskerHunt solution root, preserving
WhiskerHunt/Platforms/Android/ folder names and replacing the existing file.
Then in Visual Studio run Build > Clean Solution and Build > Rebuild Solution.

Not verified by a full .NET MAUI Android compiler/build in this environment.
Android 16 KB page-size NuGet warnings are unrelated to the CS0200 error.
