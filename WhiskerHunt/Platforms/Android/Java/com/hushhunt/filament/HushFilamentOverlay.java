package com.hushhunt.filament;

import android.app.Activity;
import android.graphics.PixelFormat;
import android.graphics.Bitmap;
import android.opengl.Matrix;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.Choreographer;
import android.view.Surface;
import android.view.SurfaceView;
import android.view.SurfaceHolder;
import android.widget.FrameLayout;

import com.google.android.filament.Box;
import com.google.android.filament.Camera;
import com.google.android.filament.Engine;
import com.google.android.filament.EntityManager;
import com.google.android.filament.Filament;
import com.google.android.filament.LightManager;
import com.google.android.filament.IndirectLight;
import com.google.android.filament.Texture;
import com.google.android.filament.PixelBufferDescriptor;
import com.google.android.filament.Renderer;
import com.google.android.filament.Scene;
import com.google.android.filament.SwapChain;
import com.google.android.filament.TransformManager;
import com.google.android.filament.View;
import com.google.android.filament.Viewport;
import com.google.android.filament.gltfio.AssetLoader;
import com.google.android.filament.gltfio.Animator;
import com.google.android.filament.gltfio.FilamentAsset;
import com.google.android.filament.gltfio.Gltfio;
import com.google.android.filament.gltfio.ResourceLoader;
import com.google.android.filament.gltfio.UbershaderProvider;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.lang.reflect.Method;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;

/**
 * Filament PBR animal overlay for Hush Hunt's existing ARCore camera session.
 * In particular, this DOES NOT start another camera / ARCore session. The C#
 * camera-background renderer supplies the view and projection matrices and
 * optional Environmental HDR light estimates. All Filament resources live on
 * the Android main thread; the ARCore thread only publishes immutable frames.
 *
 * Note: Filament is not magically photorealistic: it respects whichever GLB
 * meshes, materials and normal maps have actually been installed.
 */
