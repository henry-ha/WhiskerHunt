# v3.10.27 / Build 90 — Test results

- PASS: JavaScript syntax parses using `node --check`.
- PASS: new Android entry `index_v90.html` references `app_v90.js` and `style_v90.css`.
- PASS: `index.html` and MAUI app reference the new asset versions.
- PASS: three bundled starter GLB files parse as valid glTF 2.0 binaries with internal buffer/textures and triangle meshes.
- PASS: three ARCore species keys exist in wildlife model catalogue; no made-up model identity.
- PASS: native renderer references `HushGlbAnimal3D` and does not invoke the old `HushAnimal3D` blob class.
- PASS: unchanged Android application ID, capture handoff, and collection state logic.
- NOT RUN: .NET compilation (dotnet/MAUI Android SDK unavailable in this execution environment).
- NOT RUN: OnePlus 11 / Android 16 real GL texture/ARCore surface capture.
- LIMITATION: starters are textured sculpt-style GLB prototypes, not realistic photogrammetry wildlife; native rigging/animations not supported.
