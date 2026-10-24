# Hush Hunt v3.10.0 — build 63

- Approved blue bunny-and-butterfly icon is now used for Android launcher icon, launch splash, website icon and in-app header.
- Updated all five Android mipmap density folders and MAUI icon source, so launcher icon generation and manifest point to the approved design.
- ARCore Safari now loads transparent PNG creature cutouts instead of the square Collection thumbnails.
- 2D Safari virtual wildlife overlays use transparent cutouts, and saved 2D Safari images composite that same cutout.
- Generated 146 transparent wildlife images in `safari_cutouts_v63/` for offline Android/WebView use.
- The Collection card artworks remain unchanged (full coloured backgrounds).
- Preserved package ID, saved discoveries, camera rules and backup format.

## Limitations
Automated masking is an illustration cutout process. Some animals have fine translucent wings or pale fur that may need additional manual refinement. The Android ARCore view and splash require real phone verification; the container has no .NET Android compiler.
