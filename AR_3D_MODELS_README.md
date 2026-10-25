# Hush Hunt — ARCore textured wildlife GLB pipeline (v3.10.27 / build 90)

This release **replaces** the previous run-time ellipsoid/blob renderer with a native OpenGL ES 2.0 textured GLB model loader. Animals are fixed to a real ARCore world anchor; you can walk around the model and capture it against the real camera view.

## Bundled starter wildlife models

* `snail-garden-snail.glb` — original sculpt-style model with a marked, rounded shell, antennae and eyes
* `snail-amber-snail.glb` — original amber-shelled color variation
* `ladybird-seven-spot.glb` — original domed insect with legs, spots and antennae

These three are custom, independently generated **recognizable textured prototypes**, not photo-scanned/photorealistic wildlife.  They are provided under CC0 1.0 by the generator in `tools/generate_starter_models.py`.  Source script and generated GLBs are in this ZIP; no external content was downloaded or redistributed.

## Adding a genuine photorealistic species (asset workflow)

1. Acquire an appropriately licensed 3D asset from a wildlife scan, a professional artist or a model library. Confirm redistribution rights and attribute as the licence requires. Do not confuse a photograph with a 3D asset.
2. Export in **glTF 2.0 Binary (`.glb`)** format, **single binary file**, **static triangle meshes**, fully embedded PNG or JPEG **base-color textures**, no Draco compression, no morph targets, no skeletal skinning. To show a rigged animal, bake the pose and export a static mesh for now.
3. Convert to **Y-up**, rest pose with feet at ground level and front oriented +Z. A physical scale/profile should be defined per animal.  Images are handled as real textured geometry, not sprites.
4. Name as `<family>-<variety>.glb` using lowercase words with hyphens matching the in-app species labels, e.g. `bird-robin.glb`, `squirrel-grey-squirrel.glb` or `frog-common-frog.glb`.
5. Put the asset under `WhiskerHunt/Resources/Raw/ar_models/`. `WhiskerHunt.csproj` already includes `Resources/Raw/**` as MAUI assets.
6. Add its **existing exact** key from the `HUSH_AR_CATALOG` / `AR_CAT_MODELS` in `app_v90.js` to `HUSH_NATIVE_3D_STARTERS`. Add an optional per-model calibration to `TryLoad` in `HushGlbAnimal3D.cs`; currently the size is a safe on-screen viewing size, not claimed to be physical scale.
7. Build with Visual Studio (Windows) and .NET MAUI Android workload; test model placement and photos on device.

## Status / limitations

- **Implemented in source:** embedded GLB decoding, vertex positions/normals/UVs, base-color textures, base-color tints, indexed triangle conversion, node transforms, native GPU rendering, ARCore anchors, and existing PixelCopy image capture.
- **Intentionally unsupported:** external GLB URI fetches, Draco, KTX2, skeletal/rigged animation, physically based environment lighting, realistic fur transparency, complex material extensions, glTF embedded non-triangle primitives and contact occlusion.
- **No misleading blob fallbacks:** unknown species remain in 2D Safari until a matching real 3D asset exists. Unsupported or corrupt models return an explanatory message.
- **Not tested here:** the Android package cannot be compiled or installed in this runtime because the .NET SDK and MAUI Android workload are not installed. The OnePlus 11 / ARCore runtime and GPU output still require device testing.
- **User data:** keep the same application ID `uk.whiskerhunt.mobile`; the JavaScript app state and Android backup/capture pathways were not reset.

## Attributions for third-party replacements

Record creator, download URL, licence, modification status, and licence copy for every newly acquired file. Avoid bundling an asset until licensing is verified. The original starter meshes generated in this project do not require outside attribution.
