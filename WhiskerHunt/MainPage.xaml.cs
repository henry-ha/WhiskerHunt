using Microsoft.Maui.ApplicationModel;
using Microsoft.Maui.ApplicationModel.DataTransfer;
using Microsoft.Maui.Controls;
using Microsoft.Maui.Devices.Sensors;
using Microsoft.Maui.Media;
using Microsoft.Maui.Storage;
using System.Diagnostics;
using System.Text;
using System.Text.Json;

namespace WhiskerHunt;

/// <summary>
/// Thin native bridge; gameplay, local IndexedDB persistence and the UI are in Resources/Raw.
/// Bridge URLs are intercepted before navigation. No third-party API keys or servers needed.
/// </summary>
public partial class MainPage : ContentPage
{
    private readonly SemaphoreSlim _stateWriteLock = new(1, 1);
    private bool _stateRecoveryBlocked;
    private const string NativeLocationSettingsHost = "device-location-settings";
    private string StatePath => Path.Combine(FileSystem.AppDataDirectory, "whisker-hunt-state.json");
    private string BackupStatePath => StatePath + ".bak";

    // Reject structurally damaged snapshots before replacing a last-known-good save.
    // Keep the original v1 JSON schema so earlier collections still load.
    private static bool IsValidStateJson(string json)
    {
        try
        {
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;
            if (root.ValueKind != JsonValueKind.Object ||
                !root.TryGetProperty("app", out var app) || app.ValueKind != JsonValueKind.String ||
                app.GetString() != "Whisker Hunt" ||
                !root.TryGetProperty("cats", out var cats) || cats.ValueKind != JsonValueKind.Array ||
                cats.GetArrayLength() > 2000 ||
                !root.TryGetProperty("profile", out var profile) || profile.ValueKind != JsonValueKind.Object ||
                !profile.TryGetProperty("xp", out var xp) || xp.ValueKind != JsonValueKind.Number ||
                !xp.TryGetDouble(out var xpValue) || !double.IsFinite(xpValue) || xpValue < 0)
                return false;

            var ids = new HashSet<string>(StringComparer.Ordinal);
            foreach (var cat in cats.EnumerateArray())
            {
                if (cat.ValueKind != JsonValueKind.Object ||
                    !cat.TryGetProperty("id", out var catId) || catId.ValueKind != JsonValueKind.String ||
                    string.IsNullOrWhiteSpace(catId.GetString()) || !ids.Add(catId.GetString()!) ||
                    !cat.TryGetProperty("name", out var name) || name.ValueKind != JsonValueKind.String ||
                    !cat.TryGetProperty("photo", out var photo) || photo.ValueKind != JsonValueKind.String ||
                    !(photo.GetString()?.StartsWith("data:image/", StringComparison.OrdinalIgnoreCase) ?? false) ||
                    !cat.TryGetProperty("sightings", out var sightings) || sightings.ValueKind != JsonValueKind.Array ||
                    sightings.GetArrayLength() == 0 || sightings.GetArrayLength() > 2000)
                    return false;
                var sightingIds = new HashSet<string>(StringComparer.Ordinal);
                foreach (var sighting in sightings.EnumerateArray())
                {
                    if (sighting.ValueKind != JsonValueKind.Object ||
                        !sighting.TryGetProperty("id", out var sightingId) || sightingId.ValueKind != JsonValueKind.String ||
                        string.IsNullOrWhiteSpace(sightingId.GetString()) || !sightingIds.Add(sightingId.GetString()!) ||
                        !sighting.TryGetProperty("at", out var at) || at.ValueKind != JsonValueKind.String)
                        return false;
                }
            }
            return true;
        }
        catch (JsonException) { return false; }
        catch (InvalidOperationException) { return false; }
    }

    private async Task<string?> ReadValidStateAsync()
    {
        foreach (var path in new[] { StatePath, BackupStatePath })
        {
            if (!File.Exists(path) || new FileInfo(path).Length > 36L * 1024 * 1024) continue;
            try
            {
                var json = await File.ReadAllTextAsync(path);
                if (IsValidStateJson(json)) return json;
            }
            catch (IOException ex) { Debug.WriteLine(ex); }
        }
        return null;
    }

    public MainPage()
    {
        InitializeComponent();
#if ANDROID
        HushArCoreActivity.Completed += OnArCoreCompleted;
        HushWideCameraActivity.Completed += OnWideCameraCompleted;
#endif
    }

#if ANDROID
    private void OnArCoreCompleted(HushArCoreActivity.ArOutcome result)
    {
        Microsoft.Maui.ApplicationModel.MainThread.BeginInvokeOnMainThread(async () =>
        {
            try
            {
                var json = JsonSerializer.Serialize(result);
                await GameWebView.EvaluateJavaScriptAsync($"window.hushNativeArCoreResult?.({json});");
            }
            catch (Exception ex) { Debug.WriteLine($"ARCore handoff failed: {ex}"); }
        });
    }
#endif

