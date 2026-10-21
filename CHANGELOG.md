# Hush Hunt v3.8.3 — Build 47 (2026-10-21)

## New
- Approved rebrand from Faunigo to **Hush Hunt**, including Android app title, browser metadata, refreshed compass/moon/leaf identity, native share titles, and app icons.
- New visual Field Guide on the live sighting save screen: **17 animal groups**, **128 illustrative varieties**, each with locally bundled WebP picture cards, accessible tap targets and selected states.
- Cat appearance choices grew from eight to twelve: Tabby, Ginger, Brown, Black, White, Cream, Tuxedo, Calico, Tortoiseshell, Grey, Colourpoint, Other. Cat Bingo tracks these appearances without deleting previous progress.
- Snail, dog, butterfly, moth, bee, ladybird, beetle, dragonfly, ant, spider, bird, squirrel, rabbit, hedgehog, frog, and other wildlife each offer multiple labelled varieties.
- Every non-cat group has a clearly illustrated **Not sure** option and custom description, so a child never has to guess a difficult identification.
- Edit discovery screen allows changing an animal's variety with picture cards while keeping the photo, sightings and private location.
- FieldDex species filters show an unlockable variety album based on recorded types. Existing legacy varieties match regardless of capitalisation.
- Main home hero now features different animals; wildlife thumbnail descriptions show their true species and variety instead of saying 'Other'.

## Data safety and compatibility
- **Unchanged Android application ID**: `uk.whiskerhunt.mobile`; same installation/updating identity.
- **Unchanged IndexedDB database** `whiskerhunt_local_v1`, private MAUI JSON file storage, native backup discriminator `Whisker Hunt`, and backup schema **version 1**. These are intentional *internal compatibility names*, not visible branding.
- Prior cat, wildlife, virtual cat, photos, map pins, XP, and old JSON imports are preserved without migration.
- Live-only rules and AR Safari remain unchanged; manual user classification, **no real-time AI species recognition**.
- Illustrations are kawaii image guides, not reference photographs or scientifically verified identification.

## Deploy
1. Export a full CatDex/FieldDex backup *before* upgrading.
2. Open `WhiskerHunt.sln` in Visual Studio, clean, rebuild, and deploy over your existing app. **Do not uninstall**.
3. Check app label `Hush Hunt`, choose a live camera encounter, test Bird/Robin, Snail/Garden Snail, Dog/Labrador, Cat/Brown, and Not sure; inspect FieldDex variety badges and existing photos/pins.
4. `WhiskerHunt` remains the internal project name on purpose. The visible app name is **Hush Hunt**.

## Verification
Four dedicated Playwright/browser suites, including the visual field guide, live-only restrictions, map, and AR Safari. JavaScript syntax, asset parity and ZIP integrity checks. **Android compilation and physical phone operation were not available in this environment.**

---

## Earlier releases
See historical `tests` and original project history.
