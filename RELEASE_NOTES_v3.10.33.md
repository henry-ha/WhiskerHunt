# Hush Hunt v3.10.33 · Build 96 — AR Safari Petting Interaction v1

## Implemented

- **Tap-to-pet** works only when you tap the actual projected 3D animal, after ARCore placement/render confirmation.
- **Stroke-to-pet:** begin a one-finger gesture over an animal; a stroke of at least 30dp triggers a pet. No extra pet button.
- **Pet reactions:** the static GLB model gently bounces, sways, and pulses for ~0.85 seconds; a small 💚 feedback badge appears. These are whole-model animations, not species-specific skeletal animations.
- **Preserves controls:** two fingers still resize the model; empty-space taps still reposition the animal. Camera capture is unchanged.
- **Simple guidance:** once the model is visible, the status reads "Stroke to pet 💚".
- **Species compatibility:** works with whichever exact static GLB model is bundled locally. No new animal assets are necessary.
- Updated Android package display version to **3.10.33** and build number to **96**.

## Important limitations and validation

- **Real-world hand-over-animal occlusion is NOT included** in this source version. Showing a physical hand *in front of* the animal requires per-pixel ARCore Depth capture, display UV alignment, and an occlusion shader. No such behaviour is claimed or simulated here.
- **Camera-based hand tracking is NOT included**. The interaction is a finger touch/stroke on the phone's touchscreen.
- Animated GLB skeletal joints, anatomically realistic responses, and sound effects are not implemented; the existing static model renderer is preserved.
- These source changes were checked statically. This environment lacks the .NET Android SDK, so **an Android compile or device test could not be performed**. Verify the result on your phone before distributing a release.

## Preserve your animal models and saved collection

- The included source project has 5 starter GLBs. If your existing project has the 21 imported GLBs, **apply the small patch ZIP** on top of that project rather than replacing the complete folder. No animal assets need to be deleted.
- Do **not** uninstall Hush Hunt or change the Android signing key when deploying, or you may lose saved discoveries.

## Device QA checklist

1. Place a supported GLB in ARCore; confirm photo button enables only after rendering.
2. Tap the animal: look for green pet feedback and a gentle pulse/sway.
3. Stroke across the animal: check that the reaction occurs once, not on unrelated background touches.
4. Pinch with two fingers: 3D model grows/shrinks without triggering a pet.
5. Tap the floor away from the animal: the **Move** / placement behaviour still works.
6. Capture the animal; confirm the normal collection flow still works and no records are lost.
7. Close/resume AR Safari; verify no stale hitbox after tracking is lost.