    #if ANDROID
    private void OnWideCameraCompleted(HushWideCameraActivity.WideOutcome result)
    {
        Microsoft.Maui.ApplicationModel.MainThread.BeginInvokeOnMainThread(async () =>
        {
            try
            {
                var json = JsonSerializer.Serialize(result);
                await GameWebView.EvaluateJavaScriptAsync($"window.hushNativeWideResult?.({json});");
            }
            catch (Exception ex) { Debug.WriteLine($"Wide-camera handoff failed: {ex}"); }
        });
    }
    #endif

    // The JavaScript shell requests its snapshot only after its DOM and handlers
    // are ready. This avoids a race between WebNavigated and IndexedDB boot.
    private async Task LoadNativeStateAsync()
    {
        var hadSnapshots = File.Exists(StatePath) || File.Exists(BackupStatePath);
        var previous = await ReadValidStateAsync();
        if (hadSnapshots && previous is null)
        {
            _stateRecoveryBlocked = true;
            await GameWebView.EvaluateJavaScriptAsync(
                "window.whiskerNativeStorageError('No readable local snapshots');");
            return;
        }
        _stateRecoveryBlocked = false;
        var data = JsonSerializer.Serialize(previous);
        await GameWebView.EvaluateJavaScriptAsync(
            $"window.whiskerUseNativeStorage({data});");
    }

    // In the installed MAUI WebView, signal native AR actions independently
    // of the legacy collection storage mode. Never toggle native storage flags.
    private async void OnWebNavigated(object sender, WebNavigatedEventArgs e)
    {
        if (e.Result != WebNavigationResult.Success) return;
        try
        {
            await GameWebView.EvaluateJavaScriptAsync("window.whiskerNativeBridge=true;");
        }
        catch (Exception ex) { Debug.WriteLine($"Native AR bridge initialization failed: {ex}"); }
    }

    private void OnWebNavigating(object sender, WebNavigatingEventArgs e)
    {
        if (!e.Url.StartsWith("whiskerhunt://", StringComparison.OrdinalIgnoreCase))
            return;

        e.Cancel = true;
        _ = HandleBridgeAsync(e.Url);
    }

