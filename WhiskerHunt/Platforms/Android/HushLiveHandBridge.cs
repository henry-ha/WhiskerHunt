#if ANDROID
using Android.App;
using Android.Runtime;
using Google.AR.Core;

namespace WhiskerHunt;

/// <summary>Safe JNI interface for hand recognition; all native inference happens off ARCore GL/UI threads.</summary>
internal static class HushLiveHandBridge
{
    private const string ClassName = "com/hushhunt/filament/HushLiveHandTracker";
    private static bool _installed;
    private static bool _warned;

    private static void Warn(Exception exception)
    {
        if (_warned) return;
        _warned = true;
        Android.Util.Log.Warn("HushLivePet", "Hand tracking unavailable; touch petting remains: " + exception);
    }

    public static bool TryInstall(Activity activity)
    {
        try
        {
            // JNIEnv.FindClass returns a runtime-managed global reference.
            var clazz = JNIEnv.FindClass(ClassName);
            var method = JNIEnv.GetStaticMethodID(clazz, "install", "(Landroid/app/Activity;)Z");
            _installed = JNIEnv.CallStaticBooleanMethod(clazz, method, new JValue(activity));
            return _installed;
        }
        catch (Exception e) { Warn(e); _installed = false; return false; }
    }
    public static void SetEnabled(bool enabled)
    {
        if (!_installed) return;
        try
        {
            var clazz=JNIEnv.FindClass(ClassName);
            var method=JNIEnv.GetStaticMethodID(clazz,"setEnabled","(Z)V");
            JNIEnv.CallStaticVoidMethod(clazz,method,new JValue(enabled));
        }
        catch(Exception e){Warn(e);}
    }
    public static bool IsReady
    {
        get
        {
            if (!_installed)return false;
            try
            {
                var clazz=JNIEnv.FindClass(ClassName);
                var method=JNIEnv.GetStaticMethodID(clazz,"isReady","()Z");
                return JNIEnv.CallStaticBooleanMethod(clazz,method);
            }
            catch(Exception e){Warn(e);return false;}
        }
    }
    public static int OfferFrame(Google.AR.Core.Frame frame, float left, float top, float right, float bottom, int width, int height)
    {
        if (!_installed)return 0;
        try
        {
            var clazz=JNIEnv.FindClass(ClassName);
            var method=JNIEnv.GetStaticMethodID(clazz,"offerFrame","(Ljava/lang/Object;FFFFII)I");
            return JNIEnv.CallStaticIntMethod(clazz,method,new JValue(frame),
                new JValue(left),new JValue(top),new JValue(right),new JValue(bottom),
                new JValue(width),new JValue(height));
        }
        catch(Exception e){Warn(e);return 0;}
    }
    // HUSH_31060_PET_HUD_VARIETY - settings piggyback on existing JNI bridge.
    public static void SetSensitivity(int level)
    {
        if (!_installed) return;
        try
        {
            var klass = JNIEnv.FindClass(ClassName);
            var method = JNIEnv.GetStaticMethodID(klass, "setSensitivity", "(I)V");
            JNIEnv.CallStaticVoidMethod(klass, method, new JValue(level));
        }
        catch (Exception e) { Warn(e); }
    }
    public static void SetSkeletonVisible(bool visible)
    {
        if (!_installed) return;
        try
        {
            var klass = JNIEnv.FindClass(ClassName);
            var method = JNIEnv.GetStaticMethodID(klass, "setSkeletonVisible", "(Z)V");
            JNIEnv.CallStaticVoidMethod(klass, method, new JValue(visible));
        }
        catch (Exception e) { Warn(e); }
    }
    public static int GetTrackingStatus()
    {
        if (!_installed) return 4;
        try
        {
            var klass = JNIEnv.FindClass(ClassName);
            var method = JNIEnv.GetStaticMethodID(klass, "getTrackingStatus", "()I");
            return JNIEnv.CallStaticIntMethod(klass, method);
        }
        catch (Exception e) { Warn(e); return 4; }
    }
    public static void Dispose()
    {
        if (!_installed)return;
        _installed=false;
        try
        {
            var clazz=JNIEnv.FindClass(ClassName);
            var method=JNIEnv.GetStaticMethodID(clazz,"dispose","()V");
            JNIEnv.CallStaticVoidMethod(clazz,method);
        }
        catch(Exception e){Warn(e);}
    }
}
#endif
