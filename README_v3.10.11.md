# Hush Hunt v3.10.11 · Build 74

Updated source project implementing dynamic rotating wildlife home themes and UI/AR Safari refinements.

### Installation
1. Extract the Android MAUI source ZIP into a **fresh directory**.
2. In Visual Studio, open `WhiskerHunt.sln`.
3. Clean then rebuild the Android project and deploy **over the existing installed app**. Do not uninstall; uninstalling can remove locally stored sightings.
4. Verify version **3.10.11 · build 74** in Home's footer.

### Settings
Home gear → Home screen themes: Dynamic (changes on each app launch) or Static (choose one scene). Motion is optional and off by default.

### Safety & accuracy
- Animal identification remains user-guided; no trained automatic species classifier has been shipped.
- ARCore can now use an explicitly labelled **screen-locked fallback preview** when plane anchoring fails; this is not real-world anchored tracking.
- True 0.6× lens support depends on device camera API access.

See HushHunt_v3.10.11_CHANGELOG.md and HushHunt_v3.10.11_TEST_RESULTS.md.
