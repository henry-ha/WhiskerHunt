Hush Hunt v3.10.36 Build 99 - AR UI + Shadow Fix

Included fixes:
1. Live Capture shutter button redesigned so the camera icon is centered and no longer clipped at the bottom.
2. Live Capture controls moved slightly further above the Android navigation area.
3. 3D Safari renderer now draws a soft ground shadow under the animal.

Edited files:
- WhiskerHunt/Platforms/Android/HushWideCameraActivity.cs
- WhiskerHunt/Platforms/Android/HushGlbAnimal3D.cs

Important:
This patch improves presentation, but it does NOT replace the existing low-detail wildlife GLB assets.
Disconnected paws/limbs, missing Labrador eyes, or simplified body shapes require better 3D model assets, not only code changes.
