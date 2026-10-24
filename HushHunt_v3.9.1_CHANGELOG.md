# Hush Hunt v3.9.1 Change Log

## Implemented now

### ARCore
- Fixed the upside-down ARCore live camera preview by rotating the camera texture UV mapping 180° in `HushArCoreActivity`.
- Kept the AR overlay / anchor projection logic unchanged so placement behaviour stays consistent.

### Species artwork consistency refresh
Regenerated the field guide artwork in both:
- `WhiskerHunt/Resources/Raw/field_art`
- `BrowserPreview/field_art`

Targeted redraws and improvements:
- **Snails**: Roman, Glass, Amber, Pond, Other Snail now have more detailed shell/body treatment to better match Garden Snail and Grove Snail.
- **Butterflies**: more detailed wing shapes, spots and vein accents across the butterfly set.
- **Bees**: more detailed body/wing styling and clearer subtype differences.
- **Dragonflies**: Four-spotted Chaser and Golden-ringed Dragonfly upgraded so they better match the more detailed dragonfly variants.
- **Spiders**: Garden Spider, House Spider, Jumping Spider and Zebra Spider redrawn with more detail.
- **Squirrels**: all squirrel variants redesigned to read more clearly as squirrels.
- **Rabbits**: all rabbit variants redrawn in a more consistent, cleaner style.
- **Hedgehogs**: all hedgehog variants redrawn in a more detailed style.
- **Other animals**: Fox, Deer, Mouse, Bat, Lizard, Worm, Slug and Fish made more visually distinct.

### App icon
- Replaced the Android app icon source with the approved icon.
- Regenerated web / raw icon assets (`icon-192.png`, `icon-512.png`).
- Bumped version so launcher/icon refresh is more likely to apply on reinstall.

### Versioning
- App version updated to **3.9.1**
- Build number updated to **55**
- New raw/web entry files added:
  - `index_v55.html`
  - `app_v55.js`
  - `style_v55.css`

## Notes
- This sandbox does not contain the .NET SDK / Android build chain, so the source was updated and packaged, but a native APK was not compiled here.
