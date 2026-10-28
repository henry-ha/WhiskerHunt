#!/usr/bin/env python3
"""Hush Hunt B99 - minimal, reversible Filament overlay performance adjustments.
Not a two-surface renderer rewrite. No user GLBs, assets, or saved content changed.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, os, sys, tempfile
from pathlib import Path

REL = Path('WhiskerHunt/Platforms/Android/Java/com/hushhunt/filament/HushFilamentOverlay.java')
BACKUP_DIR = 'HushHunt_B99_Performance_Backups'
MARKER = 'HUSH_B99_FRAMESTALL_20261028'

def hash256(data): return hashlib.sha256(data).hexdigest()

def discover_root(rootarg):
    options = ([Path(rootarg)] if rootarg else [Path(__file__).resolve().parent, Path(r'E:\inetpub\wwwroot\WhiskerHunt')])
    for o in options:
        if (o / REL).is_file(): return o
    raise FileNotFoundError('Unable to locate '+str(REL)+'; extract ALL files to the solution root containing the WhiskerHunt subfolder, or supply --root "D:\\your\\project".')

def transform(text):
    if ('public final class HushFilamentOverlay' not in text or 'renderer.beginFrame' not in text or 'void doFrame(' not in text):
        raise ValueError('Unsupported Java renderer file: no changes made.')
    if MARKER in text:
        return text, ['Already applied: no edits needed.']
    new=text
    notes=[]
    # Filament's independent translucent overlay requires a colour/depth pass,
    # but additional post effects and an extra local light shadow map are avoidable.
    anchor='view.setPostProcessingEnabled(true);'
    if new.count(anchor)==1:
        new=new.replace(anchor,'view.setPostProcessingEnabled(false); // '+MARKER+': AR camera is already post-processed',1)
        notes.append('Disabled extra Filament overlay post-processing (PBR textures kept).')
    elif 'view.setPostProcessingEnabled(false)' in new:
        notes.append('Overlay post-processing is already disabled.')
    else:
        notes.append('Postprocessing code differs: left unchanged.')
    anchor='.castShadows(true)'
    if new.count(anchor)==1:
        new=new.replace(anchor,'.castShadows(false) /* '+MARKER+': the anchor already has a contact-shadow renderer */',1)
        notes.append('Disabled redundant Filament directional shadow-map pass (AR ground shadow retained).')
    elif '.castShadows(false)' in new:
        notes.append('Filament shadow map is already disabled.')
    else:
        notes.append('Shadow configuration differs: left unchanged.')

    # Visibility diagnostics can trigger a GPU->CPU copy every 1.2 s when the
    # readback never succeeds. Cap probes; do not change model visibility gating.
    # The first 6 checks retain the existing support for model/fallback detection.
    if ('!visibleAnimalPixels' in new and 'inspectVisibleAnimalPixels();' in new and
            'lastPixelValidationNanos' in new and 'pixelReadbackAttempts' not in new):
        probe='!visibleAnimalPixels && nanos - lastPixelValidationNanos > 1_200_000_000L'
        if new.count(probe)==1:
            # add field at an unambiguous location, preserve Java class compatibility
            candidates=['    private long lastPixelValidationNanos;', '    private int unsuccessfulPixelChecks;']
            fa=next((x for x in candidates if new.count(x)==1),None)
            if fa:
                new=new.replace(fa,fa+'\n    private int pixelReadbackAttempts;',1)
                new=new.replace(probe,'!visibleAnimalPixels && pixelReadbackAttempts < 6 && nanos - lastPixelValidationNanos > 1_200_000_000L',1)
                # increment only at the site in doFrame(), not inside callback
                method_start=new.find('void doFrame(')
                probe_at=new.find(probe.replace('nanos - lastPixelValidationNanos > 1_200_000_000L','pixelReadbackAttempts < 6 && nanos - lastPixelValidationNanos > 1_200_000_000L'),method_start)
                next_at=new.find('inspectVisibleAnimalPixels();',method_start)
                if probe_at>=0 and next_at>probe_at and next_at-probe_at<450:
                    new=new[:next_at]+'pixelReadbackAttempts++;\n                    '+new[next_at:]
                    notes.append('Capped repeated visibility GPU readbacks to six attempts per session; keeps legacy fallback logic.')
                else:
                    raise ValueError('Visibility readback pattern differed; aborting safely, no edits performed.')
            else:
                notes.append('Visibility probe field differs: left unchanged.')
        else:notes.append('Visibility probe conditional differs: left unchanged.')
    else:notes.append('No repeated visibility readback to cap (or already optimized).')

    if new==text:
        return new,notes
    # explicit marker needed for idempotency even if only one change was supported
    if MARKER not in new:
        class_anchor='public final class HushFilamentOverlay'
        if new.count(class_anchor)!=1:raise ValueError('Cannot tag patch safely')
        new=new.replace(class_anchor,'/* '+MARKER+' */\n'+class_anchor,1)
    return new,notes

def atomic(path,body):
    fd,tmp=tempfile.mkstemp(prefix='.hush_frames_',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f: f.write(body);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',default=None)
    g=ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--check',action='store_true');g.add_argument('--install',action='store_true');g.add_argument('--rollback',action='store_true')
    a=ap.parse_args()
    root=discover_root(a.root); target=root/REL
    backups=root/BACKUP_DIR
    manifest=backups/'frame_stall_hotfix_manifest.json'
    if a.rollback:
        if not manifest.is_file():raise RuntimeError('No recorded backup for this patch. Source unchanged.')
        m=json.loads(manifest.read_text(encoding='utf-8'))
        old=backups/m['backup_name']
        if not old.is_file() or hash256(old.read_bytes())!=m['original_sha256']:raise RuntimeError('Backup missing or corrupt; unchanged.')
        current=target.read_bytes()
        if hash256(current)!=m['installed_sha256']:raise RuntimeError('Source has since changed. Manual merge required; rollback declined to protect your newer edits.')
        atomic(target,old.read_bytes());print('ROLLBACK PASSED. Restored exactly:',target);return
    old=target.read_bytes();bom=b'\xef\xbb\xbf' if old.startswith(b'\xef\xbb\xbf') else b''
    t=old[len(bom):].decode('utf-8');newline='\r\n' if '\r\n' in t else '\n'
    out,notes=transform(t.replace('\r\n','\n'))
    updated=bom+out.replace('\n',newline).encode('utf-8')
    print('File:',target)
    print('Original SHA256:',hash256(old))
    for note in notes: print(' -',note)
    if a.check:
        print('CHECK PASSED. Source unchanged. '+ ('Patch is already installed.' if updated==old else 'Compatible changes available.'))
        return
    if updated==old:
        print('ALREADY OPTIMIZED / NO MATCHING ACTIONS. No files changed.');return
    if manifest.exists():
        raise RuntimeError('Previous patch backup manifest exists. Do not overwrite it; rollback or archive that backup first.')
    backups.mkdir(exist_ok=True)
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backupname='HushFilamentOverlay.java.before_frame_stall_'+stamp+'.bak'
    backup=backups/backupname
    backup.write_bytes(old)
    if hash256(backup.read_bytes())!=hash256(old):raise RuntimeError('Backup could not be verified; source unchanged.')
    try:
        atomic(target,updated)
        if hash256(target.read_bytes())!=hash256(updated):raise RuntimeError('Source write verification failed')
        manifest.write_text(json.dumps({'backup_name':backupname,'original_sha256':hash256(old),'installed_sha256':hash256(updated),'source_path':str(REL),'changes':notes},indent=2),encoding='utf-8')
    except Exception:
        atomic(target,old);raise
    print('INSTALL PASSED. Backup:',backup)
    print('Next: Clean, Rebuild, and deploy OVER current app. Do not uninstall or delete data.')

if __name__=='__main__':
    try:main()
    except Exception as e:
        print('PATCH ABORTED:',type(e).__name__+':',str(e));sys.exit(1)
