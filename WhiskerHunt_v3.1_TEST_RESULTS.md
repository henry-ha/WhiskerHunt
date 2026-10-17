# Whisker Hunt v3.1 test results

## Environment
- Browser preview tested with Playwright + Chromium
- Source package updated to `3.1.0` / build `31`

## Tests run

### 1) `tests/test_v31.py`
**Result:** PASS

Verified:
- `index_v31.html` is the MAUI WebView entry
- app version/build are `3.1.0` / `31`
- AR roster contains **120+** cats
- habitat roster contains **12** habitats
- no manual AR reroll button is exposed
- virtual cat save works
- habitat metadata persists in CatDex backup/restore
- optional rounded virtual-cat map pins still round to approx. 1 km and are removed in GPS-free backup

### 2) `tests/test_browser.py`
**Result:** PASS

Regression smoke coverage:
- normal catch flow
- edit cat flow
- repeat sighting flow
- export / restore round trip
- journal flow
- safe merge / duplicate protections

## Generated preview artifacts
- `WhiskerHunt_v3.1_AR_Habitat_Preview.png`
- `WhiskerHunt_v3.1_Virtual_Gallery.png`
- `tests/smoke-test.png`
