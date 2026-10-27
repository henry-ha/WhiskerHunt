#if ANDROID
using Android.App;
using Android.Content;
using Android.Content.PM;
using Android.Graphics;
using Android.Graphics.Drawables;
using Android.Opengl;
using Android.OS;
using Android.Views;
using Android.Widget;
using Google.AR.Core;
using Java.Nio;
using System.Text;
using System.Text.Json.Serialization;
using GLES = Android.Opengl.GLES20;
using JLog = Android.Util.Log;
using AndroidColor = Android.Graphics.Color;
using LayoutParams = Android.Widget.FrameLayout.LayoutParams;
// Qualify Android controls/graphics in a MAUI compilation to avoid global using collisions.
using AndroidButton = Android.Widget.Button;
using AndroidRect = Android.Graphics.Rect;
using AndroidPaint = Android.Graphics.Paint;

namespace WhiskerHunt;

/// <summary>
/// An optional native ARCore scene, separate from MAUI WebView's camera.
/// Detects real planes, creates an ARCore world anchor at a user's tap,
/// tracks its location in 3D, and renders a textured GLB wildlife mesh
/// at the anchor. Walking around reveals multiple sides (real perspective).
/// Only species with bundled, recognisable textured GLB models are allowed.
/// No image/location leaves the device through this activity.
/// </summary>
[Activity(Label = "Hush Hunt · ARCore Safari", Theme = "@android:style/Theme.Material.NoActionBar",
    Exported = false, ScreenOrientation = ScreenOrientation.Portrait)]
public sealed class HushArCoreActivity : Activity
{
    public sealed class ArOutcome
    {
        [JsonPropertyName("status")] public string Status { get; init; } = "error";
        [JsonPropertyName("model")] public string Model { get; init; } = "";
        [JsonPropertyName("photo")] public string? Photo { get; init; }
        [JsonPropertyName("message")] public string? Message { get; init; }
    }

    public static event Action<ArOutcome>? Completed;
    private static ArOutcome? _pending;
    public static void DispatchPending()
    {
        var outcome = System.Threading.Interlocked.Exchange(ref _pending, null);
        if (outcome is not null) Completed?.Invoke(outcome);
    }
    private GLSurfaceView? _surface;
    private FrameLayout? _root;
    private TextView? _status;
    private AndroidButton? _place, _collect;
    private ArRenderer? _renderer;
    private HushGlbAnimal3D? _animal;
    private Session? _session;
    private Anchor? _anchor;
    private Anchor? _walkingDestination;
    private long _walkStartMs;
    private int _walkDurationMs;
    private float _yawDegrees, _pitchDegrees;
    private string _model = "";
    private string _species = "";
    private string _animalName = "";
    private bool _installRequested, _didComplete, _resumed;
    private bool _filamentRequested;
    private bool _filamentAnnounced;
    private bool _filamentWatchdogWarned;
    private long _filamentLaunchMs;
    private PixelCopyListener? _copyListener;
    private bool _capturePending;
    private bool _placementReady;
    private bool _modelFrameConfirmed;
    // Resize the animal without moving its ARCore world anchor or digitally cropping the camera.
    private float _animalScale = 1f;
    private float _pinchDistance;
    private bool _pinching;
    private TextView? _sizeLabel;
    private TextView? _petFeedback;
    // Every tap/stroke is checked against projected 3D bounds, not the entire camera.
    private float _petLeft, _petTop, _petRight, _petBottom;
    private bool _petBoundsValid, _petGestureStarted, _petGestureTriggered;
    private float _petStartX, _petStartY, _petTravelX, _petTravelY;
    private long _lastPetTick, _reactionStartedAt;
    private readonly System.Random _petRandom = new();
    private static readonly long ReactionDurationMs = 850;