    private async Task HandleBridgeAsync(string rawUrl)
    {
        try
        {
            var request = new Uri(rawUrl);
            switch (request.Host.ToLowerInvariant())
            {
                case "ready": await LoadNativeStateAsync(); break;
                case "recovery-preview": await PreviewRecoveryCopyAsync(); break;
                case "recovery-merge": await OfferRecoveryMergeAsync(); break;
                case "recovery-export": await ExportCurrentWithoutSavingAsync(); break;
                case "arcore":
#if ANDROID
                    // A separate Activity owns ARCore's camera, avoiding collisions with WebView getUserMedia.
                    // No camera frames are retained until the player explicitly taps Collect.
                    var modelKey = GetQuery(request, "model") ?? string.Empty;
                    var species = GetQuery(request, "species") ?? string.Empty;
                    var name = GetQuery(request, "name") ?? string.Empty;
                    if (modelKey.Length > 140 || species.Length > 40 || name.Length > 90 ||
                        !System.Text.RegularExpressions.Regex.IsMatch(modelKey, @"^[a-zA-Z0-9_-]+$"))
                    {
                        await GameWebView.EvaluateJavaScriptAsync(
                            "window.hushNativeArCoreResult?.({status:'error',message:'Invalid ARCore model identifier.'});");
                        break;
                    }
                    try
                    {
                        var currentActivity = Platform.CurrentActivity;
                        if (currentActivity is null)
                            throw new InvalidOperationException("Android Activity is not available yet. Close and reopen AR Safari.");
                        var arIntent = new Android.Content.Intent(currentActivity, typeof(HushArCoreActivity));
                        arIntent.PutExtra("model", modelKey);
                        arIntent.PutExtra("species", species);
                        arIntent.PutExtra("name", name);
                        currentActivity.StartActivity(arIntent);
                    }
                    catch (Exception arEx)
                    {
                        // Send AR-specific launch failures back to the Safari screen instead
                        // of leaving players with an unresponsive button.
                        var resultJson = JsonSerializer.Serialize(new
                        {
                            status = "unavailable",
                            message = "Could not open ARCore Safari: " + arEx.Message
                        });
                        await GameWebView.EvaluateJavaScriptAsync(
                            $"window.hushNativeArCoreResult?.({resultJson});");
                    }
#else
                    await GameWebView.EvaluateJavaScriptAsync(
                        "window.hushNativeArCoreResult?.({status:'unavailable',message:'ARCore only runs on Android.'});");
#endif
                    break;
                case "camera-permission":
                    var cameraStatus = await Permissions.CheckStatusAsync<Permissions.Camera>();
                    if (cameraStatus != PermissionStatus.Granted)
                        cameraStatus = await Permissions.RequestAsync<Permissions.Camera>();
                    await GameWebView.EvaluateJavaScriptAsync(
                        $"window.whiskerNativeCameraPermission?.({(cameraStatus == PermissionStatus.Granted ? "true" : "false")});");
                    break;
                case "wide-camera":
#if ANDROID
                    var wideToken = GetQuery(request, "request") ?? "";
                    if (!System.Text.RegularExpressions.Regex.IsMatch(wideToken, @"^[0-9]{1,15}$"))
                    {
                        await GameWebView.EvaluateJavaScriptAsync("window.hushNativeWideResult?.({status:'error',message:'Invalid wide-camera request.'});");
                        break;
                    }
                    try
                    {
                        var wideActivity = Platform.CurrentActivity ??
                            throw new InvalidOperationException("Android activity unavailable.");
                        var wideIntent = new Android.Content.Intent(wideActivity, typeof(HushWideCameraActivity));
                        wideIntent.PutExtra("request", wideToken);
                        wideActivity.StartActivity(wideIntent);
                    }
                    catch (Exception ex)
                    {
                        var failure = JsonSerializer.Serialize(new {status="error",request=wideToken,message=ex.Message});
                        await GameWebView.EvaluateJavaScriptAsync($"window.hushNativeWideResult?.({failure});");
                    }
#else
                    await GameWebView.EvaluateJavaScriptAsync("window.hushNativeWideResult?.({status:'unavailable',message:'Android only.'});");
#endif
                    break;
                case "capture": await GetPhotoAsync(true, GetQuery(request, "request")); break;
                case "import": await GetPhotoAsync(false, GetQuery(request, "request")); break;
                case "location": await GetLocationAsync(GetQuery(request, "request")); break;
                case "location-check": await GetLocationDiagnosticAsync(GetQuery(request, "request")); break;
                case "app-settings":
#if ANDROID
                    try
                    {
                        // Open this app's own settings, not a generic settings page.
                        var context = Android.App.Application.Context;
                        var intent = new Android.Content.Intent(
                            Android.Provider.Settings.ActionApplicationDetailsSettings,
                            Android.Net.Uri.Parse("package:" + context.PackageName));
                        intent.AddFlags(Android.Content.ActivityFlags.NewTask);
                        context.StartActivity(intent);
                    }
                    catch (Exception ex) { Debug.WriteLine($"App settings unavailable: {ex}"); }
#else
                    try { AppInfo.Current.ShowSettingsUI(); }
                    catch (Exception ex) { Debug.WriteLine($"App settings unavailable: {ex}"); }
#endif
                    break;
                case NativeLocationSettingsHost:
#if ANDROID
                    try
                    {
                        var intent = new Android.Content.Intent(Android.Provider.Settings.ActionLocationSourceSettings);
                        intent.AddFlags(Android.Content.ActivityFlags.NewTask);
                        Android.App.Application.Context.StartActivity(intent);
                    }
                    catch (Exception ex) { Debug.WriteLine($"Location settings unavailable: {ex}"); }
#endif
                    break;
                case "export": await ExportBackupAsync(); break;
                case "export-safe": await ExportSafeBackupAsync(); break;
                case "sticker": await ShareCatCardAsync(); break;
                case "restore": await RestoreBackupAsync(); break;
                case "sync":
                    var token = GetQuery(request, "request");
                    bool saved;
                    try { saved = await SaveNativeStateAsync(
                        allowRecovery: GetQuery(request, "recover") == "1",
                        allowEmpty: GetQuery(request, "allow-empty") == "1"); }
                    catch (Exception ex) { Debug.WriteLine(ex); saved = false; }
                    await GameWebView.EvaluateJavaScriptAsync(
                        $"window.whiskerNativeSyncResult({JsonSerializer.Serialize(token)},{(saved ? "true" : "false")});");
                    break;
                case "share":
                    var text = GetQuery(request, "text");
                    if (!string.IsNullOrWhiteSpace(text))
                        await Share.Default.RequestAsync(new ShareTextRequest
                        {
                            Title = "Hush Hunt discovery",
                            Text = text
                        });
                    break;
                case "open":
                    // The WebView is loaded from file://. Open external maps with a native
                    // ACTION_VIEW intent instead of navigating the WebView or silently failing.
                    var url = GetQuery(request, "url");
                    var launched = false;
                    if (Uri.TryCreate(url, UriKind.Absolute, out var target) &&
                        target.Scheme == Uri.UriSchemeHttps &&
                        target.Host.Equals("www.openstreetmap.org", StringComparison.OrdinalIgnoreCase))
                    {
                        try
                        {
#if ANDROID
                            var context = Android.App.Application.Context;
                            var intent = new Android.Content.Intent(
                                Android.Content.Intent.ActionView,
                                Android.Net.Uri.Parse(target.AbsoluteUri));
                            intent.AddCategory(Android.Content.Intent.CategoryBrowsable);
                            intent.AddFlags(Android.Content.ActivityFlags.NewTask);
                            context.StartActivity(intent);
                            launched = true;
#else
                            launched = await Launcher.Default.TryOpenAsync(target);
#endif
                        }
                        catch (Exception ex)
                        {
                            Debug.WriteLine($"OpenStreetMap launch failed: {ex}");
                        }
                    }
                    await GameWebView.EvaluateJavaScriptAsync(
                        $"window.whiskerExternalMapResult?.({(launched ? "true" : "false")});");
                    break;
            }
        }
        catch (Exception ex)
        {
            Debug.WriteLine(ex);
            await JsErrorAsync("Action could not be completed. Please try again.");
        }
    }

