# Hush Hunt v3.10.15 — Test summary

- PASS: 53 release source checks: MAUI version/build, XAML launch chain, native bridge callback, current HTML/JS/CSS paths, matching Android/browser resources and corrected frog PNG images.
- PASS: Node syntax check on `app_v78.js` in both browser and Android sources.
- PASS: Isolated theme UI logic: clicking a wildlife scene selects Static and persists it; enabling Dynamic rotates the selected theme on the next launch.
- PASS: all 148 2D Safari sprite assets are bundled; revised frog assets in browser and native sources are byte-identical.
- PASS: older versioned JavaScript / CSS entry assets removed from the current release to prevent stale startup selection.
- NOT RUN: full Android compilation (Android/.NET MAUI SDK not available here).
- NOT RUN: Android hardware ARCore / live camera end-to-end test.
- NOT RUN: interactive browser screenshot test (local Chromium navigation blocked in this environment).