    private readonly object _frameLock = new();

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);
        _model = Intent?.GetStringExtra("model") ?? "";
        _species = Intent?.GetStringExtra("species") ?? "Other";
        _animalName = Intent?.GetStringExtra("name") ?? "Animal";
        // The Filament glTF loader understands modern PBR / skinned GLBs that
        // the legacy simplified OpenGL loader cannot parse. For those assets
        // keep the ARCore camera working even without a legacy-renderer model.
        var filename = HushGlbAnimal3D.ResolveBundledFilename(_model, _species, _animalName);
        if (string.IsNullOrWhiteSpace(filename))
        {
            FinishWith("fallback", $"No 3D model is installed for {_animalName}.");
            return;
        }
        try { using var check = Assets!.Open("ar_models/" + filename); }
        catch { FinishWith("fallback", $"Missing 3D wildlife asset: {filename}"); return; }
        bool hasLegacyMesh = HushGlbAnimal3D.TryLoad(this, _model, _species, _animalName,
            out _animal, out var loadMessage);
        string name = _animalName;

        _root = new FrameLayout(this) { Background = new ColorDrawable(AndroidColor.Black) };
        _surface = new GLSurfaceView(this);
        _surface.SetEGLContextClientVersion(2);
        _surface.SetEGLConfigChooser(8, 8, 8, 8, 16, 0); // Real 3D mesh needs a depth buffer.
        // The Android binding does not expose SetPreserveEGLContextOnPause(bool).
        // GLSurfaceView recreates the GL resources after context loss; OnSurfaceCreated
        // handles that lifecycle safely instead of requiring a non-existent setter.
        _renderer = new ArRenderer(this, _animal);
        _surface.SetRenderer(_renderer);
        _surface.RenderMode = Rendermode.Continuously;
        _root.AddView(_surface, new LayoutParams(-1, -1));
        // Reserve Filament for modern (quantised / skinned / extended) assets.
        // Running it over compatible legacy animals caused black silhouettes
        // and false-positive readiness, so keep those on the proven OpenGL path.
        bool modernHdAsset = !hasLegacyMesh || !IsPrimaryAssetLegacyCompatible(filename!);
        // Filament presents PBR geometry over ARCore's existing camera feed.
        float metres = _species.ToLowerInvariant() switch
        {
            "cat" => .47f, "dog" => .65f, "rabbit" => .35f, "squirrel" => .31f,
            "bird" => .32f, "hedgehog" => .24f,
            "other" when _animalName.Equals("Deer", StringComparison.OrdinalIgnoreCase) => 1.05f,
            "other" when _animalName.Equals("Fox", StringComparison.OrdinalIgnoreCase) => .65f,
            "snail" => .22f, "butterfly" or "bee" or "ant" or "beetle" => .13f,
            _ => .3f
        };
        _filamentRequested = modernHdAsset && HushFilamentBridge.TryInstall(this, _root, filename!, metres);
        _filamentLaunchMs = System.Environment.TickCount64;
        if (!hasLegacyMesh && !_filamentRequested)
        {
            Android.Util.Log.Error("HushHuntAR", "Neither renderer could open " + filename +
                ". Filament: " + HushFilamentBridge.LastError + ". Legacy: " + loadMessage);
            FinishWith("fallback", $"{_animalName} needs the updated 3D wildlife renderer. " +
                "Please use 2D Safari until the renderer is installed.");
            return;
        }
        if (!_filamentRequested && modernHdAsset)
            Android.Util.Log.Warn("HushHuntAR", "Filament unavailable: " + HushFilamentBridge.LastError);
        if (!modernHdAsset)
            Android.Util.Log.Info("HushHuntAR", "Legacy renderer selected for " + filename + "; retaining normal materials and real 3D camera perspective.");

        // Native ARCore now renders a dimensional animal mesh in OpenGL, directly
        // at the world anchor. Never add a 2D ImageView sprite to this activity.

        var top = new LinearLayout(this) { Orientation = Orientation.Vertical };
        top.SetPadding(Dp(16), Dp(44), Dp(72), Dp(12));
        top.SetBackgroundColor(AndroidColor.Argb(160, 14, 18, 35));
        var title = new TextView(this) { Text = "3D Safari ✨", TextSize = 19 };
        title.SetTextColor(AndroidColor.White);
        top.AddView(title);
        _status = new TextView(this) { Text = "Scan a floor or table ✨", TextSize = 15 };
        _status.SetTextColor(AndroidColor.Rgb(168, 247, 228));
        top.AddView(_status);
        // Keep the interface readable for children: technical ARCore details belong in Help, not on the camera.
        _root.AddView(top, new LayoutParams(-1, -2, GravityFlags.Top));
        var close = new AndroidButton(this) { Text = "✕", TextSize = 20 };
        close.SetTextColor(AndroidColor.White);
        var closeBg = new GradientDrawable();
        closeBg.SetColor(AndroidColor.Rgb(203, 45, 64));
        closeBg.SetCornerRadius(Dp(28));
        close.Background = closeBg;
        close.ContentDescription = "Close 3D Safari";
        close.Click += (_, _) => FinishWith("cancelled", "3D Safari closed.");
        var closeParams = new LayoutParams(Dp(48), Dp(48), GravityFlags.Top | GravityFlags.Right);
        closeParams.TopMargin = Dp(42);
        closeParams.RightMargin = Dp(12);
        _root.AddView(close, closeParams);


        // Small animal zoom controls float beside the scene, clear of both camera and action buttons.
        // They change the 3D animal's display scale, not the rear-camera field of view.
        var sizeTray = new LinearLayout(this) { Orientation = Orientation.Vertical };
        sizeTray.SetGravity(GravityFlags.Center);
        sizeTray.SetPadding(Dp(5), Dp(7), Dp(5), Dp(7));
        var sizeBackground = new GradientDrawable();
        sizeBackground.SetColor(AndroidColor.Argb(218, 12, 23, 43));
        sizeBackground.SetCornerRadius(Dp(23));
        sizeTray.Background = sizeBackground;
        var bigger = new AndroidButton(this) { Text = "+", TextSize = 23, ContentDescription = "Make 3D animal bigger" };
        var smaller = new AndroidButton(this) { Text = "−", TextSize = 23, ContentDescription = "Make 3D animal smaller" };
        StyleCaptureToken(bigger, AndroidColor.Rgb(37, 79, 89));
        StyleCaptureToken(smaller, AndroidColor.Rgb(37, 79, 89));
        _sizeLabel = new TextView(this) { Text = "1×", TextSize = 13, Gravity = GravityFlags.Center };
        _sizeLabel.SetTextColor(AndroidColor.White);
        sizeTray.AddView(bigger, new LinearLayout.LayoutParams(Dp(46), Dp(46)));
        sizeTray.AddView(_sizeLabel, new LinearLayout.LayoutParams(Dp(46), Dp(31)));
        sizeTray.AddView(smaller, new LinearLayout.LayoutParams(Dp(46), Dp(46)));
        bigger.Click += (_, _) => AdjustAnimalSize(1.25f);
        smaller.Click += (_, _) => AdjustAnimalSize(0.8f);
        var sizeParams = new LayoutParams(Dp(58), -2, GravityFlags.Right | GravityFlags.CenterVertical);
        sizeParams.RightMargin = Dp(12);
        _root.AddView(sizeTray, sizeParams);

        // A tiny, non-interactive acknowledgment replaces extra game controls.
        _petFeedback = new TextView(this)
        {
            Text = "💚 Nice pet!", TextSize = 19, Gravity = GravityFlags.Center,
            Visibility = ViewStates.Invisible, Alpha = 0f
        };
        _petFeedback.SetTextColor(AndroidColor.White);
        _petFeedback.SetPadding(Dp(14), Dp(8), Dp(14), Dp(8));
        var petBackground = new GradientDrawable();
        petBackground.SetColor(AndroidColor.Argb(219, 14, 90, 76));
        petBackground.SetCornerRadius(Dp(22));
        _petFeedback.Background = petBackground;
        var petParams = new LayoutParams(-2, -2, GravityFlags.CenterHorizontal | GravityFlags.Bottom);
        petParams.BottomMargin = Dp(152);
        _root.AddView(_petFeedback, petParams);

        var bottom = new LinearLayout(this) { Orientation = Orientation.Horizontal };
        bottom.SetGravity(GravityFlags.Center);
        bottom.SetPadding(Dp(14), Dp(10), Dp(14), Dp(10));
        bottom.SetBackgroundColor(AndroidColor.Argb(130, 12, 17, 36));
        var back = new AndroidButton(this) { Text = "2D", ContentDescription = "Switch to 2D Safari" };
        back.Click += (_, _) => FinishWith("2d", "2D Safari selected.");
        _place = new AndroidButton(this) { Text = "Place", Enabled = false, ContentDescription = "Place animal on tracked floor or table" };
        _place.Click += (_, _) => PlaceAtCenter();
        _collect = new AndroidButton(this) { Text = "📷 Photo", Enabled = false, ContentDescription = "Photograph this 3D animal" };
        _collect.Click += (_, _) => Capture();
        StyleCaptureToken(back, AndroidColor.Rgb(40, 54, 75));
        StyleCaptureToken(_place, AndroidColor.Rgb(21, 106, 103));
        StyleCaptureToken(_collect, AndroidColor.Rgb(27, 129, 79));
        var backParams = new LinearLayout.LayoutParams(0, Dp(55), 0.85f);
        var placeParams = new LinearLayout.LayoutParams(0, Dp(55), 1f);
        var photoParams = new LinearLayout.LayoutParams(0, Dp(55), 1.15f);
        backParams.RightMargin = Dp(10);
        placeParams.RightMargin = Dp(10);
        bottom.AddView(back, backParams);
        bottom.AddView(_place, placeParams);
        bottom.AddView(_collect, photoParams);
        var trayParams = new LayoutParams(-1, -2, GravityFlags.Bottom);
        trayParams.BottomMargin = Dp(62);
        _root.AddView(bottom, trayParams);
        // Yaw-only controls: tilt buttons were confused with walking controls.
        var rotationTray = new LinearLayout(this) { Orientation = Orientation.Horizontal };
        rotationTray.SetGravity(GravityFlags.Center);
        foreach (var (symbol, yaw, pitch) in new (string text, float yaw, float pitch)[]
        {
            ("↶", 25f, 0f), ("↷", -25f, 0f)
        })
        {
            var btn = new AndroidButton(this) { Text = symbol, TextSize = 19,
                ContentDescription = yaw > 0 ? "Rotate animal left" : "Rotate animal right" };
            btn.SetTextColor(AndroidColor.White);
            btn.SetBackgroundColor(AndroidColor.Argb(220, 30, 60, 69));
            btn.Click += (_, _) => RotateAnimal(yaw, pitch);
            var bp = new LinearLayout.LayoutParams(Dp(70), Dp(44));
            bp.LeftMargin = Dp(4); bp.RightMargin = Dp(4);
            rotationTray.AddView(btn, bp);
        }
        var rotationParams = new LayoutParams(-1, -2, GravityFlags.Bottom);
        rotationParams.BottomMargin = Dp(134);
        _root.AddView(rotationTray, rotationParams);
        SetContentView(_root);
        _surface.Touch += (_, e) =>
        {
            var motion = e.Event;
            if (motion is null || _surface is null || _renderer is null) { e.Handled = true; return; }
            var action = motion.ActionMasked;
            // Two-finger animal size control always wins over petting/placing.
            if (motion.PointerCount >= 2 || action == MotionEventActions.PointerDown)
            {
                _petGestureStarted = false;
                _pinching = true;
                if (motion.PointerCount >= 2)
                {
                    float dx = motion.GetX(0) - motion.GetX(1);
                    float dy = motion.GetY(0) - motion.GetY(1);
                    float distance = MathF.Sqrt(dx * dx + dy * dy);
                    if (_pinchDistance > 8f && action == MotionEventActions.Move)
                    {
                        var ratio = distance / _pinchDistance;
                        if (ratio <= .92f || ratio >= 1.09f)
                            AdjustAnimalSize(Math.Clamp(ratio, .85f, 1.18f));
                    }
                    _pinchDistance = distance;
                }
            }
            else if (action == MotionEventActions.Down)
            {
                _petStartX = motion.GetX(); _petStartY = motion.GetY();
                _petTravelX = _petStartX; _petTravelY = _petStartY;
                _petGestureStarted = IsInsideAnimal(_petStartX, _petStartY);
                _petGestureTriggered = false;
            }
            else if (action == MotionEventActions.Move && !_pinching && _petGestureStarted)
            {
                float x = motion.GetX(), y = motion.GetY();
                // A deliberate stroke of ~30dp; don't trigger on accidental jitter.
                float dx = x - _petTravelX, dy = y - _petTravelY;
                _petTravelX = x; _petTravelY = y;
                if (MathF.Abs(dx) + MathF.Abs(dy) >= Dp(3))
                {
                    float fromStartX = x - _petStartX, fromStartY = y - _petStartY;
                    if (!_petGestureTriggered && IsInsideAnimal(x, y) &&
                        MathF.Sqrt(fromStartX * fromStartX + fromStartY * fromStartY) >= Dp(30))
                    {
                        _petGestureTriggered = true;
                        PetAnimal(isStroke: true);
                    }
                }
            }
            else if (action == MotionEventActions.Up)
            {
                if (!_pinching)
                {
                    float x = motion.GetX(), y = motion.GetY();
                    if (_petGestureStarted)
                    {
                        // If the finger stayed over the creature, allow a gentle tap.
                        if (!_petGestureTriggered && IsInsideAnimal(x, y)) PetAnimal(isStroke: false);
                    }
                    else if (y > Dp(132) && y < _surface.Height - Dp(150))
                        _renderer.QueuePlacement(x, y);
                }
                _petGestureStarted = false;
                _petGestureTriggered = false;
                _pinchDistance = 0f;
                _pinching = false;
            }
            else if (action == MotionEventActions.Cancel)
            {
                _pinchDistance = 0f; _pinching = false;
                _petGestureStarted = false; _petGestureTriggered = false;
            }
            e.Handled = true;
        };
    }

    private bool IsInsideAnimal(float x, float y)
    {
        if (!_modelFrameConfirmed || _anchor is null) return false;
        lock (_frameLock)
        {
            if (!_petBoundsValid) return false;
            // A little padding makes small snails and ladybirds easier to pet.
            float pad = Dp(14);
            return x >= _petLeft - pad && x <= _petRight + pad &&
                   y >= _petTop - pad && y <= _petBottom + pad;
        }
    }

    internal void UpdatePetBounds(bool valid, float left, float top, float right, float bottom)
    {
        lock (_frameLock)
        {
            _petBoundsValid = valid;
            if (!valid) return;
            _petLeft = left; _petTop = top; _petRight = right; _petBottom = bottom;
        }
    }

    private (string bubble, string status) BuildPetResponse(bool isStroke)
    {
        string species = (_species ?? string.Empty).Trim().ToLowerInvariant();
        string name = string.IsNullOrWhiteSpace(_animalName) ? "This animal" : _animalName;
        string[] lines = species switch
        {
            "cat" => isStroke
                ? new[] { "🐱 Meow! That's a nice stroke.", "🐱 Prrr… chin scratches approved.", "🐱 Soft paws and a happy purr." }
                : new[] { "🐱 Meow! Hello there.", "🐱 Prrr… curious cat activated.", "🐱 Meow! Gentle taps are welcome." },
            "dog" => isStroke
                ? new[] { "🐶 Woof! Tail wag unlocked.", "🐶 Happy dog mode: ON.", "🐶 Woof! That feels good." }
                : new[] { "🐶 Woof! New friend spotted.", "🐶 Bark bark! Hello, human.", "🐶 Woof! Ready to play." },
            "bird" => isStroke
                ? new[] { "🐦 Chirp chirp! Easy does it.", "🐦 Fluffing feathers happily.", "🐦 Tweet! That tickles." }
                : new[] { "🐦 Chirp! Hello from the perch.", "🐦 Tweet tweet!", "🐦 A tiny greeting song." },
            "squirrel" => isStroke
                ? new[] { "🐿️ Chitter! That's friendly.", "🐿️ Tiny paws approved.", "🐿️ Chitter-chitter!" }
                : new[] { "🐿️ Chitter! Fast little friend here.", "🐿️ Sniff sniff… hello.", "🐿️ Chitter! Want a nut?" },
            "rabbit" => isStroke
                ? new[] { "🐇 Sniff! Soft strokes only.", "🐇 Hop-hop… that feels gentle.", "🐇 Wiggle-nose approved." }
                : new[] { "🐇 Hop! Hello, friend.", "🐇 Sniff sniff!", "🐇 Ears up — visitor detected." },
            "frog" => isStroke
                ? new[] { "🐸 Ribbit! Gentle touch detected.", "🐸 Croak! That's friendly.", "🐸 Ribbit-ribbit!" }
                : new[] { "🐸 Ribbit! Hello from the pond.", "🐸 Croak! Nice to meet you.", "🐸 Ribbit!" },
            "hedgehog" => isStroke
                ? new[] { "🦔 Snuffle! Careful around the spikes.", "🦔 Tiny sniff of approval.", "🦔 Snuffle snuffle!" }
                : new[] { "🦔 Snuffle! Hello there.", "🦔 Curled up, but friendly.", "🦔 Sniff… a new visitor." },
            "bee" => isStroke
                ? new[] { "🐝 Bzzz! Gentle breeze detected.", "🐝 Buzz buzz!", "🐝 A tiny happy buzz." }
                : new[] { "🐝 Bzzz! Pollinator on duty.", "🐝 Buzz! Friendly fly-by.", "🐝 Bzzz… hello!" },
            "butterfly" => isStroke
                ? new[] { "🦋 Flutter flutter!", "🦋 Wings shimmering happily.", "🦋 Light as air." }
                : new[] { "🦋 A graceful hello.", "🦋 Flutter! Nice to see you.", "🦋 Wings ready." },
            "ant" => isStroke
                ? new[] { "🐜 Marching happily.", "🐜 Tiny footsteps of approval.", "🐜 Antenna salute!" }
                : new[] { "🐜 Scout ant reporting in.", "🐜 Hello from the colony.", "🐜 Tiny but mighty." },
            "beetle" => isStroke
                ? new[] { "🪲 Click! That's enough polish.", "🪲 Shell shining nicely.", "🪲 Tap-tap… beetle approved." }
                : new[] { "🪲 Beetle says hello.", "🪲 A sturdy little greeting.", "🪲 Tiny armour, big personality." },
            _ when name.Contains("Fox", StringComparison.OrdinalIgnoreCase) => isStroke
                ? new[] { "🦊 Soft brush of the fur.", "🦊 Clever fox approves.", "🦊 A sly little smile." }
                : new[] { "🦊 Fox says hello.", "🦊 Curious eyes watching you.", "🦊 Sly but friendly." },
            _ when name.Contains("Deer", StringComparison.OrdinalIgnoreCase) => isStroke
                ? new[] { "🦌 Gentle nose nudge.", "🦌 Calm forest friend.", "🦌 Soft hoof shuffle." }
                : new[] { "🦌 A cautious hello.", "🦌 Ears twitch — visitor nearby.", "🦌 Graceful and alert." },
            _ when name.Contains("Mouse", StringComparison.OrdinalIgnoreCase) => isStroke
                ? new[] { "🐭 Squeak! Tiny paws approved.", "🐭 Little whiskers are happy.", "🐭 Squeak squeak!" }
                : new[] { "🐭 Squeak! Hello there.", "🐭 Tiny explorer on the move.", "🐭 A little nose wiggle hello." },
            _ => isStroke
                ? new[] { "💚 That tickles!", "💚 Friendly pat received.", "💚 A happy little reaction." }
                : new[] { "💚 Hello, friend!", "💚 Nice to meet you.", "💚 A curious greeting." }
        };
        var bubble = lines[_petRandom.Next(lines.Length)];
        var status = isStroke
            ? $"{name} is enjoying the attention ✨"
            : $"{name} is reacting to you ✨";
        return (bubble, status);
    }

    private void PetAnimal(bool isStroke)
    {
        if (!_modelFrameConfirmed || _anchor is null) return;
        long now = System.Environment.TickCount64;
        if (now - System.Threading.Interlocked.Read(ref _lastPetTick) < 480) return;
        System.Threading.Interlocked.Exchange(ref _lastPetTick, now);
        System.Threading.Interlocked.Exchange(ref _reactionStartedAt, now);
        var response = BuildPetResponse(isStroke);
        _surface?.PerformHapticFeedback(FeedbackConstants.VirtualKey);
        if (_petFeedback is not null)
        {
            _petFeedback.Animate().Cancel();
            _petFeedback.Text = response.bubble;
            _petFeedback.Visibility = ViewStates.Visible;
            _petFeedback.Alpha = 1f;
            _petFeedback.Animate().Alpha(0f).SetStartDelay(520).SetDuration(620).Start();
        }
        SetStatus(response.status);
    }

    private bool IsPrimaryAssetLegacyCompatible(string file)
    {
        try
        {
            using var stream = Assets!.Open("ar_models/" + file);
            using var bytes = new MemoryStream();
            stream.CopyTo(bytes);
            return bytes.Length <= 24 * 1024 * 1024 &&
                HushGlbAnimal3D.IsLegacyCompatible(bytes.ToArray());
        }
        catch (Exception e)
        {
            Android.Util.Log.Warn("HushHuntAR", "Legacy compatibility check: " + e.Message);
            return false;
        }
    }

    private void RotateAnimal(float yawDelta, float pitchDelta)
    {
        if (_anchor is null) { SetStatus("Place your animal first ✨"); return; }
        _yawDegrees = (_yawDegrees + yawDelta) % 360f;
        _pitchDegrees = 0f;
        HushFilamentBridge.SetOrientation(_yawDegrees, 0f);
        SetStatus("Wildlife rotated ✨");
    }

    private void AdjustAnimalSize(float factor)
    {
        _animalScale = Math.Clamp(_animalScale * factor, .5f, 3f);
        if (_sizeLabel is not null)
            _sizeLabel.Text = _animalScale.ToString("0.#", System.Globalization.CultureInfo.InvariantCulture) + "×";
    }

    protected override void OnResume()
    {
        base.OnResume();
        if (_didComplete || _surface is null) return;
        if (CheckSelfPermission(Android.Manifest.Permission.Camera) != Permission.Granted)
        {
            RequestPermissions(new[] { Android.Manifest.Permission.Camera }, 7102);
            return;
        }
        StartArSession();
    }

    private void StartArSession()
    {
        try
        {
            if (_session is null)
            {
                // For AR Optional, Google Play Services for AR must be installed explicitly.
                var install = ArCoreApk.Instance.RequestInstall(this, !_installRequested);
                if (install.ToString()!.Contains("Requested", StringComparison.OrdinalIgnoreCase) ||
                    install.ToString()!.Contains("INSTALL_REQUESTED", StringComparison.OrdinalIgnoreCase))
                { _installRequested = true; SetStatus("Installing Google Play Services for AR…"); return; }
                _session = new Session(this);
                // ARCore Config(Session) enables plane detection by default.
                // Do NOT use an object initializer for PlaneFindingMode: the
                // XPACE.Google.ARCore binding exposes PlaneFindingMode as a nested
                // type, which causes CS0572 and CS1913 in .NET MAUI builds.
                var config = new Google.AR.Core.Config(_session);
                if (_filamentRequested) HushFilamentBridge.ConfigureHdr(config);
                _session.Configure(config);
            }
            _session.Resume();
            _resumed = true;
            _surface.OnResume();
            SetStatus("Move slowly to find a surface ✨");
        }
        catch (Exception ex)
        {
            JLog.Warn("HushHuntAR", "ARCore could not start: " + ex);
            FinishWith("unavailable", "ARCore cannot start on this phone. Try 2D Safari. " + ex.Message);
        }
    }

    public override void OnRequestPermissionsResult(int requestCode, string[] permissions, Permission[] grantResults)
    {
        base.OnRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == 7102)
        {
            if (grantResults.Length > 0 && grantResults[0] == Permission.Granted) StartArSession();
            else FinishWith("unavailable", "Camera permission is required for ARCore.");
        }
    }

    protected override void OnPause()
    {
        if (_resumed)
        {
            UpdatePetBounds(false, 0, 0, 0, 0);
            _surface?.OnPause();
            try { _session?.Pause(); } catch (Exception e) { JLog.Warn("HushHuntAR", e.Message); }
            _resumed = false;
        }
        base.OnPause();
    }

    protected override void OnDestroy()
    {
        if (_filamentRequested) HushFilamentBridge.Dispose();
        try { _walkingDestination?.Detach(); _walkingDestination?.Dispose(); } catch { }
        try { _anchor?.Detach(); _anchor?.Dispose(); } catch { }
        try { _session?.Close(); _session?.Dispose(); } catch { }
        base.OnDestroy();
    }

    public override void OnBackPressed() { FinishWith("cancelled", "3D Safari closed."); }

    private int Dp(int px) => (int)(px * Resources!.DisplayMetrics!.Density + .5f);
    private void StyleCaptureToken(AndroidButton? button, AndroidColor color)
    {
        if (button is null) return;
        button.SetTextColor(AndroidColor.White);
        button.TextSize = 13;
        var bg = new GradientDrawable();
        bg.SetColor(color);
        bg.SetCornerRadius(Dp(18));
        button.Background = bg;
        button.SetPadding(Dp(5), Dp(4), Dp(5), Dp(4));
    }
    private void SetStatus(string text) => RunOnUiThread(() => { if (_status is not null) _status.Text = text; });

    private void FinishWith(string status, string? message, string? photo = null)
    {
        if (_didComplete) return;
        _didComplete = true;
        _pending = new ArOutcome { Status = status, Model = _model, Photo = photo, Message = message };
        Finish();
    }

    private void PlaceAtCenter()
    {
        if (_renderer is null || _surface is null) return;
        // ARCore is tracked-plane-only. Never simulate an anchored creature with a 2D screen overlay.
        _renderer.QueuePlacement(_surface.Width / 2f, _surface.Height * .62f, true);
    }

    internal void PreviewPlace(float x, float y)
    {
        // Native ARCore does not substitute 2D previews: the separate 2D Safari mode
        // is the explicit, accessible fallback when no real plane is detected.
        RunOnUiThread(() =>
            SetStatus("Try a floor or table ✨"));
    }

    internal void UpdatePlacementReady(bool ready)
    {
        if (_anchor is not null) ready = true;
        if (ready == _placementReady && _place?.Enabled == true) return;
        _placementReady = ready;
        RunOnUiThread(() =>
        {
            if (_place is not null && _anchor is null) _place.Enabled = ready;
            if (_place is not null && _anchor is not null) _place.Enabled = true;
            if (_anchor is null)
            {
                SetStatus(ready
                    ? "Ready! Tap Place ✨"
                    : "Move slowly to find a surface ✨");
            }
        });
    }

    internal void OnPlaced(Anchor anchor)
    {
        RunOnUiThread(() =>
        {
            if (_anchor is not null)
            {
                // A second surface tap creates a WAYPOINT, not a teleport.
                // Both endpoints remain ARCore anchors during the journey.
                if (_walkingDestination is not null)
                {
                    try { anchor.Detach(); anchor.Dispose(); } catch { }
                    SetStatus($"{_animalName} is already walking ✨");
                    return;
                }
                _walkingDestination = anchor;
                _walkStartMs = System.Environment.TickCount64;
                var start = new float[3]; var end = new float[3];
                _anchor.Pose.GetTranslation(start, 0);
                anchor.Pose.GetTranslation(end, 0);
                float dx = end[0] - start[0], dz = end[2] - start[2];
                float distance = MathF.Sqrt(dx * dx + dz * dz);
                _walkDurationMs = (int)Math.Clamp(distance / .35f * 1000f, 650f, 7000f);
                if (distance > .03f)
                {
                    _yawDegrees = MathF.Atan2(dx, dz) * 180f / MathF.PI;
                    HushFilamentBridge.SetOrientation(_yawDegrees, _pitchDegrees);
                }
                SetStatus($"{_animalName} is heading there ✨");
                return;
            }
            _anchor = anchor;
            _walkingDestination = null;
            _modelFrameConfirmed = false;
            UpdatePetBounds(false, 0, 0, 0, 0);
            if (_collect is not null) _collect.Enabled = false;
            if (_place is not null) _place.Text = "Walk";
            SetStatus($"Here comes {_animalName}! ✨");
        });
    }

    // Sample BOTH tracking anchors every frame. ARCore may refine their poses,
    // so we do not store stale absolute world coordinates between frames.
    internal float[] AnimalPosition(Anchor current)
    {
        float[] start = new float[3];
        current.Pose.GetTranslation(start, 0);
        var destination = _walkingDestination;
        if (destination is null || destination.TrackingState != TrackingState.Tracking) return start;
        float[] end = new float[3];
        destination.Pose.GetTranslation(end, 0);
        float t = Math.Clamp((System.Environment.TickCount64 - _walkStartMs) /
            (float)Math.Max(1, _walkDurationMs), 0f, 1f);
        var eased = t * t * (3f - 2f * t);
        var pos = new float[3];
        for (int i = 0; i < 3; i++) pos[i] = start[i] + (end[i] - start[i]) * eased;
        if (t >= 1f)
        {
            RunOnUiThread(() =>
            {
                if (!ReferenceEquals(_walkingDestination, destination)) return;
                _anchor = destination;
                _walkingDestination = null;
                try { current.Detach(); current.Dispose(); } catch { }
                SetStatus(_modelFrameConfirmed
                    ? $"{_animalName} arrived ✨"
                    : $"Reached the spot; waiting for the 3D model ✨");
            });
        }
        return pos;
    }

    // ARCore can create a perfectly valid anchor even when a shader fails.
    // Only make Capture available after the textured model issues a GL draw
    // without errors; otherwise show a useful error instead of a blank photo.
    internal void OnModelDrawn(int glError)
    {
        if (_modelFrameConfirmed) return;
        if (glError != 0)
        {
            SetStatus($"3D render error ({glError}). Please reopen AR Safari; no model photo was saved.");
            return;
        }
        _modelFrameConfirmed = true;
        RunOnUiThread(() =>
        {
            if (_collect is not null) _collect.Enabled = true;
            SetStatus(_filamentRequested && HushFilamentBridge.IsReady
                ? $"{_animalName} HD model ready ✨ Touch to pet 💚"
                : _filamentRequested
                    ? $"{_animalName} is here. Checking HD graphics… 💚"
                    : $"{_animalName} is here (standard graphics). Touch to pet 💚");
        });
    }

    // Use PixelCopy on the GLSurfaceView's actual Surface.  Unlike glReadPixels,
    // PixelCopy does not allocate several full-resolution CPU frame copies and it
    // reads the presented camera image reliably on devices such as the OnePlus 11.
    // The native 3D geometry is already rendered into the GL frame; no cutout
    // overlay is composited onto the captured photo.
    private void Capture()
    {
        if (_capturePending || _surface is null || _anchor is null) return;
        if (_surface.Width <= 0 || _surface.Height <= 0)
        {
            SetStatus("Camera not ready for a photo yet. Try again.");
            return;
        }
        _capturePending = true;
        if (_collect is not null) _collect.Enabled = false;
        SetStatus("Taking your photo… 📷");
        Bitmap? snapshot = null;
        try
        {
            float ratio = Math.Min(1f, 1080f / Math.Max(_surface.Width, _surface.Height));
            int width = Math.Max(1, (int)(_surface.Width * ratio));
            int height = Math.Max(1, (int)(_surface.Height * ratio));
            snapshot = Bitmap.CreateBitmap(width, height, Bitmap.Config.Argb8888!);
            var output = snapshot;
            _copyListener = new PixelCopyListener(result =>
            {
                try
                {
                    if (result != 0)
                    {
                        JLog.Warn("HushHuntAR", "PixelCopy result " + result);
                        SetStatus("Camera frame copy failed (" + result + "). Try again in better light.");
                        return;
                    }
                    // PixelCopy includes the GPU-rendered 3D animal in the same
                    // ARCore frame. Do not composite an old 2D illustration on top.
                    using var jpeg = new MemoryStream();
                    bool compressed = output.Compress(Bitmap.CompressFormat.Jpeg, 82, jpeg);
                    if (!compressed || jpeg.Length == 0)
                    {
                        SetStatus("Unable to encode AR photo. Try again.");
                        return;
                    }
                    FinishWith("captured", "ARCore tracked-surface encounter.",
                        "data:image/jpeg;base64," + Convert.ToBase64String(jpeg.ToArray()));
                }
                catch (Exception error)
                {
                    JLog.Warn("HushHuntAR", "PixelCopy photo failed: " + error);
                    SetStatus("Could not save the AR image: " + error.Message);
                }
                finally
                {
                    output.Dispose();
                    _copyListener = null;
                    _capturePending = false;
                    if (!_didComplete && _collect is not null) _collect.Enabled = true;
                }
            });
            // SurfaceView copy reads the latest presented camera buffer asynchronously.
            if (_filamentRequested && HushFilamentBridge.IsReady)
                PixelCopy.Request(Window!, output, _copyListener,
                    new Android.OS.Handler(Android.OS.Looper.MainLooper!));
            else
                PixelCopy.Request(_surface, output, _copyListener,
                    new Android.OS.Handler(Android.OS.Looper.MainLooper!));
        }
        catch (Exception error)
        {
            snapshot?.Dispose();
            _copyListener = null;
            _capturePending = false;
            if (_collect is not null) _collect.Enabled = true;
            JLog.Warn("HushHuntAR", "PixelCopy request failed: " + error);
            SetStatus("AR photo unavailable: " + error.Message);
        }
    }

    private sealed class PixelCopyListener : Java.Lang.Object, PixelCopy.IOnPixelCopyFinishedListener
    {
        private readonly Action<int> _finished;
        public PixelCopyListener(Action<int> finished) => _finished = finished;
        public void OnPixelCopyFinished(int result) => _finished(result);
    }

    private sealed class ArRenderer : Java.Lang.Object, GLSurfaceView.IRenderer
    {
        private readonly HushArCoreActivity _host;
        private int _texture, _program, _vertex, _uv, _sampler, _width, _height;
        private float? _tapX, _tapY;
        private bool _searchNearby;
        private bool _textureBound;
        private HushFloorShadow? _floorShadow;
        private bool _modelInitialised;
        private long _lastPlaneCheck;
        private readonly HushGlbAnimal3D? _animal;
        private readonly float[] _view = new float[16], _projection = new float[16];
        private FloatBuffer? _quad, _sourceUv, _displayUv;
        // No need to cache the ARCore frame between rendering passes.
        public ArRenderer(HushArCoreActivity host, HushGlbAnimal3D? animal) { _host = host; _animal = animal; }
        public void QueuePlacement(float x, float y, bool searchNearby = false)
        {
            lock (_host._frameLock) { _tapX = x; _tapY = y; _searchNearby = searchNearby; }
        }

        public void OnSurfaceCreated(Javax.Microedition.Khronos.Opengles.IGL10? gl, Javax.Microedition.Khronos.Egl.EGLConfig? config)
        {
            var ids = new int[1]; GLES.GlGenTextures(1, ids, 0); _texture = ids[0];
            GLES.GlBindTexture(0x8D65, _texture); // GL_TEXTURE_EXTERNAL_OES
            GLES.GlTexParameteri(0x8D65, GLES.GlTextureMinFilter, GLES.GlLinear);
            GLES.GlTexParameteri(0x8D65, GLES.GlTextureMagFilter, GLES.GlLinear);
            GLES.GlTexParameteri(0x8D65, GLES.GlTextureWrapS, GLES.GlClampToEdge);
            GLES.GlTexParameteri(0x8D65, GLES.GlTextureWrapT, GLES.GlClampToEdge);
            string vs = "attribute vec2 aPos;attribute vec2 aUv;varying vec2 vUv;void main(){vUv=aUv;gl_Position=vec4(aPos,0.,1.);}";
            string fs = "#extension GL_OES_EGL_image_external : require\nprecision mediump float;varying vec2 vUv;uniform samplerExternalOES camera;void main(){gl_FragColor=texture2D(camera,vUv);}";
            int vertex = Compile(GLES.GlVertexShader, vs), frag = Compile(GLES.GlFragmentShader, fs);
            _program = GLES.GlCreateProgram(); GLES.GlAttachShader(_program, vertex); GLES.GlAttachShader(_program, frag); GLES.GlLinkProgram(_program);
            var linked = new int[1];
            GLES.GlGetProgramiv(_program, GLES.GlLinkStatus, linked, 0);
            if (linked[0] == 0)
                JLog.Warn("HushHuntAR", "AR camera shader link: " + GLES.GlGetProgramInfoLog(_program));
            _vertex = GLES.GlGetAttribLocation(_program, "aPos"); _uv = GLES.GlGetAttribLocation(_program, "aUv"); _sampler = GLES.GlGetUniformLocation(_program, "camera");
            _quad = DirectFloatBuffer(new float[] { -1,-1, 1,-1, -1,1, 1,1 });
            // Use the standard ARCore camera UV layout and let TransformDisplayUvCoords
            // handle display rotation. This avoids manual mirroring / flipping.
            _sourceUv = DirectFloatBuffer(new float[] { 0,1, 1,1, 0,0, 1,0 });
            _displayUv = DirectFloatBuffer(new float[8]);
            _textureBound = false;
            _modelInitialised = false;
            _floorShadow = null;
            // An HD Filament model may not be supported by the fallback GLB parser.
            // Keep the ARCore ground-contact cue independent of model format.
            if (_animal is null)
            {
                try
                {
                    _floorShadow = new HushFloorShadow();
                    _floorShadow.Initialise();
                }
                catch (Exception shadowError)
                {
                    JLog.Warn("HushHuntAR", "HD animal ground shadow unavailable: " + shadowError);
                    _floorShadow = null;
                }
            }
            try
            {
                if (_animal is not null) _animal.Initialise();
                int error = GLES.GlGetError();
                if (error != GLES.GlNoError)
                    throw new InvalidOperationException("GLB initialisation error: " + error);
                _modelInitialised = _animal is not null;
                if (_modelInitialised) JLog.Info("HushHuntAR", "Legacy 3D fallback uploaded to GPU.");
            }
            catch (Exception issue)
            {
                JLog.Warn("HushHuntAR", "GLB initialisation failed: " + issue);
                _host.SetStatus("3D model graphics failed to load. Please try reopening AR Safari.");
            }
            GLES.GlClearColor(.07f,.09f,.16f,1f);
        }
        private static FloatBuffer DirectFloatBuffer(float[] data)
        {
            var buffer = ByteBuffer.AllocateDirect(data.Length * 4).Order(ByteOrder.NativeOrder()).AsFloatBuffer();
            buffer.Put(data);
            buffer.Position(0);
            return buffer;
        }
        private static int Compile(int type, string code)
        {
            int id = GLES.GlCreateShader(type);
            GLES.GlShaderSource(id, code); GLES.GlCompileShader(id); return id;
        }
        public void OnSurfaceChanged(Javax.Microedition.Khronos.Opengles.IGL10? gl, int width, int height)
        {
            _width = width; _height = height; GLES.GlViewport(0, 0, width, height);
        }
        public void OnDrawFrame(Javax.Microedition.Khronos.Opengles.IGL10? gl)
        {
            // glTF animals use real depth testing. Stale depth from earlier frames
            // obscured newly anchored models while the camera background stayed visible.
            GLES.GlDepthMask(true);
            GLES.GlClearDepthf(1f);
            GLES.GlClear(GLES.GlColorBufferBit | GLES.GlDepthBufferBit);
            GLES.GlDisable(GLES.GlDepthTest);
            var session = _host._session;
            if (session is null || !_host._resumed) return;
            try
            {
                if (!_textureBound) { session.SetCameraTextureNames(new[] { _texture }); _textureBound = true; }
                session.SetDisplayGeometry((int)_host.WindowManager!.DefaultDisplay!.Rotation, _width, _height);
                var frame = session.Update();
                if (_sourceUv is not null && _displayUv is not null)
                {
                    _sourceUv.Position(0); _displayUv.Position(0);
                    frame.TransformDisplayUvCoords(_sourceUv, _displayUv);
                    _displayUv.Position(0);
                }
                GLES.GlUseProgram(_program);
                GLES.GlActiveTexture(GLES.GlTexture0);
                GLES.GlBindTexture(0x8D65, _texture);
                GLES.GlUniform1i(_sampler, 0);
                _quad!.Position(0);
                GLES.GlVertexAttribPointer(_vertex, 2, GLES.GlFloat, false, 0, _quad);
                GLES.GlEnableVertexAttribArray(_vertex);
                GLES.GlVertexAttribPointer(_uv, 2, GLES.GlFloat, false, 0, _displayUv);
                GLES.GlEnableVertexAttribArray(_uv);
                GLES.GlDrawArrays(GLES.GlTriangleStrip, 0, 4);
                GLES.GlDisableVertexAttribArray(_vertex); GLES.GlDisableVertexAttribArray(_uv);

                var camera = frame.Camera;
                if (camera.TrackingState != TrackingState.Tracking)
                {
                    _host.UpdatePlacementReady(false);
                    _host.UpdatePetBounds(false, 0, 0, 0, 0);
                    return;
                }

                // Some phones track a floor at the LOWER third while the centre points at a wall.
                // Probe a sparse grid for genuinely tracked planes instead of locking
                // the Place item until the exact centre happens to intersect one.
                if (System.Environment.TickCount64-_lastPlaneCheck>380)
                {
                    _lastPlaneCheck=System.Environment.TickCount64;
                    _host.UpdatePlacementReady(HasNearbyTrackablePlane(frame, _width, _height));
                }
                float? x, y; bool nearby;
                lock (_host._frameLock)
                { x = _tapX; y = _tapY; nearby = _searchNearby; _tapX = _tapY = null; _searchNearby = false; }
                if (x.HasValue && y.HasValue)
                {
                    bool anchored = TryPlace(frame,x.Value,y.Value);
                    if (!anchored && nearby)
                    {
                        foreach (var (px,py) in PlaneSamplePoints(_width,_height))
                        {
                            if (TryPlace(frame,px,py)) { anchored = true; break; }
                        }
                    }
                    if (!anchored) _host.PreviewPlace(x.Value,y.Value); // guidance only: no screen-locked animal
                }
                if (_host._anchor is { } anchor && anchor.TrackingState == TrackingState.Tracking)
                {
                    camera.GetViewMatrix(_view, 0);
                    camera.GetProjectionMatrix(_projection, 0, .1f, 80f);
                    var pos = _host.AnimalPosition(anchor);
                    float scale = System.Threading.Volatile.Read(ref _host._animalScale);
                    if (_host._filamentRequested)
                        HushFilamentBridge.SubmitFrame(_view, _projection, pos, scale, frame);
                    bool filamentReady = _host._filamentRequested && HushFilamentBridge.IsReady;
                    if (!filamentReady && _host._filamentRequested &&
                        !_host._filamentWatchdogWarned &&
                        System.Environment.TickCount64 - _host._filamentLaunchMs > 9000)
                    {
                        _host._filamentWatchdogWarned = true;
                        _host.SetStatus(_modelInitialised
                            ? "Standard wildlife visible; HD renderer has not produced a frame ✨"
                            : "HD renderer hasn't produced an animal frame. Try another species ✨");
                        JLog.Warn("HushHuntAR", "No Filament model frame after 9 seconds. Inspect HushFilament STAGE in Logcat.");
                    }
                    if (filamentReady && !_host._filamentAnnounced)
                    {
                        _host._filamentAnnounced = true;
                        _host.SetStatus($"{_host._animalName} HD / Filament ready ✨ Touch to pet 💚");
                    }
                    for (int i = 0; i < 8 && GLES.GlGetError() != GLES.GlNoError; i++) { }
                    try
                    {
                        long reactionStart = System.Threading.Interlocked.Read(ref _host._reactionStartedAt);
                        float petProgress = reactionStart > 0
                            ? Math.Clamp((System.Environment.TickCount64 - reactionStart) / (float)HushArCoreActivity.ReactionDurationMs, 0f, 1f)
                            : 1f;
                        if (_modelInitialised && _animal is not null)
                        {
                            // When Filament is ready the old shape is suppressed. Keep
                            // its low-cost soft floor shadow for the real-world contact cue.
                            _animal.Draw(_view, _projection, pos, scale, petProgress,
                                System.Environment.TickCount64 % 600000L / 1000f,
                                shadowOnly: filamentReady,
                                yawDegrees: _host._yawDegrees, pitchDegrees: _host._pitchDegrees);
                            if (_animal.TryGetScreenBounds(_width, _height, out var bounds))
                                _host.UpdatePetBounds(true, bounds.left, bounds.top, bounds.right, bounds.bottom);
                            else _host.UpdatePetBounds(false, 0, 0, 0, 0);
                        }
                        else if (filamentReady)
                        {
                            // Add the contact decal ONLY when Filament has actually
                            // displayed non-transparent, lit animal pixels.
                            // It uses ARCore projection, so the shadow stays on the floor
                            // as the camera moves, without requiring legacy mesh parsing.
                            _floorShadow?.Draw(_view, _projection, pos, .17f * scale);
                            // For new PBR assets that the legacy parser cannot open,
                            // provide a conservative central touch target around anchor.
                            _host.UpdatePetBounds(true, _width * .22f, _height * .25f,
                                _width * .78f, _height * .78f);
                        }
                        if (filamentReady || _modelInitialised)
                            _host.OnModelDrawn(GLES.GlGetError());
                    }
                    catch (Exception modelError)
                    {
                        JLog.Warn("HushHuntAR", "Wildlife rendering failed: " + modelError);
                        _host.UpdatePetBounds(false, 0, 0, 0, 0);
                        _host.SetStatus("Could not render this 3D animal. Try reopening AR Safari.");
                    }
                }
            }
            catch (Exception error)
            {
                JLog.Warn("HushHuntAR", "Frame: " + error.Message);
                _host.SetStatus("Move slowly and try again ✨");
            }
        }
        private static IEnumerable<(float x, float y)> PlaneSamplePoints(int width,int height)
        {
            // Sample within camera preview, below the top status banner and above tools.
            foreach (float y in new[] { .56f, .68f, .78f, .44f })
                foreach (float x in new[] { .5f, .3f, .7f })
                    yield return (x*width, y*height);
        }
        private bool TryPlace(Google.AR.Core.Frame frame,float x,float y)
        {
            foreach (var hit in frame.HitTest(x, y))
            {
                if (hit.Trackable is Plane plane && plane.TrackingState==TrackingState.Tracking
                    && plane.IsPoseInPolygon(hit.HitPose))
                { _host.OnPlaced(hit.CreateAnchor()); return true; }
            }
            return false;
        }
        private static bool HasNearbyTrackablePlane(Google.AR.Core.Frame frame,int width,int height)
        {
            foreach (var (x,y) in PlaneSamplePoints(width,height))
            {
                foreach (var hit in frame.HitTest(x,y))
                {
                    if (hit.Trackable is Plane plane && plane.TrackingState==TrackingState.Tracking
                        && plane.IsPoseInPolygon(hit.HitPose))return true;
                }
            }
            return false;
        }


    }
}
#endif