    // Local recovery is read-only until the user confirms the existing additive merge.
    // The .bak file is never moved, overwritten or deleted by this workflow.
    private async Task<string?> ReadRecoveryCopyAsync()
    {
        if (!File.Exists(BackupStatePath) || new FileInfo(BackupStatePath).Length > 36L * 1024 * 1024)
            return null;
        try
        {
            var text = await File.ReadAllTextAsync(BackupStatePath);
            return IsValidStateJson(text) ? text : null;
        }
        catch (IOException error)
        {
            Debug.WriteLine(error);
            return null;
        }
    }

    private async Task PreviewRecoveryCopyAsync()
    {
        var snapshot = await ReadRecoveryCopyAsync();
        if (snapshot is null)
        {
            await GameWebView.EvaluateJavaScriptAsync("window.whiskerRecoveryPreview?.({available:false});");
            return;
        }
        // Send metadata only, not full photos, during preview.
        using var doc = JsonDocument.Parse(snapshot);
        var cats = doc.RootElement.GetProperty("cats").EnumerateArray()
            .Select(cat => new
            {
                id = cat.GetProperty("id").GetString(),
                name = cat.GetProperty("name").GetString(),
                sightings = cat.GetProperty("sightings").GetArrayLength()
            }).ToList();
        var preview = JsonSerializer.Serialize(new { available = true, cats });
        await GameWebView.EvaluateJavaScriptAsync(
            $"window.whiskerRecoveryPreview?.({preview});");
    }

    private async Task OfferRecoveryMergeAsync()
    {
        var snapshot = await ReadRecoveryCopyAsync();
        if (snapshot is null)
        {
            await GameWebView.EvaluateJavaScriptAsync(
                "window.whiskerRecoveryMissing?.();");
            return;
        }
        // Reuse the validated v1 additive JSON merge. JavaScript asks for explicit
        // confirmation; the native .bak file stays intact even if merge fails.
        await GameWebView.EvaluateJavaScriptAsync(
            $"window.whiskerRecoveryImport?.({JsonSerializer.Serialize(snapshot)});");
    }

    // Recovery wizard export deliberately does not call SaveNativeStateAsync:
    // that would rotate .bak and could destroy the very copy being recovered.
    private async Task ExportCurrentWithoutSavingAsync()
    {
        var result = await GameWebView.EvaluateJavaScriptAsync("window.whiskerBackupBase64();");
        if (string.IsNullOrWhiteSpace(result)) return;
        var base64 = result.StartsWith('"')
            ? JsonSerializer.Deserialize<string>(result) ?? "" : result;
        if (base64.Length == 0 || base64.Length > 48 * 1024 * 1024)
        {
            await JsErrorAsync("Collection too large to export safely.");
            return;
        }
        var data = Convert.FromBase64String(base64);
        var json = Encoding.UTF8.GetString(data);
        if (!IsValidStateJson(json))
        {
            await JsErrorAsync("Current collection did not pass backup checks. Nothing was changed.");
            return;
        }
        var copy = Path.Combine(FileSystem.CacheDirectory,
            $"whisker-hunt-before-recovery-{DateTime.Now:yyyyMMdd-HHmmss}.json");
        await File.WriteAllBytesAsync(copy, data);
        await Share.Default.RequestAsync(new ShareFileRequest
        {
            Title = "Save your current CatDex before recovery",
            File = new ShareFile(copy, "application/json")
        });
    }

    private static string? GetQuery(Uri uri, string key)
    {
        var query = uri.Query.TrimStart('?');
        foreach (var item in query.Split('&', StringSplitOptions.RemoveEmptyEntries))
        {
            var parts = item.Split('=', 2);
            if (Uri.UnescapeDataString(parts[0]) == key)
                return parts.Length == 2 ? Uri.UnescapeDataString(parts[1].Replace('+', ' ')) : "";
        }
        return null;
    }

