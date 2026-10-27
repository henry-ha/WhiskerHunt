HUSH HUNT 3D SAFARI — MATERIAL COLOUR RECOVERY
Version: 3.10.36 (Build 99 source patch); 27 October 2026

WHAT YOUR SCREENSHOTS SHOW
- Cat fur colours and markings are washed out to near-white, including cats
  whose embedded baseColor texture is actually patterned brown and black.
- Jack Russell and Kangaroo also appear overexposed; Phoenix appears pastel.
- The existing Filament Java renderer uses f/4, 1/80 s, ISO 100 together with
  a 30,000-lux directional light and 16,000-lux ambient light. Those settings
  are not matched and can saturate the baseColor textures.
- Two imported models, Cat in Motion and Phoenix, ALSO have high emissive
  material factors [1,1,1]. That adds self-illumination on top of the lighting.

CHANGES INCLUDED
1) HushFilamentOverlay.java — camera exposure f/8, 1/125 s, ISO 100;
   initial directional light 24,000 lux; ambient fill 6,500 intensity;
   dynamically estimated main light capped to prevent sudden blow-outs.
2) cat-cat-in-motion.glb — removed unwanted material emission. Original
   mesh, UV maps, texture images, normals and animations preserved.
3) fantasy-phoenix-bird.glb — emission lowered to 5% so feather colouring
   is visible. Original geometry and embedded textures preserved.

WHY THE WHITE CAT WAS NOT DELETED
Sumpitueslag Cat has several real coloured baseColor textures. It does NOT
have the extra self-illumination problem. Therefore the correct fix for it is
Filament lighting, not replacing its textures or painting it darker.
The puppy, kangaroo and meerkat also use the lighting correction automatically.
Do NOT install lower-quality fallbacks in place of existing HD models.

INSTALLATION (does NOT uninstall your app)
1. Back up your entire Hush Hunt solution folder.
2. Extract this ZIP into E:\inetpub\wwwroot\WhiskerHunt\
   You should see INSTALL_COLOR_FIX.cmd in that solution folder.
3. Close Visual Studio, run INSTALL_COLOR_FIX.cmd (a backup is generated).
4. Reopen Visual Studio: Clean Solution, Rebuild Solution, deploy over the
   installed Hush Hunt app. DO NOT uninstall or clear its data.
5. Compare Sumpitueslag Cat, Jack Russell Puppy, Phoenix, Cat in Motion and
   Kangaroo under the SAME room lighting, ideally at 1x before 3x zoom.

RESTORE
Use RESTORE_COLOR_FIX.cmd in the same folder to restore the exact previous
Java and GLB files from the last installer backup, then clean/rebuild/deploy.

WHAT WE CAN AND CANNOT CLAIM
GLB 2.0 header, embedded image counts, unmodified binary geometry and
material edits were independently checked. The revised Java code is source-
checked but an Android SDK / OnePlus runtime wasn't available for a device
build or full visual calibration. The models can still be intrinsically
stylized rather than photorealistic. If colours remain white even with these
lighting and emissive changes, capture HushFilament logcat entries and verify
that this Java source was actually included in the deployed APK.
