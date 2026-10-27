#if ANDROID
using Android.App;
using Android.Runtime;
using Android.Widget;
using Google.AR.Core;

namespace WhiskerHunt;

/// <summary>
/// JNI facade to Filament Java renderer. Important: Android.Runtime.JNIEnv.FindClass
/// returns a runtime-managed GLOBAL class reference, not a disposable local JNI ref.
/// NEVER call DeleteLocalRef or DeleteGlobalRef on its return value.
/// JNI string and array references created with NewString / NewArray ARE local and
/// are released in finally blocks below.
/// </summary>
internal static class HushFilamentBridge
{
    private const string JavaName = "com/hushhunt/filament/HushFilamentOverlay";
    private static bool _installed;
    private static bool _warned;
    internal static string LastError { get; private set; } = "none";

    private static void Warn(Exception error)
    {
        LastError = error.GetType().Name + ": " + error.Message;
        if (_warned) return;
        _warned = true;
        Android.Util.Log.Warn("HushFilament", "Bridge failed; falling back to OpenGL: " + error);
    }

    public static bool TryInstall(Activity activity, FrameLayout container, string asset, float modelMetres)
    {
        try
        {
            LastError = "none";
            if (_installed) Dispose();
            // FindClass is a runtime-managed global reference: DO NOT delete it.
            var clazz = JNIEnv.FindClass(JavaName);
            var method = JNIEnv.GetStaticMethodID(clazz, "install",
                "(Landroid/app/Activity;Landroid/widget/FrameLayout;Ljava/lang/String;F)Z");
            var text = JNIEnv.NewString(asset);
            try
            {
                _installed = JNIEnv.CallStaticBooleanMethod(clazz, method,
                    new JValue(activity), new JValue(container), new JValue(text), new JValue(modelMetres));
                if (!_installed)
                    LastError = "Java Filament install returned false. See Android Logcat (HushFilament).";
                return _installed;
            }
            finally { JNIEnv.DeleteLocalRef(text); }
        }
        catch (Exception e) { Warn(e); _installed = false; return false; }
    }

    public static bool IsReady
    {
        get
        {
            if (!_installed) return false;
            try
            {
                var clazz = JNIEnv.FindClass(JavaName);
                var method = JNIEnv.GetStaticMethodID(clazz, "isReady", "()Z");
                return JNIEnv.CallStaticBooleanMethod(clazz, method);
            }
            catch (Exception e) { Warn(e); return false; }
        }
    }

    public static void SetOrientation(float yawDegrees, float pitchDegrees)
    {
        if (!_installed) return;
        try
        {
            var clazz = JNIEnv.FindClass(JavaName);
            var method = JNIEnv.GetStaticMethodID(clazz, "setOrientation", "(FF)V");
            JNIEnv.CallStaticVoidMethod(clazz, method, new JValue(yawDegrees), new JValue(pitchDegrees));
        }
        catch (Exception e) { Warn(e); }
    }

    public static void ConfigureHdr(Java.Lang.Object config)
    {
        if (!_installed) return;
        try
        {
            var clazz = JNIEnv.FindClass(JavaName);
            var method = JNIEnv.GetStaticMethodID(clazz, "configureEnvironmentalHdr", "(Ljava/lang/Object;)V");
            JNIEnv.CallStaticVoidMethod(clazz, method, new JValue(config));
        }
        catch (Exception e) { Warn(e); }
    }

    public static void SubmitFrame(float[] view, float[] projection, float[] anchor,
        float scale, Google.AR.Core.Frame arFrame)
    {
        if (!_installed) return;
        IntPtr v = IntPtr.Zero, p = IntPtr.Zero, a = IntPtr.Zero;
        try
        {
            var clazz = JNIEnv.FindClass(JavaName);
            var method = JNIEnv.GetStaticMethodID(clazz, "submitFrame", "([F[F[FFLjava/lang/Object;)V");
            v = JNIEnv.NewArray(view);
            p = JNIEnv.NewArray(projection);
            a = JNIEnv.NewArray(anchor);
            JNIEnv.CallStaticVoidMethod(clazz, method,
                new JValue(v), new JValue(p), new JValue(a), new JValue(scale), new JValue(arFrame));
        }
        catch (Exception e) { Warn(e); }
        finally
        {
            if (v != IntPtr.Zero) JNIEnv.DeleteLocalRef(v);
            if (p != IntPtr.Zero) JNIEnv.DeleteLocalRef(p);
            if (a != IntPtr.Zero) JNIEnv.DeleteLocalRef(a);
        }
    }

    public static void Dispose()
    {
        if (!_installed) return;
        _installed = false;
        try
        {
            var clazz = JNIEnv.FindClass(JavaName);
            var method = JNIEnv.GetStaticMethodID(clazz, "dispose", "()V");
            JNIEnv.CallStaticVoidMethod(clazz, method);
        }
        catch (Exception e) { Warn(e); }
    }
}
#endif