    // Every picker response carries the JavaScript request token that opened it.
    // A cancelled or superseded Android picker can no longer replace a later photo.
    private Task ReportPhotoCancelledAsync(string? requestToken) =>
        GameWebView.EvaluateJavaScriptAsync(
            $"window.whiskerNativePhotoCancelled?.({JsonSerializer.Serialize(requestToken)});");

    private Task ReportPhotoErrorAsync(string? requestToken, string message) =>
        GameWebView.EvaluateJavaScriptAsync(
            $"window.whiskerNativePhotoError?.({JsonSerializer.Serialize(requestToken)},{JsonSerializer.Serialize(message)});");

    private async Task GetPhotoAsync(bool capture, string? requestToken)
    {
        if (string.IsNullOrWhiteSpace(requestToken))
        {
            await JsErrorAsync("Camera request could not be verified. Please try again.");
            return;
        }
        try
        {
            FileResult? photo;
            var options = new MediaPickerOptions
            {
                MaximumWidth = 1200,
                MaximumHeight = 1200,
                CompressionQuality = 85,
                RotateImage = true,
                PreserveMetaData = false,
                SelectionLimit = 1
            };
            if (capture)
            {
                if (!MediaPicker.Default.IsCaptureSupported)
                {
                    await ReportPhotoErrorAsync(requestToken, "Camera is not available on this device.");
                    return;
                }
                photo = await MediaPicker.Default.CapturePhotoAsync(options);
            }
            else
                photo = (await MediaPicker.Default.PickPhotosAsync(options)).FirstOrDefault();

            if (photo is null)
            {
                await ReportPhotoCancelledAsync(requestToken);
                return;
            }
            // Bound memory even when Android provides a non-seekable content stream.
            const int maxPhotoBytes = 8 * 1024 * 1024;
            await using var stream = await photo.OpenReadAsync();
            if (stream.CanSeek && stream.Length > maxPhotoBytes)
            {
                await ReportPhotoErrorAsync(requestToken, "Photo too large. Please use a smaller image.");
                return;
            }
            await using var copy = new MemoryStream();
            var buffer = new byte[64 * 1024];
            int read;
            while ((read = await stream.ReadAsync(buffer.AsMemory())) > 0)
            {
                if (copy.Length + read > maxPhotoBytes)
                {
                    await ReportPhotoErrorAsync(requestToken, "Photo too large. Please use a smaller image.");
                    return;
                }
                await copy.WriteAsync(buffer.AsMemory(0, read));
            }
            var bytes = copy.ToArray();
            var mime = bytes.Length >= 3 && bytes[0] == 0xFF && bytes[1] == 0xD8 && bytes[2] == 0xFF
                ? "image/jpeg"
                : bytes.Length >= 8 && bytes.AsSpan(0, 8).SequenceEqual(new byte[] { 137, 80, 78, 71, 13, 10, 26, 10 })
                    ? "image/png"
                    : bytes.Length >= 12 && Encoding.ASCII.GetString(bytes, 0, 4) == "RIFF" &&
                      Encoding.ASCII.GetString(bytes, 8, 4) == "WEBP"
                        ? "image/webp" : null;
            if (mime is null)
            {
                await ReportPhotoErrorAsync(requestToken, "Unsupported image format. Please choose JPEG, PNG or WebP.");
                return;
            }
            var dataUri = $"data:{mime};base64," + Convert.ToBase64String(bytes);
            await GameWebView.EvaluateJavaScriptAsync(
                $"window.whiskerNativePhoto({JsonSerializer.Serialize(dataUri)},{JsonSerializer.Serialize(requestToken)});");
        }
        catch (OperationCanceledException)
        {
            await ReportPhotoCancelledAsync(requestToken);
        }
        catch (Exception ex)
        {
            Debug.WriteLine(ex);
            await ReportPhotoErrorAsync(requestToken, "Could not open that photo. Please try again.");
        }
    }

    /// <summary>
    /// Reports permission/provider status only. Does not request or reveal location.
    /// Useful when Android Settings says Allowed but the app reports Denied.
    /// </summary>
    private Task GetLocationDiagnosticAsync(string? requestToken)
    {
#if ANDROID
        var context = Android.App.Application.Context;
        var diagnostic = new
        {
            build = AppInfo.Current.VersionString,
            coarse = context.CheckSelfPermission(Android.Manifest.Permission.AccessCoarseLocation) ==
                Android.Content.PM.Permission.Granted,
            fine = context.CheckSelfPermission(Android.Manifest.Permission.AccessFineLocation) ==
                Android.Content.PM.Permission.Granted,
            deviceEnabled = AndroidApproximateLocationProvider.IsDeviceLocationEnabled()
        };
        return GameWebView.EvaluateJavaScriptAsync(
            $"window.whiskerNativeLocationDiagnostic?.({JsonSerializer.Serialize(requestToken)},{JsonSerializer.Serialize(diagnostic)});");
#else
        return GameWebView.EvaluateJavaScriptAsync(
            $"window.whiskerNativeLocationDiagnostic?.({JsonSerializer.Serialize(requestToken)},null);");
#endif
    }

