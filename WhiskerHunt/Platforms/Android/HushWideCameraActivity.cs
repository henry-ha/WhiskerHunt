using Android.App;
using Android.Content.PM;
using Android.Graphics;
using Android.Hardware.Camera2;
using Android.Hardware.Camera2.Params;
using Android.Media;
using Android.OS;
using Android.Views;
using Android.Widget;
using System.Text.Json.Serialization;
using AndroidColor = Android.Graphics.Color;
using AndroidButton = Android.Widget.Button;

namespace WhiskerHunt;

/// <summary>
/// Modern Camera2 rear-ultrawide trial. Unlike Camera1, checks Android 11+
/// CONTROL_ZOOM_RATIO_RANGE on the logical rear camera (which may expose a
/// sub-1x field of view without an independently enumerated rear camera).
/// Never presents digital downscaling as ultrawide. No external camera app.
/// </summary>
[Activity(Label = "Hush Hunt · Wide Capture", Theme = "@android:style/Theme.Material.NoActionBar",
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
    private readonly Handler _handler = new(Looper.MainLooper!);
    private bool _done;
    private bool _surfaceReady;
    private bool _taking;
    private string? _cameraId;
    private float _ratio = 0.6f;
    private int _jpegOrientation = 90;
    private int _photoWidth = 1920, _photoHeight = 1080;
    private DeviceCallback? _deviceCallback;
    private SessionCallback? _sessionCallback;

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);
        _token = Intent?.GetStringExtra("request") ?? "";
        if (!System.Text.RegularExpressions.Regex.IsMatch(_token, @"^[0-9]{1,15}$"))
        { Complete("error", "Invalid wide-camera request."); return; }

        Window?.AddFlags(WindowManagerFlags.KeepScreenOn);
        var layout = new FrameLayout(this);
        layout.SetBackgroundColor(AndroidColor.Black);
        _preview = new SurfaceView(this);
        _preview.Holder?.AddCallback(this);
        layout.AddView(_preview, new FrameLayout.LayoutParams(-1, -1));

        var heading = new LinearLayout(this) { Orientation = Android.Widget.Orientation.Vertical };
        heading.SetPadding(Dp(16), Dp(40), Dp(16), Dp(12));
        heading.SetBackgroundColor(AndroidColor.Argb(207, 8, 19, 34));
        var title = new TextView(this) { Text = "Hush Hunt · Rear ultrawide", TextSize = 19 };
        title.SetTextColor(AndroidColor.White);
        heading.AddView(title);
        _status = new TextView(this) { Text = "Checking Camera2 rear zoom capabilities…", TextSize = 13 };
        _status.SetTextColor(AndroidColor.Rgb(159, 239, 220));
        heading.AddView(_status);
        layout.AddView(heading, new FrameLayout.LayoutParams(-1, -2, GravityFlags.Top));

        var tray = new LinearLayout(this) { Orientation = Android.Widget.Orientation.Horizontal };
        tray.SetGravity(GravityFlags.CenterVertical);
        tray.SetPadding(Dp(12), Dp(8), Dp(12), Dp(8));
        tray.SetBackgroundColor(AndroidColor.Argb(210, 7, 20, 35));
        var cancel = new AndroidButton(this) { Text = "✕ Cancel" };
        cancel.Click += (_, _) => Complete("cancelled", null);
        _shutter = new AndroidButton(this) { Text = "● 0.6× photo", Enabled = false };
        _shutter.Click += (_, _) => TakePhoto();
        tray.AddView(cancel, new LinearLayout.LayoutParams(0, Dp(58), 1));
        tray.AddView(_shutter, new LinearLayout.LayoutParams(0, Dp(58), 1.3f));
        var trayParams = new FrameLayout.LayoutParams(-1, -2, GravityFlags.Bottom) { BottomMargin = Dp(44) };
        layout.AddView(tray, trayParams);
        SetContentView(layout);
    }

    private int Dp(float value) => (int)(Resources!.DisplayMetrics!.Density * value + .5f);

    protected override void OnResume()
    {
        base.OnResume();
        if (_done) return;
        if (Build.VERSION.SdkInt < BuildVersionCodes.R)
        { Complete("unavailable", "Camera2 zoom-out requires Android 11 or newer."); return; }
        if (CheckSelfPermission(Android.Manifest.Permission.Camera) != Permission.Granted)
        { RequestPermissions(new[] { Android.Manifest.Permission.Camera }, 7823); return; }
        StartCamera();
    }
    public override void OnRequestPermissionsResult(int requestCode, string[] permissions, Permission[] grantResults)
    {
        base.OnRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != 7823) return;
        if (grantResults.Length > 0 && grantResults[0] == Permission.Granted) StartCamera();
        else Complete("unavailable", "Camera permission was denied.");
    }

    private void StartCamera()
    {
        if (_done || _cameraId is not null) return;
        try
        {
            var manager = (CameraManager)GetSystemService(CameraService)!;
            var candidates = new List<(string id, float min, float max, int orientation)>();
            foreach (var id in manager.GetCameraIdList())
            {
                var chars = manager.GetCameraCharacteristics(id);
                var lensFacing = chars.Get(CameraCharacteristics.LensFacing) as Java.Lang.Integer;
                if (lensFacing is null || lensFacing.IntValue() != (int)LensFacing.Back) continue;
                var range = chars.Get(CameraCharacteristics.ControlZoomRatioRange) as Android.Util.Range;
                if (range?.Lower is not Java.Lang.Float low || range.Upper is not Java.Lang.Float high) continue;
                var min = low.FloatValue();
                var max = high.FloatValue();
                if (min > 0 && min <= 0.61f && max >= 1f)
                {
                    var angle = chars.Get(CameraCharacteristics.SensorOrientation) as Java.Lang.Integer;
                    candidates.Add((id, min, max, angle?.IntValue() ?? 90));
                }
            }
            if (candidates.Count == 0)
            {
                Complete("unavailable", "Camera2 reports no rear logical camera with a genuine ≤0.6× zoom range. The manufacturer may restrict third-party ultrawide access.");
                return;
            }
            // Prefer logical rear 0.6x camera; do not choose front/telephoto cameras.
            var best = candidates.OrderBy(c => Math.Abs(c.min - .6f)).First();
            _cameraId = best.id;
            _jpegOrientation = best.orientation;
            // Select only a supported still-photo size for the chosen camera.
            var configuration = manager.GetCameraCharacteristics(best.id)
                .Get(CameraCharacteristics.ScalerStreamConfigurationMap) as StreamConfigurationMap;
            var supported = configuration?.GetOutputSizes((int)ImageFormatType.Jpeg);
            var stillSize = supported?.Where(z => z.Width > 0 && z.Height > 0 &&
                (long)z.Width * z.Height <= 12_000_000)
                .OrderByDescending(z => (long)z.Width * z.Height).FirstOrDefault()
                ?? supported?.OrderBy(z => (long)z.Width * z.Height).FirstOrDefault();
            if (stillSize is null) { Complete("unavailable", "Rear 0.6× camera does not advertise JPEG capture."); return; }
            _photoWidth = stillSize.Width;
            _photoHeight = stillSize.Height;
            _ratio = .6f;
            _status!.Text = $"Rear Camera2 lens · {best.min:0.00}×–{best.max:0.#}× reported; requesting {_ratio:0.0}×";
            _reader = ImageReader.NewInstance(_photoWidth, _photoHeight, ImageFormatType.Jpeg, 2);
            _reader.SetOnImageAvailableListener(this, _handler);
            _deviceCallback = new DeviceCallback(this);
            manager.OpenCamera(best.id, _deviceCallback, _handler);
        }
        catch (Exception ex) { Complete("unavailable", "Camera2 could not open a compatible rear camera: " + ex.Message); }
    }

    private void OpenPreview()
    {
        if (_camera is null || !_surfaceReady || _preview?.Holder?.Surface is null || _reader is null || _done) return;
        try
        {
            var viewSurface = _preview.Holder.Surface;
            _previewRequest = _camera.CreateCaptureRequest(CameraTemplate.Preview);
            _previewRequest.AddTarget(viewSurface);
            ApplyZoom(_previewRequest);
            _sessionCallback = new SessionCallback(this);
            _camera.CreateCaptureSession(new List<Surface> { viewSurface, _reader.Surface! }, _sessionCallback, _handler);
        }
        catch (Exception ex) { Complete("error", "Camera2 preview unavailable: " + ex.Message); }
    }
    private void ApplyZoom(CaptureRequest.Builder builder)
    {
        // On Android 11+ this requests an actual wider FOV from the logical camera.
        // The HAL handles switching physical lenses if it supports this range.
        builder.Set(CaptureRequest.ControlZoomRatio, new Java.Lang.Float(_ratio));
    }
    private void OnDeviceOpened(CameraDevice device)
    {
        if (_done) { device.Close(); return; }
        _camera = device;
        OpenPreview();
    }
    private void OnSessionReady(CameraCaptureSession session)
    {
        if (_done || _previewRequest is null) { session.Close(); return; }
        try
        {
            _session = session;
            session.SetRepeatingRequest(_previewRequest.Build(), null, _handler);
            if (_shutter is not null) _shutter.Enabled = true;
        }
        catch (Exception ex) { Complete("error", "Unable to stream 0.6× preview: " + ex.Message); }
    }
    private void TakePhoto()
    {
        if (_done || _taking || _camera is null || _session is null || _reader is null) return;
        _taking = true;
        _shutter!.Enabled = false;
        try
        {
            var builder = _camera.CreateCaptureRequest(CameraTemplate.StillCapture);
            builder.AddTarget(_reader.Surface!);
            ApplyZoom(builder);
            builder.Set(CaptureRequest.JpegOrientation, new Java.Lang.Integer(_jpegOrientation));
            _session.Capture(builder.Build(), null, _handler);
            _status!.Text = "Capturing true rear 0.6× photograph…";
        }
        catch (Exception ex) { Complete("error", "Camera2 capture failed: " + ex.Message); }
    }
    public void OnImageAvailable(ImageReader? reader)
    {
        if (_done || reader is null) return;
        try
        {
            using var image = reader.AcquireLatestImage();
            if (image is null) return;
            var buffer = image.GetPlanes()[0].Buffer!;
            var data = new byte[buffer.Remaining()];
            buffer.Get(data);
            using var decoded = BitmapFactory.DecodeByteArray(data, 0, data.Length);
            if (decoded is null) throw new InvalidOperationException("No JPEG image data returned.");
            // Keep significantly more detail than the old 1280px handoff.
            const int maxSide = 2048;
            var factor = Math.Min(1d, maxSide / (double)Math.Max(decoded.Width, decoded.Height));
            using var scaled = factor < 1 ? Bitmap.CreateScaledBitmap(decoded,
                Math.Max(1, (int)(decoded.Width * factor)), Math.Max(1, (int)(decoded.Height * factor)), true) : null;
            using var output = new MemoryStream();
            (scaled ?? decoded).Compress(Bitmap.CompressFormat.Jpeg, 90, output);
            Complete("captured", null, "data:image/jpeg;base64," + Convert.ToBase64String(output.ToArray()));
        }
        catch (Exception ex) { Complete("error", "Unable to read the 0.6× photograph: " + ex.Message); }
    }

    public void SurfaceCreated(ISurfaceHolder holder) { _surfaceReady = true; OpenPreview(); }
    public void SurfaceDestroyed(ISurfaceHolder holder) { _surfaceReady = false; }
    public void SurfaceChanged(ISurfaceHolder holder, Format format, int width, int height) { }
    private sealed class DeviceCallback(HushWideCameraActivity owner) : CameraDevice.StateCallback
    {
        public override void OnOpened(CameraDevice camera) => owner.OnDeviceOpened(camera);
        public override void OnDisconnected(CameraDevice camera) => owner.Complete("error", "Rear camera was disconnected.");
        public override void OnError(CameraDevice camera, CameraError error) => owner.Complete("error", $"Android Camera2 error: {error}");
    }
    private sealed class SessionCallback(HushWideCameraActivity owner) : CameraCaptureSession.StateCallback
    {
        public override void OnConfigured(CameraCaptureSession session) => owner.OnSessionReady(session);
        public override void OnConfigureFailed(CameraCaptureSession session) => owner.Complete("unavailable", "The camera cannot configure a 0.6× preview on this device.");
    }
    private void Complete(string status, string? message, string? photo = null)
    {
        if (_done) return;
        _done = true;
        _pending = new WideOutcome { Status = status, Request = _token, Message = message, Photo = photo };
        ReleaseCamera();
        RunOnUiThread(Finish);
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
