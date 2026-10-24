# Hush Hunt v3.9.8 — Artwork cache fix (build 61)

- Corrected a release packaging oversight: build 60 (v3.9.7) still loaded wildlife art from `field_art_v59` even though art file contents had changed. On Android, cached image responses may have continued displaying the older versions.
- Added `field_art_v61` with the updated 146 WEBP artwork assets.
- Updated current JavaScript, Android native ARCore bridge validation and native ARCore activity to use `field_art_v61`.
- Added `index_v61.html`, `app_v61.js`, and `style_v61.css`; Android WebView loads the new entry file.
- Updated browser service-worker cache name and asset list to v61.
- Version bumped to 3.9.8 / build 61.
- Preserved older asset folders, application ID and saved collection schema. No data migration, uninstall or app-data clear needed.

This release is an asset-path/cache fix; it does not add a new species artwork redraw or change ARCore plane-detection behaviour.
