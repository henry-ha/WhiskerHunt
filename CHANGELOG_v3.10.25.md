# Hush Hunt v3.10.25 · build 88

## Native ARCore launch / 3D prototype
- Removed a stale asset-version check that rejected every ARCore launch, causing apparent fallback to 2D.
- Native ARCore is independent of the 2D Safari sprite library.
- Added HushAnimal3D.cs: offline, dimensioned OpenGL ES low-poly wildlife prototypes, anchored to a genuine ARCore tracked plane. Move around the anchor to see different sides.
- Dedicated mode selection: ARCore (tracked, low-poly 3D) vs 2D Safari (screen-based illustrated sprites).
- ARCore photo captures the GL-rendered model via PixelCopy, without compositing a cutout PNG.
- No silently substituted screen-locked AR as 3D; plane tracking is still mandatory.

## 2D creature image repairs
- Rebuilt bird-swan.png and bird-group.png from the complete educational swan photograph with the head and curved neck included. The previous transparent masks erased the head.
- Audited all 148 Safari cutout PNG assets for severe edge clipping and broken foreground components; preserved approved artwork that passed checks.

## Compatibility
- Android ApplicationId and collection save format unchanged.
- Updated MainPage.xaml to launch index_v88.html; WebView shell/cache updated.
- NOTE: This is a test-source release. No APK compiled or ARCore device test in this environment. Low-poly 3D is a prototype rather than species-accurate animation/texture artwork.
