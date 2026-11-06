package com.hushhunt.filament;

import android.app.Activity;
import android.media.Image;
import android.os.SystemClock;
import android.util.Log;
import com.google.mediapipe.framework.image.BitmapImageBuilder;
import com.google.mediapipe.framework.image.MPImage;
import com.google.mediapipe.tasks.core.BaseOptions;
import com.google.mediapipe.tasks.vision.core.RunningMode;
import com.google.mediapipe.tasks.vision.handlandmarker.HandLandmarker;
import com.google.mediapipe.tasks.vision.handlandmarker.HandLandmarkerResult;
import com.google.mediapipe.tasks.components.containers.NormalizedLandmark;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Color;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import java.lang.reflect.Method;
import java.nio.ByteBuffer;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * HUSH_31059_LIVE_HAND_PET: on-device, opt-in vision on the SAME ARCore CPU camera
 * feed as the live Safari camera. No second camera, web service or recording.
 *
 * Only the current Frame can transform IMAGE_PIXELS -> VIEW; calculate the
 * affine transform synchronously, while its Image is open, and pass a copied
 * frame to the dedicated inference worker. No ML or Bitmap work on GL/UI thread.
 *
 * This is screen-space hand/animal overlap, NOT physical 3D collision. The
 * occlusion/depth of the fingers is deliberately not invented or assumed.
 */
public final class HushLiveHandTracker {
    private static final String TAG = "HushLivePet";
    private static HushLiveHandTracker instance;
    private final Activity activity;
    // Draw the real 21 landmarks and status over the existing AR view.
    private final HandOverlay overlay;
    private long lastCaptureWarningMs;
    private int cameraImages;
    private final ExecutorService worker = Executors.newSingleThreadExecutor(r -> {
        Thread t = new Thread(r, "Hush-Live-Hand-ML");
        t.setDaemon(true);
        return t;
    });
    private final AtomicBoolean busy = new AtomicBoolean(false);
    private volatile boolean enabled;
    private volatile boolean ready;
    private volatile boolean disposed;
    private volatile Sample sample;
    // HUSH_31060_PET_HUD_VARIETY: independent gesture sensitivity and skeleton visibility.
    private volatile int sensitivity = 1;
    private volatile boolean showSkeleton = false;
    private volatile int handStatus = 1; // 0 off, 1 loading, 2 searching, 3 detected, 4 error
    private long lastSubmittedMs;
    private long lastPetMs;
    private long lastSampleSeenMs;
    private long enterMs;
    private float enterX, enterY;
    private boolean inside;
    private boolean dwellFired;
    private int stableInsideFrames;
    private final float density;
    private HandLandmarker detector; // worker thread only
    private long lastInferenceMs;

