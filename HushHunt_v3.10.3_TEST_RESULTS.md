# Hush Hunt v3.10.3 · Build 66 — Test results

## Passed locally
- JavaScript syntax checks: browser and Android WebView copies of `app_v66.js`.
- Automated Playwright Chromium checks: Home entry, full-screen field-guide visibility, all 17 animal groups, selecting Bird → Robin, closing by Escape and button, Collection entry, passing selected kind back to the real sighting form, no new saved records.
- 17 group descriptions and 128 subtype identification clues validated for exact coverage.
- 146 WebP asset files validated and synchronized between browser and MAUI Raw resources.
- Updated `WhiskerHunt/MainPage.xaml` to load the new versioned native entry page (`index_v66.html`), ensuring no stale v64 script takes precedence.
- Browser and MAUI versioned shell files and service worker verified in sync; new cache key `whisker-hunt-shell-v66`.
- Native Android package ID (`uk.whiskerhunt.mobile`) retained; MAUI display version 3.10.3, build 66.

## Limitations
- Android APK could not be compiled in this container (no .NET MAUI/Android SDK). Please build and test with Visual Studio on your OnePlus 11.
- Reference art is AI-generated/illustrative and is not a verified natural-history image dataset. The Peacock butterfly remains a stylised image pending a reviewed image replacement; no automated visual species identification is claimed.
- Older recorded sightings, locations, collections, photos and JSON backups have not been modified.
