Hush Hunt v3.10.36 Build 99 — Android JNI SIGABRT Repair

ROOT CAUSE (confirmed from uploaded device log):
  JNI DETECTED ERROR IN APPLICATION: expected reference of kind Local but found Global
  in call to DeleteLocalRef
  from HushArCoreActivity.n_onCreate(android.os.Bundle)

The original HushFilamentBridge.cs calls JNIEnv.DeleteLocalRef(clazz) five times.
The clazz value is returned by Android.Runtime.JNIEnv.FindClass(), which in
.NET for Android is a runtime-managed cached global class reference.
Do not delete it as a local or manually delete it as a global ref.

WHAT CHANGED:
  - Removed incorrect reference cleanup at all five FindClass call sites
  - Preserved proper local-ref cleanup for NewString and NewArray results
  - Did not touch other C# / Java renderer files or wildlife assets

HOW TO INSTALL:
1. Close Visual Studio.
2. Extract the ZIP at the root of your existing solution folder:
   E:\inetpub\wwwroot\WhiskerHunt
3. Overwrite ONLY the matching HushFilamentBridge.cs.
4. Open solution, Clean Solution then Rebuild Solution.
5. Redeploy over the existing app (DO NOT uninstall) and test Domestic Shorthair.

This patch targets a confirmed JNI SIGABRT root cause.
It does not guarantee the Filament HD models render correctly. If the app no
longer crashes but shows a different Filament error, capture only the newer
HushFilament / HushHuntAR Logcat lines after this repair.

Validation: source-level sanity checks + ZIP integrity; no full Android build.
