#if ANDROID
using Android.App;
using Android.Content.PM;
using Android.Graphics;
using Android.Graphics.Drawables;
using Android.Views.Animations;
using Android.Hardware.Camera2;
using Android.Hardware.Camera2.Params;
using Android.Media;
using Android.OS;
using Android.Views;
using Android.Widget;
using System.Text.Json.Serialization;
using AndroidColor = Android.Graphics.Color;
using AndroidButton = Android.Widget.Button;
using AndroidView = Android.Views.View;

namespace WhiskerHunt;

/// <summary>
/// The complete native Live Capture screen. All zoom ratios share ONE camera
/// preview/session; tapping 0.6x never launches an activity or modal.
/// The optical ultrawide button is enabled only when Camera2 advertises a
/// sub-1x rear zoom range. No downscaled 1x image is labelled 0.6x.
/// </summary>
[Activity(Label = "Hush Hunt · Live Capture", Theme = "@android:style/Theme.Material.NoActionBar",
    Exported = false, ScreenOrientation = ScreenOrientation.Portrait)]
public sealed class HushWideCameraActivity : Activity, ISurfaceHolderCallback, ImageReader.IOnImageAvailableListener
{
    public sealed class WideOutcome
    {
        [JsonPropertyName("status")] public string Status { get; init; } = "cancelled";
        [JsonPropertyName("request")] public string Request { get; init; } = "";
        [JsonPropertyName("photo")] public string? Photo { get; init; }
        [JsonPropertyName("message")] public string? Message { get; init; }
    }
    public static event Action<WideOutcome>? Completed;
    private static WideOutcome? _pending;
    public static void DispatchPending()
    {
        var result = System.Threading.Interlocked.Exchange(ref _pending, null);
        if (result is not null) Completed?.Invoke(result);
    }

