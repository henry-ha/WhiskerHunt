# Hush Hunt v3.10.28 · Build 91 — Android Source

## Addressed

- Native ARCore **2D Safari** button now returns a distinct `2d` result rather than the `fallback` result reserved for failed or unavailable 3D assets. The web app immediately launches picture-based Safari without showing the erroneous **“3D wildlife not ready”** sheet.
- Native 3D rendering initializes the GLB shaders and textures with additional validation and reporting. Placement no longer immediately enables Capture. Capture is enabled after a GL draw has completed without a reported OpenGL error. Failed GPU initialization or draw now displays a useful status instead of silently allowing an empty photo.
- Live Capture uses four **small rounded zoom pills**, one circular camera shutter, a quick white shutter-flash effect and a red circular close control. It removes the large opaque capture panel and preserves touch/pinch camera interactions.
- All 20 approved Home themes and saved wildlife collections remain unchanged. Package ID and existing storage schema preserved.

## Important remaining test / limitations

- **The Android APK was NOT compiled or run** in this environment. Please rebuild in Visual Studio and report any compiler errors.
- **ARCore model visibility is not yet confirmed on a real phone.** Draw-status checks detect API errors but cannot guarantee that a model is visible. Test Garden Snail on a well-lit floor; if the status says rendered and the animal is still missing, capture Android Logcat filtered to `HushHuntAR` and note whether Capture becomes enabled.
- Only Garden Snail, Amber Snail and Seven-spot Ladybird have original textured GLB starters. Other animals intentionally use 2D Safari; no fabricated blob models are added.
- The shutter flash is cosmetic and does not change the saved photo. A throwable item/gesture is not included; the central camera button provides one easy capture action.

## Installation

Open `WhiskerHunt/WhiskerHunt.csproj` in Visual Studio and **Clean + Rebuild**. Deploy on top of the existing app; **do not uninstall**, to retain saved collections.
