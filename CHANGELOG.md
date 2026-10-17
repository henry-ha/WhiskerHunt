# Whisker Hunt v3.3.0 changelog

## Live capture / AR Safari
- Alternative-only tool selector with clear **Switch to Lure** and **Switch to Paw** labels.
- 250 ms spring-pop when the selected capture tool changes, disabled by reduced-motion accessibility settings.
- Minimal AR Safari HUD: shorter instructions, no redundant photo-quality and launch panels during virtual encounters.
- Retains the stylised clawed Whisker Paw from v3.2.

## Child-friendly collection recovery
- **Find missing cats** option on Explorer profile.
- Android read-only inspection of last valid `.bak` copy, reporting missing cat IDs and cats with potentially missing sightings. No photo or GPS content included in preview metadata.
- Explicitly confirmed additive restoration via existing v1 backup merge; never replaces unrelated current cats.
- **Save my current CatDex first** export avoids native save/backup rotation, protecting the last-known-good recovery copy while inspecting it.
- Fallback to importing an existing JSON backup when no usable local recovery snapshot exists.

## Compatibility and limitations
- Keeps `uk.whiskerhunt.mobile` application ID and v1 CatDex backup format.
- No existing cats, photos, XP, quests, or pins are deleted or migrated by this UI update.
- A deleted Android app or cleared app data may be unrecoverable unless a separate JSON backup exists.
- Android APK not compiled; native .NET MAUI recovery path requires testing on a physical device.
