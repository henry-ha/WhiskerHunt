# Whisker Hunt v3.1 changelog

## New in 3.1
- **AR Safari performance pass:** reduced AR camera resolution/FPS for smoother playback, lighter startup analysis, and lower-latency preview text so the live AR view should feel less laggy.
- **120 collectible cats:** the virtual roster now expands to **120 cats** generated across many breeds and coat mixes. The experience remains mission-based — you discover cats by catching them, not by manually picking them.
- **More detailed cat art:** AR cats now render with richer SVG detail including improved fur/body shading, eyes, whiskers, fluff variations, and better composition in the saved AR photo.
- **Habitat system:** AR Safari now places cats in themed encounter habitats such as **Window perch**, **Bookshelf nook**, **Kitchen chair**, **Desk corner**, **Garden path**, and more. The game prioritises unseen habitats first.
- **Habitat progress tracking:** the Virtual Friends gallery now shows both total cats discovered and habitats visited.
- **Saved habitat metadata:** virtual catches store their habitat on the sighting record and keep it through backup/restore.
- **Improved AR photo composites:** saved virtual photos now use a larger canvas, include the real captured camera frame, a stronger shadow/flooring effect, and a habitat label badge.

## Existing features retained from v3.0
- Name and memory dice for real and virtual cats.
- Multi-photo review workflow for normal camera capture.
- Optional rounded private map pins.
- Full backup and GPS-free backup export.

## Notes / limitations
- AR Safari is still a **screen-space overlay**, not world-anchored ARCore surface tracking.
- Cat art is more detailed but still based on a reusable illustrated system rather than 120 hand-modelled 3D assets.
- Android device performance still needs real-device verification outside this environment.
