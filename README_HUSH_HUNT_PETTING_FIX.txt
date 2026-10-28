HUSH HUNT v3.10.36 / Build 99 — HD WILDLIFE PETTING REACTION REPAIR
27 October 2026

WHAT WAS ACTUALLY WRONG
The older OpenGL wildlife path already receives a petting progress value and
animates a wobble. The HD Filament path was not receiving that event at all,
so users saw a petting message but no reaction. The five original downloaded
Sketchfab GLBs contain no exported GLTF animation sequences, even though some
contain skeleton/skin data. Skeletons alone do not animate themselves.

THE FIX
- Connect the existing HushArCoreActivity.PetAnimal callback to a new JNI method
  in HushFilamentBridge and a new reactToPet(bool) event in HushFilamentOverlay.
- Apply 0.85-second damped left/right yaw, gentle roll and very small bounce.
- Cats react gently, puppies more enthusiastically, birds with subtle sway.
- Tap and swipe have slightly different motion and frequency.
- React in anchored world coordinates. No teleporting or altered world anchor.
- No GLBs, textures, lighting, UI, user collection, or saved photos are changed.
- The existing OpenGL fallback remains intact.

INSTALL
1) Save/backup the project and close Visual Studio.
2) Extract this ZIP directly into the solution root:
   E:\inetpub\wwwroot\WhiskerHunt\
   CHECK_PETTING_FIX.cmd, INSTALL_PETTING_FIX.cmd, and
   apply_hush_petting_fix.py should be next to WhiskerHunt.sln.
3) Run CHECK_PETTING_FIX.cmd to verify the source matches this patch.
4) Run INSTALL_PETTING_FIX.cmd (Windows Python or Python launcher required).
5) Clean Solution, Rebuild Solution in Visual Studio, deploy over existing app.
   Do not uninstall or clear app data.
6) Test Cat in Motion, Sumpitueslag Cat, Jack Russell Puppy and Phoenix Bird:
   after the model is visible, tap/pet the actual animal.
   A short left/right sway and slight bounce should play, then settle.

ROLLBACK
The installer creates:
    HushHunt_Petting_Backups\Petting_<timestamp>\
with the three original source files and a manifest.json.
To restore, run from your solution root:
    py -3 apply_hush_petting_fix.py --restore "<full backup folder path>"
then Clean/Rebuild/Deploy again.

LIMITATIONS
- This is a root-transform petting reaction, NOT skeletal tail wagging,
  individually articulated paws, walking cycles, or real wing flapping.
  For those, add usable baked glTF animation clips or author new keyframes.
- Original Sketchfab Phoenix GLB contains green in its base-colour texture
  and multicoloured feather art. Green is intentional; do not recolour.
- Tested against the project's supplied C#/Java sources for Build 99 and the
  most recent colour fix Java file. No Android build or live OnePlus test was
  possible in this environment. Please confirm on device.
- If the source differs from this version, the installer aborts instead of
  blindly overwriting your working custom changes.

WINDOWS PATH REPAIR — 27 OCT 2026
This package replaces the earlier installers that incorrectly passed %~dp0
(with its trailing backslash) as a Python command-line parameter. The Windows
command-line parser could then incorporate the closing quote and the --check
option into the directory name, causing WinError 123.

The corrected batch files pass --project "%CD%" after cd /d "%~dp0".
The installation does not require deleting any existing wildlife assets.

If CHECK says 'Could not find WhiskerHunt.sln', move the .cmd and .py files
into the directory that actually contains WhiskerHunt.sln. Don't run them
from a nested ZIP extraction folder.
