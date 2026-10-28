#!/usr/bin/env python3
"""Hush Hunt v3.10.36 B99: remove unsafe per-pet JNI call; use existing frame JNI.

Install guardrails: a known old source layout is required, backups created first,
atomic writes, all-or-nothing rollback on any installer exception.
Does not touch GLBs, textures, MAUI pages, app storage, or saved discoveries.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

TAG = 'HUSH_PET_REACTION_B99_V2_FRAMESYNC'
JAVA = Path('WhiskerHunt/Platforms/Android/Java/com/hushhunt/filament/HushFilamentOverlay.java')
ACTIVITY = Path('WhiskerHunt/Platforms/Android/HushArCoreActivity.cs')

OLD_PET='''        // HUSH_PET_REACTION_B99_V1: legacy OpenGL already reads _reactionStartedAt.
        // Tell Filament too, so its HD GLBs move rather than only changing text.
        if (_filamentRequested) HushFilamentBridge.TriggerPetReaction(isStroke);'''

NEW_PET='''        // HUSH_PET_REACTION_B99_V2_FRAMESYNC: no JNI calls on the touch/UI thread.
        // The already-working ARCore frame submission safely delivers this event.
        System.Threading.Volatile.Write(ref _filamentPetStroke, isStroke ? 1 : 0);
        System.Threading.Interlocked.Increment(ref _filamentPetSequence);'''

OLD_SUBMIT='''                    if (_host._filamentRequested)
                        HushFilamentBridge.SubmitFrame(_view, _projection, pos, scale, frame);'''

NEW_SUBMIT='''                    if (_host._filamentRequested)
                    {
                        // HUSH_PET_REACTION_B99_V2_FRAMESYNC: the first 3 values remain
                        // unchanged XYZ; values 4 and 5 carry a pet event sequence/type.
                        // Reuse the already functioning JNI submitFrame signature.
                        float[] filamentAnchorWithPet =
                        {
                            pos[0], pos[1], pos[2],
                            System.Threading.Volatile.Read(ref _host._filamentPetSequence),
                            System.Threading.Volatile.Read(ref _host._filamentPetStroke)
                        };
                        HushFilamentBridge.SubmitFrame(
                            _view, _projection, filamentAnchorWithPet, scale, frame);
                    }'''

JAVA_GUARD='''        if (item == null || item.destroyed || view == null || projection == null || anchor == null) return;'''

JAVA_EVENT='''        // HUSH_PET_REACTION_B99_V2_FRAMESYNC: receive pet events in the same
        // established ARCore frame stream; NEVER use a second JNI call on tap.
        if (anchor.length >= 5) {
            int sequence = (int) anchor[3];
            if (sequence != 0 && sequence != item.lastPetSignalSequence) {
                item.lastPetSignalSequence = sequence;
                item.petReactionIsStroke = anchor[4] > 0.5f;
                item.petReactionStartedMs = android.os.SystemClock.uptimeMillis();
                Log.i(TAG, "Pet reaction via AR frame, stroke=" + item.petReactionIsStroke);
            }
        }'''


def require_once(s, needle, where):
    if s.count(needle) != 1:
        raise ValueError(f'{where}: expected one source anchor, found {s.count(needle)}. No changes made.')


def patch_activity(s):
    if TAG in s:
        if 'TriggerPetReaction(isStroke)' in s:
            raise ValueError('Activity partially updated: old JNI call still present')
        return s
    require_once(s, OLD_PET, 'PetAnimal V1')
    require_once(s, OLD_SUBMIT, 'SubmitFrame V1')
    anchor='    private long _lastPetTick, _reactionStartedAt;'
    require_once(s, anchor, 'Pet sequence fields')
    s=s.replace(anchor,anchor+'\n    private int _filamentPetSequence, _filamentPetStroke;')
    s=s.replace(OLD_PET,NEW_PET)
    s=s.replace(OLD_SUBMIT,NEW_SUBMIT)
    return s


def patch_java(s):
    if TAG in s:
        return s
    if 'HUSH_PET_REACTION_B99_V1' not in s or 'petYaw' not in s or 'petReactionStartedMs' not in s:
        raise ValueError('Pet reaction Java V1 missing. This repair targets the latest installed petting fix.')
    anchor='    private volatile boolean petReactionIsStroke;'
    require_once(s,anchor,'Pet callback field')
    s=s.replace(anchor,anchor+'\n    private int lastPetSignalSequence;')
    require_once(s,JAVA_GUARD,'ARCore frame method')
    s=s.replace(JAVA_GUARD,JAVA_GUARD+'\n'+JAVA_EVENT)
    return s


def atomic_write(path, content):
    fd, name=tempfile.mkstemp(prefix='.hush_petting_',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='') as f:
            f.write(content)
            f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)


def main():
    ap=argparse.ArgumentParser(description='Hush Hunt petting crash repair')
    ap.add_argument('--project',type=Path,default=Path.cwd())
    ap.add_argument('--check',action='store_true')
    ap.add_argument('--disable',action='store_true',help='Emergency: turn off custom HD pet motion safely')
    args=ap.parse_args()
    root=args.project.resolve()
    if not (root/'WhiskerHunt.sln').is_file():
        raise ValueError('WhiskerHunt.sln not found in '+str(root)+'. Extract scripts directly into the solution root.')
    paths=[ACTIVITY,JAVA]
    originals={p:(root/p).read_text(encoding='utf-8-sig') for p in paths}
    if args.disable:
        s=originals[ACTIVITY]
        # Applies to V1 installations as well as this repaired V2 build.
        if 'TriggerPetReaction(isStroke)' in s:
            s=s.replace('if (_filamentRequested) HushFilamentBridge.TriggerPetReaction(isStroke);',
                        '// Crash stop: removed standalone JNI pet event.')
        if TAG in s:
            s=s.replace('System.Threading.Interlocked.Increment(ref _filamentPetSequence);',
                        '// Crash stop: HD pet motion disabled; legacy UI feedback unaffected.')
        revised={ACTIVITY:s,JAVA:originals[JAVA]}
    else:
        revised={ACTIVITY:patch_activity(originals[ACTIVITY]),JAVA:patch_java(originals[JAVA])}
        if (TAG in revised[ACTIVITY]) != (TAG in revised[JAVA]):
            raise ValueError('Partial petting patch detected; refusing to deploy an inconsistent renderer.')
        if 'TriggerPetReaction(isStroke)' in revised[ACTIVITY]:
            raise ValueError('Unsafe tap-time JNI call still present; repair refused.')
    changed=[p for p in paths if revised[p] != originals[p]]
    print('Project:',root)
    for p in paths:
        print(('WOULD UPDATE' if p in changed else 'ALREADY SAFE')+': '+str(p))
    if args.check:
        print('CHECK PASSED: compatibility and file paths validated; no files modified.')
        return
    if not changed:
        print('Already at requested state; nothing modified.')
        return
    bdir=root/'HushHunt_Petting_Backups'/('PettingCrashRepair_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    for p in changed:
        dest=bdir/p
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/p,dest)
    (bdir/'manifest.json').write_text(json.dumps({
        'type':'HushHunt Petting Crash Repair B99',
        'mode':'disable' if args.disable else 'frame-synchronised pet reaction',
        'files':[str(x).replace('\\','/') for x in changed]
    },indent=2),encoding='utf-8')
    done=[]
    try:
        for p in changed:
            atomic_write(root/p,revised[p]);done.append(p)
    except Exception:
        for p in done: shutil.copy2(bdir/p,root/p)
        raise
    print('INSTALL PASSED: '+str(len(changed))+' source files updated.')
    print('Backup:',bdir)
    print('Clean, rebuild, and deploy over existing Android app. DO NOT uninstall.')

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('REPAIR ABORTED:',exc,file=sys.stderr)
        sys.exit(1)
