# Hush Hunt v3.8.5 · build 49 — Experimental native ARCore Safari

## What's new

- Native Android ARCore Safari launched from a new **AR Safari → ARCore • Real surfaces** choice.
- Uses a Google Play Services for AR `Session`, camera image on an OpenGL ES `GLSurfaceView`, real detected plane hit-tests, and `Anchor` tracking.
- Tapping a floor/table attaches the creature's **2D field-guide illustration** to that real-world anchor. As the phone moves, the illustration is reprojected using ARCore camera view/projection matrices. This is **2.5D anchored artwork, not a 3D skinned creature model**; no AR depth occlusion or physical shadows are implemented.
- **Collect** composites the illustration into the AR camera frame and passes one JPEG to the existing **virtual discovery** naming/saving workflow. Does not grant live wildlife discovery credit.
- Google Play Services for AR install prompting; requests camera permission; AR-only app support is optional rather than required. Can choose existing **2D Safari** at any time.
- ARCore privacy notice; no device location permission needed for tracking and no image uploaded by the new ARCore activity.
- Version 3.8.5 / Android build 49. Preserves `uk.whiskerhunt.mobile`, `whisker-hunt-state.json`, and all historical collection/backup formats. Native WebView shell flag remains enabled.

## Integration and limits

- The Android project references **XPACE.Google.ARCore 1.41.0** (NuGet). Internet access for NuGet restore is needed in Visual Studio.
- **Not compiled in this environment:** .NET/Android SDK and the ARCore runtime are unavailable here. The ARCore surface, renderer and camera handoff need an actual supported Android phone test. See `HushHunt_v3.8.5_TEST_RESULTS.md`.
- OnePlus 11 testing checklist: NuGet restore, compile, permission prompt, optional Google Play Services for AR install, surface placement, device-move tracking, photo collection, and 2D fallback. Report any compiler errors verbatim.
- The older **2D camera overlay Safari** continues to be the stable mode for unsupported phones and browsers.
- No changes to database tables or original save identifiers. Don't uninstall the app.
