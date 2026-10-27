# Hush Hunt v3.10.36 Build 99 — Filament Maven 404 correction

The previous source requested com.google.android.filament:filament-android:1.78.1 and
com.google.android.filament:gltfio-android:1.78.1, but both returned HTTP 404.
This patch pins BOTH Maven artifacts to the published 1.77.3 release.
It also corrects the Filament Java ClearOptions API, which uses clearColor (double[]) and
clear fields rather than the nonexistent setClearColor()/setClear() methods.

## To apply the patch (recommended)
Close Visual Studio. Extract this patch into the ROOT directory containing
WhiskerHunt.sln, preserving subdirectories and overwrite the two matching files.
Reopen Visual Studio and run Clean Solution, Restore NuGet Packages and Rebuild Solution.

The installer already installed two high-detail GLBs on your PC:
  WhiskerHunt/Resources/Raw/ar_models/other-deer.glb
  WhiskerHunt/Resources/Raw/ar_models/dog-labrador.glb
DON'T replace these with older low-poly assets from the full source package.
This small patch changes ONLY the project configuration and Filament Java bridge.
It intentionally leaves all animal assets and saved user data alone.

Notes:
- Maven packages are published to Maven Central, not Google's Maven repository.
- Internet is needed on the development PC for first restore.
- If clean/rebuild fails again, use the NEW first error list; the two XA4236 404s
  should no longer be caused by unlisted version 1.78.1.
- ZIP integrity/source sanity checked; not compiled or device-tested in this environment.

References:
https://central.sonatype.com/artifact/com.google.android.filament/filament-android/1.77.3
https://central.sonatype.com/artifact/com.google.android.filament/gltfio-android/1.77.3
