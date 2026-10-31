#if ANDROID
using Android.App;
using Android.Content;
using Android.Graphics.Drawables;
using Android.Views;
using Android.Widget;
using Android.Media;
using Microsoft.Maui.Storage;
using System;
using System.IO;

namespace WhiskerHunt;

// 3D Safari ONLY. User choice is private and survives app restarts; AR rendering is unaffected.
internal sealed class HushSafariMusicController : IDisposable
{
    private const string PreferencesName = "hushhunt_ar_safari_audio";
    private const string EnabledKey = "lounge_music_enabled";
    private const string TrackAsset = "hush_safari_lounge.ogg";
    private readonly Activity _host;
    private readonly ISharedPreferences _preferences;
    private readonly TextView _toggle;
    private MediaPlayer? _player;
    private bool _enabled;
    private bool _foreground;
    private bool _disposed;

    private HushSafariMusicController(Activity host, FrameLayout root)
    {
        _host = host;
        _preferences = host.GetSharedPreferences(PreferencesName, FileCreationMode.Private)!;
        _enabled = _preferences.GetBoolean(EnabledKey, true);
        var density = host.Resources?.DisplayMetrics?.Density ?? 1f;
        int Dp(int value) => (int)(value * density + .5f);
        // Compact, accessible button alongside (not over) the red close button.
        _toggle = new TextView(host)
        {
            TextSize = 23,
            Gravity = GravityFlags.Center,
            Clickable = true,
            Focusable = true,
        };
        _toggle.SetTextColor(Android.Graphics.Color.White);
        _toggle.SetPadding(0, 0, 0, 0);
        var background = new GradientDrawable();
        background.SetColor(Android.Graphics.Color.Argb(160, 39, 48, 65));
        background.SetStroke(Dp(1), Android.Graphics.Color.Argb(130, 226, 235, 241));
        background.SetCornerRadius(Dp(23));
        _toggle.Background = background;
        _toggle.Click += (_, _) => Toggle();
        var layout = new FrameLayout.LayoutParams(Dp(44), Dp(44), GravityFlags.Top | GravityFlags.Right);
        layout.TopMargin = Dp(44);
        layout.RightMargin = Dp(72);
        root.AddView(_toggle, layout);
        RefreshIcon();
    }

    public static HushSafariMusicController Attach(Activity host, FrameLayout root)
        => new(host, root);

    private void RefreshIcon()
    {
        _toggle.Text = _enabled ? "♫" : "🔇";
        _toggle.ContentDescription = _enabled ? "Mute 3D Safari music" : "Play 3D Safari music";
    }

    private void Toggle()
    {
        if (_disposed) return;
        _enabled = !_enabled;
        _preferences.Edit()!.PutBoolean(EnabledKey, _enabled)!.Apply();
        RefreshIcon();
        if (_enabled && _foreground) StartOrResume();
        else PauseMusic();
    }

    public void OnArForeground()
    {
        if (_disposed) return;
        _foreground = true;
        if (_enabled) StartOrResume();
    }

    public void OnArBackground()
    {
        _foreground = false;
        PauseMusic();
    }

    private void StartOrResume()
    {
        if (!_foreground || !_enabled || _disposed) return;
        try
        {
            if (_player is null)
            {
                // .NET MAUI bundles Resources/Raw/** as MauiAsset.
                // Copy to the private cache once to give MediaPlayer a seekable source.
                var directory = _host.CacheDir?.AbsolutePath ?? _host.FilesDir?.AbsolutePath;
                if (string.IsNullOrWhiteSpace(directory)) return;
                var path = Path.Combine(directory, TrackAsset);
                if (!File.Exists(path) || new FileInfo(path).Length < 1024)
                {
                    using var input = FileSystem.OpenAppPackageFileAsync(TrackAsset)
                        .GetAwaiter().GetResult();
                    using var output = File.Create(path);
                    input.CopyTo(output);
                }
                var player = new MediaPlayer();
                player.SetDataSource(path);
                player.Looping = true;
                player.SetVolume(0.18f, 0.18f); // Background ambience, not foreground audio.
                player.Prepare();
                _player = player;
            }
            if (!_player.IsPlaying) _player.Start();
        }
        catch (Exception ex)
        {
            Android.Util.Log.Warn("HushSafariMusic", "Music unavailable: " + ex.Message);
            // Audio failure must never crash AR or the petting interaction.
            try { _player?.Release(); _player?.Dispose(); } catch { }
            _player = null;
        }
    }

    private void PauseMusic()
    {
        try { if (_player?.IsPlaying == true) _player.Pause(); }
        catch (Exception ex) { Android.Util.Log.Warn("HushSafariMusic", ex.Message); }
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        _foreground = false;
        try { _player?.Stop(); } catch { }
        try { _player?.Release(); _player?.Dispose(); } catch { }
        _player = null;
    }
}
#endif
