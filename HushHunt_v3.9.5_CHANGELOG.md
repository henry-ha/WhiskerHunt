# Hush Hunt v3.9.5 · build 59

## Android ARCore launch failure
Fixed `ARCore not ready: Invalid creature selection` by making **all three layers** agree on the versioned illustration directory `field_art_v59/`:

1. JavaScript `hushLaunchArCore()` sprite validation.
2. `MainPage.xaml.cs` native deep-link validation.
3. `HushArCoreActivity.cs` sprite loading validation.

In v3.9.4, JavaScript sent `field_art_v58/`, while `MainPage.xaml.cs` still only accepted `field_art/`. The activity had a third check. These mismatched checks caused a failure **before the native ARCore camera opened**. The new resources are in a versioned directory to avoid stale image reuse, and the service worker cache version has been advanced too. The native ARCore world-tracking/capture code from build 58 is preserved; on-device behaviour still requires verification.

## Species illustration refinement
- Refined 91 illustration files / group images, including butterflies, moths, bees, ladybirds, beetles, spiders, birds, squirrels, rabbits, hedgehogs, frogs and snails.
- Added species-specific patterns, texture, wing veins, shell markings, feather markings, and body details to improve distinction at phone scale.
- Differentiate flying, ground, grey, red and other squirrels using membrane/marking/orientation changes.
- Differentiate lop-eared, lionhead, Netherland dwarf and Flemish giant rabbits through posture/ruff/scale treatment.
- Make African pygmy, long-eared and other hedgehogs visibly different through ear, mask and texture details.
- Added visibly different spots and markings to the frog types while retaining the existing Tree Frog artwork.
- Restored the **previous Spaniel design** with its two long floppy ears, as requested.
- Changed the main Dog group thumbnail to a clearly recognisable Labrador-style dog.
- Added safe padding to Slug, Worm, Fish and Tortoise artwork, reducing edge cropping.
- Retained the approved dragonfly artwork and existing high-detail Swan and Owl illustrations.

All wildlife thumbnails are **stylised game illustrations**, not diagnostic illustrations or automatic species recognition. Some variants continue to share a related base design with added markings, rather than being wholly different photorealistic images.

## Compatibility
- Android application ID remains `uk.whiskerhunt.mobile`.
- Native private storage, collection format, recovery backups and live-only wildlife capture rules are unchanged.
- App version updated to **3.9.5**, Android build number to **59**.

## Deployment
**Export your Collection backup before updating.** Open `WhiskerHunt.sln` in Visual Studio, clean and rebuild the Android solution, and deploy *over the installed Hush Hunt*. Do **not** uninstall the app; uninstalling may delete your local wildlife collection and private photographs.
