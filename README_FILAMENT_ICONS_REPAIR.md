# Hush Hunt — Filament renderer class & Safari icons repair (Build 99)

## Diagnosed from device screenshots
- `ClassNotFoundException: com.hushhunt.filament.HushFilamentOverlay`: the native Java Filament entry point is not in the installed APK. Project now forces `AndroidJavaSource Include` after removing an implicit duplicate.
- The native Safari picker generator used an `Other -> 🐾` fallback for many distinct species, including existing animals. Icon mapping is now per species.
- The HD GLBs are NOT missing merely because the legacy parser rejects them. The PBR HD assets depend on Filament working first.

## Apply to your *existing* Windows project
1. Close Visual Studio. Back up the complete solution folder first.
2. Extract the small patch ZIP into the solution root (where `WhiskerHunt.sln` is), replace matching source/scripts.
3. **Do not overwrite or delete** `WhiskerHunt/Resources/Raw/ar_models`, `installed_species.json`, `app_v99.js` or your saved collection. This patch intentionally contains no GLBs or pre-generated `app_v99.js`.
4. Double click `REPAIR_AR_SAFARI_ICONS.bat`. This reads your installed catalogue (48 on your screenshot), removes entries only if the GLB is actually absent on disk, and updates the existing picker with animal-specific icons.
5. Delete `WhiskerHunt/bin` and `WhiskerHunt/obj` (back up if desired). Reopen `WhiskerHunt.sln`, restore dependencies, Rebuild, then redeploy *without uninstalling*.
6. Before deployment, verify the APK contains the renderer class with `py tools/verify_filament_apk.py "C:\path\to\app.apk"`. Expected: `Native HushFilamentOverlay class: PRESENT`. The verifier also checks GLB assets are packaged.

## Limits and next diagnosis
The patch was source-audited and the picker rewrite and test manifest were exercised locally. .NET MAUI Android cannot be built in this Linux container, so Java compilation and Filament rendering on OnePlus must be verified in Visual Studio. If `JAVAC0000` follows explicit Java inclusion, send the full compiler error; that will expose any remaining Java API incompatibility that previous builds did not compile.

No marketplace or new high-detail GLBs were added in this repair. Existing HD files and any new animals you've installed remain intact.
