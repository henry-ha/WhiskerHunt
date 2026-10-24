# Hush Hunt 3.10.11 — Build 74

## New home-screen themes
- Six bundled, offline wildlife scenes: Purple Fox Twilight, Blue Morpho Garden, Mountain Deer, Robin Woodland, Moonlit Owl and Butterfly Meadow.
- **Dynamic by default**: each new app launch rotates to a different theme; normal screen navigation does not shuffle it.
- **Static mode**: select and retain one scene via the Home gear or Explorer Profile settings.
- Optional subtle animation (off by default and respects Reduced Motion).
- Theme scenes extend behind the primary Live Capture / AR Safari buttons; colors and contrast are coordinated.
- Themes are locally created illustrations/composites, not documentary wildlife photography.

## Live Capture
- Clean, full-camera preview inside reserved Android status/navigation safe areas.
- Zoom buttons and existing pinch gestures retained from 3.10.10; native 0.6× still requires a truly wider lens.
- Quick shutter remains prominent, and older collection game controls are hidden behind an optional **Game** toggle.
- Removes intrusive Discovery Token / Focus Lens status copy from the main capture screen.

## Capture result and identification
- Unidentified live captures start as **Mystery discovery**, not automatically as Cat.
- Species selection and guide remain available to the explorer; **no unvalidated automated AI identification claim**.
- The only unmatched-species choice is now **Other** (instead of duplicated Other Frog / Not sure / My own description options).
- The full-screen guide also offers an Other choice.
- Existing collection records are preserved, including previously recorded Not sure values.
- “⇄ Change animal” stays on a single line and uses an understandable replacement icon.

## Artwork
- New field_art_v74 replaces remaining frog tiles with clean, caption-free squares.
- Added new neutral magnifier artwork for **Other**, without embedded labels.

## Native ARCore
- Place no longer remains disabled when no plane is found. It tries anchored plane placement first.
- When no plane is tracked, shows a clearly labeled **screen-locked preview** so the user can still reposition/capture the creature.
- Preview capture is explicitly **not world-anchored tracking**; genuine ARCore plane anchoring still needs adequate tracking conditions.
- Kept separate 2D Safari fallback.

## Version and preservation
- MAUI Android application ID remains `uk.whiskerhunt.mobile`; database schema and installed collection are unchanged.
- Android launch `MainPage.xaml → index_v74.html → app_v74.js + style_v74.css`.
- Display version 3.10.11, build 74; browser and Android assets matched.

## Limits / still to test on device
- No Android SDK / dotnet compilation available in this environment; source-level checks only.
- Local headless browser could not navigate due environment restrictions.
- Validate status bar/nav safe areas, native ARCore preview, pinches and 0.6× lens on a physical phone.
- Automated species recognition would require a suitable offline classifier; this build does not fabricate a model confidence score.
