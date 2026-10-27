HUSH HUNT | FIVE NEW SKETCHFAB MODELS | v3.10.36 Build 99
========================================================

WHAT IS IN THIS PACKAGE
 - Five exact GLBs supplied by the user, copied without geometry or texture changes.
 - A Python standard-library installer and a Windows click-to-run launcher.
 - Five new 3D Safari picker entries, not replacements.
 - A model manifest, provenance information, and backups for changed JS/JSON files.

INSTALL
 1. Back up your E:\inetpub\wwwroot\WhiskerHunt solution first.
 2. Extract the ZIP into E:\inetpub\wwwroot\WhiskerHunt (solution root).
    The extracted folder is Sketchfab_Five_Additions.
 3. Double-click Sketchfab_Five_Additions\ADD_SKETCHFAB_3D_ANIMALS.cmd.
 4. You should see five VALID checks and a summary ending INSTALLED.
 5. Open Visual Studio. Clean then Rebuild the solution and deploy to your phone.
    Do NOT uninstall the current app or clear its app data.

ALTERNATIVE COMMAND
 py -3 Sketchfab_Five_Additions\install_sketchfab_five.py --project E:\inetpub\wwwroot\WhiskerHunt

FIVE NEW PICKER ITEMS
 🔥 Phoenix Bird (Fantasy)       -> fantasy-phoenix-bird.glb
 🐈 Sumpitueslag Cat             -> cat-sumpitueslag-cat.glb
 🐈 Cat in Motion (Static)       -> cat-cat-in-motion.glb
 🦅 Bald Eagle Catching Fish     -> bird-bald-eagle-catching-fish.glb
 🐕 Jack Russell Puppy           -> dog-jack-russell-puppy.glb

ORIGINAL UPLOADS RETAINED
 User's original 5 GLBs remain in the staging folder.  We never change
 existing Hush Hunt GLBs or generated fallback models. The primary models
 are copied to WhiskerHunt/Resources/Raw/ar_models/ using unique filenames.

KNOWN LIMITATIONS
 - The original GLBs contain no baked glTF animation clips.  'Cat in Motion'
   is a model title, NOT functional walking animation.
 - Cat in Motion: ~390,000 triangles and 30 MB, heavy on mobile.
 - Jack Russell Puppy: ~674,000 triangles and 37 MB, very heavy on mobile.
 - Bald Eagle asset includes a catching-fish scene/pose.
 - Phoenix is a FANTASY animal, not a real wildlife species.
 - GLBs contain textures, but material/shader compatibility and 3D rendering
   on the OnePlus phone have not been tested. Some effects may differ.
 - This installs assets and adds picker entries; it is NOT a verified APK.
 - Review the original Sketchfab asset licence (including whether commercial
   use is allowed and what credit is required) before distribution.
 - The installer may safely be run again; it detects previously added items.

ROLLBACK
 Backups of modified JS / manifest files are saved with a
 '.before-sketchfab-<date>.bak' suffix in their original folder.
 Original GLB filenames were never replaced; to hide new species, restore the
 backed-up JS and installed_species.json files and rebuild.

Do not run the old one-sweep installer AFTER this installation without
 checking whether it rewrites app_v99.js / installed_species.json.
