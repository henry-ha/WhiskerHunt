# Whisker Hunt v3.4.0 — Test Results

## Automated checks run

### JavaScript syntax
- `node --check BrowserPreview/app.js`
- **Result:** Passed

### Python smoke tests
- `pytest -q tests/test_v36_location_and_ar.py`
- **Result:** 4 passed

## Covered by smoke tests
- Build/version bump to 3.4.0 / 36
- Presence of location helper UI and native app-settings bridge
- AR catalogue expanded beyond 120 and rarity weighting present
- Claw animation CSS hooks and realistic AR cat renderer class present

## Not executed in this environment
- Full MAUI / Android build (dotnet SDK unavailable here)
- Device-side runtime validation for Android location settings intent
- Manual touch/animation verification on handset
