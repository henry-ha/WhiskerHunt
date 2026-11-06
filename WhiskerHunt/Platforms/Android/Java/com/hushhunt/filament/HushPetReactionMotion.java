package com.hushhunt.filament;

/**
 * Hush Hunt 3D Safari: low-allocation, whole-body reaction poses for animals whose
 * GLB has no pet-specific skeletal clips.  The original glTF animation (if any)
 * continues to play in the renderer.  This only animates the asset root transform;
 * it never modifies textures, material colours or the anchored position.
 */
public final class HushPetReactionMotion {
    private HushPetReactionMotion() {}
    public static final int NOD = 1, HOP = 2, LEAN = 3,
                            FLUTTER = 4, SHY = 5, GREET = 6;
    public static final long DURATION_MS = 1150L;
    public static final int FLYING = 1, GENTLE = 2, PLAYFUL = 4;
    // Output: [translation x, y, z in metres; yaw, roll, pitch in degrees; scale]
    public static void evaluate(int speciesFlags, int style, long elapsedMs,
                                float targetSize, boolean stroke, float[] out) {
        if (out == null || out.length < 7) return;
        for (int i = 0; i < 6; i++) out[i] = 0f;
        out[6] = 1f;
        if (elapsedMs < 0L || elapsedMs >= DURATION_MS) return;
        boolean flying = (speciesFlags & FLYING) != 0;
        boolean gentle = (speciesFlags & GENTLE) != 0;
        boolean playful = (speciesFlags & PLAYFUL) != 0;
        // A bird doesn't 'hop' as if it were a dog. Heavier creatures should
        // respond more subtly; never fake limb articulation for unrigged assets.
        if (flying && (style == HOP || style == LEAN)) style = FLUTTER;
        if (gentle && style == HOP) style = NOD;
        float p = Math.max(0f, Math.min(1f, elapsedMs / (float) DURATION_MS));
        float envelope = (float)Math.sin(Math.PI * p);
        envelope = Math.max(0f, envelope);
        float size = Math.max(.12f, Math.min(1.8f, targetSize));
        float energy = (stroke ? 1.12f : .88f) * (gentle ? .55f : (playful ? 1.15f : 1f));
        switch (style) {
            case HOP: // cheerful bounce: two distinct lift peaks, squash and settle
                float lift = (float)Math.pow(Math.sin(Math.PI * p * 2.0), 2);
                out[1] = size * .06f * energy * lift * (1f - .4f*p);
                out[5] = -3.5f * envelope * energy;
                out[6] = 1f + .035f * energy * (float)Math.sin(Math.PI * p * 4.0) * envelope;
                break;
            case LEAN: // gentle sideways lean with a return to upright
                out[0] = size * .027f * energy * envelope;
                out[4] = -9f * energy * envelope;
                out[3] = 4.5f * energy * envelope;
                break;
            case FLUTTER: // short airy flutter, NOT a claim of rigged wing flaps
                float flutter = (float)Math.sin(Math.PI * p * 7.0);
                out[1] = size * .024f * energy * envelope;
                out[4] = 6.5f * energy * envelope * flutter;
                out[5] = 4.5f * energy * envelope * flutter;
                out[6] = 1f + .012f * envelope;
                break;
            case SHY: // shy recoil and approach, suitable for cautious wildlife
                out[2] = size * .033f * energy * envelope;
                out[5] = 8f * energy * envelope;
                out[3] = -4.5f * energy * envelope;
                break;
            case GREET: // turn to acknowledge the person's hand, then return
                out[3] = 18f * energy * envelope;
                out[4] = 2f * energy * envelope;
                out[5] = -3f * energy * envelope;
                break;
            case NOD:
            default: // friendly nod plus a tiny rise
                out[5] = 11f * energy * envelope * (float)Math.sin(Math.PI * p * 3.0);
                out[1] = size * .011f * energy * envelope;
                break;
        }
        // Defensive guard: no NaNs or negative scales enter Filament JNI.
        for (int i=0; i<7; i++) {
            if (!Float.isFinite(out[i])) out[i] = (i == 6 ? 1f : 0f);
        }
        out[6] = Math.max(.94f, Math.min(1.07f, out[6]));
    }
    /** One-time classification when loading a GLB, not a per-frame string allocation. */
    public static int classify(String assetName) {
        if (assetName == null) return 0;
        // The renderer already validates lowercase-only asset filenames.
        int flags = 0;
        if (assetName.contains("bat") || assetName.contains("bird") ||
            assetName.contains("butterfly") || assetName.contains("bee") ||
            assetName.contains("dragonfly") || assetName.contains("phoenix") ||
            assetName.contains("eagle") || assetName.contains("owl")) flags |= FLYING;
        if (assetName.contains("deer") || assetName.contains("tortoise") ||
            assetName.contains("turtle") || assetName.contains("snail") ||
            assetName.contains("hedgehog") || assetName.contains("elephant") ||
            assetName.contains("giraffe")) flags |= GENTLE;
        if (assetName.contains("dog") || assetName.contains("puppy") ||
            assetName.contains("rabbit") || assetName.contains("hare") ||
            assetName.contains("squirrel") || assetName.contains("mouse") ||
            assetName.contains("kangaroo")) flags |= PLAYFUL;
        return flags;
    }
}