// HUSH_B99_POSESYNC_V5_20261028
public final class HushFilamentOverlay implements SurfaceHolder.Callback,
        Choreographer.FrameCallback {
    private static final String TAG = "HushFilament";
    private static volatile HushFilamentOverlay instance;
    // Last non-native diagnostic. A native SIGABRT cannot be handled in Java,
    // so stage markers in Logcat are essential for identifying its cause.
    private static volatile String lastStage = "not started";
    private final Activity activity;
    private final FrameLayout container;
    private final SurfaceView surfaceView;
    private final String assetName;
    private final float targetSize;
    // HUSH_31056_SHARED_PBR_ONLY: all GLB materials are supplied directly by gltfio, with one shared scene light/exposure profile.
    // No per-species emissive/metallic/brightness adjustments.
    private final Object snapshotLock = new Object();
    private final Handler main = new Handler(Looper.getMainLooper());
    private boolean destroyed;
    private volatile boolean modelReady;
    private volatile boolean hasPresentedAnimalFrame;
    private volatile float orientationYaw, orientationPitch;
    private boolean frameScheduled;
    private volatile boolean visibleAnimalPixels;
    private long lastPixelValidationNanos;
    private int pixelReadbackAttempts;
    private long lastRenderedNanos;
    // Draw the animal only against an actual ARCore camera update. This avoids
    // rendering a stale pose in a second TextureView while the background moves.
    private long frameGeneration;
    private long renderedGeneration;
    // v3.10.39: cap the second GPU render pass to ~30fps for dense GLBs.
    // ARCore camera and tracking continue at full speed on their GL thread.
    private long frameBudgetNanos = 33_000_000L;
    // HUSH_31040_SCALE_BUFFER_HOTFIX: calibrate the 28 Meshy centimeter-rig animals.
    // 0.01x in v3.10.39 was visibly too small; 0.08x is a TEST calibration,
    // not a claim of real-world metric size. Does not affect static GLBs.
    private static final float MESHY_ANIMATED_SIZE_FACTOR = 0.08f;
    // Render ONLY the Filament animal overlay at 72% per dimension.
    // ARCore camera background and tracking retain their full resolution.
    private static final float FILAMENT_BUFFER_FACTOR = 0.65f;
    private boolean overlayBufferConfigured;
    private int packagedGlbBytes;
    private int unsuccessfulPixelChecks;
    private boolean textureVisibilityWarned;

    private Engine engine;
    private Renderer renderer;
    private Scene scene;
    private View view;
    private Camera camera;
    private SwapChain swapChain;
    private Surface surface;
    private AssetLoader loader;
    private UbershaderProvider materialProvider;
    private ResourceLoader resourceLoader;
    private FilamentAsset asset;
    private Animator animator;
    private int cameraEntity;
    private int sunEntity;
    private IndirectLight ambientLight;
    private Texture reflectionCubemap;
    private ByteBuffer[] reflectionUploadBuffers;
    private volatile float[] ambientCoefficients;
    private long lastAmbientUpdate;
    private int lightReadFrameCounter;
    private final float[] worldScratch = new float[16];
    private final float[] lastProjection = new float[16];
    private long lastLightNanos;
    private float[] viewSnapshot;
    private float[] projectionSnapshot;
    private float[] anchorSnapshot;
    // ARCore returns direction TOWARDS the light. Filament expects the ray
    // travel direction, so negate these coordinates before setting the lamp.
    private float[] lightDirection = new float[] { -0.35f, 1f, 0.4f };
    private float[] lightIntensity = new float[] { 1f, 1f, 1f };
    private float animalScale = 1f;
    private float unitScale = 1f;
    private float centreX, centreY, centreZ, bottomY;
    // HUSH_31041_ANIMATION_LIGHT_GPU: pick named idle/walk clips and keep time advancing.
    // HUSH_31043_STEADY_ANIMATION: ensure animations advance while a camera pose is unchanged.
    private long animationStartNanos;
    private long lastLongFrameLogNanos;
    private int idleClip = -1, walkClip = -1, currentClip = -1;
    private int animationClipCount;
    private long perfStartNanos;
    private int perfFrames;
    private volatile boolean isWalking;
    // Filament render calls are confined to the Android UI / Choreographer thread.
    // Scratch arrays are not shared with the ARCore camera thread; these reduce
    // 60 Hz allocations that can trigger GC stalls on mobile.
    private final float[] cameraWorldScratch = new float[16];
    private final double[] projectionScratch = new double[16];
    private final float[] modelWorldScratch = new float[16];

    // HUSH_PET_REACTION_B99_V1: tap/stroke feedback for models with no baked animation.
    // Written by the UI thread and read by Filament's Choreographer thread.
    private volatile long petReactionStartedMs;
    private volatile boolean petReactionIsStroke;
    // HUSH_31060_PET_HUD_VARIETY: 6 root-motion styles, no new JNI entrypoint.
    private volatile int petReactionStyle = 1;
    private final float[] petPoseScratch = new float[7];
    private final int petSpeciesFlags;
    private int lastPetSignalSequence;


    // Meshy animated exports have a 0.01 Armature root and
    // ~100x inverse-bind scale. Their skin-deformed extent can exceed the
    // accessor-only AABB reported by FilamentAsset.getBoundingBox().
    // The remaining two skinned models (Red Panda and Turtle) use normal units.
    // This list is audited against the exact 88 GLBs supplied for v3.10.38.
    private static boolean hasMeshyCentimeterRig(String path) {
        switch (path) {
            case "wildlife/models/arctic_wolf.glb":
            case "wildlife/models/camel.glb":
            case "wildlife/models/capybara.glb":
            case "wildlife/models/celestial_deer.glb":
            case "wildlife/models/celestial_fox.glb":
            case "wildlife/models/chow_chow_dog.glb":
            case "wildlife/models/corgi.glb":
            case "wildlife/models/donkey.glb":
            case "wildlife/models/elephant.glb":
            case "wildlife/models/giraffe.glb":
            case "wildlife/models/golden_retriever.glb":
            case "wildlife/models/jack_russell_dog.glb":
            case "wildlife/models/jack_russell_terrier.glb":
            case "wildlife/models/labrador.glb":
            case "wildlife/models/lion.glb":
            case "wildlife/models/lion_alternate.glb":
            case "wildlife/models/pitbull_dog.glb":
            case "wildlife/models/ragdoll_cat_grey.glb":
            case "wildlife/models/rhinoceros.glb":
            case "wildlife/models/seal_baby.glb":
            case "wildlife/models/shiba_inu_dog.glb":
            case "wildlife/models/silverback_gorilla.glb":
            case "wildlife/models/snow_leopard.glb":
            case "wildlife/models/stag.glb":
            case "wildlife/models/tabby_cat.glb":
            case "wildlife/models/tuxedo_cat.glb":
            case "wildlife/models/wild_boar.glb":
            case "wildlife/models/wolf.glb":
                return true;
            default: return false;
        }
    }

    private HushFilamentOverlay(Activity activity, FrameLayout container, String assetName, float targetSize) {
        this.activity = activity;
        this.container = container;
        this.assetName = assetName;
        this.petSpeciesFlags = HushPetReactionMotion.classify(assetName);
        this.targetSize = targetSize;
        surfaceView = new SurfaceView(activity);
        // HUSH_B99_SURFACEVIEW_SILHOUETTE_AR_20261028
        // Transparent AR overlay above the ARCore camera surface.
        surfaceView.setZOrderMediaOverlay(true);
        surfaceView.getHolder().setFormat(PixelFormat.TRANSLUCENT);
        
        // Keep the GPU layer compositable from its first frame. An alpha=0
        // TextureView can be optimised out of hardware composition on some
        // Android 16 builds even after a later setAlpha(1).
        // We never render an animal until an ARCore world anchor exists.
        surfaceView.setAlpha(1f);
        surfaceView.setClickable(false);
        surfaceView.setFocusable(false);
        surfaceView.getHolder().addCallback(this);
        // Under the native UI controls, above the existing ARCore camera GLSurfaceView.
        // Allocate a lower-resolution transparent SurfaceView BUFFER, while
        // its on-screen View remains full-size and aligned with ARCore.
        // The Android hardware compositor scales this surface to its view.
        surfaceView.addOnLayoutChangeListener((v, left, top, right, bottom, ol, ot, or, ob) -> {
            int w = right - left, h = bottom - top;
            if (!overlayBufferConfigured && w >= 64 && h >= 64) {
                overlayBufferConfigured = true;
                int bw = Math.max(64, Math.round(w * FILAMENT_BUFFER_FACTOR));
                int bh = Math.max(64, Math.round(h * FILAMENT_BUFFER_FACTOR));
                surfaceView.getHolder().setFixedSize(bw, bh);
                Log.i(TAG, "3D overlay buffer=" + bw + "x" + bh +
                    " fullView=" + w + "x" + h);
            }
        });
        container.addView(surfaceView, Math.min(1, container.getChildCount()),
            new FrameLayout.LayoutParams(-1, -1));
    }

    /** Install from MAUI. Any failure leaves the existing OpenGL renderer intact. */
    public static boolean install(Activity activity, FrameLayout container,
                                  String assetName, float targetSize) {
        try {
            if (instance != null) dispose();
            if (assetName == null || !assetName.matches("wildlife/models/[a-z0-9_]{1,80}\\.glb")) return false;
            try (InputStream check = activity.getAssets().open(assetName)) {
                if (check.read() < 0) return false;
            }
            instance = new HushFilamentOverlay(activity, container, assetName, targetSize);
            return true;
        } catch (Throwable t) {
            Log.e(TAG, "Filament overlay install failed; using legacy wildlife renderer", t);
            dispose();
            return false;
        }
    }

    /** True only AFTER the Filament GLB is loaded and the overlay swapchain is usable. */
    public static boolean isReady() {
        HushFilamentOverlay item = instance;
        return item != null && item.hasPresentedAnimalFrame && item.visibleAnimalPixels && item.modelReady && item.swapChain != null && !item.destroyed;
    }

    /** Rotate an already-placed model. Degrees; independent of ARCore's camera pose. */
    public static void setOrientation(float yaw, float pitch) {
        HushFilamentOverlay item = instance;
        if (item == null) return;
        item.orientationYaw = yaw;
        item.orientationPitch = Math.max(-65f, Math.min(65f, pitch));
    }

    /** Request a gentle in-world body reaction without moving the AR anchor. */
    public static void reactToPet(boolean isStroke) {
        HushFilamentOverlay item = instance;
        if (item == null || item.destroyed || !item.modelReady) return;
        item.petReactionIsStroke = isStroke;
        item.petReactionStyle = isStroke ? 2 : 1;
        item.petReactionStartedMs = android.os.SystemClock.uptimeMillis();
    }

    public static void configureEnvironmentalHdr(Object config) {
        if (config == null) return;
        try {
            Class<?> type = Class.forName("com.google.ar.core.Config$LightEstimationMode");
            @SuppressWarnings({"unchecked", "rawtypes"})
            Object hdr = Enum.valueOf((Class<? extends Enum>) type, "ENVIRONMENTAL_HDR");
            config.getClass().getMethod("setLightEstimationMode", type).invoke(config, hdr);
        } catch (Throwable t) {
            Log.w(TAG, "Environmental HDR unavailable; Filament will use neutral light", t);
        }
    }

    /** Called on ARCore GL thread each frame; no Filament GPU calls are made here. */
    public static void submitFrame(float[] view, float[] projection, float[] anchor,
                                   float scale, Object arFrame) {
        HushFilamentOverlay item = instance;
        if (item == null || item.destroyed || view == null || projection == null || anchor == null) return;
        // HUSH_PET_REACTION_B99_V2_FRAMESYNC: receive pet events in the same
        // established ARCore frame stream; NEVER use a second JNI call on tap.
        if (anchor.length >= 5) {
            int sequence = (int) anchor[3];
            if (sequence != 0 && sequence != item.lastPetSignalSequence) {
                item.lastPetSignalSequence = sequence;
                // HUSH_31060c_PACKED_PET_EVENT: style in upper bits, stroke in bit 0.
                int petBits = Math.max(0, (int)anchor[4]);
                item.petReactionStyle = Math.max(1, Math.min(6, petBits >> 1));
                item.petReactionIsStroke = (petBits & 1) != 0;
                item.petReactionStartedMs = android.os.SystemClock.uptimeMillis();
                Log.i(TAG, "Pet reaction via AR frame, stroke=" + item.petReactionIsStroke);
            }
        }
        item.isWalking = anchor.length > 5 && anchor[5] > 0.5f;
        synchronized (item.snapshotLock) {
            // JNI.NewArray creates fresh Java arrays for each ARCore frame.
            // Retain their immutable references; cloning them again allocated
            // three extra arrays every frame and induced GC pauses.
            item.viewSnapshot = view;
            item.projectionSnapshot = projection;
            item.anchorSnapshot = anchor;
            item.animalScale = Math.max(.5f, Math.min(3f, scale));
            item.frameGeneration++;
        }
        // Read the estimate while its ARCore Frame is still current.
        if (arFrame != null && (++item.lightReadFrameCounter % 20) == 0) {
            try {
                Object estimate = arFrame.getClass().getMethod("getLightEstimate").invoke(arFrame);
                String state = String.valueOf(estimate.getClass().getMethod("getState").invoke(estimate));
                if (state.equalsIgnoreCase("VALID")) {
                    float[] d = (float[]) estimate.getClass().getMethod("getEnvironmentalHdrMainLightDirection").invoke(estimate);
                    float[] i = (float[]) estimate.getClass().getMethod("getEnvironmentalHdrMainLightIntensity").invoke(estimate);
                    if (d.length >= 3 && i.length >= 3) {
                        synchronized (item.snapshotLock) {
                            item.lightDirection = d.clone();
                            item.lightIntensity = i.clone();
                        }
                    }
                    // 27-coefficient SH read intentionally omitted: the
                    // renderer uses a stable neutral fill, not these values.
                    // Avoid allocating unused arrays via reflection.
                }
            } catch (Throwable ignored) { /* ARCore binding may not expose HDR on all devices. */ }
        }
    }

    @Override public void surfaceCreated(SurfaceHolder holder) {
        int width = Math.max(1, surfaceView.getWidth()), height = Math.max(1, surfaceView.getHeight());
        try {
            stage("filament.init");
            Filament.init();
            stage("gltfio.init");
            Gltfio.init();
            stage("engine.create");
            engine = Engine.create();
            renderer = engine.createRenderer();
            scene = engine.createScene();
            cameraEntity = EntityManager.get().create();
            camera = engine.createCamera(cameraEntity);
            // Colour-fidelity correction (B99): the old f/4 at 1/80 s exposure
            // (EV100 ~10.3), combined with a 30,000 lux sun and 16,000 lux
            // ambient fill, badly clipped normal baseColor textures. f/8 at
            // 1/125 s (EV100 13) uses a physically compatible exposure for
            // daylight-strength lights. Avoid reintroducing a bright ISO.
            // HUSH_31042_COLOR_FRAME_COST: compensate for the reduced v3.10.41
            // key light without clipping bright fur by doubling the sun.
            // Keep baseColor textures and physically based material properties intact.
            // HUSH_31047_COLOR_SCALE: prior EV/exposure was calibrated for
            // bright daylight, making textured animals almost black indoors.
            // This is a modest exposure change, NOT a texture or material edit.
            // HUSH_31050_UNIFORM_EXPOSURE: one Filament exposure for every GLB.
            // No animal-specific overrides; original GLBs remain untouched.
            float safariAperture = 6.8f;
            camera.setExposure(safariAperture, 1f / 125f, 100f);
            Log.i(TAG, "HUSH_31050_EXPOSURE animal=" + assetName +
                " aperture=" + safariAperture + " shared=true");
            view = engine.createView();
            view.setScene(scene);
            view.setCamera(camera);
            view.setShadowType(View.ShadowType.PCF);
            view.setBlendMode(View.BlendMode.TRANSLUCENT);
            view.setPostProcessingEnabled(false); // AR camera is already post-processed.
            // Dynamic resolution is not relied upon: this View has post-processing
            // disabled for a transparent AR overlay. Its fixed SurfaceView
            // buffer already lowers the actual raster workload.
            Renderer.ClearOptions clear = renderer.getClearOptions();
            // Filament 1.77.3 exposes clear colour via setClearColor(...).
            clear.setClearColor(0.0, 0.0, 0.0, 0.0);
            clear.clear = true;
            renderer.setClearOptions(clear);
            stage("swapchain.create");
            surface = holder.getSurface();
            swapChain = engine.createSwapChain(surface);
            view.setViewport(new Viewport(0, 0, width, height));

            // HUSH_31055_LIT_STUDIO: one neutral key for every Filament wildlife GLB.
            // Stable indoor/outdoor appearance; original textures / PBR materials unchanged.
            sunEntity = EntityManager.get().create();
            new LightManager.Builder(LightManager.Type.DIRECTIONAL)
                .direction(.35f, -1f, -.4f)
                .intensity(17500f)
                .castShadows(true)
                .build(engine, sunEntity);
            scene.addEntity(sunEntity);
            // Modest PCF shadow resolution preserves mobile AR GPU time.
            // Preserve the engine's other default shadow-map values.
            try {
                LightManager lm = engine.getLightManager();
                int key = lm.getInstance(sunEntity);
                LightManager.ShadowOptions opts = lm.getShadowOptions(key);
                opts.setMapSize(512);
                lm.setShadowOptions(key, opts);
            } catch (Throwable shadowError) {
                Log.w(TAG, "HUSH_31055_LIT shadow map defaults retained", shadowError);
            }
            Log.i(TAG, "HUSH_31055_LIT_STUDIO default=lit keyLux=17500 shadow=PCF512 sharedExposure=true");
            // Conservative neutral fill: the old 16,000 lux ambient washed out
            // light fur. Keep the fill stable while honouring the source colour.
            ambientLight = new IndirectLight.Builder()
                .irradiance(1, new float[] { .9f, .9f, .9f })
                .intensity(9500f).build(engine);
            scene.setIndirectLight(ambientLight);
            installStudioReflections();

            stage("gltfio.loader.create");
            materialProvider = new UbershaderProvider(engine);
            loader = new AssetLoader(engine, materialProvider, EntityManager.get());
            resourceLoader = new ResourceLoader(engine);
            stage("asset.read:" + assetName);
            byte[] bytes = applyGlobalGltfMaterialPolicy(readAsset(assetName));
            packagedGlbBytes = bytes.length;
            // ARCore camera tracking stays full rate. Filament is a second GPU
            // pass with 100k-triangle/4K textured assets; cap only this pass.
            // The latest pose is sampled at render time, never queued.
            // Heavy textures/skinned meshes get additional GPU time for ARCore.
            // This is a load-management measure, NOT an asset simplification.
            // 41ms against a 60Hz display quantises to 3 VSync intervals (~20fps).
            // Use 33ms for both paths; Filament's beginFrame handles GPU backlog.
            frameBudgetNanos = 33_000_000L;
            Log.i(TAG, "HD GLB=" + assetName + " bytes=" + packagedGlbBytes +
                " frameBudgetNs=" + frameBudgetNanos);
            verifyGlbHeader(bytes);
            stage("asset.create:" + assetName + " (" + bytes.length + " bytes)");
            ByteBuffer bb = ByteBuffer.allocateDirect(bytes.length).order(ByteOrder.nativeOrder());
            bb.put(bytes); bb.flip();
            asset = loader.createAsset(bb);
            if (asset == null) throw new IllegalStateException("glTF asset parser returned null");
            stage("resources.load:" + assetName);
            resourceLoader.loadResources(asset);
            stage("resources.release:" + assetName);
            asset.releaseSourceData();
            scene.addEntities(asset.getEntities());
            // Imported GLB punctual lights can have uncontrolled lux/intensity,
            // causing white blowout or very harsh contrast. The app supplies
            // its own balanced environmental rig; do not add authored GLB lights.
            Log.i(TAG, "Ignoring imported GLB light entities=" + asset.getLightEntities().length);
            animator = asset.getInstance().getAnimator();
            animationClipCount = animator == null ? 0 : animator.getAnimationCount();
            // Prefer a real idle/breathing clip while stationary, and a walking
            // clip when travelling between AR anchors. Do not assume clip 0.
            for (int clip = 0; clip < animationClipCount; clip++) {
                String name = animator.getAnimationName(clip);
                String key = name == null ? "" : name.toLowerCase(java.util.Locale.ROOT);
                if (idleClip < 0 && (key.contains("idle") || key.contains("breath") ||
                        key.contains("rest") || key.contains("stand"))) idleClip = clip;
                if (walkClip < 0 && (key.contains("walk") || key.contains("run") ||
                        key.contains("trot") || key.contains("move") ||
                        key.contains("fly") || key.contains("flap"))) walkClip = clip;
                Log.i(TAG, "GLB animation #" + clip + " name='" + name +
                    "' duration=" + animator.getAnimationDuration(clip) + "s");
            }
            if (animationClipCount > 0) {
                if (walkClip < 0) walkClip = 0;
                if (idleClip < 0) idleClip = 0; // no idle clip: slow first clip instead of freezing
            } else {
                Log.i(TAG, "GLB has NO baked animation clips: " + assetName);
            }
            int visibleMeshes = asset.getRenderableEntities().length;
            if (visibleMeshes == 0) throw new IllegalStateException("GLB has no renderable geometry: " + assetName);
            Log.i(TAG, "GLB renderable entities=" + visibleMeshes + " name=" + assetName);
            // HUSH_31055_LIT_STUDIO: model surfaces both cast and receive self shadows.
            // Runs only on asset load, not on every render frame; protects animation FPS.
            try {
                com.google.android.filament.RenderableManager rm = engine.getRenderableManager();
                int shadowMeshes = 0;
                for (int entity : asset.getRenderableEntities()) {
                    int ri = rm.getInstance(entity);
                    if (ri == 0) continue;
                    rm.setCastShadows(ri, true);
                    rm.setReceiveShadows(ri, true);
                    shadowMeshes++;
                }
                Log.i(TAG, "HUSH_31055_LIT_STUDIO animal=" + assetName +
                    " shadowMeshes=" + shadowMeshes + " GLBUnchanged=true");
            } catch (Throwable t) {
                Log.w(TAG, "HUSH_31055_LIT_STUDIO self-shadow setup unavailable", t);
            }


            Box bounds = asset.getBoundingBox();
            float[] half = bounds.getHalfExtent();
            float[] center = bounds.getCenter();
            float max = Math.max(.001f, 2f * Math.max(half[0], Math.max(half[1], half[2])));
            // HUSH_31048_STUDIO_IBL: Elephant uses actual vertical extent for size.
            // All others retain existing max-axis normalization and rig correction.
            float referenceExtent = max;
            if ("wildlife/models/elephant.glb".equals(assetName)) {
                float verticalExtent = 2f * half[1];
                if (verticalExtent > .05f && Float.isFinite(verticalExtent)) {
                    referenceExtent = verticalExtent;
                }
            }
            unitScale = targetSize / referenceExtent;
            Log.i(TAG, "HUSH_31048_BOUNDS animal=" + assetName +
                " half=" + half[0] + "," + half[1] + "," + half[2] +
                " longest=" + max + " reference=" + referenceExtent +
                " targetMetres=" + targetSize + " unitScale=" + unitScale);
            // glTF accessor AABBs may omit skeletal deformation; apply an
            // empirically tuned per-rig factor without touching GLB bones.
            if (hasMeshyCentimeterRig(assetName)) unitScale *= MESHY_ANIMATED_SIZE_FACTOR;
            Log.i(TAG, "AR model scale: " + assetName + " bboxLongest=" + max +
                " targetMetres=" + targetSize + " normalizedScale=" + unitScale +
                " centimeterRig=" + hasMeshyCentimeterRig(assetName));
            centreX = center[0]; centreY = center[1]; centreZ = center[2];
            bottomY = center[1] - half[1];
            stage("model.ready:" + assetName);

            modelReady = true;
            hasPresentedAnimalFrame = false;
            visibleAnimalPixels = false;
            lastPixelValidationNanos = 0;
            lastRenderedNanos = 0;
            unsuccessfulPixelChecks = 0;
            scheduleFrame();
            Log.i(TAG, "Filament glTF ready: " + assetName + " with PBR materials");
        } catch (Throwable t) {
            Log.e(TAG, "Filament failed at " + lastStage + " for " + assetName +
                "; legacy renderer will remain active", t);
            modelReady = false;
            shutdownGpu();
            surfaceView.setVisibility(android.view.View.GONE);
        }
    }

    // HUSH_31048_STUDIO_IBL: neutral prefiltered reflection cubemap for metallic GLB surfaces.
    // Built OFFLINE (32px; 6 faces; 6 roughness mips); upload once, never per-frame.
    // Environment is a studio approximation, not the ARCore camera capture.
    private void installStudioReflections() {
        Texture cubemap = null;
        try {
            final int size = 32;
            final int levels = 6;
            cubemap = new Texture.Builder()
                .width(size).height(size).levels(levels)
                .sampler(Texture.Sampler.SAMPLER_CUBEMAP)
                .format(Texture.InternalFormat.RGBA16F).build(engine);
            reflectionUploadBuffers = new ByteBuffer[levels];
            try (InputStream input = activity.getAssets().open(
                    "wildlife/lighting/studio_ibl_32_linear_rgba32.bin")) {
                for (int mip = 0; mip < levels; ++mip) {
                    int edge = size >> mip;
                    int length = 6 * edge * edge * 4 * Float.BYTES;
                    ByteBuffer pixels = ByteBuffer.allocateDirect(length).order(ByteOrder.nativeOrder());
                    byte[] part = new byte[length];
                    int have = 0;
                    while (have < length) {
                        int count = input.read(part, have, length - have);
                        if (count < 0) throw new IllegalStateException("Truncated studio IBL level " + mip);
                        have += count;
                    }
                    pixels.put(part);
                    pixels.flip();
                    reflectionUploadBuffers[mip] = pixels;
                    cubemap.setImage(engine, mip, 0, 0, 0, edge, edge, 6,                        
                        new com.google.android.filament.Texture.PixelBufferDescriptor(
                            pixels,
                            Texture.Format.RGBA,
                            Texture.Type.FLOAT
                        ))
;
                }
                if (input.read() != -1) throw new IllegalStateException("Studio IBL unexpected trailing data");
            }
            // Keep the previously calibrated diffuse ambient energy; only add
            // roughness-dependent specular reflections, not an extra fill light.
            IndirectLight upgraded = new IndirectLight.Builder()
                .reflections(cubemap)
                .irradiance(1, new float[] { .9f, .9f, .9f })
                .intensity(9500f).build(engine);
            IndirectLight previous = ambientLight;
            scene.setIndirectLight(upgraded);
            ambientLight = upgraded;
            reflectionCubemap = cubemap;
            // From here the new IBL owns the cubemap. A failure while freeing
            // the previous diffuse-only light must NOT dispose the active map.
            if (previous != null) {
                try { engine.destroyIndirectLight(previous); }
                catch (Throwable cleanupError) {
                    Log.w(TAG, "Old ambient cleanup failed", cleanupError);
                }
            }
            Log.i(TAG, "HUSH_31048_IBL enabled: 32px studio reflections, 6 roughness mips");
        } catch (Throwable failure) {
            Log.w(TAG, "HUSH_31048_IBL failed; keeping previous ambient lighting", failure);
            // Avoid changing the already-working renderer if the device lacks
            // floating-point cubemaps. Resource ownership is balanced in cleanup.
            if (cubemap != null && cubemap != reflectionCubemap) {
                try { engine.destroyTexture(cubemap); } catch (Throwable ignored) { }
            }
            if (cubemap != reflectionCubemap) reflectionUploadBuffers = null;
        }
    }



    private void stage(String value) {
        lastStage = value;
        Log.i(TAG, "STAGE " + value);
    }

    // HUSH_31058_GLOBAL_PBR_PARITY
    // General material hygiene for every GLB, regardless of wildlife species.
    // A known glTF-export pattern uses one base-colour image as its full-strength
    // emissive source, omits metallicFactor and omits the metallic-roughness map.
    // In glTF, missing metallicFactor defaults to 1 (fully metallic), which can
    // make organic surfaces unexpectedly dark once duplicate emission is removed.
    // Correct the export pattern in an IN-MEMORY copy of the GLB only.
    private static byte[] applyGlobalGltfMaterialPolicy(byte[] glb) {
        try {
            if (glb == null || glb.length < 28) return glb;
            java.nio.ByteBuffer header = java.nio.ByteBuffer.wrap(glb)
                .order(java.nio.ByteOrder.LITTLE_ENDIAN);
            if (header.getInt(0) != 0x46546C67 || header.getInt(4) != 2 ||
                header.getInt(8) != glb.length || header.getInt(16) != 0x4E4F534A) return glb;
            int originalJsonLength = header.getInt(12);
            int followingChunks = 20 + originalJsonLength;
            if (originalJsonLength < 2 || followingChunks > glb.length) return glb;
            String json = new String(glb, 20, originalJsonLength,
                java.nio.charset.StandardCharsets.UTF_8);
            org.json.JSONObject doc = new org.json.JSONObject(json);
            org.json.JSONArray materials = doc.optJSONArray("materials");
            org.json.JSONArray textures = doc.optJSONArray("textures");
            if (materials == null || textures == null || materials.length() == 0) return glb;

            java.util.regex.Matcher materialKey = java.util.regex.Pattern
                .compile("\\\"materials\\\"\\s*:\\s*\\[").matcher(json);
            if (!materialKey.find()) return glb;
            int cursor = materialKey.end();
            java.util.ArrayList<int[]> edits = new java.util.ArrayList<>();
            java.util.ArrayList<String> values = new java.util.ArrayList<>();
            int emissionCorrected = 0, metallicCorrected = 0;
            for (int index = 0; index < materials.length(); index++) {
                while (cursor < json.length() &&
                    (Character.isWhitespace(json.charAt(cursor)) || json.charAt(cursor) == ',')) cursor++;
                if (cursor >= json.length() || json.charAt(cursor) != '{') return glb;
                int finish = findGltfJsonObjectEnd(json, cursor);
                if (finish < 0) return glb;
                org.json.JSONObject material = materials.optJSONObject(index);
                if (material != null) {
                    org.json.JSONObject pbr = material.optJSONObject("pbrMetallicRoughness");
                    org.json.JSONObject base = pbr == null ? null : pbr.optJSONObject("baseColorTexture");
                    org.json.JSONObject emission = material.optJSONObject("emissiveTexture");
                    org.json.JSONArray emissionFactor = material.optJSONArray("emissiveFactor");
                    if (base != null && emission != null && emissionFactor != null &&
                        emissionFactor.length() == 3) {
                        int bi = base.optInt("index", -1), ei = emission.optInt("index", -1);
                        if (bi >= 0 && ei >= 0 && bi < textures.length() && ei < textures.length()) {
                            org.json.JSONObject bt = textures.optJSONObject(bi);
                            org.json.JSONObject et = textures.optJSONObject(ei);
                            boolean sameSource = bt != null && et != null &&
                                bt.optInt("source", -1) >= 0 &&
                                bt.optInt("source", -1) == et.optInt("source", -2) &&
                                bt.optInt("sampler", -1) == et.optInt("sampler", -1);
                            boolean sameUv = base.optInt("texCoord", 0) == emission.optInt("texCoord", 0) &&
                                String.valueOf(base.optJSONObject("extensions"))
                                    .equals(String.valueOf(emission.optJSONObject("extensions")));
                            boolean active = false;
                            for (int ch = 0; ch < 3; ch++) {
                                active |= emissionFactor.optDouble(ch, 0) > 0;
                            }
                            if (sameSource && sameUv && active) {
                                java.util.regex.Matcher em = java.util.regex.Pattern.compile(
                                    "\\\"emissiveFactor\\\"\\s*:\\s*(\\[[^\\]]*\\])")
                                    .matcher(json);
                                em.region(cursor, finish + 1);
                                if (!em.find()) return glb;
                                edits.add(new int[]{em.start(1), em.end(1)});
                                values.add("[0,0,0]");
                                emissionCorrected++;

                                // Only the same duplicate-emission export pattern is eligible.
                                // Respect explicit metallic factors, roughness maps and all other GLBs.
                                if (!pbr.has("metallicFactor") &&
                                    !pbr.has("metallicRoughnessTexture") &&
                                    !material.has("KHR_materials_unlit") &&
                                    !(material.optJSONObject("extensions") != null &&
                                      material.optJSONObject("extensions").has("KHR_materials_unlit"))) {
                                    java.util.regex.Matcher pbrStart = java.util.regex.Pattern.compile(
                                        "\\\"pbrMetallicRoughness\\\"\\s*:\\s*\\{").matcher(json);
                                    pbrStart.region(cursor, finish + 1);
                                    if (!pbrStart.find()) return glb;
                                    int open = json.indexOf('{', pbrStart.start());
                                    int pbrEnd = findGltfJsonObjectEnd(json, open);
                                    if (pbrEnd < 0 || pbrEnd > finish + 1) return glb;
                                    // Add a missing property rather than changing original values.
                                    edits.add(new int[]{open + 1, open + 1});
                                    values.add("\"metallicFactor\":0,");
                                    metallicCorrected++;
                                }
                            }
                        }
                    }
                }
                cursor = finish + 1;
            }
            if (edits.isEmpty()) return glb;
            java.util.ArrayList<Integer> order = new java.util.ArrayList<>();
            for (int i = 0; i < edits.size(); i++) order.add(i);
            java.util.Collections.sort(order, (a, b) ->
                Integer.compare(edits.get(b)[0], edits.get(a)[0]));
            StringBuilder builder = new StringBuilder(json);
            for (int idx : order) {
                int[] bounds = edits.get(idx);
                builder.replace(bounds[0], bounds[1], values.get(idx));
            }
            byte[] content = builder.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8);
            int paddedJsonLength = (content.length + 3) & ~3;
            long totalSize = (long) glb.length + paddedJsonLength - originalJsonLength;
            if (totalSize > Integer.MAX_VALUE || totalSize < 28) return glb;
            byte[] fixed = new byte[(int) totalSize];
            java.nio.ByteBuffer dest = java.nio.ByteBuffer.wrap(fixed)
                .order(java.nio.ByteOrder.LITTLE_ENDIAN);
            dest.putInt(0x46546C67); // glTF magic
            dest.putInt(2);          // glTF version
            dest.putInt(fixed.length);
            dest.putInt(paddedJsonLength);
            dest.putInt(0x4E4F534A); // JSON chunk
            dest.put(content);
            for (int i = content.length; i < paddedJsonLength; i++) dest.put((byte) ' ');
            dest.put(glb, followingChunks, glb.length - followingChunks);
            Log.i(TAG, "Global GLB PBR parity: disabled " + emissionCorrected +
                " duplicated emission(s), corrected " + metallicCorrected +
                " implicit metal(s); original GLB retained");
            return fixed;
        } catch (Exception e) {
            Log.w(TAG, "Global GLB PBR parity skipped; using unchanged GLB", e);
            return glb;
        }
    }

    private static int findGltfJsonObjectEnd(String text, int start) {
        int depth = 0;
        boolean quoted = false, escaped = false;
        for (int i = start; i < text.length(); i++) {
            char c = text.charAt(i);
            if (quoted) {
                if (escaped) escaped = false;
                else if (c == '\\') escaped = true;
                else if (c == '"') quoted = false;
            } else if (c == '"') quoted = true;
            else if (c == '{') depth++;
            else if (c == '}' && --depth == 0) return i;
        }
        return -1;
    }

    private static void verifyGlbHeader(byte[] data) {
        if (data == null || data.length < 28)
            throw new IllegalArgumentException("Invalid glTF binary: too short");
        ByteBuffer header = ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN);
        if (header.getInt(0) != 0x46546C67 || header.getInt(4) != 2 ||
            header.getInt(8) != data.length || header.getInt(16) != 0x4E4F534A)
            throw new IllegalArgumentException("Invalid glTF binary container header");
        int jsonLength = header.getInt(12);
        if (jsonLength <= 0 || jsonLength > data.length - 20)
            throw new IllegalArgumentException("Invalid glTF binary JSON chunk length");
    }

    private byte[] readAsset(String path) throws Exception {
        try (InputStream in = activity.getAssets().open(path);
             ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[16384]; int n;
            while ((n = in.read(buffer)) != -1) {
                out.write(buffer, 0, n);
                // The former 24 MiB cap silently rejected Cat in Motion
                // (~31.3 MB) and the Jack Russell puppy (~38.9 MB).
                // Keep a finite bound for mobile safety, but admit both assets.
                if (out.size() > 64 * 1024 * 1024)
                    throw new IllegalStateException("GLB exceeds mobile 64 MiB safety limit: " + path);
            }
            return out.toByteArray();
        }
    }

    private void scheduleFrame() {
        if (!frameScheduled && !destroyed && modelReady) {
            frameScheduled = true;
            Choreographer.getInstance().postFrameCallback(this);
        }
    }
    @Override public void doFrame(long nanos) {
        frameScheduled = false;
        if (destroyed || !modelReady || swapChain == null) return;
        // At most 30 Filament GPU submissions/sec. The background ARCore layer
        // is still refreshed every frame; on rendering we use its newest camera
        // pose, so we do not queue / accumulate stale frames.
        if (lastRenderedNanos != 0L && nanos - lastRenderedNanos < frameBudgetNanos) {
            scheduleFrame();
            return;
        }
        try {
            float[] v, p, a, d, intensity;
            float scale;
            long generation;
            synchronized (snapshotLock) {
                v = viewSnapshot; p = projectionSnapshot; a = anchorSnapshot;
                d = lightDirection; intensity = lightIntensity; scale = animalScale;
                generation = frameGeneration;
            }
            if (v == null || p == null || a == null) {
                scheduleFrame();
                return;
            }
            // With a valid anchor, a skinned animal can continue playing its
            // clip even when ARCore hasn't delivered another camera pose yet.
            // Static assets still avoid wasteful redraws of identical poses.
            if (generation == renderedGeneration && animationClipCount == 0) {
                scheduleFrame();
                return;
            }
            
            if (v != null && p != null && a != null) {
                if (Matrix.invertM(cameraWorldScratch, 0, v, 0)) {
                    camera.setModelMatrix(cameraWorldScratch);
                    for (int i = 0; i < 16; i++) projectionScratch[i] = p[i];
                    camera.setCustomProjection(projectionScratch, .1, 80.0);
                    // Triggered from MAUI touch events. Root-space animation works
                    // even when a licensed Sketchfab GLB has zero animation clips.
                    // This is additive to manual yaw and never changes the AR anchor.
                    float[] pose = petPoseScratch; // reused scratch: no GC every 60 Hz.
                    HushPetReactionMotion.evaluate(petSpeciesFlags, petReactionStyle,
                        android.os.SystemClock.uptimeMillis() - petReactionStartedMs,
                        targetSize, petReactionIsStroke, pose);
                    float s = unitScale * scale;
                    float[] world = modelWorldScratch;
                    Matrix.setIdentityM(world, 0);
                    Matrix.translateM(world, 0, a[0] + pose[0], a[1] + pose[1], a[2] + pose[2]);
                    Matrix.rotateM(world, 0, orientationYaw + pose[3], 0f, 1f, 0f);
                    Matrix.rotateM(world, 0, pose[4], 0f, 0f, 1f);
                    Matrix.rotateM(world, 0, orientationPitch + pose[5], 1f, 0f, 0f);
                    Matrix.scaleM(world, 0, s * pose[6], s * pose[6], s * pose[6]);
                    Matrix.translateM(world, 0, -centreX, -bottomY, -centreZ);
                    TransformManager tm = engine.getTransformManager();
                    int instance = tm.getInstance(asset.getRoot());
                    tm.setTransform(instance, world);

                    // ARCore world-space environmental HDR directional estimate. PBR
                    // material response is handled by Filament, not a fake tint.
                    // Keep stable neutral ambient lighting until the ARCore SH
                    // coefficients have been validated and converted correctly.
                    // The previous code allocated an HDR environment every second,
                    // creating frame stalls and inverting contrast indoors.
                    // HUSH_31055_LIT_STUDIO: do not overwrite the fixed key direction
                    // or intensity from ARCore's sometimes extreme HDR estimates.
                    // ARCore still provides camera poses, projection, and anchors.
                }
            }
            if (animator != null && animationClipCount > 0) {
                // Previously idle animals were forced to animation time zero
                // EVERY frame, which made all characters appear frozen.
                int index = isWalking ? walkClip : idleClip;
                if (index != currentClip || animationStartNanos == 0L) {
                    currentClip = index;
                    animationStartNanos = nanos;
                }
                float duration = Math.max(.1f, animator.getAnimationDuration(index));
                // Most Meshy exports have exactly one 1-second baked clip.
                // The previous .40x speed made their motion appear to stop.
                float speed = 1f;
                float seconds = ((nanos - animationStartNanos) * 1e-9f * speed) % duration;
                animator.applyAnimation(index, seconds);
                animator.updateBoneMatrices();
            }
            // Never claim model readiness just because bytes parsed. The overlay
            // becomes visible only after the first anchored frame was submitted.
            if (v != null && p != null && a != null && renderer.beginFrame(swapChain, nanos)) {
                renderer.render(view);
                renderer.endFrame();
                renderedGeneration = generation;
                if (nanos - lastRenderedNanos > 180_000_000L &&
                    nanos - lastLongFrameLogNanos > 3_000_000_000L && lastRenderedNanos != 0L) {
                    lastLongFrameLogNanos = nanos;
                    Log.w(TAG, "AR_OVERLAY_STALL_MS=" +
                        ((nanos - lastRenderedNanos) / 1_000_000L) + " animal=" + assetName);
                }
                lastRenderedNanos = nanos;
                if (perfStartNanos == 0L) perfStartNanos = nanos;
                perfFrames++;
                if (nanos - perfStartNanos > 5_000_000_000L) {
                    float fps = perfFrames * 1_000_000_000f / (nanos - perfStartNanos);
                    Log.i(TAG, "AR_OVERLAY_FPS=" + fps + " animal=" + assetName +
                        " clip=" + currentClip + "/" + animationClipCount +
                        " walking=" + isWalking + " bytes=" + packagedGlbBytes);
                    perfFrames = 0; perfStartNanos = nanos;
                }
                if (!hasPresentedAnimalFrame) {
                    hasPresentedAnimalFrame = true;
                    Log.i(TAG, "First anchored GPU frame submitted: " + assetName);
                }
                // A submitted GPU frame is NOT evidence that the GLB is
                // actually visible. Verify there are lit, non-transparent
                // pixels before hiding the reliable legacy renderer.
                // Asynchronous PixelCopy validates the real SurfaceView image.
                // Stop sampling once the HD animal is visibly rendered.
                if (!visibleAnimalPixels && pixelReadbackAttempts < 6 && nanos - lastPixelValidationNanos > 1_200_000_000L) {
                    lastPixelValidationNanos = nanos;
                    pixelReadbackAttempts++;
                    inspectVisibleAnimalPixels();
                }
            }
        } catch (Throwable t) {
            Log.e(TAG, "Filament render failed; restoring legacy model", t);
            modelReady = false;
            hasPresentedAnimalFrame = false;
            surfaceView.setVisibility(android.view.View.GONE);
        }
        scheduleFrame();
    }

    // HUSH_B99_SURFACEVIEW_PIXELCOPY_HOTFIX_20261028: SurfaceView has no getBitmap(). Copy asynchronously instead.
    private boolean pixelCopyInFlight;
    private void inspectVisibleAnimalPixels() {
        if (pixelCopyInFlight || destroyed || !modelReady ||
            !surfaceView.getHolder().getSurface().isValid()) return;
        pixelCopyInFlight = true;
        Bitmap created = null;
        try {
            // PixelCopy scales the SurfaceView image into this small destination.
            created = Bitmap.createBitmap(96, 96, Bitmap.Config.ARGB_8888);
            final Bitmap sample = created;
            android.view.PixelCopy.request(surfaceView, sample, result -> {
                pixelCopyInFlight = false;
                if (result != android.view.PixelCopy.SUCCESS || destroyed ||
                    !modelReady || asset == null) {
                    sample.recycle();
                    return;
                }
                inspectCopiedAnimalPixels(sample);
            }, main);
        } catch (Throwable t) {
            pixelCopyInFlight = false;
            if (created != null && !created.isRecycled()) created.recycle();
            Log.w(TAG, "PixelCopy visibility request failed: " + t.getMessage());
        }
    }

    private void inspectCopiedAnimalPixels(Bitmap frame) {
        try {
            if (frame == null) return;
            int[] pixels = new int[96 * 96];
            frame.getPixels(pixels, 0, 96, 0, 0, 96, 96);
            int lit = 0;
            int opaque = 0;
            for (int color : pixels) {
                int alpha = color >>> 24;
                if (alpha < 48) continue;
                opaque++;
                int brightness = Math.max((color >>> 16) & 255,
                    Math.max((color >>> 8) & 255, color & 255));
                if (brightness >= 13) lit++;
            }
            // Ignore a totally opaque clear buffer or completely black model.
            boolean visible = lit >= 3 && opaque < pixels.length * .7f;
            visibleAnimalPixels = visible;
            if (!visible) {
                unsuccessfulPixelChecks++;
                if (unsuccessfulPixelChecks == 3 || unsuccessfulPixelChecks == 8)
                    Log.w(TAG, "No visible lit animal pixels: " + assetName +
                        " nontransparent=" + opaque + " lit=" + lit +
                        " modelEntities=" + asset.getRenderableEntities().length);
            } else {
                if (!textureVisibilityWarned)
                    Log.i(TAG, "VERIFIED visible Filament animal pixels: " + assetName +
                        " lit=" + lit + " nontransparent=" + opaque);
                textureVisibilityWarned = true;
                unsuccessfulPixelChecks = 0;
            }
        } catch (Throwable t) {
            Log.w(TAG, "GPU frame visibility check unavailable: " + t.getMessage());
        } finally {
            if (frame != null) frame.recycle();
        }
    }

    @Override public void surfaceChanged(SurfaceHolder holder, int format, int w, int h) {
        if (view != null) view.setViewport(new Viewport(0, 0, w, h));
    }
    @Override public void surfaceDestroyed(SurfaceHolder holder) {
        shutdownGpu();
    }

    public static void dispose() {
        HushFilamentOverlay item = instance; instance = null;
        if (item == null) return;
        if (Looper.myLooper() != Looper.getMainLooper()) {
            item.main.post(item::doDispose);
        } else item.doDispose();
    }
    private void doDispose() {
        destroyed = true;
        if (frameScheduled) Choreographer.getInstance().removeFrameCallback(this);
        frameScheduled = false;
        shutdownGpu();
        if (surfaceView.getParent() == container) container.removeView(surfaceView);
    }
    private void shutdownGpu() {
        modelReady = false;
        hasPresentedAnimalFrame = false;
        visibleAnimalPixels = false;
        try {
            if (engine == null) return;
            if (asset != null && scene != null) {
                scene.removeEntities(asset.getEntities());
                scene.removeEntities(asset.getLightEntities());
                loader.destroyAsset(asset); asset = null;
            }
            if (resourceLoader != null) { resourceLoader.destroy(); resourceLoader = null; }
            if (loader != null) { loader.destroy(); loader = null; }
            if (materialProvider != null) {
                materialProvider.destroyMaterials();
                materialProvider.destroy(); materialProvider = null;
            }
            if (scene != null && ambientLight != null) scene.setIndirectLight(null);
            if (ambientLight != null) { engine.destroyIndirectLight(ambientLight); ambientLight = null; }
            if (reflectionCubemap != null) {
                engine.destroyTexture(reflectionCubemap);
                reflectionCubemap = null;
            }
            reflectionUploadBuffers = null;
            if (scene != null && sunEntity != 0) scene.remove(sunEntity);
            if (sunEntity != 0) { engine.destroyEntity(sunEntity); EntityManager.get().destroy(sunEntity); sunEntity = 0; }
            if (cameraEntity != 0) { engine.destroyCameraComponent(cameraEntity); EntityManager.get().destroy(cameraEntity); cameraEntity = 0; }
            if (swapChain != null) { engine.destroySwapChain(swapChain); swapChain = null; }
            if (view != null) { engine.destroyView(view); view = null; }
            if (scene != null) { engine.destroyScene(scene); scene = null; }
            if (renderer != null) { engine.destroyRenderer(renderer); renderer = null; }
            engine.destroy(); engine = null;
            // SurfaceHolder owns its Surface; do not release it here.
            surface = null;
        } catch (Throwable t) { Log.w(TAG, "Filament cleanup", t); }
    }
}
