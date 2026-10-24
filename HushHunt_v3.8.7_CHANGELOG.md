# Hush Hunt 3.8.7 · build 51 · 21 October 2026

## ARCore Android compilation hotfix

- Fixed `CS0104`: `Button` now resolves explicitly to `Android.Widget.Button` (previously ambiguous with `Microsoft.Maui.Controls.Button`). This also resolves the resulting `CS1503` and `CS1061` native-button errors.
- Fixed `CS1061`: removed unsupported `GLSurfaceView.SetPreserveEGLContextOnPause(bool)` call; the existing GL renderer re-creates resources when the GL context is re-created.
- Fixed `CS0104`: `Environment` now explicitly resolves to `System.Environment`.
- Fixed `CS0104`: removed unused ARCore `Frame` field (previously ambiguous with MAUI `Frame`).
- Fixed `CS0819`: split `var eye` and `var clip` into separate local variable statements.
- Fixed `CS0104`: use `Android.Graphics.Rect` and `Android.Graphics.Paint` explicitly for native AR photo composition.
- Advanced version and bundled entry page from 3.8.6/build 50 to 3.8.7/build 51; update native page source and browser cache key.

## Unchanged

- Existing Android package ID `uk.whiskerhunt.mobile`, storage file `whisker-hunt-state.json`, backup `.bak` and legacy JSON marker `Whisker Hunt` (required for migration safety).
- FieldDex / CatDex, wildlife art and catalog, AR Safari modes, remembered street map, distance preferences and wildlife captions.

## Verification caveat

Static source checks and browser tests pass. **This is not an Android-compiled APK**. The exact ARCore NuGet binding and real tracking need confirmation in your Visual Studio Android build and on your OnePlus.
