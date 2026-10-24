# Hush Hunt 3.9.7 (build 60) — ARCore compiler hotfix

Based on v3.9.6 (same artwork and collection data model).

- **Fixed CS0572 / CS1913 in `HushArCoreActivity.cs` line 170**: removed the invalid `PlaneFindingMode` object initializer. `Google.AR.Core.Config(_session)` enables plane detection by default, according to Google's ARCore documentation. Other ARCore placement and photo capture code is unchanged.
- App version bumped to **3.9.7**, build **60**. Updated the MAUI WebView entry point and browser scripts to v60 so the displayed build stamp matches.
- Application ID stays `uk.whiskerhunt.mobile`; no migration or deletion of saved discoveries.

**Validation limitation:** The environment does not contain the .NET Android toolchain. Source and package checks can pass, but native compilation and on-device ARCore placement remain unverified.
