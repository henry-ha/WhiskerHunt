#if ANDROID
using System;
using Android.Content;
using Android.OS;
using Android.Views;
using AndroidView = Android.Views.View;
using AndroidCanvas = Android.Graphics.Canvas;
using AndroidPaint = Android.Graphics.Paint;
using AndroidPaintFlags = Android.Graphics.PaintFlags;
using AndroidColor = Android.Graphics.Color;

namespace WhiskerHunt;

/// <summary>
/// Minimal, non-interactive AR carry guidance (v3.10.62c).
/// Amber rotating ring = ARCore has NOT confirmed a placement point at the palm.
/// Green pulsing check = CURRENT ARCore frame confirmed a plane hit at the palm.
/// There are deliberately no full-screen grids, no GLB changes and no new hit tests.
/// </summary>
internal sealed class HushCarryGuidanceOverlay : AndroidView
{
    // Preserve the v3.10.62 scanner contract used by HushArCoreActivity.
    public const int Columns = 6;
    public const int Rows = 4;
    public const int CellCount = Columns * Rows;

    private readonly float _density;
    private readonly AndroidPaint _ring = new(AndroidPaintFlags.AntiAlias);
    private readonly AndroidPaint _spinner = new(AndroidPaintFlags.AntiAlias);
    private readonly AndroidPaint _fill = new(AndroidPaintFlags.AntiAlias);
    private readonly AndroidPaint _tick = new(AndroidPaintFlags.AntiAlias);
    private bool _carrying;
    private bool _dropConfirmed;
    private int _validFrameStreak;
    private float _palmX, _palmY, _cameraWidth = 1f, _cameraHeight = 1f;
    private long _started;
    private long _confirmedAt;

    public HushCarryGuidanceOverlay(Context context) : base(context)
    {
        _density = context.Resources?.DisplayMetrics?.Density ?? 1f;
        Clickable = false;
        Focusable = false;
        SetWillNotDraw(false);

        _ring.SetStyle(AndroidPaint.Style.Stroke);
        _ring.StrokeWidth = 1.7f * _density;
        _spinner.SetStyle(AndroidPaint.Style.Stroke);
        _spinner.StrokeWidth = 3.2f * _density;
        _fill.SetStyle(AndroidPaint.Style.Fill);
        _tick.SetStyle(AndroidPaint.Style.Stroke);
        _tick.StrokeWidth = 2.9f * _density;
        _tick.Color = AndroidColor.White;
        Visibility = ViewStates.Gone;
    }

    // UI thread only. Keep the established method signature intact; the bool is
    // the current ARCore plane-hit result, not the cached/nearby grid candidates.
    public void SetGuide(float palmX, float palmY, int cameraWidth, int cameraHeight,
                         bool[] confirmedSurfaceCells, bool validDrop)
    {
        if (cameraWidth <= 0 || cameraHeight <= 0 ||
            !float.IsFinite(palmX) || !float.IsFinite(palmY) ||
            confirmedSurfaceCells is null || confirmedSurfaceCells.Length != CellCount)
        {
            Reset();
            return;
        }

        long now = SystemClock.UptimeMillis();
        if (!_carrying)
        {
            _started = now;
            _validFrameStreak = 0;
            _dropConfirmed = false;
        }
        _carrying = true;
        _palmX = palmX;
        _palmY = palmY;
        _cameraWidth = cameraWidth;
        _cameraHeight = cameraHeight;

        // Brief confirmation prevents single-frame flicker. Crucially, losing the
        // plane hit immediately returns to AMBER; never show a stale green tick.
        _validFrameStreak = validDrop ? Math.Min(3, _validFrameStreak + 1) : 0;
        bool confirmedNow = validDrop && _validFrameStreak >= 2;
        if (confirmedNow && !_dropConfirmed) _confirmedAt = now;
        _dropConfirmed = confirmedNow;

        Visibility = ViewStates.Visible;
        Invalidate();
    }

    public void Reset()
    {
        _carrying = false;
        _dropConfirmed = false;
        _validFrameStreak = 0;
        Visibility = ViewStates.Gone;
        Invalidate();
    }

    protected override void OnDraw(AndroidCanvas? canvas)
    {
        base.OnDraw(canvas);
        if (!_carrying || canvas is null || Width < 2 || Height < 2) return;

        float w = Width, h = Height;
        float x = Math.Clamp(_palmX / _cameraWidth * w, 0f, w);
        float y = Math.Clamp(_palmY / _cameraHeight * h, 0f, h);
        long now = SystemClock.UptimeMillis();
        float r = 22f * _density;

        if (!_dropConfirmed)
        {
            // AMBER: no *current* valid plane under palm. Indeterminate loader
            // makes 'searching' unmistakable without covering the camera view.
            _ring.Color = AndroidColor.Argb(90, 248, 190, 61);
            canvas.DrawCircle(x, y, r, _ring);
            float spinPhase = (now - _started) % 1100L / 1100f;
            float sweep = 99f + 22f * (float)Math.Sin(spinPhase * Math.PI * 2);
            _spinner.Color = AndroidColor.Argb(245, 249, 186, 48);
            canvas.DrawArc(x - r, y - r, x + r, y + r,
                           spinPhase * 360f - 90f, sweep, false, _spinner);
            _fill.Color = AndroidColor.Argb(185, 251, 199, 86);
            canvas.DrawCircle(x, y, 2.4f * _density, _fill);
        }
        else
        {
            // GREEN: two consecutive live valid surface checks. A larger check
            // pops into view then gently breathes to say 'release here'.
            float age = Math.Max(0L, now - _confirmedAt);
            float entry = Math.Clamp(age / 270f, 0f, 1f);
            float easeOut = 1f - (1f - entry) * (1f - entry) * (1f - entry);
            float breathe = 1f + .075f * (float)Math.Sin(age * Math.PI * 2 / 1350f);

            _ring.Color = AndroidColor.Argb(118, 35, 209, 144);
            canvas.DrawCircle(x, y, r + 1.7f * _density * breathe, _ring);

            float bx = Math.Clamp(x + 16f * _density, 19f * _density, w - 19f * _density);
            float by = Math.Clamp(y - 17f * _density, 19f * _density, h - 19f * _density);
            float badgeR = (11.5f + 4.2f * easeOut) * breathe * _density;

            _fill.Color = AndroidColor.Argb(48, 33, 217, 141);
            canvas.DrawCircle(bx, by, badgeR + 4f * _density, _fill);
            _fill.Color = AndroidColor.Argb(248, 17, 163, 109);
            canvas.DrawCircle(bx, by, badgeR, _fill);

            _tick.StrokeWidth = 2.9f * _density;
            canvas.DrawLine(bx - badgeR * .46f, by,
                            bx - badgeR * .12f, by + badgeR * .34f, _tick);
            canvas.DrawLine(bx - badgeR * .12f, by + badgeR * .34f,
                            bx + badgeR * .50f, by - badgeR * .37f, _tick);
        }

        // Animate only while the existing carry overlay is visible.
        PostInvalidateDelayed(75);
    }
}
#endif
