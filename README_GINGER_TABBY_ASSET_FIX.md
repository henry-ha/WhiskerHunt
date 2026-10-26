# Hush Hunt v3.10.36 Build 99 — Ginger Tabby AR asset hotfix

## What was discovered

- `WhiskerHunt/Resources/Raw/ar_models/cat-ginger-tabby.glb` is **included** in the full source ZIP.
- The native 3D Safari selector uses model ID `ginger-tabby`. The runtime lookup previously rebuilt filenames from text labels, rather than using the supplied model ID. The new lookup makes this relationship explicit and validates the group/name.
- **No distinct `cat-american-shorthair.glb` is shipped.** American Shorthair is not advertised as a 3D model; use 2D Safari until a breed-specific, redistributable GLB is added.
- A missing or unreadable GLB now produces a more specific message containing its filename or exception type, and the Android log records parse errors.
- The JavaScript picker no longer silently replaces an unknown animal with a ladybird or Ginger Tabby.

## Files updated

- `WhiskerHunt/Platforms/Android/HushGlbAnimal3D.cs`
- `WhiskerHunt/Platforms/Android/HushArCoreActivity.cs`
- `WhiskerHunt/Resources/Raw/app_v99.js`

## Installation

Extract patch over the existing project root preserving paths, clean/rebuild and deploy **over** your current installation using the same signing key and app ID. Never clear app data or uninstall unless your saved collection is backed up. For an entirely fresh copy, use the full-source ZIP.

## Limitations

The existing Ginger Tabby is a stylised static GLB, not a photo-realistic model or a precise American Shorthair. Android SDK is not installed in this build environment; this is a source-level fix, not a device-tested APK. Check the actual 3D Safari runtime on your phone after rebuilding.
