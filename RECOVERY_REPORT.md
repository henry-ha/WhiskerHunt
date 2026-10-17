# Whisker Hunt recovery assessment — 17 October 2026

**Uploaded files were only read; no changes were made to the originals.**

- Main state file: 4 cats, 4 valid photos, 4 sightings, 0 sightings with saved coordinates, 250 XP.
- .bak file: 3 cats, 3 valid photos, 3 sightings, 0 saved coordinates, 250 XP.
- The older .bak contains Byeol, fluffy gray-brown tabby, and Persian. The newer main file also has Calico.
- The 3 overlapping photos match byte-for-byte across both files.
- These files do not provide any earlier GPS positions and cannot reconstruct past locations.
- The uploaded files establish recovery of four photos, but do not prove that there are no other older photos in Android WebView storage or previous backups.

## Verified photos

- **Byeol** (Real): `01_byeol_real.jpg`, 713×950, 97924 JPEG bytes; SHA-256 `d516907e3078aad1…`
- **fluffy, gray-brown tabby bushy tail** (Real): `02_fluffy_gray-brown_tabby_bushy_tail_real.jpg`, 713×950, 160420 JPEG bytes; SHA-256 `6e447941b312a12b…`
- **Persian** (Virtual): `03_persian_virtual.jpg`, 600×800, 53026 JPEG bytes; SHA-256 `4e8974d3aa74cc5a…`
- **Calico** (Virtual): `04_calico_virtual.jpg`, 600×800, 51240 JPEG bytes; SHA-256 `07cb09e754f8e7b4…`

## Recovery recommendations

1. Keep this ZIP plus the two original phone files in a safe place, ideally with a second offline copy.
2. Do not uninstall Whisker Hunt, clear storage, or import a three-cat .bak over the four-cat main file.
3. Export any more recent app data before trying a restore. If the current app shows missing photos, restore/merge a copy of `WhiskerHunt_Restore_4_Cats.json` using the app’s Restore a backup feature only after checking that the app supports safe merging.
4. If you previously had more than two real-cat photos, look for earlier WebView storage or older backups. These two files contain only two real cats.
5. Missing GPS positions cannot be recreated from these JSON files; if prompted, only attach current GPS when physically at the original sighting place.

## File integrity

- Main JSON SHA-256: `24c96f121c939c5804cdda2b47c7f0fe87a7b43387e3e654bbec6adbecd6121e`
- Backup JSON SHA-256: `5ef9dc73a3c0670658acfbe7ae8a2460aa3eadcf85775058734048ebfc423f1d`
- The restore JSON included here is an identical byte-for-byte copy of the uploaded four-cat main file.
