# Whisker Hunt 3.7.4 · Build 43

Complete Android .NET MAUI project and browser preview.

## Install safely
1. Back up the existing CatDex first from **Your data → Save full backup**.
2. Extract this ZIP into a fresh folder and open `WhiskerHunt.sln` in Visual Studio.
3. Keep the current Whisker Hunt app **installed** on the phone. Never uninstall or clear app storage, because that may erase your collection.
4. Select Android **Debug** and your OnePlus device. Confirm Build and Deploy are enabled in Configuration Manager.
5. Clean, rebuild, and deploy over the installed app.
6. Verify the in-app version stamp reads **Whisker Hunt v3.7.4 · build 43**.

## Test the map
- Go to **Map → Saved locations**. A cat with a saved pin (e.g. Socks) should now have a large labelled marker and cat photo card.
- Tap **Show pin** to highlight it on the private plot.
- Tap **Street map → Open street map**. Android should offer/open an external browser showing the saved approximate area in OpenStreetMap.
- Tapping **Stay private** should remain in Whisker Hunt and contact no map website.

## Privacy
The in-app coordinate plot works fully offline and does not show street tiles. An external street map can be viewed only with explicit user consent; then only the selected approximate saved location is shared with OpenStreetMap. Never use the app to follow cats into unsafe/private areas.

## Build note
The Android APK has **not** been compiled in this environment. The native external-browser handoff still needs your physical-device test.
