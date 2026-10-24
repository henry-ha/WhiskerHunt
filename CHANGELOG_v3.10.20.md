# Hush Hunt v3.10.20 (build 83) — Home theme rendering correction

## Implemented
- Removed the explicit horizontal vignette/overlay from the Home renderer CSS.
- Reconstructed all 20 current Home wallpapers as **continuous full-bleed images** without the top and bottom blurred extension panels contained in the previous assets.
- Rebuilt matching theme chooser thumbnails directly from each replacement wallpaper so the preview reflects the selected Home image.
- Preserved the theme-specific Live Capture / AR Safari button images, copied to a new versioned asset directory.
- Pointed the active theme registry to `themes_v83`, `theme_previews_v83`, and `button_scenes_v83`.
- Updated MainPage.xaml to launch `index_v83.html`; updated both HTML entry points to `app_v83.js` and `style_v83.css`.
- Increased the Android display/build version to v3.10.20/build 83, and service worker cache namespace to v83.
- Kept application ID, app storage keys, Dynamic/Static settings, and user collection schema unchanged.

## Important limitations
- These wallpapers are rasterized at **2160 × 3840**, but their source illustrations were smaller. Enlargement and sharpening do **not** create genuine native 4K source detail.
- To achieve truly crisp, natural-detail 4K wildlife imagery across all 20 scenes, new full-resolution illustrations are still required.
- Some scene framing is tighter than v3.10.19 because the old blurred margins were removed without inventing missing subject or background details.
- Android camera and in-app appearance need validation on a physical phone; this package contains **source**, not a compiled APK.
