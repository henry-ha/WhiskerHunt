# Hush Hunt — realistic wildlife upgrade (development source)

**This ZIP does not contain downloaded HD wildlife models.** It contains the known low-poly GLBs, a larger camera icon in the now-correct circular shutter, and a safe upgrade utility for importing licensed realistic models.

## To add properly modelled animals

On an internet-connected Windows computer:

1. Extract the **full source** ZIP and back it up.
2. Double-click `INSTALL_REALISTIC_WILDLIFE.bat`. This installs Python libraries and runs the automated model search/validator.
3. Read the console carefully. Only lines marked `INSTALLED` are genuine replacements. Models marked `NOT INSTALLED` stay unchanged.
4. Check the installed models visually using Visual Studio/AR Safari, since even high-polygon CC0 models can look wrong or contain poor textures.
5. Clean & Rebuild the solution. Deploy over the existing Android installation — **never uninstall** to protect collections.

The importer targets these exact animals: **red deer, Labrador, ginger tabby cat, and grey squirrel**. It never swaps a different species or breed, even if the collection contains a similarly named asset. It backs up originals in `RealisticAssetBackups/` (not included in the app bundle), records provenance, checks model size/geometry/GLB compatibility, and converts quantized/WebP glTF data into Hush Hunt's currently supported static glTF format.

**High-definition deer verified in catalogue:** https://3dassets.dev/assets/exotic-wildlife-hd-red-deer-stag-82f8d92a (CC0 1.0, ~20k triangles, static). Other exact models are searched at run time and installed *only if* title, CC0 license and geometry gate match. The app's current native renderer does not play skeletal animation or render full physically-based fur shading. No actual animal audio files are supplied.

If an exact model is unavailable from the online catalogue, you can download a compatible **GLB** from a source you are licensed to use and install it with:

`py tools\upgrade_realistic_wildlife.py --local grey-squirrel "C:\models\my-grey-squirrel.glb"`

Supported target keys: `deer`, `labrador`, `ginger-tabby`, `grey-squirrel`. For a model with an unusual hierarchy or skeleton, first export a static GLB with baked transforms and embedded texture maps from Blender. Do not automatically assume that Twinkl examples are licensed for incorporation.

To restore a model: `py tools\upgrade_realistic_wildlife.py --restore deer`

## Adobe Aero

Adobe discontinued Aero in Nov/Dec 2025. Its trigger design patterns can be recreated through Hush Hunt's ARCore (tap and swipe petting, proximity, placement, animation cues) but Aero itself is **not** bundled or an SDK dependency. The current renderer uses a static animal mesh and animated whole-body reaction, not limb skeletal motion.

## Testing status

Source-level check, Python syntax checks, test imports and ZIP integrity checks are possible here. External GLB downloads and Android runtime/build checks are not. HD models cannot be claimed as already installed in the delivered archive.
