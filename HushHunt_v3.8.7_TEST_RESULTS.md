# Hush Hunt v3.8.7 · Build 51 — Test results

| Check | Outcome |
|---|---|
| Screenshot ARCore source errors (Button, GLSurfaceView, Environment, Frame, var, Rect, Paint) | PASS — static source assertions |
| Android package ID, original state file name and backward-compatible legacy backup marker retained | PASS — source assertions |
| Android WebView index_v51 native bridge flag present | PASS |
| Android and BrowserPreview app_v51.js / style_v51.css exact parity | PASS |
| JavaScript syntax (`node --check`) | PASS |
| v51 Preferences and Safari regression (miles/yards, metric, map consent persistence, species-specific tools) | PASS — Playwright |
| v51 live-only real wildlife / older collection backups | PASS — Playwright |
| v51 virtual cat collection compatibility | PASS — Playwright |
| ZIP archive integrity & required solution files | PASS |
| Actual Android/.NET MAUI compilation and native ARCore world tracking | **NOT TESTED — .NET SDK and device not available** |

The static regression demonstrates that the exact syntactic/type-resolution issues from the submitted Visual Studio screenshot are addressed. It is not a substitute for invoking the actual Android C# compiler. If the fresh build reports new errors, use the first full error line and its code/file/line to refine the fix.
