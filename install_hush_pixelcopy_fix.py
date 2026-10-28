#!/usr/bin/env python3
"""Fix SurfaceView.getBitmap compile failure in Hush Hunt B99 Filament overlay.
Safe targeted source repair: check-only, backup, atomic write, rollback.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
import tempfile

TAG = 'HUSH_B99_SURFACEVIEW_PIXELCOPY_HOTFIX_20261028'
SOURCE_RELATIVE = Path('WhiskerHunt/Platforms/Android/Java/com/hushhunt/filament/HushFilamentOverlay.java')
BACKUP_FOLDER = 'HushHunt_PixelCopy_Hotfix_Backups'


def project_file(root: Path) -> Path:
    if not (root / 'WhiskerHunt.sln').is_file():
        raise ValueError(f'Expected WhiskerHunt.sln in {root}. Extract this ZIP into the solution root.')
    source = root / SOURCE_RELATIVE
    if not source.is_file():
        raise ValueError(f'Cannot find {source}. Project files unchanged.')
    return source


def span_method(s: str, name: str):
    rx = rf'(?m)^[ \t]*private\s+void\s+{re.escape(name)}\s*\(\s*\)\s*\{{'
    matches = list(re.finditer(rx, s))
    if len(matches) != 1:
        raise ValueError(f'{name}: expected one method, found {len(matches)}. Source unchanged.')
    m = matches[0]
    depth = 0
    for i in range(m.end() - 1, len(s)):
        if s[i] == '{': depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0: return (m.start(), i+1)
    raise ValueError(f'{name}: unbalanced braces. Source unchanged.')


def repair(s: str):
    if TAG in s:
        if 'android.view.PixelCopy.request(surfaceView,' not in s or re.search(r'\bsurfaceView\s*\.\s*getBitmap\s*\(', s):
            raise ValueError('Patch marker present but code is inconsistent. No changes made.')
        return s, False

    if not re.search(r'\b(?:private|protected)\s+(?:final\s+)?SurfaceView\s+surfaceView\s*;', s):
        raise ValueError('This version is not the expected SurfaceView renderer. No changes made.')
    if 'private final Handler main' not in s or 'private volatile boolean visibleAnimalPixels' not in s:
        raise ValueError('Expected Filament class fields missing. Do not apply this patch to a different version.')
    if len(re.findall(r'\bsurfaceView\s*\.\s*getBitmap\s*\(', s)) != 1:
        raise ValueError('Unexpected SurfaceView.getBitmap count. No changes made.')
    start, end = span_method(s, 'inspectVisibleAnimalPixels')
    old_method = s[start:end]
    if old_method.count('surfaceView.getBitmap(') != 1 or 'frame.getPixels(' not in old_method or 'frame.recycle()' not in old_method:
        raise ValueError('Pixel inspection method differs from this Build 99 repair. No changes made.')

    head = re.compile(
        r'^([ \t]*)private void inspectVisibleAnimalPixels\(\)\s*\{\s*'
        r'Bitmap frame = null;\s*try\s*\{\s*'
        r'frame\s*=\s*surfaceView\.getBitmap\(\s*96\s*,\s*96\s*\);\s*'
        r'if\s*\(\s*frame\s*==\s*null\s*\)\s*return\s*;', re.S
    )
    mt = head.match(old_method)
    if not mt:
        raise ValueError('Pixel inspection body changed; cannot safely rewrite. No changes made.')
    indent = mt.group(1)
    rest = old_method[mt.end():]
    # Preserve ALL of the existing pixel scoring, diagnostics, and finally/recycle code.
    score_method = (indent + 'private void inspectCopiedAnimalPixels(Bitmap frame) {\n'
                    + indent + '    try {\n'
                    + indent + '        if (frame == null) return;' + rest)

    request_method = f'''{indent}// {TAG}: SurfaceView has no getBitmap(). Copy asynchronously instead.
{indent}private boolean pixelCopyInFlight;
{indent}private void inspectVisibleAnimalPixels() {{
{indent}    if (pixelCopyInFlight || destroyed || !modelReady ||
{indent}        !surfaceView.getHolder().getSurface().isValid()) return;
{indent}    pixelCopyInFlight = true;
{indent}    Bitmap created = null;
{indent}    try {{
{indent}        // PixelCopy scales the SurfaceView image into this small destination.
{indent}        created = Bitmap.createBitmap(96, 96, Bitmap.Config.ARGB_8888);
{indent}        final Bitmap sample = created;
{indent}        android.view.PixelCopy.request(surfaceView, sample, result -> {{
{indent}            pixelCopyInFlight = false;
{indent}            if (result != android.view.PixelCopy.SUCCESS || destroyed ||
{indent}                !modelReady || asset == null) {{
{indent}                sample.recycle();
{indent}                return;
{indent}            }}
{indent}            inspectCopiedAnimalPixels(sample);
{indent}        }}, main);
{indent}    }} catch (Throwable t) {{
{indent}        pixelCopyInFlight = false;
{indent}        if (created != null && !created.isRecycled()) created.recycle();
{indent}        Log.w(TAG, "PixelCopy visibility request failed: " + t.getMessage());
{indent}    }}
{indent}}}

'''
    s = s[:start] + request_method + score_method + s[end:]
    s = s.replace('// TextureView.getBitmap() forces a GPU-to-CPU synchronisation.\n'
                  '                // Do it only until a model has actually shown pixels; doing it\n'
                  '                // every second for the lifetime of AR Safari causes stuttering.',
                  '// Asynchronous PixelCopy validates the real SurfaceView image.\n'
                  '                // Stop sampling once the HD animal is visibly rendered.')
    if re.search(r'\bsurfaceView\s*\.\s*getBitmap\s*\(', s):
        raise ValueError('Unsafe residual getBitmap call. Source unchanged.')
    if s.count(TAG) != 1: raise ValueError('Tag mismatch; source unchanged.')
    if 'private void inspectCopiedAnimalPixels(Bitmap frame)' not in s:
        raise ValueError('Pixel inspection helper missing; source unchanged.')
    return s, True


def write_atomic(path: Path, data: bytes):
    fd, temp = tempfile.mkstemp(prefix='.hush_pixelcopy_', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp): os.remove(temp)


def main():
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--install', action='store_true')
    mode.add_argument('--rollback', action='store_true')
    ap.add_argument('--root', type=Path, default=Path.cwd())
    args = ap.parse_args()
    root = args.root.resolve()
    source = project_file(root)
    backups = root / BACKUP_FOLDER
    if args.rollback:
        previous = sorted(backups.glob('PixelCopy_*'), reverse=True)
        previous = [x for x in previous if (x / 'HushFilamentOverlay.java').is_file()]
        if not previous: raise ValueError('No matching PixelCopy hotfix backup available.')
        selected = previous[0]
        original = (selected / 'HushFilamentOverlay.java').read_bytes()
        write_atomic(source, original)
        print('ROLLBACK COMPLETE:', source)
        print('Restored original source from:', selected)
        return

    original = source.read_bytes()
    bom = b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b''
    content = original[len(bom):].decode('utf-8')
    linebreak = '\r\n' if '\r\n' in content else '\n'
    content_lf = content.replace('\r\n', '\n')
    patched, changed = repair(content_lf)
    print('SOURCE:', source)
    print('PATCH:', 'Safe change validated' if changed else 'Already installed (unchanged)')
    if args.check:
        print('CHECK PASSED - this check did not change project files.')
        return
    if not changed:
        print('INSTALL COMPLETED - hotfix already installed.')
        return

    destination = backups / ('PixelCopy_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    destination.mkdir(parents=True, exist_ok=False)
    (destination / 'HushFilamentOverlay.java').write_bytes(original)
    (destination / 'manifest.json').write_text(json.dumps({'source': str(source), 'fix': TAG}, indent=2), encoding='utf-8')
    try:
        write_atomic(source, bom + patched.replace('\n', linebreak).encode('utf-8'))
    except Exception:
        write_atomic(source, original)
        raise
    print('INSTALL COMPLETED - fixed SurfaceView pixel copying.')
    print('Backup:', destination)
    print('Now: Clean Solution > Rebuild Solution > deploy over existing app.')

if __name__ == '__main__':
    try: main()
    except Exception as ex:
        print('PATCH ABORTED:', ex, file=sys.stderr)
        sys.exit(1)
