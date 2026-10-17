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

    public MainPage() => InitializeComponent();

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
                case "camera-permission":
                    var cameraStatus = await Permissions.CheckStatusAsync<Permissions.Camera>();
                    if (cameraStatus != PermissionStatus.Granted)
                        cameraStatus = await Permissions.RequestAsync<Permissions.Camera>();
                    await GameWebView.EvaluateJavaScriptAsync(
                        $"window.whiskerNativeCameraPermission?.({(cameraStatus == PermissionStatus.Granted ? "true" : "false")});");
                    break;
                case "capture": await GetPhotoAsync(true, GetQuery(request, "request")); break;
                case "import": await GetPhotoAsync(false, GetQuery(request, "request")); break;
                case "location": await GetLocationAsync(); break;
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
                            Title = "Whisker Hunt discovery",
                            Text = text
                        });
                    break;
                case "open":
                    var url = GetQuery(request, "url");
                    if (Uri.TryCreate(url, UriKind.Absolute, out var target) &&
                        target.Scheme == Uri.UriSchemeHttps &&
                        target.Host.Equals("www.openstreetmap.org", StringComparison.OrdinalIgnoreCase))
                        await Launcher.Default.OpenAsync(target);
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

    private async Task GetLocationAsync()
    {
        try
        {
        var status = await Permissions.CheckStatusAsync<Permissions.LocationWhenInUse>();
        if (status != PermissionStatus.Granted)
            status = await Permissions.RequestAsync<Permissions.LocationWhenInUse>();
        if (status != PermissionStatus.Granted)
        {
            await GameWebView.EvaluateJavaScriptAsync("window.whiskerNativeLocationError?.();");
            return;
        }
        var request = new GeolocationRequest(GeolocationAccuracy.Medium, TimeSpan.FromSeconds(10));
        var position = await Geolocation.Default.GetLocationAsync(request);
        if (position is null)
        {
            await GameWebView.EvaluateJavaScriptAsync("window.whiskerNativeLocationError?.();");
            return;
        }
        await GameWebView.EvaluateJavaScriptAsync(
            $"window.whiskerNativeLocation({position.Latitude.ToString(System.Globalization.CultureInfo.InvariantCulture)},{position.Longitude.ToString(System.Globalization.CultureInfo.InvariantCulture)});");
        }
        catch (Exception ex)
        {
            Debug.WriteLine(ex);
            await GameWebView.EvaluateJavaScriptAsync("window.whiskerNativeLocationError?.();");
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
            Title = "Share your Whisker Hunt collectible card",
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
            Title = "Save your Whisker Hunt backup",
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
            Title = "Save your GPS-free Whisker Hunt backup",
            File = new ShareFile(destination, "application/json")
        });
    }

    private async Task RestoreBackupAsync()
    {
        var file = await FilePicker.Default.PickAsync(new PickOptions
        {
            PickerTitle = "Select your Whisker Hunt JSON backup"
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
