# Hush Hunt v3.8.9 (build 53)

## Fixes
- Changed the remaining visible **FieldDex** actions and labels to **Collection** in the real-world discovery flow.
- Improved variety tiles so each subtype now has a clearer visual identity using an in-tile accent tint and subtype badge, instead of relying only on the small numbered colour chip baked into the artwork.
- Relaxed the **ARCore** availability gate so the ARCore mode is enabled whenever the Android app bridge is present, rather than requiring the later `whiskerNativeReady` flag before the button can be tapped.
- Updated AR Safari wording from cat-specific copy to more generic creature wording where appropriate.

## Notes
- The variety-art improvement in this build is a UI-driven first pass. It makes each subtype easier to distinguish immediately in the picker. A future pass can replace more of the underlying illustrations with fully bespoke per-variety artwork.
