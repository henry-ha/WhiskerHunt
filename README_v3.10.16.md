# Hush Hunt v3.10.16 · Build 79

## Fixes
- Fixed the root theme bug: the v74 screen handler was overwriting v76+ CSS variable artwork every time Home rendered. It now respects the v79 theme system.
- Updated the image paths to new versioned v79 folders; existing animal collections, IDs, and storage are unchanged.
- Reworked the capture confirmation screen so the header comes first, the photo is unobstructed, and species/kind appear in a small summary below. Removed redundant capture callout on this screen.
- Highlighted primary action now says New Cat, New Dog, New Squirrel, New Butterfly, etc., depending on the selected group.
- Seen before is explained inline as a *new sighting of an individual animal already collected*, and disabled if the selected group has no saved entries. Existing selection and save paths retained.
- New Android launch chain: MainPage.xaml → index_v79.html → style_v79.css/app_v79.js.

## Verification limits
Static checks and browser simulation can verify HTML, CSS, event handling and assets. Physical Android builds and native camera behavior remain unverified until deployment to your phone.
