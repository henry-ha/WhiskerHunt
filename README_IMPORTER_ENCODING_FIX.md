# Windows import encoding fix — Hush Hunt v3.10.31 (Build 94)

Your earlier run successfully downloaded animal GLBs and then stopped with:
`'charmap' codec can't decode byte 0x90 ...`.

Cause: the Python importer read `tools/cc0_candidate_species.json` without specifying UTF-8 on Windows. The catalog contains UTF-8 animal emojis. The patched script always reads UTF-8. The batch launcher also switches the console to UTF-8. It no longer clears the third-party license/source log on subsequent runs.

## Apply to your EXISTING extracted project

1. Copy `tools/import_cc0_wildlife.py` from this patch over the same file in your Hush Hunt project.
2. Copy `INSTALL_CC0_WILDLIFE.bat` over the existing file at the project root.
3. Double-click `INSTALL_CC0_WILDLIFE.bat` again. Already-downloaded models are skipped; missing matches can still be attempted. **Do not delete the `ar_models` folder.**
4. It should finish by printing `Ready for ARCore: ... exactly matched species` and `Complete. Rebuild ...`.
5. Clean and Rebuild the MAUI project in Visual Studio, then deploy over your existing app without uninstalling it.

For a quick offline check that simply regenerates the selector from already-downloaded models, open a terminal in the project root and run:

`py tools\import_cc0_wildlife.py`

The `NOT AVAILABLE (no exact wildlife match)` messages are expected when these third-party libraries don't contain an exact match. They do **not** indicate download failure. The imported GLBs are only candidates until visually and technically tested on the device.

No Android C# changes are required for this encoding issue. The app version remains v3.10.31 build 94.
