# Whisker Hunt v3.2.0 test results

## Automated checks run
- PASS `tests/test_browser.py` — end-to-end browser smoke test for catch flow, save, edit, repeat sighting, and backup/restore.
- PASS `tests/test_v34_live_tool_ui.py` — verifies build 3.2.0 / 34, hidden active tool behaviour, alternative tool switching, and cat-claw paw SVG presence.

## Notes
- CatDex format remains compatible with v3.1.x.
- This build changes live encounter UI only; it does not wipe or migrate data.
