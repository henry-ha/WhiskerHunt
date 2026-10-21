# Hush Hunt — Android .NET MAUI / WebView

**Version 3.8.3 · build 47** · Live-only wildlife discovery, illustrated visual Field Guide.

## Open and deploy

Use **WhiskerHunt.sln** (the internal legacy project name is retained for save compatibility) in Visual Studio with the .NET 10 Android MAUI workload, and build/deploy to your OnePlus device **without uninstalling the old app**. Export a full backup first.

## Discover wildlife

1. Tap the large + button and start the real-wildlife live camera. Imported photos cannot earn new sightings.
2. Complete the virtual capture tool, pick the animal group, tap a variety picture, and optionally add a memory/private approximate map pin.
3. If unsure of a variety select **Not sure**. The illustrated tiles do **not** provide automatic identification.
4. In **FieldDex** choose an animal filter to see your discovered varieties. Cat Bingo and AR Safari virtual cats remain separately supported.

## Privacy, local storage, upgrading

- Android package ID: `uk.whiskerhunt.mobile` (not renamed).
- Browser database: `whiskerhunt_local_v1`; existing native JSON backup signature also retains its Whisker Hunt name.
- Personal photographs and private pins remain on-device; opening an external OpenStreetMap requires explicit consent.
- Export and verify a backup before installing; do not clear storage or uninstall. No account is required.

## Testing and limitations

See `HushHunt_v3.8.3_TEST_RESULTS.md` and `tests/test_v47_*` for source/browser regression checks. There is no generated Android APK in this package, and Android-device camera operation must be verified after deployment.
