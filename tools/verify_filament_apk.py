#!/usr/bin/env python3
"""Check built APK contains the native Filament Java class and named animal GLBs.
Run AFTER building in Visual Studio: py tools/verify_filament_apk.py path/to/app.apk
"""
import sys,zipfile
from pathlib import Path
TARGET=b'Lcom/hushhunt/filament/HushFilamentOverlay;'

def run(path:Path):
    with zipfile.ZipFile(path) as z:
        dex=[n for n in z.namelist() if n.startswith('classes') and n.endswith('.dex')]
        if not dex:
            print('FAIL: APK has no classes.dex');return 2
        present=any(TARGET in z.read(n) for n in dex)
        assets=[n for n in z.namelist() if n.startswith('assets/ar_models/') and n.endswith('.glb')]
    print('APK:',path)
    print('Native HushFilamentOverlay class:', 'PRESENT' if present else 'MISSING')
    print('Bundled wildlife GLB files:',len(assets))
    if not present:
        print('FAIL: Native Java bridge not packaged. Delete bin/obj, rebuild and verify Java source build action.')
        return 3
    if not assets:
        print('WARNING: No GLB files found under assets/ar_models; verify MauiAsset LogicalName.')
        return 4
    print('PASS: Filament JNI entry point and 3D models found in APK.')
    return 0

if __name__=='__main__':
    if len(sys.argv)!=2:
        print('Usage: py tools/verify_filament_apk.py "path\\to\\app.apk"')
        sys.exit(2)
    sys.exit(run(Path(sys.argv[1])))
