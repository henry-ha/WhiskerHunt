# Hush Hunt: Realistic 3D Wildlife - research and import shortlist

Research date: 27 October 2026. Prioritise previewing face, eyes, ears, paws, silhouette, fur and texture maps **before** replacing a model. Developer claims and web previews are not equivalent to on-device acceptance testing.

| Priority | Animal(s) | Publisher and candidate | Source | Licence / pricing | Technical notes |
|---|---|---|---|---|---|
| 1 | Red panda | **Lesser Red Panda**, Nyi Nyi Tun on Fab | https://www.fab.com/listings/7088dc2e-ee62-45b1-a5ef-a29d65f4120e | Commercial marketplace model; obtain and review licence before use | Advertised 34,160 tris, 4K PBR, rigged, ~30 animations, GLB/glTF included. No trustworthy user rating established. Best feature fit to Walk/Pet. |
| 2 | Red panda | **Red Panda** by kenchoo on Sketchfab | https://sketchfab.com/3d-models/red-panda-c003c2985e0e462684063a893a0e85ee | CC BY (attribution required). Authenticated Sketchfab download. | 82.4k tris; 55 likes, 1,155 downloads; simple animation. Inspect actual textures/quality and provenance. |
| 3 | Gray Wolf, Brown Bear, Red Deer, Fox, others | **Animalia - Starter Kit**, GiM on Fab | https://www.fab.com/listings/2c7944a6-8b49-4c0b-9ad1-108e1637a8a9 | Marketplace licence; not safe to redistribute the source models freely | 4.8/5 (4 ratings); 4K textures for major mammals, 2K for fox; real 60fps animations. Listed format Unreal Engine only, conversion/export feasibility must be verified. |
| 4 | Wolf | **WOLF**, PROTOFACTOR INC on Fab | https://www.fab.com/listings/3d8068ff-7d46-4fd2-966b-cfc25c769655 | Marketplace licence | 5.0/5 (1 rating); 4 LODs, 4K textures, 17 animations. Unity and Unreal formats, needs conversion/test for Android. |
| 5 | Broad selection | **Animal Pack Ultra**, JanPecnik on Fab | https://www.fab.com/listings/a29a8f63-d025-4a00-ab86-75b05667671b | Marketplace licence; UE-specific | 4.8/5 (133 ratings); 32 animated animals, aimed at PC. Not automatically phone-ready. |
| 6 | Gorilla | **Free Gorilla**, Filip on Sketchfab | https://sketchfab.com/3d-models/free-gorilla-ad28003205884841a028e80edb4089ef | CC BY, attribution required | 44.3k tris, 72 likes, 5,215 downloads. Download through Sketchfab, inspect realism first. |
| 7 | Zebra | **Zebra**, Direct Dimensions on Sketchfab | https://sketchfab.com/3d-models/zebra-bd7258ee007b4e0fb521abb74bfa99d0 | CC BY, attribution required | 15.2k tris, photos of a sedated zebra used for photogrammetry; accurate silhouette possible. Foal proportions, not full adult. |
| 8 | Zebra | **Zebra - Rigged**, Noa Seller on Sketchfab | https://sketchfab.com/3d-models/zebra-rigged-5d6ff2749afc438b9989f91ecb242574 | CC BY | 12.3k tris, 66 likes, hand-sculpted and rigged; not confirmed animated. |
| 9 | Red panda, Zebra, Wolf, Fox, Kangaroo | **1DesignTool Animals** - five individual models | https://1designtool.com/3d/models/red-panda | Free to embed in an app/game; NO redistribution as standalone models or model pack | Explicit JPEG/PNG textures, eyes and fur details; available via included downloader. All static and agent-generated. Potential upgrade, but real visual quality must be tested. |

**Avoid:** game character rips, copyrighted character models, CC BY-NC/ND for paid apps, AI-generated models with distorted anatomy, raw Blender particle fur that cannot be exported to glTF without baking, and sketchy uploaders with no verified permissions.

## What must work in Hush Hunt

- glTF 2.0 GLB, triangles, UVs, colour/normal/roughness textures, correctly rendered `alphaMode=MASK`/`BLEND` where fur cards are used.
- Eyes must visibly render; head/legs/paws must be attached and have sensible physical proportions.
- PBR lighting: indirect + directional, ambient/exposure tuned, no inverted normals, no duplicated material layers.
- Animations: `idle`, `walk`, `turn`, `pet reaction` need rigs and glTF animation clips. Static models may look good but **cannot walk realistically**.
- AR anchoring: model stays fixed in world coordinates as phone moves, rotates about its own pivot, correct scale and ground height, shadow follows model.
- Prefer 1K/2K textures and LODs for the OnePlus 11; 4K assets may be too memory-intensive if many are loaded concurrently.

## Licences

1DesignTool: https://1designtool.com/3d/license (apps allowed; standalone model redistribution forbidden)

Sketchfab download and licensing: https://sketchfab.com/licenses ; respect CC BY attribution and author rights.

Fab: https://www.fab.com/eula ; licensed files can generally be incorporated in projects under applicable tier, but don't redistribute raw models as a separate pack.
