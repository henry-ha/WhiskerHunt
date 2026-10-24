# v3.10.23 · Source inspection checklist

- [x] Web JavaScript parses with Node.js
- [x] Android and browser main JS/CSS mirrored
- [x] New index / launch points to v86 source
- [x] Camera returns new event and handles cancellation without external picker
- [x] ARCore only uses actual anchored placement; 2D Safari remains separate
- [x] Existing app ID and collection persistence code unchanged
- [x] ZIPs validated after packaging
- [ ] Android MAUI compilation (dotnet Android SDK unavailable in this environment)
- [ ] OnePlus 11 ultrawide camera exposed by native APIs and real field of view checked
- [ ] Live camera restart following cancelled wide capture on device
- [ ] ARCore native anchored placement tested on a physical phone
