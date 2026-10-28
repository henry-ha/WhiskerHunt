#!/usr/bin/env python3
"""Hush Hunt B99 Filament live AR cadence repair.
Updates only HushFilamentOverlay.java. Fail-closed, backup and rollback.
This is a source-level performance fix; full AR compositing may require architectural work.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

REL = Path('WhiskerHunt/Platforms/Android/Java/com/hushhunt/filament/HushFilamentOverlay.java')
TAG='HUSH_B99_ARCORE_LATEST_POSE_FILAMENT_PACING_01'

OLD_BUDGET='''            frameBudgetNanos = bytes.length > 24 * 1024 * 1024
                ? 30_000_000L : (bytes.length > 12 * 1024 * 1024 ? 22_000_000L : 16_000_000L);'''
NEW_BUDGET='''            // HUSH_B99_ARCORE_LATEST_POSE_FILAMENT_PACING_01
            // Do not hold 12-24 MiB animals at ~45 fps or 24+ MiB at ~33 fps.
            // Follow the latest ARCore frame at every display VSYNC. Filament's
            // beginFrame() handles native GPU backlog and may skip when needed.
            frameBudgetNanos = 0L;'''
OLD_SKIP='''        // Small models follow ARCore at display cadence; heavier models are
        // budgeted to protect the camera thread from GPU starvation.
        if (lastRenderedNanos != 0 && nanos - lastRenderedNanos < frameBudgetNanos) {
            scheduleFrame();
            return;
        }
        lastRenderedNanos = nanos;'''
NEW_SKIP='''        // NO secondary app-level cadence limiter. A slow TextureView is especially
        // visible during walk-around: its old animal pose trails the live AR video.
        // The main thread owns all Filament GPU calls. ARCore publishes immutable
        // same-frame camera/anchor matrices from its own GL thread.
        lastRenderedNanos = nanos;'''
OLD_MATRICES='''                float[] cameraWorld = new float[16];
                if (Matrix.invertM(cameraWorld, 0, v, 0)) {
                    camera.setModelMatrix(cameraWorld);
                    double[] proj = new double[16];
                    for (int i = 0; i < 16; i++) proj[i] = p[i];
                    camera.setCustomProjection(proj, .1, 80.0);'''
NEW_MATRICES='''                if (Matrix.invertM(cameraWorldScratch, 0, v, 0)) {
                    camera.setModelMatrix(cameraWorldScratch);
                    for (int i = 0; i < 16; i++) projectionScratch[i] = p[i];
                    camera.setCustomProjection(projectionScratch, .1, 80.0);'''
OLD_WORLD='''                    float[] world = new float[16];
                    Matrix.setIdentityM(world, 0);'''
NEW_WORLD='''                    float[] world = modelWorldScratch;
                    Matrix.setIdentityM(world, 0);'''
FIELDS='''    // Filament render calls are confined to the Android UI / Choreographer thread.
    // Scratch arrays are not shared with the ARCore camera thread; these reduce
    // 60 Hz allocations that can trigger GC stalls on mobile.
    private final float[] cameraWorldScratch = new float[16];
    private final double[] projectionScratch = new double[16];
    private final float[] modelWorldScratch = new float[16];
'''


def replace_once(s: str, old: str, new: str, step: str) -> str:
    count = s.count(old)
    if count != 1:
        raise ValueError(f'{step}: expected exactly one source match, found {count}; no modifications made')
    return s.replace(old, new, 1)


def patch(s: str) -> str:
    if TAG in s:
        if OLD_SKIP in s or OLD_BUDGET in s:
            raise ValueError('Partially patched file; refusing to continue')
        return s
    if 'petReactionStartedMs' not in s or 'lastPetSignalSequence' not in s:
        raise ValueError('Previous petting crash frame-sync repair not found; install that fix first')
    if 'if (anchor.length >= 5)' not in s:
        raise ValueError('AR-frame pet event support missing; refusing to overwrite petting')
    if 'orientationYaw + petYaw' not in s:
        raise ValueError('HD petting animation missing; refusing to modify unknown renderer')
    s=replace_once(s,OLD_BUDGET,NEW_BUDGET,'GLB frame budget')
    s=replace_once(s,OLD_SKIP,NEW_SKIP,'Frame callback throttling')
    s=replace_once(s,OLD_MATRICES,NEW_MATRICES,'Camera and projection matrices')
    s=replace_once(s,OLD_WORLD,NEW_WORLD,'Model transform')
    s=replace_once(s,'    private long animationStartNanos;', '    private long animationStartNanos;\n'+FIELDS,'scratch fields')
    s=replace_once(s,'renderer.beginFrame(swapChain, nanos)', 'renderer.beginFrame(swapChain, nanos)', 'Filament vsync') if 'renderer.beginFrame(swapChain, nanos)' in s else replace_once(s,'renderer.beginFrame(swapChain)', 'renderer.beginFrame(swapChain, nanos)', 'Filament vsync')
    return s


def restore(root: Path, backup: Path):
    backup = backup.resolve()
    manifest = backup/'manifest.json'
    data = json.loads(manifest.read_text(encoding='utf-8'))
    if data.get('source') != str(REL).replace('\\','/'):
        raise ValueError('Backup manifest does not match this Hush Hunt patch')
    source = backup/REL
    if not source.is_file():
        raise ValueError('Backup source missing: '+str(source))
    target=root/REL
    safe_atomic(target, source.read_bytes())
    print('ROLLBACK COMPLETE: restored '+str(target))


def safe_atomic(path: Path, data: bytes):
    fd,name=tempfile.mkstemp(prefix='.hush_ar_latency_',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


def main():
    ap=argparse.ArgumentParser(description='Hush Hunt HD AR low-latency renderer patch')
    ap.add_argument('--project',type=Path,default=Path.cwd())
    ap.add_argument('--check',action='store_true',help='Validate patch without modifying files')
    ap.add_argument('--restore',type=Path,help='Restore a specified generated backup folder')
    ap.add_argument('--restore-latest',action='store_true',help='Restore the newest saved patch backup')
    args=ap.parse_args()
    root=args.project.resolve()
    if not (root/'WhiskerHunt.sln').is_file():
        raise ValueError('WhiskerHunt.sln not found in '+str(root)+'. Unzip directly into the solution directory.')
    if args.restore and args.restore_latest:
        raise ValueError('Choose only one of --restore or --restore-latest')
    if args.restore_latest:
        base=root/'HushHunt_AR_Performance_Backups'
        candidates=sorted((p for p in base.glob('LowLatency_*') if p.is_dir() and (p/'manifest.json').is_file()),reverse=True) if base.is_dir() else []
        if not candidates:
            raise ValueError('No backup found under '+str(base))
        print('Using newest backup:',candidates[0])
        restore(root,candidates[0]);return
    if args.restore:
        restore(root,args.restore);return
    path=root/REL
    source=path.read_bytes()
    bom=b'\xef\xbb\xbf' if source.startswith(b'\xef\xbb\xbf') else b''
    s=source.decode('utf-8-sig')
    revised=patch(s)
    changed=s!=revised
    print('Project:', root)
    print('Java source:',path)
    print('Source sha256:',hashlib.sha256(source).hexdigest())
    print('Patch status:', 'WOULD UPDATE' if changed else 'ALREADY INSTALLED')
    print('Checks: HD petting preserved, frame-synced events preserved, camera/anchor untouched.')
    if args.check or not changed:
        print('CHECK PASSED; no source files changed.')
        return
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup=root/'HushHunt_AR_Performance_Backups'/('LowLatency_'+stamp)
    (backup/REL).parent.mkdir(parents=True,exist_ok=True)
    (backup/REL).write_bytes(source)
    (backup/'manifest.json').write_text(json.dumps({
        'patch':TAG, 'source':str(REL).replace('\\','/'), 'original_sha256':hashlib.sha256(source).hexdigest(),
        'backup_date': stamp},indent=2),encoding='utf-8')
    try:
        revised_bytes=bom+revised.encode('utf-8')
        safe_atomic(path,revised_bytes)
        if hashlib.sha256(path.read_bytes()).digest()!=hashlib.sha256(revised_bytes).digest():
            raise IOError('Verification failed: source did not match patched content')
    except Exception:
        safe_atomic(path,source)
        raise
    print('INSTALLED: 1 Java file patched, petting and all 3D assets preserved.')
    print('ROLLBACK BACKUP: '+str(backup))
    print('Clean & rebuild in Visual Studio; deploy OVER the installed app (do not uninstall).')

if __name__=='__main__':
    try: main()
    except Exception as ex:
        print('PATCH ABORTED (source unchanged / rolled back):',ex,file=sys.stderr)
        sys.exit(1)
