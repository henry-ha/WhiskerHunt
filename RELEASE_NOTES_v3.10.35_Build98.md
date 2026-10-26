# Hush Hunt v3.10.35 (proposed Build 98) – targeted wildlife realism & UI fixes

## Included fixes
- **Profile page terminology migration**
  - Existing default profile name `Cat Explorer` auto-migrates to **Wildlife Explorer**.
  - Profile avatar changed from cat to compass.
  - Main stat label changed from `Cats` to **Discoveries**.

- **Live Capture shutter button**
  - Replaced the emoji-text shutter with a native Android **camera icon button**.
  - Increased the shutter button size and padding to prevent the icon appearing clipped at the bottom.

- **3D Safari Ginger Tabby selection hardening**
  - Added key alias handling so Ginger Tabby cannot silently fall back to the default ladybird when a cat-specific key variant is supplied.

- **2D Safari worm preview**
  - Replaced the problematic `other-worm.png` cutout with a better framed version so the worm preview is no longer visibly chopped/cropped.

- **Bundled 3D animal asset refresh**
  - Rebuilt these GLB models with smoother geometry and better-connected body parts:
    - Grey Squirrel
    - Ginger Tabby
    - Labrador
    - Fox
    - Deer
    - Mouse
  - Improvements include more rounded meshes, neck/body connectors, better limb attachment, squirrel ears, and less “floating parts” appearance.

- **Native 3D shading improvement**
  - Updated the OpenGL fragment shader to use stronger key/fill lighting plus a light rim highlight.
  - Result: models should read with more depth and shape instead of looking as flat.

## Limitations / blocker note
- These changes improve the current **stylised low-poly** wildlife pipeline.
- They do **not** turn the animals into fully photoreal furry/scanned models.
- To go substantially beyond this, the project needs a different content pipeline (higher-quality authored meshes/textures or licensed 3D wildlife assets).

## Files changed
- `WhiskerHunt/Resources/Raw/index.html`
- `WhiskerHunt/Resources/Raw/app_v98.js`
- `WhiskerHunt/Resources/Raw/style_v98.css`
- `WhiskerHunt/Resources/Raw/safari_cutouts_v85/other-worm.png`
- `WhiskerHunt/Platforms/Android/HushWideCameraActivity.cs`
- `WhiskerHunt/Platforms/Android/HushGlbAnimal3D.cs`
- `WhiskerHunt/Resources/Raw/ar_models/squirrel-grey-squirrel.glb`
- `WhiskerHunt/Resources/Raw/ar_models/cat-ginger-tabby.glb`
- `WhiskerHunt/Resources/Raw/ar_models/dog-labrador.glb`
- `WhiskerHunt/Resources/Raw/ar_models/other-fox.glb`
- `WhiskerHunt/Resources/Raw/ar_models/other-deer.glb`
- `WhiskerHunt/Resources/Raw/ar_models/other-mouse.glb`
