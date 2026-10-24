# Hush Hunt v3.9.5 · Build 59

Open `WhiskerHunt.sln` in Visual Studio with .NET MAUI Android workloads.

1. Export your existing Collection backup in Hush Hunt.
2. Extract this ZIP to a new folder, then **Clean Solution → Rebuild Solution**.
3. Deploy to the same Android application ID: `uk.whiskerhunt.mobile`.
4. **Do not uninstall the existing app.** The app's saved animals and pictures live in app-private storage and can be deleted on uninstall.
5. Test **AR Safari → ARCore Real surfaces**, then **Place → Collect** on your OnePlus.

The ARCore artwork-path bug is fixed in source, but a native Android build and on-device tracking/capture have **not** been tested in this environment. Share any Visual Studio errors or ARCore status messages if they occur.
