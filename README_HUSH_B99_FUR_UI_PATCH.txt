Hush Hunt v3.10.36 Build 99 — Fur Material & Controls Repair
============================================================

This is a source-only correction for the current Hush Hunt solution.
It is NOT an APK or a pre-tested Android build.

WHAT CHANGED
- glTF 2.0 alphaMode MASK/BLEND now uses cutout/translucency, rather
  than forcing fur and whisker texture cards to be solid opaque pieces.
- Detects alpha-channel textures in legacy GLB fallbacks whose conversion
  discarded the material alpha mode. Does not remove the base meshes.
- Skips texture-dependent pieces if their texture cannot decode, rather
  than showing large untextured spikes.
- Fixed shader uniforms to be declared outside the fragment main() function.
- Original ARCore anchor placement, Walk, photo and petting controls remain.
- Redesigned 3D controls: circular rotate-left, centered resize + / -, and
  circular rotate-right on the sides at mid-height.
- Removed the surrounding navy size-control enclosure and the translucent
  bottom tray background. Does NOT remove the 2D, WALK or PHOTO buttons.

WHAT THIS CANNOT FIX AUTOMATICALLY
This cannot restore eyes, anatomy, alpha cutouts or fur information missing
from a model's SOURCE GLB or lost by the previous Trimesh fallback exporter.
Those animals must be re-exported from properly textured originals and
reviewed individually. HD GLBs have NOT been replaced in this patch.

INSTALL
1. Back up E:\inetpub\wwwroot\WhiskerHunt.
2. Extract this ZIP into E:\inetpub\wwwroot\WhiskerHunt, preserving paths.
3. Overwrite only:
   WhiskerHunt\Platforms\Android\HushArCoreActivity.cs
   WhiskerHunt\Platforms\Android\HushGlbAnimal3D.cs
4. Visual Studio: Clean Solution, then Rebuild Solution.
5. Deploy without uninstalling the existing app (protects saved collection).
6. Test Domestic Shorthair, Plains Zebra, Red Panda, Fox, and Garden Snail.

IMPORTANT
A successful ZIP check does NOT prove Android compilation or on-phone
visual quality. If the geometry is still wrong, do not ship that model to
users: the next step is replacing or re-exporting those specific GLBs.
