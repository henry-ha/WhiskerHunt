Hush Hunt v3.10.33 / Build 96 – Petting Interaction v1
======================================================

RECOMMENDED: install the PATCH into your existing project.
The full source archive contains only five bundled starter GLBs, whereas your
own Windows project may contain 21 imported CC0 models.

1. Back up your entire WhiskerHunt project and signing keystore.
2. Extract this patch over the project root (the folder that contains WhiskerHunt/).
   Allow matching .cs and .csproj files to be overwritten.
3. Do NOT delete or replace WhiskerHunt/Resources/Raw/ar_models/*.glb.
4. Open WhiskerHunt/WhiskerHunt.csproj in Visual Studio.
5. Clean, rebuild, and deploy to your phone. Use your existing signing key.
6. Verify ARCore surface placement, tap/stroke petting, pinch resizing and photo.

No APK was produced in this environment. For GitHub cloud APK builds, the full
source archive has .github/workflows/hush-hunt-apk.yml and instructions.

Petting v1 = screen-touch gestures + static model bounce/sway + heart feedback.
Actual hand tracking and real-world Depth occlusion are not implemented in v1.

See RELEASE_NOTES_v3.10.33.md for test instructions and limitations.
