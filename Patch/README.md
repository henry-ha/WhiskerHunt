# Hush Hunt v3.10.60d — Debug APK signing recovery

Your uploaded build output says **Build succeeded, 0 errors**. Only *Deploy* failed with Android ADB0010 `NO_CERTIFICATES`. The earlier v3.10.60c live petting code compiled.

This utility is a **deployment helper**, not a new app version, a complete project, or a ready-built APK. It does **not** change `WhiskerHunt.csproj`, GLB models, Filament shaders, UI, or hand tracking code.

## Steps

1. On the Windows machine that has Hush Hunt and .NET 10 Android installed, extract this ZIP into a new folder.
2. Plug in your OnePlus 11 with USB debugging enabled and authorise the PC. Close any other attached Android devices/emulators.
3. Run `BUILD_SIGN_AND_INSTALL.cmd`. It invokes the documented .NET `SignAndroidPackage` target in **Debug**, forces the usual debug key rather than a custom release keystore, embeds assemblies, and selects the newest `*-Signed.apk`.
4. The script calls Android SDK `apksigner verify --print-certs` on the produced APK. **If verification fails, it refuses to install**.
5. Only after verification does it run `adb install -r` (update, preserving app data when the certificate matches) and launch the app.
6. To check an existing signed APK without building or installing, run `CHECK_SIGNED_APK.cmd`.

## Important safety notes

- **Do not uninstall the existing Hush Hunt app just to clear this error**. Uninstalling can erase saved data. If `adb install -r` reports mismatched signing certificates, stop and restore the signing identity that was used for the installed app; don't force an uninstall.
- This assumes your existing development installs used the default debug keystore. If you normally use a custom certificate, edit the signing command to use that certificate instead.
- It assumes your `.csproj` is at `E:\inetpub\wwwroot\WhiskerHunt\WhiskerHunt\WhiskerHunt.csproj` and your app ID is `uk.whiskerhunt.mobile` (both from your logs). If the project moved, edit `$project` at the top of the `.ps1` file.
- The script requires `dotnet`, Android SDK `adb.exe` and `apksigner.bat` on your Windows machine. It tries common SDK locations.
- No Linux/container Android .NET toolchain was available here, so this utility has **not** been tested on your Windows machine or phone. Only static script/package checks were run.

## Why this approach?

Microsoft documents that plain .NET Android builds need not sign packages, whereas `SignAndroidPackage` creates a `-Signed.apk` and generates/uses a default debug keystore. The error is in deploy, not source compilation.

References:
- https://github.com/dotnet/android/blob/main/Documentation/docs-mobile/building-apps/build-process.md
- https://learn.microsoft.com/en-us/dotnet/android/building-apps/build-properties
- https://learn.microsoft.com/en-us/dotnet/maui/android/deployment/publish-cli?view=net-maui-10.0
