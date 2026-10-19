# Whisker Hunt v3.5 testing

## Passed
- `node --check BrowserPreview/app_v37.js`: JavaScript syntax
- `python3 tests/test_v37_location_race.py`: tagged native request simulation; out-of-order callback ignored; approximate rounding; new capture invalidates previous cached location; Android versioned file consistency
- `python3 tests/test_browser.py`: CatDex browser smoke tests, normal encounter, sightings, collection, journal and backup/restore

## Build status
- Android APK: **not compiled** (the .NET Android SDK is unavailable in this environment).
- Native Android permission panel and GPS behaviour: **not verified on a physical phone**.

## Deployment
- `WhiskerHunt.sln` included with Deploy configuration enabled.
- Version 3.5.0 / Android version code 37.
- Entry page `index_v37.html` / `app_v37.js` / `style_v37.css`.
- Data: no destructive migration; preserve existing installed package and export a backup before upgrading.
