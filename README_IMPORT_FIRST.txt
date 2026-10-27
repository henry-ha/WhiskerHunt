HUSH HUNT | REALISTIC WILDLIFE CANDIDATES (27 OCT 2026)
======================================================
This is a downloader, compatibility checker, audit tool and controlled importer.
It is NOT a new APK, NOT a full wildlife asset pack, and does NOT include model
binary files from third-party publishers. Hush Hunt's own application source
is unchanged. Direct downloads need internet access on your Windows PC.

Setup: Extract into E:\inetpub\wwwroot\WhiskerHunt (solution root, where
WhiskerHunt\Resources\Raw\ar_models exists). This does NOT replace GLBs.

1. Double-click REVIEW_AND_DOWNLOAD_REALISTIC_MODELS.cmd. Five freely
   licensed models are fetched to HushHunt_Realistic_Model_Candidates.
2. Check EACH model in Blender or your GLB viewer: face, coat, eyes, ears,
   legs, scale, fur cards from all directions. Read REALISM_SOURCES.md.
3. Audit your existing Hush Hunt models using AUDIT_INSTALLED_REALISTIC_MODELS.cmd.
4. After approval, open Windows Command Prompt in the solution root, run:
      py -3 tools\hush_realistic_models.py install red-panda --yes
   Substitute red-panda with zebra/wolf/fox/kangaroo. This automatically
   backs up the existing matching GLB and installs the chosen reviewed model.
   For files licensed and downloaded from Sketchfab/Fab separately, use:
      py -3 tools\hush_realistic_models.py install red-panda --file "C:\Your\Model.glb" --yes
5. Clean/Rebuild/Deploy in Visual Studio, keeping your same application ID.
   DON'T UNINSTALL THE APP. Previous collection data should be preserved.

NOTE: 1DesignTool models use a licence allowing compilation/bundling in a game
or app, but not redistribution as standalone model files/model packs.
This downloader only supplies source URLs; binaries are downloaded directly
from the publisher onto your PC.

IMPORTANT: These five static models DO NOT contain walking skeleton animation.
Some may have difficult alpha-fur transparency and high triangle counts.
The red panda includes a LOG, so it is not suitable for free roaming until
its log is removed in Blender and the animal is rigged/animated.
This is an evaluation workflow, NOT an automatic photorealism guarantee.
