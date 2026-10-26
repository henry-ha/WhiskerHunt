# Hush Hunt v3.10.32 — Build 95 patch for existing projects

**Choose this patch if you already installed the extra 3D wildlife with the CC0 importer.**

1. CLOSE Visual Studio and make a backup of your current `WhiskerHunt` source folder.
2. Extract this patch ZIP **into the project root** (the directory containing the `WhiskerHunt` and `tools` folders), allowing the changed source files to overwrite old ones. Do **not** delete the existing project or `WhiskerHunt/Resources/Raw/ar_models/` directory.
3. Run `REFRESH_ARCORE_MODELS_V95.bat` from that root. It does **not** download animals: it scans your existing local GLBs and updates `app_v95.js` to list every installed exact match. It should say `Ready for ARCore: 21 exactly matched species` on the PC where you previously imported 16 extra models.
4. Open `WhiskerHunt/WhiskerHunt.csproj` in Visual Studio, Clean, Rebuild and deploy **over** the existing Android app **without uninstalling**. Look for v3.10.32 / build 95.
5. Test 2D Safari close, 3D animal zoom, plane placement, and photo capture on your phone.

**What changed**: simplified ARCore prompts, spaced and rounded bottom buttons, compact 3D size zoom (+/- and pinch), and 2D Safari close alignment. Zoom changes the virtual animal's size and is not optical camera zoom. The supplied GLB meshes and textures remain unchanged; this update does not turn low-poly assets into photorealistic 3D animals.

**Important**: The complete source ZIP contains only the five original ARCore starter models. Applying the full ZIP over your folder rather than this patch risks overwriting your local `ar_models/` content. Any new model must have valid redistribution rights. This source was not compiled or tested on Android in this environment.
