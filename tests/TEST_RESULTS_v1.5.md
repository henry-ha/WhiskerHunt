# Whisker Hunt v1.5 test results

**Passed (12):** `test_browser.py`, `test_v05.py`, `test_v06.py`, `test_v07.py`, `test_v08.py`, `test_v09.py`, `test_v10.py`, `test_v11.py`, `test_v12.py`, `test_v13.py`, `test_v14.py`, `test_v15.py`.

**Blocked by execution environment (2):** `test_real_storage.py` (`http://127.0.0.1/...`) and `test_v06_real_indexeddb.py` (`https://whisker.test/`) both fail at navigation with `net::ERR_BLOCKED_BY_ADMINISTRATOR`. These tests were **not** counted as passed. Native Android APK was **not** compiled.

The v1.5 suite covers low-light/texture heuristics, retake and picker cancellation, photo replacement, out-of-order image decoding, preservation of previous CatDex/XP until saving, and existing repeat-sighting intent. Other suites cover quests, persistence simulation, JSON backup, and capture interactions.
