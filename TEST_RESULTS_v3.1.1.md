# Whisker Hunt v3.1.1 (build 32) hotfix test report

The failing v3.1 code was reproduced in Playwright. `beginEncounter(image,{live:true,ar:true})` raised `ReferenceError: arMode is not defined` inside `refreshArEncounterUi()`.

## Completed passing tests

- **tests/test_v32_ar_hotfix.py** — exact crashing AR encounter now opens successfully, all 120 virtual cats and 12 habitats available; paw capture opens name/memory screen; saving adds a virtual cat with a habitat and photo; Android entry/versioned assets match.
- **tests/test_v32_live_ar_mock.py** — mocked camera MediaStream opens AR Safari without the false 'unavailable' screen; camera resources close correctly.
- **tests/test_v32_compat.py** — original v3.1 integration behavior: 120+ cats, habitats, virtual collection save/backup restore, optional rounded GPS and GPS-free export.
- **tests/test_browser.py** — existing CatDex smoke test: normal capture, reunions, edits, journal, export/restore, merge and duplicate validation.
- **tests/test_v19_subject.py** — focused photo ranking, cancelled camera safeguards.
- `node --check BrowserPreview/app_v32.js` and `node --check BrowserPreview/sw.js` — syntax passed.

## Not tested

- Android APK was **not compiled** (Android .NET MAUI workload/SDK unavailable here).
- Real OnePlus camera permissions and performance still require physical-device deployment.

## Installation precautions

Deploy build 32 over the existing package ID `uk.whiskerhunt.mobile`. Do **not** uninstall or clear app storage; the local CatDex and backups retain their previous schema.
