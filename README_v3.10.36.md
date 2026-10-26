# Hush Hunt v3.10.36 · Build 99

Use `WhiskerHunt.sln` or `WhiskerHunt/WhiskerHunt.csproj` with Visual Studio / .NET 10 MAUI Android workload.

This is a new packaging/entry-point correctness release of the v3.10.35 improvements. Android WebView now actually loads the updated v99 HTML/JS/CSS, and native code and UI version numbers agree. The source includes the improved bundled GLB wildlife, Ginger Tabby selection alias, cropped worm cutout fix, profile wording and native shutter changes described in `RELEASE_NOTES_v3.10.36_Build99.md`.

The project is configured with Android application ID `uk.whiskerhunt.mobile`. **Do not uninstall or clear app data.** Make a Collection backup and deploy with the same signing key as the existing app. No Android APK was compiled in this environment.

For GitHub Actions: unzip to the repository root, preserving `WhiskerHunt/` and `.github/workflows/`; push. If the APK workflow fails, open the red job and inspect its first failing step in logs; GitHub's Node.js 20 and Java setup deprecation warnings alone do not reveal the cause.
