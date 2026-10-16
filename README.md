# Whisker Hunt v2.5.0 (build 25)

This archive is the Android .NET MAUI source code and web assets for the Whisker Hunt prototype.

## Install/update safely

1. Export your CatDex JSON backup in the currently installed app, and keep a copy outside the app.
2. Extract this **entire new folder** to a new location. Open `WhiskerHunt.sln` from the extracted v2.5 project (not the old solution).
3. In Visual Studio, choose **Restore NuGet Packages**, **Clean Solution** and **Rebuild Solution**.
4. Deploy to the phone over the existing installed app. **Do not uninstall the app or clear app storage**, because that can remove the collection.
5. Open **Catch → Live encounter**. Check the green stamp **Whisker Hunt v2.5.0 · build 25** at the top of the encounter sheet. If you still see the old design or there is no stamp, you are not running these new web assets.
6. Test: Retake live → immediately Use normal camera instead → cancel the system camera. The app should show **Choose your camera**, with working Live, Normal camera and Gallery buttons, not the old spinner.

The Android `ApplicationId` remains `uk.whiskerhunt.mobile`, to retain existing private app data on an in-place upgrade. The display version is now **2.5.0** and Android version code **25**.

## Native UI files

- `WhiskerHunt/MainPage.xaml`: loads `index_v25.html`
- `WhiskerHunt/Resources/Raw/index_v25.html`: loads `app_v25.js` + `style_v25.css`
- `WhiskerHunt/MauiProgram.cs`: WebView settings including cache mode
- `WhiskerHunt/MainPage.xaml.cs`: local CatDex persistence + native camera/photo picker bridge

## Platform validation

Browser smoke and regression tests passed. No Android APK was compiled; .NET Android SDK and on-device verification are required.