    private HushLiveHandTracker(Activity a) {
        activity = a;
        density = a.getResources().getDisplayMetrics().density;
        overlay = new HandOverlay(a);
        // install() is called from Activity.OnCreate on the UI thread.
        ViewGroup content = a.findViewById(android.R.id.content);
        if (content != null) {
            content.addView(overlay, new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        }
    }

    public static boolean install(Activity activity) {
        dispose();
        try (java.io.InputStream model = activity.getAssets().open("hand_landmarker.task")) {
            if (model.read() < 0) return false;
        } catch (Exception missing) {
            Log.w(TAG, "Hand model missing: install v3.10.59 resources before launching", missing);
            return false;
        }
        HushLiveHandTracker next = new HushLiveHandTracker(activity);
        instance = next;
        next.worker.execute(() -> {
            try {
                BaseOptions base = BaseOptions.builder()
                    .setModelAssetPath("hand_landmarker.task").build();
                HandLandmarker.HandLandmarkerOptions options =
                    HandLandmarker.HandLandmarkerOptions.builder()
                        .setBaseOptions(base)
                        .setRunningMode(RunningMode.VIDEO)
                        .setNumHands(1)
                        .setMinHandDetectionConfidence(.62f)
                        .setMinHandPresenceConfidence(.58f)
                        .setMinTrackingConfidence(.55f)
                        .build();
                if (next.disposed) return;
                next.detector = HandLandmarker.createFromOptions(activity, options);
                if (next.disposed) { next.detector.close(); next.detector = null; return; }
                next.ready = true;
                next.handStatus = 2;
                next.overlay.publish("Camera ready - show your hand", null, 0);
                Log.i(TAG, "On-device hand detection ready (MediaPipe CPU)");
            } catch (Throwable t) {
                next.ready = false;
                next.handStatus = 4;
                next.overlay.publish("Hand ML failed: " + t.getClass().getSimpleName(), null, 0);
                Log.e(TAG, "Hand tracker initialization failed; screen petting unaffected", t);
            }
        });
        return true;
    }

    public static void setEnabled(boolean value) {
        HushLiveHandTracker item = instance;
        if (item != null) {
            item.enabled = value;
            item.handStatus = !value ? 0 : (item.ready ? 2 : 1);
            if (!value) item.reset();
            item.overlay.publish(value ? (item.ready ? "Camera ready - show your hand" : "Hand model loading...")
                                       : "Live hand tracking OFF", null, 0);
            item.overlay.postInvalidate();
        }
    }

    public static void setSensitivity(int sensitivity) {
        HushLiveHandTracker item = instance;
        if (item != null) {
            item.sensitivity = Math.max(0, Math.min(2, sensitivity));
            item.reset();
        }
    }
    public static void setSkeletonVisible(boolean visible) {
        HushLiveHandTracker item = instance;
        if (item != null) {
            item.showSkeleton = visible;
            item.overlay.postInvalidate();
        }
    }
    public static int getTrackingStatus() {
        HushLiveHandTracker item = instance;
        return item == null ? 4 : item.handStatus;
    }
    public static boolean isReady() {
        HushLiveHandTracker item = instance;
        return item != null && item.enabled && item.ready && !item.disposed;
    }

    /**
     * Called by existing ARCore GL thread. Result: 0=none, 1=gentle touch,
     * 2=stroke. Coordinates are already the *actual* animal's screen bounds.
     */
    public static int offerFrame(Object arFrame, float left, float top, float right,
                                 float bottom, int viewWidth, int viewHeight) {
        HushLiveHandTracker item = instance;
        if (item == null || !item.enabled || item.disposed || !item.ready || arFrame == null
            || viewWidth <= 0 || viewHeight <= 0)
            return 0;

        long now = SystemClock.uptimeMillis();
        // Inference completion is asynchronous. Only accept recent detections.
        Sample detected = item.sample;
        // Detection runs even before an animal is placed, so skeleton tracking
        // can be diagnosed independently of animal placement and Filament draw.
        int event = (right > left && bottom > top)
            ? item.interpret(detected, left, top, right, bottom, now) : 0;

        // One pending job maximum, ~8 Hz, avoiding ARCore and Filament stalls.
        if (now - item.lastSubmittedMs < 120 || !item.busy.compareAndSet(false, true))
            return event;
        item.lastSubmittedMs = now;
        Image image = null;
        try {
            image = (Image) arFrame.getClass().getMethod("acquireCameraImage").invoke(arFrame);
            item.cameraImages++;
            int w = image.getWidth(), h = image.getHeight();
            if (w <= 0 || h <= 0) return event;
            float[] mapping = mapCameraPixelsToView(arFrame, w, h);
            if (mapping == null) {
                item.overlay.publish("ARCore image mapping unavailable", null, 0);
                return event;
            } // Never invent a rotation/crop mapping.
            Image.Plane[] planes = image.getPlanes();
            if (planes.length < 3) return event;
            RawFrame copy = new RawFrame(w, h, mapping,
                copied(planes[0].getBuffer()), planes[0].getRowStride(), planes[0].getPixelStride(),
                copied(planes[1].getBuffer()), planes[1].getRowStride(), planes[1].getPixelStride(),
                copied(planes[2].getBuffer()), planes[2].getRowStride(), planes[2].getPixelStride(), now);
            item.worker.execute(() -> item.detect(copy));
            item.lastEnqueueMs = now;
            // Once handed to the worker, it owns busy until result or failure.
            image.close(); image = null;
            return event;
        } catch (Throwable failure) {
            // NOT_YET_AVAILABLE is normal at startup. All other failures must
            // be visible in Logcat instead of silently appearing as 'no hand'.
            Throwable cause = failure;
            if (failure instanceof java.lang.reflect.InvocationTargetException &&
                ((java.lang.reflect.InvocationTargetException)failure).getCause() != null)
                cause = ((java.lang.reflect.InvocationTargetException)failure).getCause();
            String kind = cause.getClass().getSimpleName();
            if (!"NotYetAvailableException".equals(kind) &&
                now - item.lastCaptureWarningMs > 5000) {
                item.lastCaptureWarningMs = now;
                Log.w(TAG, "AR camera image cannot be acquired", cause);
                item.overlay.publish("AR camera error: " + kind, null, 0);
            }
            return event;
        } finally {
            if (image != null) image.close();
            // The worker is responsible for releasing busy only after submission.
            // lastEnqueueMs identifies successful queue submissions.
            if (item.lastEnqueueMs != now) item.busy.set(false);
        }
    }

    private volatile long lastEnqueueMs;

    private static byte[] copied(ByteBuffer input) {
        ByteBuffer read = input.duplicate();
        read.position(0);
        byte[] out = new byte[read.remaining()];
        read.get(out);
        return out;
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private static float[] mapCameraPixelsToView(Object frame, int width, int height) {
        try {
            Class<? extends Enum> type = (Class<? extends Enum>)
                Class.forName("com.google.ar.core.Coordinates2d").asSubclass(Enum.class);
            Object in = Enum.valueOf(type, "IMAGE_PIXELS");
            Object out = Enum.valueOf(type, "VIEW");
            float[] from = {0f,0f, (float)width,0f, 0f,(float)height};
            float[] to = new float[6];
            Method method = frame.getClass().getMethod("transformCoordinates2d",
                type, float[].class, type, float[].class);
            method.invoke(frame, in, from, out, to);
            for (float v : to) if (!Float.isFinite(v)) return null;
            if (Math.abs(to[2]-to[0]) + Math.abs(to[3]-to[1]) < 1f &&
                Math.abs(to[4]-to[0]) + Math.abs(to[5]-to[1]) < 1f) return null;
            return to;
        } catch (Throwable t) {
            // Some ARCore bindings expose only FloatBuffer overload; signal so
            // the user may update ARCore instead of using incorrect coordinates.
            if (!loggedMappingFailure) {
                loggedMappingFailure = true;
                Log.w(TAG, "ARCore IMAGE_PIXELS->VIEW mapping unavailable", t);
            }
            return null;
        }
    }
    private static volatile boolean loggedMappingFailure;

    private void detect(RawFrame image) {
        try {
            if (disposed || !enabled || detector == null) return;
            // 256px often makes the palm too small to detect. 384px is still
            // inexpensive at ~8 FPS on modern Snapdragon Android devices.
            final int targetW = 384;
            final int targetH = Math.max(128, Math.round(targetW * image.h / (float)image.w));
            int[] pixels = new int[targetW * targetH];
            for (int y=0; y<targetH; ++y) {
                int sy = Math.min(image.h-1, y * image.h / targetH);
                for (int x=0; x<targetW; ++x) {
                    int sx = Math.min(image.w-1, x * image.w / targetW);
                    int Y = at(image.Y,sy*image.yRow+sx*image.yPixel) & 255;
                    int uvX=sx/2,uvY=sy/2;
                    int U=(at(image.U,uvY*image.uRow+uvX*image.uPixel)&255)-128;
                    int V=(at(image.V,uvY*image.vRow+uvX*image.vPixel)&255)-128;
                    int r=clamp(Math.round(Y+1.402f*V));
                    int g=clamp(Math.round(Y-.344136f*U-.714136f*V));
                    int b=clamp(Math.round(Y+1.772f*U));
                    pixels[y*targetW+x]=0xff000000|(r<<16)|(g<<8)|b;
                }
            }
            Bitmap bitmap=Bitmap.createBitmap(pixels,targetW,targetH,Bitmap.Config.ARGB_8888);
            MPImage mp = new BitmapImageBuilder(bitmap).build();
            long timestamp = Math.max(image.t, lastInferenceMs+1);
            lastInferenceMs=timestamp;
            HandLandmarkerResult result = detector.detectForVideo(mp,timestamp);
            if (result != null && !result.landmarks().isEmpty()) {
                List<NormalizedLandmark> points = result.landmarks().get(0);
                // All 21 MediaPipe joints are projected to Android view pixels.
                // This draws a real hand skeleton, rather than an invented graphic.
                if (points.size() >= 21) {
                    float[] raw = new float[42];
                    for (int i=0; i<21; i++) {
                        NormalizedLandmark p=points.get(i);
                        float imageX=p.x(), imageY=p.y();
                        raw[i*2]=image.m[0]+imageX*(image.m[2]-image.m[0])+imageY*(image.m[4]-image.m[0]);
                        raw[i*2+1]=image.m[1]+imageX*(image.m[3]-image.m[1])+imageY*(image.m[5]-image.m[1]);
                    }
                    boolean finite = true;
                    for (float v : raw) if (!Float.isFinite(v)) { finite=false; break; }
                    if (finite) {
                        sample=new Sample(raw,image.t,true);
                        handStatus = 3;
                    } else {
                        sample=new Sample(null,image.t,false);
                        handStatus = 2;
                    }
                    overlay.publish(finite ? "Hand detected - move over animal" : "Tracking coordinates invalid",
                        finite ? raw : null, image.t);
                } else {
                    handStatus = 2;
                    sample=new Sample(null,image.t,false);
                    overlay.publish("Camera active - hand not found", null, image.t);
                }
            } else {
                handStatus = 2;
                sample=new Sample(null,image.t,false);
                overlay.publish("Camera active - show an open hand", null, image.t);
            }
        } catch (Throwable e) {
            handStatus = 4;
            sample=new Sample(null,SystemClock.uptimeMillis(),false);
            overlay.publish("Hand inference error: " + e.getClass().getSimpleName(), null, 0);
            if (SystemClock.uptimeMillis() - lastCaptureWarningMs > 5000) {
                lastCaptureWarningMs = SystemClock.uptimeMillis();
                Log.w(TAG, "Hand inference skipped", e);
            }
        } finally { busy.set(false); }
    }
    private static byte at(byte[] arr, int pos) {return pos>=0 && pos<arr.length?arr[pos]:0;}
    private static int clamp(int v){return v<0?0:(v>255?255:v);}

    private synchronized int interpret(Sample s, float l, float t, float r, float b, long now) {
        if (s == null || s.t == lastSampleSeenMs || now-s.t>550) return 0;
        lastSampleSeenMs=s.t;
        if (!s.hand || s.points == null) { resetGesture(); return 0; }
        float pad=(sensitivity == 0 ? 7f : sensitivity == 2 ? 20f : 12f)*density;
        float x=0,y=0;
        // Fixed fingertip priority avoids point switching from looking like a stroke.
        // (index tip -> middle tip -> palm centre)
        boolean matched=false;
        // 21-landmark array: never use wrist/knuckles as fingertip contacts.
        int[] fingertips = {8, 12, 9};
        for (int joint : fingertips) {
            int i = joint * 2;
            float px=s.points[i],py=s.points[i+1];
            if (!Float.isFinite(px) || !Float.isFinite(py) ||
                px<l-pad||px>r+pad||py<t-pad||py>b+pad) continue;
            x=px;y=py;matched=true;break;
        }
        if (!matched){resetGesture();return 0;}
        if (!inside){inside=true;enterMs=now;enterX=x;enterY=y;stableInsideFrames=1;dwellFired=false;return 0;}
        stableInsideFrames++;
        if (stableInsideFrames<2 || now-lastPetMs<(sensitivity == 2 ? 650 : sensitivity == 0 ? 1100 : 850)) return 0;
        float dx=x-enterX,dy=y-enterY;
        float stroke = (sensitivity == 0 ? 36f : sensitivity == 2 ? 20f : 28f)*density;
        if (dx*dx+dy*dy >= stroke*stroke) {
            lastPetMs=now; enterX=x;enterY=y;enterMs=now;dwellFired=true;
            overlay.publish("STROKE OK", s.points, s.t);
            Log.d(TAG,"Live hand stroke detected");
            return 2;
        }
        // Open-hand dwell is a gentle touch, only once per entry.
        if (!dwellFired && now-enterMs >= (sensitivity == 0 ? 740 : sensitivity == 2 ? 390 : 550)) {
            lastPetMs=now; dwellFired=true;
            overlay.publish("TOUCH OK", s.points, s.t);
            Log.d(TAG,"Live hand touch detected");
            return 1;
        }
        return 0;
    }
    private synchronized void resetGesture(){inside=false;stableInsideFrames=0;dwellFired=false;}
    private synchronized void reset(){sample=null;lastSampleSeenMs=0;resetGesture();}

    public static void dispose(){
        HushLiveHandTracker old=instance;
        instance=null;
        if (old==null)return;
        old.enabled=false;old.disposed=true;old.ready=false;
        old.activity.runOnUiThread(() -> {
            ViewGroup p = (ViewGroup)old.overlay.getParent();
            if (p != null) p.removeView(old.overlay);
        });
        old.worker.execute(() -> {
            try {if(old.detector!=null)old.detector.close();} catch(Throwable ignored) {}
            old.worker.shutdown();
        });
    }
    // Overlay never intercepts touches: ordinary petting/buttons stay functional.
    // Drawing is UI-thread only; the ML thread publishes immutable coordinates.
    private static final class HandOverlay extends View {
        private static final int[][] CHAINS = {
            {0,1,2,3,4}, {0,5,6,7,8}, {0,9,10,11,12},
            {0,13,14,15,16}, {0,17,18,19,20}, {5,9,13,17}
        };
        private final Paint line = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint point = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint caption = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint panel = new Paint(Paint.ANTI_ALIAS_FLAG);
        private volatile float[] joints;
        private volatile long pointsAt;
        private volatile String state = "Hand model loading...";
        private final float scale;

        HandOverlay(Activity a) {
            super(a);
            scale = a.getResources().getDisplayMetrics().density;
            setClickable(false);
            setFocusable(false);
            line.setColor(Color.rgb(38, 249, 170));
            line.setStrokeWidth(2.5f * scale);
            line.setStyle(Paint.Style.STROKE);
            point.setColor(Color.rgb(255, 209, 71));
            point.setStyle(Paint.Style.FILL);
            caption.setColor(Color.WHITE);
            caption.setTextSize(13f * scale);
            panel.setColor(Color.argb(162, 20, 27, 34));
        }

        void publish(String status, float[] screenJoints, long atMs) {
            state = status;
            joints = screenJoints;
            pointsAt = atMs;
            postInvalidate();
        }

        @Override protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            HushLiveHandTracker tracker = instance;
            if (tracker == null || !tracker.enabled || tracker.disposed) return;
            float[] positions = joints;
            // Draw only fresh, genuine tracked positions; no fake skeleton.
            if (tracker.showSkeleton && positions != null && positions.length == 42 &&
                SystemClock.uptimeMillis() - pointsAt < 650) {
                for (int[] chain : CHAINS) {
                    for (int i=1; i<chain.length; i++) {
                        int a=2*chain[i-1], b=2*chain[i];
                        canvas.drawLine(positions[a], positions[a+1],
                            positions[b], positions[b+1], line);
                    }
                }
                for (int i=0; i<21; i++)
                    canvas.drawCircle(positions[2*i], positions[2*i+1], 3.5f*scale, point);
            }
            // Advanced diagnostic captions are visible with the skeleton; errors remain visible.
            if (!tracker.showSkeleton && tracker.handStatus != 4) return;
            // Put a small status strip near the bottom, above the main controls.
            float x=12*scale, y=getHeight()-155*scale;
            if (y < 60*scale) y=60*scale;
            float textW=caption.measureText(state);
            canvas.drawRoundRect(x, y-24*scale, x+Math.min(getWidth()-2*x, textW+20*scale),
                y+8*scale, 9*scale, 9*scale, panel);
            canvas.drawText(state, x+10*scale, y-2*scale, caption);
        }
    }

    private static final class Sample {
        final float[] points; final long t; final boolean hand;
        Sample(float[] p,long at,boolean h){points=p;t=at;hand=h;}
    }
    private static final class RawFrame {
        final int w,h,yRow,yPixel,uRow,uPixel,vRow,vPixel;
        final byte[] Y,U,V;final float[] m;final long t;
        RawFrame(int width,int height,float[] map,byte[] y,int ys,int yp,byte[] u,int us,int up,
            byte[] v,int vs,int vp,long when){
            w=width;h=height;m=map;Y=y;yRow=ys;yPixel=yp;U=u;uRow=us;uPixel=up;
            V=v;vRow=vs;vPixel=vp;t=when;
        }
    }
}
