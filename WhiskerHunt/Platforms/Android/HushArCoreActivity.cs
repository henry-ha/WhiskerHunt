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
    private string _model = "";
    private string _species = "";
    private string _animalName = "";
    private bool _installRequested, _didComplete, _resumed;
    private PixelCopyListener? _copyListener;
    private bool _capturePending;
    private bool _placementReady;
    private bool _modelFrameConfirmed;
    private readonly object _frameLock = new();

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);
        _model = Intent?.GetStringExtra("model") ?? "";
        _species = Intent?.GetStringExtra("species") ?? "Other";
        _animalName = Intent?.GetStringExtra("name") ?? "Animal";
        // Exact species/variety match only. Do not mislabel generic shapes as wildlife.
        if (!HushGlbAnimal3D.TryLoad(this, _species, _animalName, out _animal, out var loadMessage))
        {
            FinishWith("fallback", loadMessage);
            return;
        }
        string name = _animalName;

        _root = new FrameLayout(this) { Background = new ColorDrawable(AndroidColor.Black) };
        _surface = new GLSurfaceView(this);
        _surface.SetEGLContextClientVersion(2);
        _surface.SetEGLConfigChooser(8, 8, 8, 8, 16, 0); // Real 3D mesh needs a depth buffer.
        // The Android binding does not expose SetPreserveEGLContextOnPause(bool).
        // GLSurfaceView recreates the GL resources after context loss; OnSurfaceCreated
        // handles that lifecycle safely instead of requiring a non-existent setter.
        _renderer = new ArRenderer(this, _animal!);
        _surface.SetRenderer(_renderer);
        _surface.RenderMode = Rendermode.Continuously;
        _root.AddView(_surface, new LayoutParams(-1, -1));

        // Native ARCore now renders a dimensional animal mesh in OpenGL, directly
        // at the world anchor. Never add a 2D ImageView sprite to this activity.

        var top = new LinearLayout(this) { Orientation = Orientation.Vertical };
        top.SetPadding(Dp(16), Dp(44), Dp(73), Dp(9));
        top.SetBackgroundColor(AndroidColor.Argb(160, 14, 18, 35));
        var title = new TextView(this) { Text = "AR Safari ✨", TextSize = 19 };
        title.SetTextColor(AndroidColor.White);
        top.AddView(title);
        _status = new TextView(this) { Text = $"Find a floor or table, then tap Place {name}.", TextSize = 15 };
        _status.SetTextColor(AndroidColor.Rgb(168, 247, 228));
        top.AddView(_status);
        var tip = new TextView(this) { Text = "Textured 3D species model · anchored in your room · walk around to view all sides. Prototype assets are not photogrammetry.", TextSize = 11 };
        tip.SetTextColor(AndroidColor.LightGray);
        top.AddView(tip);
        _root.AddView(top, new LayoutParams(-1, -2, GravityFlags.Top));
        var close = new AndroidButton(this) { Text = "✕", TextSize = 20 };
        close.SetTextColor(AndroidColor.White);
        var closeBg = new GradientDrawable();
        closeBg.SetColor(AndroidColor.Rgb(203, 45, 64));
        closeBg.SetCornerRadius(Dp(28));
        close.Background = closeBg;
        close.ContentDescription = "Close AR Safari";
        close.Click += (_, _) => FinishWith("cancelled", "AR Safari closed.");
        var closeParams = new LayoutParams(Dp(48), Dp(48), GravityFlags.Top | GravityFlags.Right);
        closeParams.TopMargin = Dp(42);
        closeParams.RightMargin = Dp(12);
        _root.AddView(close, closeParams);


        var bottom = new LinearLayout(this) { Orientation = Orientation.Horizontal };
        bottom.SetGravity(GravityFlags.Center);
        bottom.SetPadding(Dp(9), Dp(8), Dp(9), Dp(8)); // Native buttons sit in their own safe-area tray
        bottom.SetBackgroundColor(AndroidColor.Argb(195, 12, 17, 36));
        var back = new AndroidButton(this) { Text = "← 2D Safari" };
        back.Click += (_, _) => FinishWith("2d", "2D Safari selected.");
        _place = new AndroidButton(this) { Text = "🐾 Place 3D", Enabled = false };
        _place.Click += (_, _) => PlaceAtCenter();
        _collect = new AndroidButton(this) { Text = "🐾 Capture", Enabled = false };
        _collect.Click += (_, _) => Capture();
        // Big, clearly separated capture tokens. Placement and capture use the same wildlife
        // icon language as the WebView encounter tools; these remain accessible tap targets.
        StyleCaptureToken(_place, AndroidColor.Rgb(21, 106, 103));
        StyleCaptureToken(_collect, AndroidColor.Rgb(27, 129, 79));
        StyleCaptureToken(back, AndroidColor.Rgb(40, 54, 75));
        bottom.AddView(back, new LinearLayout.LayoutParams(0, Dp(62), 1f));
        bottom.AddView(_place, new LinearLayout.LayoutParams(0, Dp(62), 1f));
        bottom.AddView(_collect, new LinearLayout.LayoutParams(0, Dp(62), 1f));
        // Android gesture/three-button navigation can cover a bottom-aligned FrameLayout.
        // Lift the entire action tray rather than padding buttons inside the occluded area.
        var trayParams = new LayoutParams(-1, -2, GravityFlags.Bottom);
        trayParams.BottomMargin = Dp(68);
        _root.AddView(bottom, trayParams);
        SetContentView(_root);
        _surface.Touch += (_, e) =>
        {
            if (e.Event?.Action == MotionEventActions.Up && _surface is not null && _renderer is not null)
            {
                float x = e.Event.GetX(), y = e.Event.GetY();
                if (y > Dp(156) && y < _surface.Height - Dp(178)) _renderer.QueuePlacement(x, y);
            }
            e.Handled = true;
        };
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
                _session.Configure(config);
            }
            _session.Resume();
            _resumed = true;
            _surface.OnResume();
            SetStatus("Find a well-lit, textured floor or table. Move your phone slowly side to side, then tap that surface to place a creature. If unavailable, use 2D Safari.");
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
            _surface?.OnPause();
            try { _session?.Pause(); } catch (Exception e) { JLog.Warn("HushHuntAR", e.Message); }
            _resumed = false;
        }
        base.OnPause();
    }

    protected override void OnDestroy()
    {
        try { _anchor?.Detach(); _anchor?.Dispose(); } catch { }
        try { _session?.Close(); _session?.Dispose(); } catch { }
        base.OnDestroy();
    }

    public override void OnBackPressed() { FinishWith("cancelled", "AR Safari closed."); }

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
            SetStatus("No tracked surface here. Scan a textured floor or table slowly, or tap 2D Safari to play without tracking."));
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
                    ? "Surface tracked! Tap the surface or the Place token to add your creature."
                    : "Searching for a real plane… move slowly over a textured floor or table. Use 2D Safari if tracking is unavailable.");
            }
        });
    }

    internal void OnPlaced(Anchor anchor)
    {
        RunOnUiThread(() =>
        {
            _anchor?.Detach();
            _anchor?.Dispose();
            _anchor = anchor;
            // Placement alone does NOT establish that the GLB is visible.
            _modelFrameConfirmed = false;
            if (_collect is not null) _collect.Enabled = false;
            if (_place is not null) _place.Text = "🧭 Move";
            SetStatus($"Surface anchor ready. Rendering {_animalName}…");
        });
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
            SetStatus($"3D draw submitted for {_animalName}. If it is not visible, tap Move and choose another tracked surface before Capture.");
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
        SetStatus("Saving your AR discovery photo…");
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
        private bool _modelInitialised;
        private long _lastPlaneCheck;
        private readonly HushGlbAnimal3D _animal;
        private readonly float[] _view = new float[16], _projection = new float[16];
        private FloatBuffer? _quad, _sourceUv, _displayUv;
        // No need to cache the ARCore frame between rendering passes.
        public ArRenderer(HushArCoreActivity host, HushGlbAnimal3D animal) { _host = host; _animal = animal; }
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
            try
            {
                _animal.Initialise();
                int error = GLES.GlGetError();
                if (error != GLES.GlNoError)
                    throw new InvalidOperationException("GLB initialisation error: " + error);
                _modelInitialised = true;
                JLog.Info("HushHuntAR", "Textured 3D model uploaded to the GPU.");
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
                if (camera.TrackingState != TrackingState.Tracking) { _host.UpdatePlacementReady(false); return; }

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
                if (_modelInitialised && _host._anchor is { } anchor && anchor.TrackingState == TrackingState.Tracking)
                {
                    camera.GetViewMatrix(_view, 0);
                    camera.GetProjectionMatrix(_projection, 0, .1f, 80f);
                    var pos = new float[3]; anchor.Pose.GetTranslation(pos,0);
                    // Clear any stale driver error before submitting the 3D mesh.
                    for (int i = 0; i < 8 && GLES.GlGetError() != GLES.GlNoError; i++) { }
                    try
                    {
                        _animal.Draw(_view, _projection, pos);
                        _host.OnModelDrawn(GLES.GlGetError());
                    }
                    catch (Exception modelError)
                    {
                        JLog.Warn("HushHuntAR", "Textured GLB rendering failed: " + modelError);
                        _host.SetStatus("Could not render this 3D animal. Try reopening AR Safari.");
                    }
                }
            }
            catch (Exception error)
            {
                JLog.Warn("HushHuntAR", "Frame: " + error.Message);
                _host.SetStatus("Tracking needs more light or space. Move slowly and try again.");
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
