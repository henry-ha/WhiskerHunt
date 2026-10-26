# Hush Hunt v3.10.32 / Android build 95 — Safari clarity update

- ARCore now uses concise, child-friendly on-camera instructions. Technical explanations were removed from the camera overlay.
- Rounded 2D, Place/Move and Photo buttons are separated by 10dp and raised above the Android system navigation region.
- A right-side +/- control and two-finger pinch can resize **the 3D animal** between 0.5x and 3x without disturbing the ARCore anchor. This is *not* optical or digital camera zoom.
- 2D Safari modal close button sits at the right edge of the content area.
- Safari mode chooser text and selection grid simplified.
- Existing ARCore plane tracking, GLB mesh loading, photo capture and saved collection workflows are otherwise preserved.

## IMPORTANT: keep locally imported 3D models

Your local project may include **21 species** after running INSTALL_CC0_WILDLIFE.bat; this distributed source ZIP contains **five** CC0/prototype base GLBs only. DO NOT replace an imported project's Resources/Raw/ar_models folder with this ZIP's folder. Use the **source-update patch** ZIP instead, copying the changed files and running REFRESH_ARCORE_MODELS_V95.bat. This regenerates the picker list from GLBs already present, without downloading again. See PATCH_INSTALL_README.md in that ZIP.

The underlying animal detail is unchanged; low-poly meshes remain low-poly until suitable high-detail, correctly licensed GLB assets are imported. Native .NET MAUI/ARCore deployment and on-device testing were not available in this Linux runtime. Validate visually on a physical Android handset before release.
