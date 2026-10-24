# Hush Hunt v3.9.2 test notes

## Static verification completed

- Confirmed `WhiskerHunt.csproj` version bump from **3.9.1 / 55** to **3.9.2 / 56**.
- Confirmed MAUI icon input switched to `Resources/AppIcon/appicon_v392.png`.
- Confirmed `HushArCoreActivity.cs` now:
  - uses standard ARCore UV coordinates,
  - tracks whether a centre-screen plane is available,
  - disables `Place` until a plane is found,
  - shows clearer surface-detection messages.
- Confirmed updated asset files copied to both:
  - `WhiskerHunt/Resources/Raw/field_art/...`
  - `BrowserPreview/field_art/...`

## Environment limitation

- A full Android build / device install could not be executed in this container because the .NET Android toolchain is not available here.
- This patch package is therefore provided as an updated source/browser bundle for installation/build on the normal development machine.
