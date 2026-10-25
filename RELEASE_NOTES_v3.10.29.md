# Hush Hunt v3.10.29 — Build 92 (source release)

## Repairs
- Native Live Capture: zoom buttons are tighter (59dp instead of 64dp); shutter is smaller and the control dock is raised 27dp to prevent Android navigation from cutting off the circular shutter.
- Live Capture: photo JPEG processing now runs on a worker task instead of blocking Android's UI thread. The capture payload is limited to 1800px for faster transport and the camera activity closes on the UI thread.
- Capture-to-discovery: a temporary dark processing screen is retained behind the native camera and removed once the species-identification sheet is ready, avoiding a Home-screen flash. A 12-second failsafe prevents a stuck overlay on decode failures.
- 2D Safari: all 148 bundled creature cutouts were inspected for transparency-bounds touching the image edges. Tree Frog and Blue Morpho were padded/recentered. Drawing into AR souvenir JPEGs now preserves original aspect ratios rather than squeezing to 370x370, and Safari images use object-fit: contain. NOTE: padding cannot reconstruct anatomy already absent in an original asset; artist-replaced assets are still needed for any intrinsically incomplete drawings.
- 2D Safari: multi-line New Discovery/rarity labels centered. The modal close button is red and circular.
- Native ARCore: a red close button is aligned to the top-right. The renderer now clears GL_DEPTH_BUFFER_BIT along with GL_COLOR_BUFFER_BIT every frame and disables depth testing while drawing the camera image; this fixes an identified source bug that could hide models behind stale depth data. Model render status no longer falsely guarantees that the animal is visible on screen.
- Versioned entry point, JS and CSS: MainPage.xaml now loads index_v92.html -> app_v92.js + style_v92.css. App version 3.10.29, Android version code 92.

## Limitations and next verification
- Android compilation and actual ARCore device rendering cannot be tested in this container (Android/.NET MAUI workload is not installed).
- The depth-buffer fix is a grounded rendering correction; it is not proof that GLB models are visible on the user's OnePlus. If invisible, capture Android Logcat filtered to `HushHuntAR`.
- No existing collection files, Android package ID or persistent storage schema are changed.
