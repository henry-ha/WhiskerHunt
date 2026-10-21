# Whisker Hunt v3.8.1 · Build 45

## New: live-only real-world wildlife discoveries

- New real-world FieldDex catches must originate from a live camera encounter in Whisker Hunt.
- The capture chooser now offers **Spot real wildlife** and **AR Safari**. The normal-camera and gallery-import catch actions were removed.
- Once the live camera is running, users can drag the Whisker Paw or switch to the Dangle Lure, then choose the clearest of a few recent **live frames** and identify the species manually.
- New real-world saves check that the selected still belongs to the recent live session, rather than a gallery import. The gate is about in-app camera provenance; it is **not** computer-vision animal verification or tamper-proof evidence.
- **Retake live** restarts the live camera. The former **Choose another** gallery button is removed from real encounters.
- If live access fails, users can retry or browse FieldDex. The app no longer falls back to importing a photo as a new discovery.
- Existing real and virtual collections, photos, map pins, XP, backup/restore and the v1 JSON backup schema remain compatible. The virtual AR Safari continues working separately.

## Notes

- Photos imported and saved in earlier versions still display correctly; the change applies to **new** real-world catches.
- Imported JSON backups remain supported for recovery. Backup restore is not a new live catch.
- No video recordings are stored; the chosen frame is saved as the sighting photo.
- Android APK compilation and physical-device camera performance have **not** been verified in this environment.
