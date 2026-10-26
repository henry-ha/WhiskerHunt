# Hush Hunt · build 99 maintenance patch — regressions restored

**What changed**

- Restored these actual GLB files from the earlier v3.10.34 / build 97 source archive, before the build 98 geometry replacement: `other-deer.glb`, `dog-labrador.glb`, `squirrel-grey-squirrel.glb`. This recovers the earlier geometry, including the deer lower limbs and Labrador facial details. They remain stylised, not photorealistic.
- Native 3D Ginger Tabby: the 3D picker now checks the explicit bundled-file manifest instead of the unrelated 2D breed catalogue; `getArModel('ginger-tabby')` resolves to a stable Ginger Tabby entry. A 2D combination `american-shorthair-ginger-tabby`, when explicitly passed to native 3D, uses the installed **generic Ginger Tabby visual**, not a breed-certified American Shorthair. No claim of breed realism.
- Live Capture button: complete 34dp camera icon restored; 78dp perfect oval shutter in a 102dp explicit holder. Removed the top-margin layout that could clip its lower circular border. Circle is slightly smaller than the previous 86dp shell; icon is not reduced.

**Files changed**

- `WhiskerHunt/Platforms/Android/HushWideCameraActivity.cs`
- `WhiskerHunt/Resources/Raw/app_v99.js`
- `WhiskerHunt/Resources/Raw/ar_models/other-deer.glb`
- `WhiskerHunt/Resources/Raw/ar_models/dog-labrador.glb`
- `WhiskerHunt/Resources/Raw/ar_models/squirrel-grey-squirrel.glb`

**Limitations**

- Ground squirrels naturally use four legs while running; they can sit upright on hind legs when inspecting food or their surroundings. This update restores the previous squirrel asset rather than claiming to add a new upright animation. Rigged species-specific standing motion requires a new rigged GLB and animation-capable renderer.
- The restored models are not photorealistic. External detailed assets and an upgraded PBR/animation renderer are still needed to reach the supplied Twinkl-quality visual standard.
- No runtime Android compilation/device testing was performed in this environment. Please Clean then Rebuild in Visual Studio.
- Do not uninstall the app, change its package ID or signing certificate. Keep a collection backup before upgrades.
