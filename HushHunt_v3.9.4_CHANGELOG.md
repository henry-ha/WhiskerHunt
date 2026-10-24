# Hush Hunt v3.9.4 — Build 58

## Wildlife Field Guide artwork
- Replaced 52 individual field guide/card illustrations and group thumbnails with detailed wildlife-inspired artwork. The updated set includes the requested Labrador vs fluffy Golden Retriever, a two-eared Spaniel, Mixed Breed and dog group thumbnail, snail varieties, Four-spotted Chaser and Golden-ringed Dragonfly, squirrels, rabbits, hedgehogs, frogs, swan, owl, antlered deer, lizard, fish, tortoise and additional animals.
- Kept all 128 variety names and their saved-data values unchanged. Existing discoveries and backups do not need migration.
- Introduced `field_art_v58/` as a **new versioned asset folder** in both Android and Browser Preview. This prevents older cached `field_art/` images from being reused.
- Garden Snail and Grove Snail retain their earlier approved artwork.
- These are artistic wildlife illustrations, not taxonomic references or automatic species identification.

## ARCore Safari
- Replaced the failure-prone, full-resolution `glReadPixels` snapshot code with Android `PixelCopy.Request(GLSurfaceView, ...)` to obtain the latest presented camera surface at up to 1080 pixels on the long axis.
- Composites the on-screen world-anchored creature onto the captured image, then encodes a local JPEG and sends it through the existing `hushNativeArCoreResult` collection bridge.
- Added success/error reporting from PixelCopy and resource cleanup; reduced the snapshot memory burden.
- Smoothed world-anchored creature overlay position to reduce visible jitter.
- Retained real horizontal-plane hit tests and world-anchor placement, with existing 2D Safari fallback.
- Retained `Google.AR.Core.Frame` qualification (v3.9.3 compile fix).

## Android app icon
- Preserved the approved Hush Hunt icon.
- Added explicit Android mipmap launcher images (five densities) and Android Manifest `android:icon`/`android:roundIcon` references, instead of relying only on the MAUI-generated default icon.
- Updated MAUI icon input, browser icons, display version 3.9.4 and Android version code 58.

## Storage and safety
- `ApplicationId` remains `uk.whiskerhunt.mobile`.
- No changes to private collection/photo data keys, database schema or backup format.
- Deploy over the existing installation; do NOT uninstall the app just to refresh the icon.
- If the launcher still shows an old pinned shortcut, remove the home-screen shortcut only and add it again from the app drawer after installing; do not clear the app's storage.

## Important limitations
- Android APK compilation and on-device PixelCopy/ARCore behaviour could not be verified in this environment because the Android/.NET toolchain and physical OnePlus are not available.
- A browser regression confirms the JavaScript integration path, but the native capture fix needs a physical phone test.
- Some minor varieties share a related anatomical illustration with altered treatment; not every subtype is a scientifically exact identification plate.
