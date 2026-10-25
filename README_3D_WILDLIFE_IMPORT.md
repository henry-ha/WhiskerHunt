# Hush Hunt v3.10.31 (build 94) — realistic wildlife asset workflow

## What's actually in this ZIP

**Five existing ARCore assets** are still bundled: garden snail, amber snail, seven-spot ladybird, garden spider, garden slug. These are hand-built textured prototypes, **not photorealistic**. The newly added ability to import more third-party GLB wildlife assets is **ready in the source**, but external commercial-quality meshes **could not be downloaded in this workspace**. Do not call this a 239-model ARCore release.

## One-click import on your Windows development machine

1. Extract the source archive to a writable folder.
2. Double-click `INSTALL_CC0_WILDLIFE.bat`. It will install the Python libraries if missing, read the CC0 manifests, download only explicitly matched models, and convert them into GLBs that this native Android renderer understands.
3. Read its terminal output: **INSTALLED** means imported; **NOT AVAILABLE** or **SKIPPED** means that animal remains in 2D Safari.
4. In Visual Studio, **Clean**, then **Rebuild** and deploy `WhiskerHunt/WhiskerHunt.csproj` on your Android device. Keep the same package ID and **do not uninstall** if you want to retain your collections.
5. Open AR Safari → ARCore → choose the installed animal. The selector lists only files that were successfully imported and validated.

Command line alternative:

```powershell
py -m pip install trimesh Pillow numpy
py tools\import_cc0_wildlife.py --download
```

To update the native picker after adding your own compatible models:

```powershell
py tools\import_cc0_wildlife.py
```

**Current catalog:** `tools/cc0_candidate_species.json` contains 22 researched candidate matches, not 22 installed models. Some may be unavailable. Most are static poses, **not animated**. Source packs are from <https://3dassets.dev/packs/companion-animals-and-pet-home>, <https://3dassets.dev/packs/pets-and-companions-hd>, and <https://3dassets.dev/packs/exotic-wildlife-hd>, whose publisher advertises CC0 1.0. Verify source quality and current license before distributing a build. A portion of the pets pack is **stylized rather than photorealistic** and should only be kept if it meets your visual standard. The script never downloads another Sketchfab creator's model without a license.

**Technical detail:** the original GLBs from those packs often have `KHR_mesh_quantization` and WebP texture extensions. Hush Hunt's custom Android loader currently requires **unquantized floating-point vertex attributes and PNG/JPEG textures**. The importer uses Trimesh/Pillow to normalize those meshes for this particular renderer and validates the exported GLB. It cannot support rigged animations yet, and it does not claim physically based environmental lighting or photo-scanned detail.

**Educational accuracy:** only exact catalog variants are selectable in native AR. No animal is misrepresented using a blob or another species model. Species that still have no suitable GLB remain available in 2D Safari. Reaching all 239 varieties will need many individually matched, licensed and quality-checked assets, plus animation-capable/PBR engine support.

**Tested here:** source syntax, five packaged GLBs, sample GLB import normalization, picker generation, ZIP integrity. **Not tested here:** downloading new files (no external network access in this build environment); Windows installation; full Android compile; runtime ARCore rendering on OnePlus 11.
