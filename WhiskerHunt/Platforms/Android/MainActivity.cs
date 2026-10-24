using Android.App;
using Android.Content.PM;
using Android.OS;

namespace WhiskerHunt;

[Activity(Theme = "@style/Maui.SplashTheme", MainLauncher = true,
    ConfigurationChanges = ConfigChanges.ScreenSize | ConfigChanges.Orientation |
                           ConfigChanges.UiMode | ConfigChanges.ScreenLayout |
                           ConfigChanges.SmallestScreenSize | ConfigChanges.Density)]
public class MainActivity : MauiAppCompatActivity
{
    protected override void OnResume()
    {
        base.OnResume();
        // Deliver the ARCore photo only after this WebView's activity is foreground again.
        new Android.OS.Handler(Android.OS.Looper.MainLooper!).PostDelayed(
            HushArCoreActivity.DispatchPending, 350);
        new Android.OS.Handler(Android.OS.Looper.MainLooper!).PostDelayed(
            HushWideCameraActivity.DispatchPending, 420);
    }
}
