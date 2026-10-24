# Hush Hunt v3.8.7 — ARCore compile-fix release (Android .NET MAUI)

**Visual Studio solution:** `WhiskerHunt.sln`  
**App ID:** `uk.whiskerhunt.mobile` (unchanged)  
**Display version/build:** `3.8.7 / 51`

This release fixes the 19 ARCore-related C# errors shown by Visual Studio on the v3.8.6 source. It does not add gameplay changes. Your existing collection, photos, sighting locations, user preferences and legacy backups remain untouched.

### What was corrected

In `WhiskerHunt/Platforms/Android/HushArCoreActivity.cs`:
- Explicitly use `Android.Widget.Button` in the native activity, avoiding ambiguity with MAUI `Button`. This also fixes the `AddView` and `.Click`/`.Enabled` cascading errors.
- Removed unsupported `GLSurfaceView.SetPreserveEGLContextOnPause(true)` call. GL resources are reinitialised in `OnSurfaceCreated` on context recreation.
- Qualify `System.Environment.TickCount64` to avoid a collision with Android `Environment`.
- Removed unused `Frame` field that collided with MAUI `Frame`.
- Split a prohibited `var` multi-declarator into separate statements.
- Explicitly use `Android.Graphics.Rect` and `Android.Graphics.Paint` when composing the AR photo.

### Build/install instructions

1. **Export a complete FieldDex/collection backup** from the installed version.
2. Extract the v3.8.7 complete project into a *new* directory and open `WhiskerHunt.sln`.
3. In Visual Studio, restore NuGet packages and **Build → Clean Solution**, then **Build → Rebuild Solution** with `Debug`, your OnePlus Android device as the target.
4. **Do not uninstall the existing app.** Deploy over it with the same signing identity to preserve private data. If Visual Studio requests uninstalling for a signing mismatch, stop and preserve the collection rather than agreeing.
5. Test AR Safari → ARCore. `XPACE.Google.ARCore` still needs to restore, Google Play Services for AR must be supported/installed, and actual world-tracking needs validation on device.

**Optional one-file patch:** replace `WhiskerHunt/Platforms/Android/HushArCoreActivity.cs` with the included `HushArCoreActivity_fixed.cs` file if you prefer not to switch projects. For manual file replacement the app will still show your current version/build unless you update the project version separately.

### Verification

- Static checks for all 19 screenshot errors and source integrity passed.
- Three browser regression suites passed (profile units, saved map choice, wildlife Safari, live-only real-animal capture and existing virtual cats).
- JavaScript syntax and Android/bundled web-asset checks passed.
- **An Android build or APK and physical ARCore runtime could NOT be verified here because no .NET Android SDK / attached phone is available.** Additional errors may be exposed by an actual build; send the updated Visual Studio Error List if needed.

See `HushHunt_v3.8.7_TEST_RESULTS.md` for more detail.
