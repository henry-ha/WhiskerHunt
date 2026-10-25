# Hush Hunt v3.10.27 — build 90

ARCore 3D model pipeline replaced; no misleading sphere-only creatures.

- Added Android native textured GLB 2.0 renderer (`HushGlbAnimal3D.cs`) with GPU texture/material loading, actual triangular 3D mesh geometry, transforms and normal-based shading.
- Added 3 bundled, original, textured 3D example wildlife assets (Garden Snail, Amber Snail and Seven-spot Ladybird) plus reproducible model-generation script. These are not photogrammetry scans.
- Added explicit ARCore starter species picker. Unsupported species continue using 2D Safari instead of misleading generic blob shapes.
- Preserved ARCore hit testing, plane anchors, 360-degree viewpoint from walking around, and PixelCopy capture.
- Removed unused old ellipsoid renderer, left Live Capture and home themes untouched.
- Bumped Android app to 3.10.27 / build 90; updated asset version and service worker cache, preserving package ID and saved collections.

**Important:** Native device rendering is not verified; .NET 10/MAUI Android SDK unavailable in this environment. This release is a source build, not an APK. The new models are artistically generated textured GLBs; actual photo-quality 3D animal assets still need to be obtained with verifiable redistribution licences.