    private string _token = "";
    private SurfaceView? _preview;
    private CameraDevice? _camera;
    private CameraCaptureSession? _session;
    private CaptureRequest.Builder? _previewRequest;
    private ImageReader? _reader;
    private TextView? _status;
    private AndroidButton? _shutter;
    private AndroidView? _flashOverlay;
    private readonly Dictionary<float, AndroidButton> _zoomButtons = new();
    private readonly Handler _handler = new(Looper.MainLooper!);
    private bool _done, _surfaceReady, _taking;
    private string? _cameraId;
    private float _ratio = 1f, _minZoom = 1f, _maxZoom = 1f;
    private int _jpegOrientation = 90;
    private int _photoWidth = 1920, _photoHeight = 1080;
    private float _previousPinch;
    private DeviceCallback? _deviceCallback;
    private SessionCallback? _sessionCallback;

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);
        _token = Intent?.GetStringExtra("request") ?? "";
        if (!System.Text.RegularExpressions.Regex.IsMatch(_token, @"^[0-9]{1,15}$"))
        { Complete("error", "Invalid Live Capture request."); return; }
        Window?.AddFlags(WindowManagerFlags.KeepScreenOn);
        var root = new FrameLayout(this);
        root.SetBackgroundColor(AndroidColor.Black);
        _preview = new SurfaceView(this);
        _preview.Holder?.AddCallback(this);
        root.AddView(_preview, new FrameLayout.LayoutParams(-1, -1));
        _preview.Touch += (_, ev) =>
        {
            var pointer = ev.Event;
            if (pointer != null && pointer.PointerCount >= 2)
            {
                float dx = pointer.GetX(0) - pointer.GetX(1);
                float dy = pointer.GetY(0) - pointer.GetY(1);
                float distance = (float)Math.Sqrt(dx * dx + dy * dy);
                if (_previousPinch > 0 && distance > 0 && pointer.ActionMasked == MotionEventActions.Move)
                    SelectZoom(_ratio * distance / _previousPinch, true);
                _previousPinch = distance;
            }
            else _previousPinch = 0;
            ev.Handled = true;
        };
        // A momentary white shutter flash is displayed over the camera feed only.
        // It never changes the captured JPEG or blocks camera interactions.
        _flashOverlay = new AndroidView(this);
        _flashOverlay.SetBackgroundColor(AndroidColor.White);
        _flashOverlay.Alpha = 0f;
        _flashOverlay.Clickable = false;
        root.AddView(_flashOverlay, new FrameLayout.LayoutParams(-1, -1));

        var header = new LinearLayout(this) { Orientation = Android.Widget.Orientation.Horizontal };
        header.SetGravity(GravityFlags.CenterVertical);
        header.SetPadding(Dp(14), Dp(34), Dp(14), Dp(7));
        // Compact transparent header: more of the wildlife remains visible.
        var close = new AndroidButton(this) { Text = "✕", TextSize = 19 };
        close.SetTextColor(AndroidColor.White);
        close.Background = Rounded(AndroidColor.Rgb(199, 48, 62), 40);
        close.ContentDescription = "Close Live Capture";
        close.Click += (_, _) => Complete("cancelled", null);
        var title = new TextView(this) { Text = "Live Capture", TextSize = 20 };
        title.SetTextColor(AndroidColor.White);
        title.Gravity = GravityFlags.Center;
        title.SetShadowLayer(3f, 0f, 2f, AndroidColor.Black);
        header.AddView(close, new LinearLayout.LayoutParams(Dp(46), Dp(46)));
        header.AddView(title, new LinearLayout.LayoutParams(0, Dp(46), 1));
        header.AddView(new TextView(this), new LinearLayout.LayoutParams(Dp(46), Dp(46)));
        root.AddView(header, new FrameLayout.LayoutParams(-1, -2, GravityFlags.Top));

        _status = new TextView(this) { Text = "Opening rear camera…", TextSize = 12 };
        _status.SetTextColor(AndroidColor.Rgb(175, 255, 229));
        _status.Gravity = GravityFlags.Center;
        _status.SetPadding(Dp(12), Dp(7), Dp(12), Dp(7));
        _status.Background = Rounded(AndroidColor.Argb(182, 13, 30, 48), 18);
        var statusParams = new FrameLayout.LayoutParams(-2, -2, GravityFlags.Top | GravityFlags.CenterHorizontal);
        statusParams.TopMargin = Dp(93);
        root.AddView(_status, statusParams);

        // Single, compact camera control floating above Android's navigation area.
        var controls = new LinearLayout(this) { Orientation = Android.Widget.Orientation.Vertical };
        controls.SetGravity(GravityFlags.Center);
        controls.SetPadding(0, 0, 0, Dp(2));
        var zoomStrip = new LinearLayout(this) { Orientation = Android.Widget.Orientation.Horizontal };
        zoomStrip.SetGravity(GravityFlags.Center);
        zoomStrip.SetPadding(0, Dp(3), 0, Dp(3));
        zoomStrip.Background = Rounded(AndroidColor.Argb(192, 12, 27, 45), 32);
        foreach (float z in new[] { .6f, 1f, 2f, 3f })
        {
            float requested = z;
            var zoom = new AndroidButton(this)
            {
                Text = $"{z:0.#}×", Enabled = false, TextSize = 13
            };
            zoom.SetMinimumHeight(0);
            zoom.SetMinimumWidth(0);
            zoom.SetTextColor(AndroidColor.White);
            zoom.SetPadding(0, 0, 0, 0);
            zoom.Background = Rounded(AndroidColor.Transparent, 23);
            zoom.Click += (_, _) => SelectZoom(requested);
            zoom.ContentDescription = $"Set zoom to {z:0.#} times";
            _zoomButtons[z] = zoom;
            var item = new LinearLayout.LayoutParams(Dp(53), Dp(42));
            item.SetMargins(Dp(1), 0, Dp(1), 0);
            zoomStrip.AddView(zoom, item);
        }
        // In a VERTICAL LinearLayout the default child width is MATCH_PARENT.
        // Explicit WRAP_CONTENT stops the grey zoom pill spanning the entire screen.
        var zoomParams = new LinearLayout.LayoutParams(-2, -2);
        zoomParams.Gravity = GravityFlags.CenterHorizontal;
        controls.AddView(zoomStrip, zoomParams);
        _shutter = new AndroidButton(this)
        {
            Text = "📷", Enabled = false, TextSize = 28
        };
        _shutter.SetMinimumHeight(0);
        _shutter.SetMinimumWidth(0);
        _shutter.SetTextColor(AndroidColor.Rgb(13, 35, 56));
        _shutter.Background = ShutterBackground();
        _shutter.Elevation = Dp(6);
        _shutter.ContentDescription = "Capture wildlife photo";
        _shutter.Click += (_, _) => { PlayShutterFlash(); TakePhoto(); };
        var shutterHolder = new LinearLayout(this) { Orientation = Android.Widget.Orientation.Horizontal };
        shutterHolder.SetGravity(GravityFlags.Center);
        var shutterParams = new LinearLayout.LayoutParams(Dp(70), Dp(70));
        shutterParams.TopMargin = Dp(9);
        shutterHolder.AddView(_shutter, shutterParams);
        controls.AddView(shutterHolder);
        var hint = new TextView(this) { Text = "Pinch to zoom  •  Tap the camera to capture", TextSize = 11 };
        hint.Gravity = GravityFlags.Center;
        hint.SetTextColor(AndroidColor.White);
        hint.SetShadowLayer(3f, 0f, 1f, AndroidColor.Black);
        hint.SetPadding(0, Dp(8), 0, Dp(2));
        controls.AddView(hint);
        var controlsParams = new FrameLayout.LayoutParams(-1, -2, GravityFlags.Bottom);
        controlsParams.BottomMargin = Dp(112); // Extra safety gap: circular shutter and hint stay clear of Android navigation.
        root.AddView(controls, controlsParams);
        SetContentView(root);
    }

    private GradientDrawable Rounded(AndroidColor color, float radiusDp)
    {
        var d = new GradientDrawable();
        d.SetColor(color);
        d.SetCornerRadius(Dp(radiusDp));
        return d;
    }
    private GradientDrawable ShutterBackground()
    {
        var d = Rounded(AndroidColor.White, 100);
        d.SetStroke(Dp(4), AndroidColor.Rgb(133, 242, 213));
        return d;
    }
    private void PlayShutterFlash()
    {
        if (_flashOverlay is null || _taking || _done) return;
        _flashOverlay.ClearAnimation();
        var flash = new AlphaAnimation(.86f, 0f) { Duration = 230, FillAfter = true };
        _flashOverlay.StartAnimation(flash);
    }
    private int Dp(float value) => (int)(Resources!.DisplayMetrics!.Density * value + .5f);
    protected override void OnResume()
    {
        base.OnResume();
        if (_done) return;
        if (CheckSelfPermission(Android.Manifest.Permission.Camera) != Permission.Granted)
        { RequestPermissions(new[] { Android.Manifest.Permission.Camera }, 7823); return; }
        StartCamera();
    }
    public override void OnRequestPermissionsResult(int code, string[] permissions, Permission[] results)
    {
        base.OnRequestPermissionsResult(code, permissions, results);
        if (code == 7823 && results.Length > 0 && results[0] == Permission.Granted) StartCamera();
        else if (code == 7823) Complete("unavailable", "Camera permission is required.");
    }
    private void StartCamera()
    {
        if (_done || _cameraId is not null) return;
        try
        {
            var manager = (CameraManager)GetSystemService(CameraService)!;
            var candidates = new List<(string id, float min, float max, int angle)>();
            foreach (var id in manager.GetCameraIdList())
            {
                var chars = manager.GetCameraCharacteristics(id);
                var facing = chars.Get(CameraCharacteristics.LensFacing) as Java.Lang.Integer;
                if (facing is null || facing.IntValue() != (int)LensFacing.Back) continue;
                float min = 1f, max = 1f;
                if (Build.VERSION.SdkInt >= BuildVersionCodes.R)
                {
                    var range = chars.Get(CameraCharacteristics.ControlZoomRatioRange) as Android.Util.Range;
                    if (range?.Lower is Java.Lang.Float low && range.Upper is Java.Lang.Float high)
                    { min = low.FloatValue(); max = high.FloatValue(); }
                }
                if (min <= 1f && max >= 1f)
                {
                    var angle = chars.Get(CameraCharacteristics.SensorOrientation) as Java.Lang.Integer;
                    candidates.Add((id, min, max, angle?.IntValue() ?? 90));
                }
            }
            if (candidates.Count == 0)
            { Complete("unavailable", "No rear camera is accessible to Hush Hunt."); return; }
            // Prefer the logical rear camera with optical ultrawide range, if exported.
            var selected = candidates.OrderBy(c => c.min).ThenByDescending(c => c.max).First();
            _cameraId = selected.id; _minZoom = Math.Max(.1f, selected.min);
            _maxZoom = Math.Max(1f, selected.max); _jpegOrientation = selected.angle;
            _ratio = 1f;
            var configuration = manager.GetCameraCharacteristics(selected.id)
                .Get(CameraCharacteristics.ScalerStreamConfigurationMap) as StreamConfigurationMap;
            var supported = configuration?.GetOutputSizes((int)ImageFormatType.Jpeg);
            var size = supported?.Where(s => s.Width > 0 && s.Height > 0 &&
                (long)s.Width * s.Height <= 16_000_000).OrderByDescending(s => (long)s.Width * s.Height).FirstOrDefault()
                ?? supported?.FirstOrDefault();
            if (size is null) { Complete("unavailable", "Rear camera has no JPEG output."); return; }
            _photoWidth = size.Width; _photoHeight = size.Height;
            _reader = ImageReader.NewInstance(_photoWidth, _photoHeight, ImageFormatType.Jpeg, 2);
            _reader.SetOnImageAvailableListener(this, _handler);
            foreach (var (zoom, button) in _zoomButtons)
                button.Enabled = zoom != .6f || _minZoom <= .601f;
            RunOnUiThread(() =>
            {
                _status!.Text = _minZoom <= .601f
                    ? "Rear camera ready · tap 0.6× / 1× / 2× / 3×"
                    : "Rear camera ready · ultrawide not exposed to third-party apps";
                HighlightZoom();
            });
            _deviceCallback = new DeviceCallback(this);
            manager.OpenCamera(selected.id, _deviceCallback, _handler);
        }
        catch (Exception ex) { Complete("unavailable", "Rear Camera2 preview failed: " + ex.Message); }
    }
    private void HighlightZoom()
    {
        foreach (var (ratio, button) in _zoomButtons)
        {
            bool selected = Math.Abs(_ratio - ratio) <= .08f;
            button.Alpha = button.Enabled ? 1f : .35f;
            button.SetTextColor(selected ? AndroidColor.Rgb(11, 32, 49) : AndroidColor.White);
            button.Background = Rounded(selected ? AndroidColor.Rgb(160, 250, 222)
                                                  : AndroidColor.Transparent, 24);
        }
    }
    private void SelectZoom(float requested, bool gesture = false)
    {
        if (_done || _taking || _camera is null || _session is null || _previewRequest is null) return;
        if (requested < 1f && _minZoom > .601f)
        { _status!.Text = "0.6× unavailable: the rear camera does not expose ultrawide."; return; }
        float target = Math.Min(_maxZoom, Math.Max(_minZoom, requested));
        if (Math.Abs(target - _ratio) <= .005f) return;
        try
        {
            _ratio = target;
            ApplyZoom(_previewRequest);
            _session.SetRepeatingRequest(_previewRequest.Build(), null, _handler);
            _status!.Text = $"Rear live camera · {_ratio:0.0}×";
            HighlightZoom();
        }
        catch (Exception ex) { _status!.Text = "Lens switch unavailable: " + ex.Message; }
    }
    private void OpenPreview()
    {
        if (_camera is null || !_surfaceReady || _preview?.Holder?.Surface is null || _reader is null || _done) return;
        try
        {
            var surface = _preview.Holder.Surface;
            _previewRequest = _camera.CreateCaptureRequest(CameraTemplate.Preview);
            _previewRequest.AddTarget(surface);
            ApplyZoom(_previewRequest);
            _sessionCallback = new SessionCallback(this);
            _camera.CreateCaptureSession(new List<Surface> { surface, _reader.Surface! }, _sessionCallback, _handler);
        }
        catch (Exception ex) { Complete("error", "Camera preview unavailable: " + ex.Message); }
    }
    private void ApplyZoom(CaptureRequest.Builder builder)
    {
        if (Build.VERSION.SdkInt >= BuildVersionCodes.R)
            builder.Set(CaptureRequest.ControlZoomRatio, new Java.Lang.Float(_ratio));
    }
    private void OnDeviceOpened(CameraDevice camera)
    { if (_done) { camera.Close(); return; } _camera = camera; OpenPreview(); }
    private void OnSessionReady(CameraCaptureSession session)
    {
        if (_done || _previewRequest is null) { session.Close(); return; }
        try
        {
            _session = session;
            session.SetRepeatingRequest(_previewRequest.Build(), null, _handler);
            RunOnUiThread(() => { if (_shutter is not null) _shutter.Enabled = true; });
        }
        catch (Exception ex) { Complete("error", "Live camera unavailable: " + ex.Message); }
    }
    private void TakePhoto()
    {
        if (_done || _taking || _camera is null || _session is null || _reader is null) return;
        _taking = true;
        _shutter!.Enabled = false;
        try
        {
            var request = _camera.CreateCaptureRequest(CameraTemplate.StillCapture);
            request.AddTarget(_reader.Surface!);
            ApplyZoom(request);
            // On a portrait-locked rear camera, request the sensor rotation.
            // Pixel orientation is checked AGAIN after decoding below because
            // BitmapFactory does not necessarily honour JPEG EXIF orientation.
            int displayDegrees = (int)WindowManager!.DefaultDisplay!.Rotation * 90;
            int rearRotation = (_jpegOrientation - displayDegrees + 360) % 360;
            request.Set(CaptureRequest.JpegOrientation, new Java.Lang.Integer(rearRotation));
            _session.Capture(request.Build(), null, _handler);
            _status!.Text = "Saving photo…";
        }
        catch (Exception ex) { Complete("error", "Photo capture failed: " + ex.Message); }
    }
    public void OnImageAvailable(ImageReader? reader)
    {
        if (_done || reader is null) return;
        byte[] jpeg;
        try
        {
            // Copy and release the Camera2 image promptly. Decoding / encoding
            // can take seconds on high-resolution phones and must NOT block UI.
            using var image = reader.AcquireLatestImage();
            if (image is null) return;
            var source = image.GetPlanes()[0].Buffer!;
            jpeg = new byte[source.Remaining()];
            source.Get(jpeg);
        }
        catch (Exception ex) { Complete("error", "Camera photo read failed: " + ex.Message); return; }
        _ = System.Threading.Tasks.Task.Run(() => ProcessPhotoOffUiThread(jpeg));
    }
    private void ProcessPhotoOffUiThread(byte[] bytes)
    {
        try
        {
            using var decoded = BitmapFactory.DecodeByteArray(bytes, 0, bytes.Length);
            if (decoded is null) throw new InvalidOperationException("Camera returned invalid JPEG data.");
            // Camera2 can supply landscape pixels with an EXIF rotation.
            // Normalize pixels for the WebView's canvas before handing off.
            Bitmap upright = decoded;
            Bitmap? rotated = null;
            if (decoded.Width > decoded.Height)
            {
                using var transform = new Android.Graphics.Matrix();
                transform.PostRotate(90f);
                rotated = Bitmap.CreateBitmap(decoded, 0, 0, decoded.Width, decoded.Height, transform, true);
                upright = rotated;
            }
            const int maxSide = 1800; // Collection converts to a 1200px still later.
            double shrink = Math.Min(1d, maxSide / (double)Math.Max(upright.Width, upright.Height));
            using var resized = shrink < 1d ? Bitmap.CreateScaledBitmap(upright,
                Math.Max(1, (int)(upright.Width * shrink)),
                Math.Max(1, (int)(upright.Height * shrink)), true) : null;
            using var destination = new MemoryStream();
            bool compressed = (resized ?? upright).Compress(Bitmap.CompressFormat.Jpeg, 87, destination);
            rotated?.Dispose();
            if (!compressed || destination.Length == 0)
                throw new InvalidOperationException("Camera JPEG encoding failed.");
            Complete("captured", null, "data:image/jpeg;base64," + Convert.ToBase64String(destination.ToArray()));
        }
        catch (Exception ex) { Complete("error", "Photo processing failed: " + ex.Message); }
    }
    public void SurfaceCreated(ISurfaceHolder holder) { _surfaceReady = true; OpenPreview(); }
    public void SurfaceDestroyed(ISurfaceHolder holder) { _surfaceReady = false; }
    public void SurfaceChanged(ISurfaceHolder holder, Format format, int width, int height) { }
    private sealed class DeviceCallback(HushWideCameraActivity activity) : CameraDevice.StateCallback
    {
        public override void OnOpened(CameraDevice camera) => activity.OnDeviceOpened(camera);
        public override void OnDisconnected(CameraDevice camera) => activity.Complete("error", "Camera disconnected.");
        public override void OnError(CameraDevice camera, CameraError error) => activity.Complete("error", $"Camera2 error: {error}");
    }
    private sealed class SessionCallback(HushWideCameraActivity activity) : CameraCaptureSession.StateCallback
    {
        public override void OnConfigured(CameraCaptureSession session) => activity.OnSessionReady(session);
        public override void OnConfigureFailed(CameraCaptureSession session) => activity.Complete("error", "Camera session configuration failed.");
    }
    private void Complete(string status, string? message, string? photo = null)
    {
        if (_done) return;
        _done = true;
        _pending = new WideOutcome { Status = status, Request = _token, Message = message, Photo = photo };
        // Camera2 is owned by the activity; close it and finish on the UI thread.
        RunOnUiThread(() => { ReleaseCamera(); Finish(); });
    }
    private void ReleaseCamera()
    {
        try { _session?.Close(); } catch { }
        try { _camera?.Close(); } catch { }
        try { _reader?.Close(); } catch { }
        _session?.Dispose(); _session = null;
        _camera?.Dispose(); _camera = null;
        _reader?.Dispose(); _reader = null;
        _cameraId = null;
    }
    public override void OnBackPressed() => Complete("cancelled", null);
    protected override void OnPause() { ReleaseCamera(); base.OnPause(); }
    protected override void OnDestroy() { ReleaseCamera(); base.OnDestroy(); }
}
#endif
