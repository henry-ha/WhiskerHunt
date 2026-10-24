# Hush Hunt 3.8.6 / build 50 — Test report

**Environment:** headless Chromium Playwright + Python + Node.js on Linux. Native .NET/Android SDK unavailable.

| Test | Result | Notes |
|---|---|---|
| `node --check BrowserPreview/app_v50.js` | PASS | Syntax check |
| `tests/test_v50_preferences_safari.py` | PASS | Units conversion, persist profile options in local storage, simulate Android data reload, zero online tile requests before consent, offline fallback, correct virtual hedgehog/butterfly/cat symbols and labels |
| `tests/test_v50_legacy_wildlife.py` | PASS | 17 wildlife groups, live species choice, Cat Bingo, collection backup, street-map consent |
| `tests/test_v50_live_only_compat.py` | PASS | Live-only real sightings, legacy photos and backups preserved, gallery prevented |
| `tests/test_v50_virtual_compat.py` | PASS | Virtual cat collection and backups remain functional |
| Project and assets | PASS | Native bridge flag in v50 HTML, package ID and storage keys retained, versioned assets matching |
| ZIP integrity | PASS | CRC checks and expected main project entries |
| Android compilation and physical ARCore tracking | NOT TESTED | Requires Visual Studio with .NET MAUI Android workload and an ARCore-supported phone |

**Privacy limitation:** online OpenStreetMap tiles share the area of the map being browsed and IP address with that provider after explicit consent. Persisting the user's last choice does not grant permanent device GPS permission. Saved discovery pins continue to be rounded (~1 km), so displayed miles/yards are approximate straight-line distances.

**Data safety:** Test collections contained only fictional example animals/coordinates. The build retains the original Android app ID, private file paths, IndexedDB name and backup format. Do not uninstall the existing app during upgrade. Export a full backup before deploying.
