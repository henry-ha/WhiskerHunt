Hush Hunt v3.10.36 Build 99 – AR placement / visibility / Safari art patch

Purpose
- Reduce 3D Safari empty-shadow and pre-placement silhouette regressions.
- Add 4-way controls to rotate / tilt installed models.
- Make subsequent tapped ARCore floor destinations into smooth travel paths instead of replacing the existing anchor instantly.
- Make 2D Safari images larger and fully contained inside the interactive target.
- Improve indoor lighting in Filament and lighten overly dark legacy meshes.

Files changed
  WhiskerHunt/Platforms/Android/HushArCoreActivity.cs
  WhiskerHunt/Platforms/Android/HushFilamentBridge.cs
  WhiskerHunt/Platforms/Android/HushGlbAnimal3D.cs
  WhiskerHunt/Platforms/Android/Java/com/hushhunt/filament/HushFilamentOverlay.java
  WhiskerHunt/Resources/Raw/style_v99.css

How to apply
1. BACK UP your project folder E:\inetpub\wwwroot\WhiskerHunt.
2. Extract patch ZIP to that project folder, preserving subfolders and overwriting the five matching source files.
3. Do NOT delete Resources/Raw/ar_models, the 48-species catalogue, application storage, or existing HD GLBs.
4. Clean Solution > Rebuild Solution > deploy to existing app using same signing key.
5. Check animals that previously failed: gorilla, lion, fox and rabbit, then 2D mouse.

Behaviour and caveats
- Filament overlay now starts transparent and waits for an actual anchored, submitted frame. A parsed GLB alone does not signal display readiness.
- Missing/malformed GPU GLB content may still require on-device logs. Error messages now make it less likely to claim success with only a shadow.
- Walking is smooth ARCore world-space translation between two tracked anchors. If a GLB lacks rigged walk animation, it GLIDES: no invented skeletal locomotion.
- Rotation is yaw in 25-degree steps, tilt in 15-degree steps, capped to 65 degrees. Works with Filament and the simple legacy renderer.
- Animal position is sampled from fresh ARCore anchor poses each frame; never locked to screen-space camera position.
- CSS removes UI cropping and enlarges the 2D creature viewport; it CANNOT recreate anatomy cropped from the original PNG or add realistic detail to balloon meshes.
- Filament lighting is adjusted for indoor exposure and the legacy hardcoded shadow is softer.

Checks performed
- Source and brace checks; JavaScript syntax check; changed file paths present.
- No full Android/MAUI Java+C# build or on-device Filament test was possible here.
- For a persistent blank model, collect HushFilament STAGE and HushHuntAR lines in Logcat.
