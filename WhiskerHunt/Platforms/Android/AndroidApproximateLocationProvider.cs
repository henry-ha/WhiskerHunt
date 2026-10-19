using Android.Content;
using Android.Locations;
using Android.OS;
using DiagnosticDebug = System.Diagnostics.Debug;
using MauiLocation = Microsoft.Maui.Devices.Sensors.Location;

namespace WhiskerHunt;

/// <summary>
/// Foreground-only Android fallback. Unlike Essentials' LocationWhenInUse status,
/// this path works when the user granted COARSE but not FINE location.
/// Returns coordinates only to native code; the caller rounds them before WebView.
/// </summary>
internal static class AndroidApproximateLocationProvider
{
    private sealed class OneShotListener : Java.Lang.Object, ILocationListener
    {
        public TaskCompletionSource<Android.Locations.Location> Result { get; } =
            new(TaskCreationOptions.RunContinuationsAsynchronously);

        public void OnLocationChanged(Android.Locations.Location location) => Result.TrySetResult(location);
        public void OnProviderDisabled(string provider) { }
        public void OnProviderEnabled(string provider) { }
        [Obsolete]
        public void OnStatusChanged(string? provider, Availability status, Bundle? extras) { }
        public void OnFlushComplete(int requestCode) { }
    }

    private static LocationManager? GetManager() =>
        Android.App.Application.Context.GetSystemService(Context.LocationService) as LocationManager;

    internal static bool HasForegroundPermission()
    {
        var ctx = Android.App.Application.Context;
        return ctx.CheckSelfPermission(Android.Manifest.Permission.AccessCoarseLocation) ==
                   Android.Content.PM.Permission.Granted ||
               ctx.CheckSelfPermission(Android.Manifest.Permission.AccessFineLocation) ==
                   Android.Content.PM.Permission.Granted;
    }

    internal static bool? IsDeviceLocationEnabled()
    {
        var manager = GetManager();
        if (manager is null) return null;
        try
        {
            return manager.IsProviderEnabled(LocationManager.NetworkProvider) ||
                   manager.IsProviderEnabled(LocationManager.GpsProvider);
        }
        catch (Exception ex)
        {
            DiagnosticDebug.WriteLine($"Provider status unavailable: {ex.GetType().Name}");
            return null;
        }
    }

    internal static async Task<MauiLocation?> TryGetAsync(TimeSpan timeout)
    {
        if (!HasForegroundPermission()) return null;
        var manager = GetManager();
        if (manager is null) return null;

        var providers = new[] { LocationManager.NetworkProvider, LocationManager.GpsProvider }
            .Where(provider =>
            {
                try { return manager.IsProviderEnabled(provider); }
                catch { return false; }
            }).ToArray();
        if (providers.Length == 0) return null;

        // A very recent cached fix avoids repeated GPS activation indoors.
        foreach (var provider in providers)
        {
            try
            {
                var cached = manager.GetLastKnownLocation(provider);
                if (cached is null || cached.Time <= 0) continue;
                var age = DateTimeOffset.UtcNow - DateTimeOffset.FromUnixTimeMilliseconds(cached.Time);
                if (age >= TimeSpan.FromSeconds(-10) && age <= TimeSpan.FromMinutes(2) &&
                    IsValid(cached))
                    return new MauiLocation(cached.Latitude, cached.Longitude);
            }
            catch (Exception ex)
            {
                DiagnosticDebug.WriteLine($"Cached provider unavailable: {ex.GetType().Name}");
            }
        }

        using var listener = new OneShotListener();
        try
        {
            // Network and GPS are both eligible. First fix wins; callers never
            // need exact location for their coarse ~1 km private map pin.
            foreach (var provider in providers)
            {
                try { manager.RequestSingleUpdate(provider, listener, Looper.MainLooper); }
                catch (Exception ex)
                {
                    DiagnosticDebug.WriteLine($"Provider registration failed: {ex.GetType().Name}");
                }
            }
            var finished = await Task.WhenAny(listener.Result.Task, Task.Delay(timeout));
            if (finished != listener.Result.Task) return null;
            var fix = await listener.Result.Task;
            return IsValid(fix) ? new MauiLocation(fix.Latitude, fix.Longitude) : null;
        }
        catch (Exception ex)
        {
            DiagnosticDebug.WriteLine($"Android coarse provider unavailable: {ex.GetType().Name}");
            return null;
        }
        finally
        {
            try { manager.RemoveUpdates(listener); }
            catch (Exception ex) { DiagnosticDebug.WriteLine($"Provider cleanup: {ex.GetType().Name}"); }
        }
    }

    private static bool IsValid(Android.Locations.Location location) =>
        double.IsFinite(location.Latitude) && double.IsFinite(location.Longitude) &&
        Math.Abs(location.Latitude) <= 90 && Math.Abs(location.Longitude) <= 180;
}
