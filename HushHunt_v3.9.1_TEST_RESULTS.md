# Hush Hunt v3.9.1 Test Results

## Source-level checks completed

### 1) Artwork regeneration
- `python3 tools/build_species_art.py` completed successfully.
- Result: `Generated 128 bespoke subtype illustrations for 17 groups`
- Result: `Integrated 19 approved reference illustrations with transparent poster borders`

### 2) File update checks
Verified updated source locations exist:
- `WhiskerHunt/Platforms/Android/HushArCoreActivity.cs`
- `WhiskerHunt/Resources/AppIcon/appicon.png`
- `WhiskerHunt/Resources/Raw/index_v55.html`
- `WhiskerHunt/Resources/Raw/app_v55.js`
- `WhiskerHunt/Resources/Raw/style_v55.css`
- `BrowserPreview/index_v55.html`
- `BrowserPreview/app_v55.js`
- `BrowserPreview/style_v55.css`

### 3) Version checks
- `WhiskerHunt.csproj` now targets display version `3.9.1`
- `WhiskerHunt.csproj` now uses app version `55`
- JS build stamp updated to `3.9.1 / 55`

### 4) App icon refresh
- `Resources/AppIcon/appicon.png` replaced with approved icon asset.
- Browser/raw `icon-192.png` and `icon-512.png` regenerated from approved icon.

## Not executed in this sandbox
- Android / MAUI compile
- APK installation
- On-device ARCore runtime verification
- Launcher icon refresh verification on a physical phone

## Recommended device checks after you build/install
1. Uninstall the previous Hush Hunt build from the phone.
2. Install the new build.
3. Confirm the home-screen app icon is the approved one.
4. Open ARCore Safari and confirm the live view is upright.
5. Check species variety tiles for snails, butterflies, bees, dragonflies, spiders, squirrels, rabbits, hedgehogs and other animals.
