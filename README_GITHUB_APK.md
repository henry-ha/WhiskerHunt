# Hush Hunt — build a downloadable APK with GitHub Actions

**Prepared for Hush Hunt v3.10.33 (Build 96)** — `WhiskerHunt/WhiskerHunt.csproj`, `net10.0-android`.

This is a **CI setup**, not an APK. It has not been run on GitHub yet. The workflow builds a **signed release APK** on a GitHub-hosted Ubuntu runner, uploads the APK as an artifact for 30 days, and runs when you push to `main` or press **Run workflow**. You need to complete the one-time setup below, after which you can start/download builds from your phone.

## 1. Put the files in a GitHub repository

Place `.github/workflows/hush-hunt-apk.yml` at the **repository root**, next to `WhiskerHunt/WhiskerHunt.csproj` (one directory below root). Commit the actual `WhiskerHunt` source tree, not a ZIP of the source. The workflow won't run directly on a ZIP stored in the repo.

**Important: ARCore animals.** Your PC currently has 21 GLB assets after importing them. The source ZIP supplied separately still contains only the five base models. **Commit your locally imported `WhiskerHunt/Resources/Raw/ar_models/*.glb` files, plus `installed_species.json` and the native source the importer updated.** Cloud builds see only Git-committed files, not uncommitted local models.

Do NOT commit a `.keystore`, `.jks` or private signing passwords. `.gitignore` is provided in this setup.

## 2. Configure Android signing ONCE

**Warning: the same app identifier + signing certificate is required to install an APK *over* an existing installation without uninstalling it.** Your app ID is `uk.whiskerhunt.mobile`. If you have already deployed from Visual Studio with the default Android debug certificate, use that exact signing key for your **personal testing** releases. It's usually `C:\Users\<WindowsUser>\.android\debug.keystore` (alias `androiddebugkey`, keystore and key passwords both `android`). Run `keytool -list -v -keystore <path>` to verify it and compare the certificate with the one on your current APK. Do not assume that it's the correct key if you customized signing settings.

The debug keystore is insecure for public distribution; for public production apps, use a long-term **release** key. If that differs from the certificate currently on your phone, installation over your existing app will fail. **Back up/export your saved Hush Hunt discoveries before considering uninstalling the old app.** This workflow never uninstalls apps or modifies your phone.

To copy the Base64 value of your existing keystore to clipboard on Windows (no new key is generated), open PowerShell in your project folder and run:

```powershell
.\COPY_ANDROID_KEYSTORE_SECRET.ps1 -KeyStorePath "$env:USERPROFILE\.android\debug.keystore"
```

The script copies one long Base64 value; paste it into the first GitHub secret. It does **not** upload your private key or save its Base64 in the project. You can also give `-KeyStorePath` the path to your own release keystore.

On GitHub: **repository Settings → Secrets and variables → Actions → New repository secret**. Create these four secrets (case-sensitive):

| Secret name | Value |
| --- | --- |
| `ANDROID_KEYSTORE_BASE64` | Base64 of the existing signing keystore (`COPY_ANDROID_KEYSTORE_SECRET.ps1`) |
| `ANDROID_KEY_ALIAS` | Alias in keystore (default debug: `androiddebugkey`) |
| `ANDROID_KEYSTORE_PASSWORD` | Keystore password (default debug: `android`) |
| `ANDROID_KEY_PASSWORD` | Key password (default debug: `android`) |

Use **repository secrets** (not Actions variables). Save a secure backup of your keystore and credentials outside the repo. Without all four secrets, the workflow **fails deliberately** rather than producing an APK signed by an unknown key.

## 3. Run your first cloud build

1. Commit and push source + `.github/workflows/hush-hunt-apk.yml` to the `main` branch.
2. Open your GitHub repository → **Actions** → **Hush Hunt - Android APK** → **Run workflow** → **Run workflow**.
3. When the workflow completes with a green tick, open the run → **Artifacts** (near the bottom) → `HushHunt-Android-APK-<run-number>`.
4. Download the GitHub artifact ZIP on your Android phone, extract it, and tap `HushHunt-v3.10.33-ci100001-Signed.apk` (build number will vary).
5. Allow installing APKs from the app you're using (Files/browser), if Android prompts you.

GitHub may require you to sign in to download the artifact. The ZIP includes the signed APK and SHA-256 checksum. Artifacts are retained for **30 days**. A workflow run is not the same as a published GitHub Release; this uses the **Actions artifacts** download area.

Once configured, future source pushes to `main` trigger an APK build; or start one manually from your phone at any time. Build time depends on GitHub runners and Android workload downloads.

## 4. Compatibility and troubleshooting

- **`INSTALL_FAILED_UPDATE_INCOMPATIBLE`**: Signing key differs from installed APK. Use exactly the same old signing key; do not uninstall until discoveries are backed up.
- **Version downgrade / version code**: Workflow assigns `100000 + GitHub run number` as Android `ApplicationVersion` (higher than Build 96) and displays the project's `3.10.32` version. If your manually installed version code is already higher than this, edit that base number.
- **Missing 3D animals**: The GitHub repo must contain the imported GLB assets. The source archive alone includes five base prototypes; no on-run 3D downloads are attempted.
- **`maui-android` or Android SDK workload failure**: Read the **Install .NET MAUI Android workload** / **Install required Android API** logs. The workflow is tailored to .NET 10 and installs Android API 36 tools, but SDK images and upstream workloads can change.
- **Build errors**: This workflow is not a workaround for C# or XAML compilation errors. The MAUI source must compile normally.
- **APK not found**: The workflow fails if .NET's publish folder does not contain exactly one `*-Signed.apk`, deliberately preventing an unsigned artifact.
- **If your default branch isn't `main`**: Edit the `push.branches` entry. `workflow_dispatch` must first be committed to the repository's default branch to show the Run workflow button.
- **Private repositories**: GitHub Actions usage/limits depend on your plan; the repository remains private if configured so.

## Technical choices

Linux `ubuntu-24.04` + .NET SDK 10 + `maui-android` + Temurin JDK 17 + Android SDK 36 + `dotnet publish` of the **project**, not a solution. Uses `AndroidPackageFormats=apk`, signed via Android's keystore properties with `env:` passwords (secrets aren't placed in command-line arguments). Only signed APKs are uploaded, no key material, raw camera images, user data, or keystore.

References:
- Microsoft: https://learn.microsoft.com/en-us/dotnet/maui/android/deployment/publish-cli?view=net-maui-10.0
- Microsoft workload setup: https://learn.microsoft.com/en-us/dotnet/maui/get-started/installation?view=net-maui-10.0
- GitHub artifacts: https://github.com/actions/upload-artifact

## Verification boundary

This package has been checked locally for YAML parsing, shell block syntax, expected .csproj path/target framework, archive completeness and file naming. This environment does not have `dotnet`, an Android SDK, access to your repository, or your signing credentials, so no APK was compiled and no workflow was run on GitHub. The first workflow run will determine end-to-end compatibility and might reveal additional project build errors.
