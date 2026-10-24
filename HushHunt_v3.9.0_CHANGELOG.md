# Hush Hunt v3.9.0 · Build 54

## Approved app icon
- The **approved woodland Hush Hunt artwork** is installed as the Android .NET MAUI launcher icon (`Resources/AppIcon/appicon.png`, referenced from `WhiskerHunt.csproj`).
- Browser/PWA 192 px and 512 px icons and the in-app masthead use the same approved design.

## Distinct wildlife varieties
- Rebuilt **128 variety cards across all 17 wildlife groups**, preserving all existing species names, collection fields and subtype identifiers.
- Used 19 illustrated animals from the approved species-style reference sheet for exact matching varieties, with new original drawn characters, species-family-specific body structures, coat patterns, wings, shell markings, and colouring for the remaining varieties.
- Updated the card UI to let the animal illustration—not a numbered tint badge—do the identifying. Each illustration is shipped locally as a 240×240 WebP in both Android and browser resources.
- Existing 2D Safari virtual wildlife images automatically use the new field-guide art. These are playful illustrations, not authoritative taxonomic identification images.

## ARCore Safari launch
- The **ARCore · Real surfaces** mode-selection button is now always interactive. The UI no longer disables it based on a WebView/initial-storage-handshake flag.
- In the browser demo, pressing ARCore explains that the installed Android app is needed and offers 2D Safari.
- On Android, the existing native ARCore launch path is called, with a readable failure callback if starting the Android Activity throws an error. The activity can ask for Google Play Services for AR and camera permission as previously implemented.
- Native mode still anchors **2D creature illustrations** in world-tracked AR space; these are not rigged 3D animal models.

## Upgrade and compatibility
- Hush Hunt version **3.9.0 (build 54)**; versioned `app_v54.js`, `style_v54.css`, `index_v54.html`, updated cache and native page entry.
- `WhiskerHunt.sln` restored into the complete archive (absent from a previous zip).
- **No change** to `uk.whiskerhunt.mobile`, `whisker-hunt-state.json`, the v1 IndexedDB name, backups or collection schema. Rebuild/deploy without uninstalling.
