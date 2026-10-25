# Hush Hunt v3.10.30 — Android build 93

## Changes
- Native Live Capture zoom capsule uses WRAP_CONTENT rather than the Android default MATCH_PARENT; 0.6x, 1x, 2x, 3x controls remain touch-sized at 53dp wide and the capsule is visibly narrower.
- Circular shutter reduced 76dp → 70dp and camera toolbar lifted another 18dp (bottom margin 94dp → 112dp) to ensure it sits above the Android nav bar. Pinch zoom, Camera2 camera handling and existing photo capture flow unchanged.
- ARCore starter list expanded from 3 to 5 species-specific textured GLB models: **Garden Snail, Amber Snail, Seven-spot Ladybird, Garden Spider, Garden Slug**. The two additional models are original stylised textured prototypes, not photogrammetry or species-grade scientific reconstructions.
- Tapping the main ARCore launch defaults to the ladybird, so the experience no longer starts with a snail most of the time. Individual animal buttons launch the matching 3D model directly. 2D Safari remains separate.
- Existing working native ARCore tracked-surface renderer and captures are unchanged. Home themes, user collections, Android ApplicationId and stored data schema remain unchanged.
- Updated app to v3.10.30, build 93. Web asset entrypoint versioned to `index_v93.html`, `app_v93.js`, `style_v93.css` to prevent stale startup.

## Important limitations
- New original animal models are textured and genuinely three-dimensional, but not photorealistic or biologically verified. All 5 require physical-device testing. No model is fabricated for an unsupported species.
- Source validation is not an Android compile or on-device verification; the Windows .NET MAUI Android workload and OnePlus 11 device are unavailable here.
- Deploy over the existing application to preserve the collection. Do not uninstall.
