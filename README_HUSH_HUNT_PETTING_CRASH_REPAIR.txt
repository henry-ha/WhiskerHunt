Hush Hunt v3.10.36 / Build 99 - 3D Safari Petting Crash Repair
October 2026

WHY THE UPDATE
The last petting patch introduced HushFilamentBridge.TriggerPetReaction,
a separate JNI call executed immediately on each tap/stroke. A fatal JNI
failure cannot reliably be caught by a managed C# try/catch. The reported
crash occurs on petting after installing this patch. This is a suspected
failure point, not a confirmed device-native stack trace.

WHAT THIS REPAIR DOES
- Removes the tap-time TriggerPetReaction JNI invocation.
- Carries a small pet-event counter through the existing, WORKING
  ARCore/Filament SubmitFrame float[] channel instead. This does NOT change
  the existing JNI method signature, camera, anchor, GLB, materials or textures.
- Filament reuses its existing 850ms pet sway/bob code from the earlier patch.
- Adds a fallback emergency command to disable HD pet movement if needed;
  text, haptics and existing non-HD pet response remain available.
- Makes a timestamped backup of every source file modified.

HOW TO INSTALL
1. BACK UP your Hush Hunt project. Close Visual Studio first.
2. Extract this ZIP into E:\inetpub\wwwroot\WhiskerHunt
   (the directory containing WhiskerHunt.sln).
3. Run CHECK_CRASH_REPAIR.cmd; it must say CHECK PASSED.
4. Run INSTALL_CRASH_REPAIR.cmd.
5. In Visual Studio: Clean Solution, Rebuild Solution, deploy over the
   existing app to preserve saved captures and discoveries.
6. Test a single cat touch, then swipe, then a bird. Also test rotating,
   zooming and walking around to make sure AR anchoring is unchanged.

IF ANY TOUCH STILL CRASHES
Run EMERGENCY_DISABLE_PETTING_MOTION.cmd, then Clean/Rebuild/Deploy.
This disables newly introduced HD sway, but leaves pet messages, haptic
feedback and the previously working wildlife/colour fixes intact.

TECHNICAL NOTES
- The first 3 entries of submitted AR float[] retain exact XYZ positions.
- Two additional elements carry pet event sequence and stroke flag.
- Java only reads them when the array has >= 5 floats.
- Uses an existing verified JNI signature, rather than calling a new
  unverified Java static method from the Android UI thread.
- No APK generated or on-phone run. Device results require testing.
- If checks fail because source differs, this installer refuses to modify.
- DO NOT edit Xamarin.Android.Java.targets or any build system file.
