# Hush Hunt v3.10.2 – Realistic Field Guide Refresh

## Implemented
- Replaced the wildlife field-guide art pack with a new `field_art_v65` set.
- Kept the same filenames as the previous guide pack so the species/type picker remains compatible.
- Updated both the browser preview and MAUI raw resources to use the new field-guide pack.
- Switched runtime references in `BrowserPreview/app.js` and `WhiskerHunt/Resources/Raw/app.js` from `field_art_v62` to `field_art_v65`.

## Goal of this refresh
- Make the wildlife guide more realistic and educational.
- Improve visual identification of species and common sub-types for children.
- Reduce the older cartoon-like look in the species picker.

## Notes
- The pack is still offline and bundled with the app.
- A small number of generic fallback tiles were retained where that gave a clearer result than an incorrect generated tile.
