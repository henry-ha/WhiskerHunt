HUSH HUNT - FULL-LIBRARY REALISTIC WILDLIFE UPGRADER (27 October 2026)
===================================================================

WHAT THIS PACKAGE REALLY DOES
- Contains a 61-slot catalogue matching Hush Hunt's source GLB filenames.
- Can automatically fetch EIGHT previously researched, direct-download GLBs
  (Red Panda, Plains Zebra, Grey Wolf, Fox, Red Kangaroo) onto YOUR Windows PC.
- Can STAGE any licensed GLB you download for the other 53 slots.
- VALIDATES GLB header, embedded textures/materials, rough geometry size,
  extensions and known rendering risks.
- Requires your explicit visual approval (eyes, anatomy, fur, scale, pose,
  unwanted scenery) and licence confirmation before ANY replacement.
- Backs up each installed file by timestamp and SHA256; supports rollback.
- Writes a CSV report of all 61 slots, including which replacements were made.

WHAT IT DOES NOT DO
- Does NOT include 61 new realistic models. Eight verified candidate URL entries
  are available to attempt to download; 53 need sourced/licensed individually.
- Does NOT automatically download from Sketchfab, Fab or CGTrader without
  authentication or purchase. DO NOT bypass licences or redistribute paid GLBs.
- Does NOT make static GLBs walk naturally; this requires animation/rigging.
- Does NOT fix incompatible Android shaders, normals or Filament PBR setup.
- Does NOT guarantee all animals will LOOK good: viewer and phone review needed.

INSTALL
1. BACK UP E:\inetpub\wwwroot\WhiskerHunt (especially Resources\Raw\ar_models).
2. Extract ALL this package's files DIRECTLY into your solution folder,
   such that START_WILDLIFE_UPGRADE.cmd is alongside the WhiskerHunt project folder.
   It does not overwrite your project C# files or existing GLBs.
3. Double-click START_WILDLIFE_UPGRADE.cmd (Python 3.9+ needed).
4. Choose 1 to list all 61 assets, and 2 to fetch the known eight candidates.
5. Open each staged candidate in Blender or a GLB viewer. Never approve an
   animal with missing eyes, exploded fur, broken feet or inappropriate props.
6. Choose 5 to approve one candidate at a time; use 6 to simulate all installs;
   use 7 to install ONLY those you've individually approved.
7. In Visual Studio: Clean, Rebuild, Deploy OVER the existing installation.
   DO NOT uninstall Hush Hunt or clear its app data.
8. Test Red Panda/Gorilla/Zebra in AR. Option 8 restores a previous asset.

FOR OTHER REALISTIC MODELS
- Obtain a compatible, appropriately licensed .glb from a creator or store.
- Choose 4 in the menu and give the EXACT Hush Hunt asset slot filename.
- Enter the creator, model page, and precise licence information.
- Inspect and approve before installation.
- The provided WILDLIFE_61_SLOTS.json contains all exact filenames plus
  research leads for Gorilla, Zebra and Red Panda.

COMMAND LINE
py -3 tools\hush_full_wildlife_upgrade.py list
py -3 tools\hush_full_wildlife_upgrade.py fetch all
py -3 tools\hush_full_wildlife_upgrade.py audit
py -3 tools\hush_full_wildlife_upgrade.py stage other-silverback-gorilla.glb "C:\Assets\gorilla.glb" --source "Creator" --license "CC BY 4.0" --page "https://..."
py -3 tools\hush_full_wildlife_upgrade.py approve other-silverback-gorilla.glb --yes-i-reviewed-anatomy
py -3 tools\hush_full_wildlife_upgrade.py install all --dry-run
py -3 tools\hush_full_wildlife_upgrade.py install all --yes
py -3 tools\hush_full_wildlife_upgrade.py restore other-silverback-gorilla.glb --yes

IMPORTANT LIMITATION
With marketplace models, rights to use a GLB inside a game/app do not necessarily
permit republishing the raw downloadable GLBs. The automatic fetches download
only to your PC, never distribute third-party GLB assets in this ZIP.
