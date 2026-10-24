# Hush Hunt v3.9.2 changelog

## Fixes included

- **ARCore preview fix:** removed the manual UV flip/rotation so the camera view is no longer intentionally mirrored.
- **ARCore placement UX:** the **Place** button now stays disabled until a real ARCore plane is detected at the centre of the screen.
- **ARCore status guidance:** added clearer in-app messaging when no floor/table is detected yet.
- **Home-screen icon refresh:** bumped the app version to **3.9.2 / 56** and switched the MAUI launcher icon input to `appicon_v392.png` to force Android icon regeneration.
- **Species art touch-ups:** updated the bundled **Swan** icon to a more swan-like long-neck pose and refreshed the **Golden Retriever** sprite to align better with the Labrador/Golden look.

## Notes

- This is a focused bug-fix patch based on the latest feedback screenshots.
- Because Android launcher caches can be sticky, if the icon still looks old after installing over the top, uninstalling the previous build once before installing the new one may still help.
