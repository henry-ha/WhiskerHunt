# Whisker Hunt v2.8 test results

## Passed
1. **tests/test_v28.py**
   - Verified MAUI project points to `index_v28.html`
   - Verified app version `2.8.0` / build `28`
   - Verified BrowserPreview and MAUI raw assets are synchronised
   - Verified AR Safari UI renders
   - Verified six AR cat model buttons appear
   - Verified switching to `midnight-panther` updates the selected model
   - Verified AR Safari save flow stores compatible metadata (`captureMode`, `arModel`, `arModelHint`)

2. **tests/test_browser.py**
   - Passed browser smoke tests for encounter flow, collection, journal, reunion, safe merge, and ID validation

## Environment-limited / not relied upon
- Some older tests are version-locked to earlier service worker or project version identifiers.
- Some localhost-based tests are blocked in this environment by `net::ERR_BLOCKED_BY_ADMINISTRATOR`.
- Real-device Android camera smoothness and AR Safari touch feel still need manual testing.