    /// <summary>
    /// Foreground-only, opt-in, approximate location. Permission being allowed
    /// does not guarantee that Android has a GPS/network fix (e.g., indoors).
    /// Returns a typed failure reason so the UI can help without asking the
    /// child to re-enable a permission that is already granted.
    /// </summary>
    private async Task GetLocationAsync(string? requestToken)
    {
        var safeToken = JsonSerializer.Serialize(requestToken);
        async Task FailAsync(string reason) => await GameWebView.EvaluateJavaScriptAsync(
            $"window.whiskerNativeLocationError?.({safeToken},{JsonSerializer.Serialize(reason)});");

        try
        {
#if ANDROID
            // Android can report LocationWhenInUse as denied when the user
            // granted only Approximate location. COARSE alone is sufficient.
            var permitted = AndroidApproximateLocationProvider.HasForegroundPermission();
            if (!permitted)
            {
                // Request only ACCESS_COARSE_LOCATION. The combined MAUI location
                // request may report Denied for an Android approximate-only grant.
                // Do not request precise or background access for a private area pin.
                await Permissions.RequestAsync<WhiskerCoarseLocationPermission>();
                // The OS grant, not MAUI's grouped status, is authoritative.
                permitted = AndroidApproximateLocationProvider.HasForegroundPermission();
            }
            if (!permitted)
            {
                await FailAsync("permission");
                return;
            }
            if (AndroidApproximateLocationProvider.IsDeviceLocationEnabled() == false)
            {
                await FailAsync("disabled");
                return;
            }

            // Use Android's foreground providers directly. MAUI's generic
            // geolocation wrapper can reject an approximate-only grant.
            var position = await AndroidApproximateLocationProvider.TryGetAsync(TimeSpan.FromSeconds(18));
#else
            var permission = await Permissions.CheckStatusAsync<Permissions.LocationWhenInUse>();
            if (permission != PermissionStatus.Granted)
                permission = await Permissions.RequestAsync<Permissions.LocationWhenInUse>();
            if (permission != PermissionStatus.Granted)
            {
                await FailAsync("permission");
                return;
            }
            Location? position = null;
#endif
            if (position is null)
            {
                try
                {
                    position = await Geolocation.Default.GetLocationAsync(
                        new GeolocationRequest(GeolocationAccuracy.Low, TimeSpan.FromSeconds(10)));
                }
                catch (FeatureNotEnabledException)
                {
                    await FailAsync("disabled");
                    return;
                }
                catch (PermissionException ex)
                {
                    Debug.WriteLine($"MAUI geolocation permission check rejected coarse access: {ex.GetType().Name}");
#if ANDROID
                    // Do not incorrectly tell users with COARSE permission that
                    // location is denied. The native fallback was already tried.
                    if (!AndroidApproximateLocationProvider.HasForegroundPermission())
                    {
                        await FailAsync("permission");
                        return;
                    }
#else
                    await FailAsync("permission");
                    return;
#endif
                }
                catch (OperationCanceledException)
                {
                    // Last-known location is still worth checking.
                }
            }
            if (position is null)
            {
                try
                {
                    var cached = await Geolocation.Default.GetLastKnownLocationAsync();
                    if (cached != null && cached.Timestamp <= DateTimeOffset.UtcNow.AddSeconds(10)
                        && DateTimeOffset.UtcNow - cached.Timestamp <= TimeSpan.FromMinutes(2))
                        position = cached;
                }
                catch (Exception ex) { Debug.WriteLine($"Last-known location: {ex.GetType().Name}"); }
            }
            if (position is null || !double.IsFinite(position.Latitude) ||
                !double.IsFinite(position.Longitude) || Math.Abs(position.Latitude) > 90 ||
                Math.Abs(position.Longitude) > 180)
            {
                await FailAsync("no_fix");
                return;
            }

            // Never send precise coordinates into the WebView / JSON backups.
            var lat = Math.Round(position.Latitude, 2, MidpointRounding.AwayFromZero);
            var lng = Math.Round(position.Longitude, 2, MidpointRounding.AwayFromZero);
            await GameWebView.EvaluateJavaScriptAsync(
                $"window.whiskerNativeLocation?.({lat.ToString(System.Globalization.CultureInfo.InvariantCulture)},{lng.ToString(System.Globalization.CultureInfo.InvariantCulture)},{safeToken});");
        }
        catch (FeatureNotEnabledException ex)
        {
            Debug.WriteLine(ex); await FailAsync("disabled");
        }
        catch (FeatureNotSupportedException ex)
        {
            Debug.WriteLine(ex); await FailAsync("unsupported");
        }
        catch (PermissionException ex)
        {
            Debug.WriteLine(ex);
#if ANDROID
            await FailAsync(AndroidApproximateLocationProvider.HasForegroundPermission() ? "no_fix" : "permission");
#else
            await FailAsync("permission");
#endif
        }
        catch (OperationCanceledException ex)
        {
            Debug.WriteLine(ex); await FailAsync("timeout");
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"Whisker Hunt native location failure: {ex}");
            await FailAsync("no_fix");
        }
    }

    // Safety gate: reject a snapshot unexpectedly losing a large part of the
    // collection. This avoids replacing populated photos with a fresh empty
    // state if a WebView/session inadvertently resets. Only a confirmed user
    // deletion of the final cat may authorise an empty collection.
    private static int CountCats(string json)
    {
        using var document = JsonDocument.Parse(json);
        return document.RootElement.GetProperty("cats").GetArrayLength();
    }

    private async Task<bool> SaveNativeStateAsync(bool allowRecovery = false, bool allowEmpty = false)
    {
        await _stateWriteLock.WaitAsync();
        try
        {
            // Even direct native export must not replace an unreadable collection.
            if (_stateRecoveryBlocked && !allowRecovery) return false;
            var result = await GameWebView.EvaluateJavaScriptAsync("window.whiskerBackupBase64();");
            if (string.IsNullOrWhiteSpace(result)) return false;
            var base64 = result.StartsWith('"')
                ? JsonSerializer.Deserialize<string>(result) ?? ""
                : result;
            if (base64.Length > 48 * 1024 * 1024)
            {
                await JsErrorAsync("Your collection exceeds the current local save limit.");
                return false;
            }
            var bytes = Convert.FromBase64String(base64);
            var json = Encoding.UTF8.GetString(bytes);
            if (!IsValidStateJson(json))
            {
                await JsErrorAsync("Could not verify the saved collection. Your previous save was kept.");
                return false;
            }
            // Compare with the strongest valid on-device snapshot. A one-off
            // WebView state reset must never silently replace someone's photos.
            var newCount = CountCats(json);
            var previousCounts = new List<int>();
            foreach (var path in new[] { StatePath, BackupStatePath })
            {
                if (!File.Exists(path) || new FileInfo(path).Length > 36L * 1024 * 1024) continue;
                try
                {
                    var existing = await File.ReadAllTextAsync(path);
                    if (IsValidStateJson(existing)) previousCounts.Add(CountCats(existing));
                }
                catch (IOException ex) { Debug.WriteLine(ex); }
            }
            var previousCount = previousCounts.Count > 0 ? previousCounts.Max() : 0;
            var suspiciousDrop = newCount < previousCount - Math.Max(2, previousCount / 4);
            if ((!allowRecovery && suspiciousDrop) ||
                (previousCount > 0 && newCount == 0 && !allowEmpty && !allowRecovery))
            {
                await JsErrorAsync("Collection safety lock: an unexpected loss of saved cats was detected. Your previous collection was not overwritten. Export your existing backups before continuing.");
                return false;
            }
            var temp = StatePath + ".tmp";
            await File.WriteAllBytesAsync(temp, bytes);
            // Retain a last-known-good snapshot if an Android process is interrupted.
            if (File.Exists(StatePath) && new FileInfo(StatePath).Length <= 36L * 1024 * 1024)
            {
                try
                {
                    // Never replace the recovery snapshot with a corrupt primary file.
                    var oldState = await File.ReadAllTextAsync(StatePath);
                    if (IsValidStateJson(oldState))
                        File.Copy(StatePath, BackupStatePath, overwrite: true);
                }
                catch (IOException ex) { Debug.WriteLine(ex); }
            }
            File.Move(temp, StatePath, overwrite: true);
            _stateRecoveryBlocked = false;
            return true;
        }
        finally
        {
            _stateWriteLock.Release();
        }
    }

    /// <summary>Creates a shareable, location-free collectible card in the app cache.</summary>
    private async Task ShareCatCardAsync()
    {
        var result = await GameWebView.EvaluateJavaScriptAsync("window.whiskerCardBase64();");
        if (string.IsNullOrWhiteSpace(result))
        {
            await JsErrorAsync("Generate a cat card first.");
            return;
        }
        var value = result.StartsWith('"')
            ? JsonSerializer.Deserialize<string>(result) ?? ""
            : result;
        // Prevent oversized JavaScript bridge data or unbounded file writes.
        if (value.Length == 0 || value.Length > 16 * 1024 * 1024)
        {
            await JsErrorAsync("The cat card is too large to share.");
            return;
        }
        var bytes = Convert.FromBase64String(value);
        if (bytes.Length < 8 || !bytes.AsSpan(0, 8).SequenceEqual(new byte[] { 137, 80, 78, 71, 13, 10, 26, 10 }))
        {
            await JsErrorAsync("Invalid PNG card data.");
            return;
        }
        var path = Path.Combine(FileSystem.CacheDirectory, $"whisker-hunt-card-{DateTime.Now:yyyyMMdd-HHmmss}.png");
        await File.WriteAllBytesAsync(path, bytes);
        await Share.Default.RequestAsync(new ShareFileRequest
        {
            Title = "Share your Hush Hunt collectible card",
            File = new ShareFile(path, "image/png")
        });
    }

    private async Task ExportBackupAsync()
    {
        // Never share a stale snapshot when the current JavaScript save failed.
        if (!await SaveNativeStateAsync()) return;
        if (!File.Exists(StatePath))
        {
            await JsErrorAsync("No collection backup could be created.");
            return;
        }
        var destination = Path.Combine(FileSystem.CacheDirectory,
            $"whisker-hunt-backup-{DateTime.Now:yyyyMMdd-HHmmss}.json");
        File.Copy(StatePath, destination, overwrite: true);
        await Share.Default.RequestAsync(new ShareFileRequest
        {
            Title = "Save your Hush Hunt backup",
            File = new ShareFile(destination)
        });
    }

    /// <summary>Shares a GPS-free backup without altering local pins or replacing the primary snapshot.</summary>
    private async Task ExportSafeBackupAsync()
    {
        if (_stateRecoveryBlocked)
        {
            await JsErrorAsync("Restore your CatDex backup before exporting.");
            return;
        }
        var result = await GameWebView.EvaluateJavaScriptAsync("window.whiskerBackupBase64(true);");
        if (string.IsNullOrWhiteSpace(result))
        {
            await JsErrorAsync("Unable to prepare the GPS-free backup.");
            return;
        }
        var base64 = result.StartsWith('"')
            ? JsonSerializer.Deserialize<string>(result) ?? ""
            : result;
        if (base64.Length == 0 || base64.Length > 48 * 1024 * 1024)
        {
            await JsErrorAsync("The backup exceeds the 36 MB limit.");
            return;
        }
        var bytes = Convert.FromBase64String(base64);
        var json = Encoding.UTF8.GetString(bytes);
        if (!IsValidStateJson(json))
        {
            await JsErrorAsync("GPS-free backup validation failed.");
            return;
        }
        using (var document = JsonDocument.Parse(json))
        {
            foreach (var cat in document.RootElement.GetProperty("cats").EnumerateArray())
            {
                if (!cat.TryGetProperty("sightings", out var sightings) || sightings.ValueKind != JsonValueKind.Array)
                {
                    await JsErrorAsync("Backup has an invalid sightings list.");
                    return;
                }
                foreach (var sighting in sightings.EnumerateArray())
                {
                    if (sighting.TryGetProperty("lat", out _) || sighting.TryGetProperty("lng", out _))
                    {
                        await JsErrorAsync("The backup still contains location coordinates. Nothing was shared.");
                        return;
                    }
                }
            }
        }
        var destination = Path.Combine(FileSystem.CacheDirectory,
            $"whisker-hunt-gps-free-backup-{DateTime.Now:yyyyMMdd-HHmmss}.json");
        await File.WriteAllBytesAsync(destination, bytes);
        await Share.Default.RequestAsync(new ShareFileRequest
        {
            Title = "Save your GPS-free Hush Hunt backup",
            File = new ShareFile(destination, "application/json")
        });
    }

    private async Task RestoreBackupAsync()
    {
        var file = await FilePicker.Default.PickAsync(new PickOptions
        {
            PickerTitle = "Select your Hush Hunt JSON backup"
        });
        if (file is null) return;
        await using var stream = await file.OpenReadAsync();
        if (stream.CanSeek && stream.Length > 30 * 1024 * 1024)
        {
            await JsErrorAsync("Backup is too large (30 MB maximum).");
            return;
        }
        // FilePicker can return non-seekable streams; enforce the limit while reading.
        const int maxBackupCharacters = 30 * 1024 * 1024;
        using var reader = new StreamReader(stream);
        var jsonBuilder = new StringBuilder();
        var chars = new char[8192];
        int count;
        while ((count = await reader.ReadAsync(chars.AsMemory())) > 0)
        {
            if (jsonBuilder.Length + count > maxBackupCharacters)
            {
                await JsErrorAsync("Backup is too large (30 MB maximum).");
                return;
            }
            jsonBuilder.Append(chars, 0, count);
        }
        var json = jsonBuilder.ToString();
        await GameWebView.EvaluateJavaScriptAsync(
            $"window.whiskerLoadBackup({JsonSerializer.Serialize(json)});");
    }

    private Task JsErrorAsync(string message)
        => GameWebView.EvaluateJavaScriptAsync(
            $"window.whiskerNativeError({JsonSerializer.Serialize(message)});");
}
