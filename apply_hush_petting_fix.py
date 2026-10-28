#!/usr/bin/env python3
"""Hush Hunt Build 99: send pet events to Filament and animate the anchored GLB.
This is an intentionally fail-closed, idempotent source patch. No GLB/user data touched.
"""
from __future__ import annotations
import argparse
import datetime
import json
from pathlib import Path
import shutil
import sys

REQUIRED = {
    'java': Path('WhiskerHunt/Platforms/Android/Java/com/hushhunt/filament/HushFilamentOverlay.java'),
    'bridge': Path('WhiskerHunt/Platforms/Android/HushFilamentBridge.cs'),
    'activity': Path('WhiskerHunt/Platforms/Android/HushArCoreActivity.cs'),
}
TAG='HUSH_PET_REACTION_B99_V1'

def patch_java(s: str) -> str:
    if TAG in s:
        return s
    a='    private long animationStartNanos;'
    b='''    // HUSH_PET_REACTION_B99_V1: tap/stroke feedback for models with no baked animation.
    // Written by the UI thread and read by Filament's Choreographer thread.
    private volatile long petReactionStartedMs;
    private volatile boolean petReactionIsStroke;
'''
    if s.count(a) != 1: raise ValueError('Java fields anchor missing/ambiguous')
    s=s.replace(a,a+'\n'+b)
    a='    public static void configureEnvironmentalHdr(Object config) {'
    b='''    /** Request a gentle in-world body reaction without moving the AR anchor. */
    public static void reactToPet(boolean isStroke) {
        HushFilamentOverlay item = instance;
        if (item == null || item.destroyed || !item.modelReady) return;
        item.petReactionIsStroke = isStroke;
        item.petReactionStartedMs = android.os.SystemClock.uptimeMillis();
    }

'''
    if s.count(a) != 1: raise ValueError('Java static method anchor missing/ambiguous')
    s=s.replace(a,b+a)
    a='                    float s = unitScale * scale;'
    b='''                    // Triggered from MAUI touch events. Root-space animation works
                    // even when a licensed Sketchfab GLB has zero animation clips.
                    // This is additive to manual yaw and never changes the AR anchor.
                    float petYaw = 0f;
                    float petRoll = 0f;
                    float petBob = 0f;
                    long reactedAt = petReactionStartedMs;
                    long petElapsed = android.os.SystemClock.uptimeMillis() - reactedAt;
                    if (reactedAt > 0L && petElapsed >= 0L && petElapsed < 850L) {
                        float t = petElapsed / 850f;
                        float damping = (1f - t) * (1f - t);
                        boolean stroke = petReactionIsStroke;
                        float oscillation = (float) Math.sin(t * Math.PI * (stroke ? 7.0 : 5.0));
                        // Species personalities: cats lean softly, puppies wag
                        // more enthusiastically, birds give a small feathered sway.
                        boolean isCat = assetName.startsWith("cat-");
                        boolean isDog = assetName.startsWith("dog-");
                        boolean isBird = assetName.startsWith("bird-") || assetName.startsWith("fantasy-");
                        float personality = isCat ? .72f : (isDog ? 1.28f : (isBird ? .84f : 1f));
                        petYaw = (stroke ? 12f : 9f) * personality * damping * oscillation;
                        petRoll = (stroke ? 3.5f : 2.5f) * personality * damping * oscillation;
                        float bounce = isDog ? 1.3f : (isCat ? .6f : 1f);
                        petBob = Math.min(.025f, targetSize * .055f) * bounce *
                            damping * Math.abs(oscillation);
                    }
'''
    if s.count(a) != 1: raise ValueError('Java model matrix anchor missing/ambiguous')
    s=s.replace(a,b+a)
    a='                    Matrix.translateM(world, 0, a[0], a[1], a[2]);'
    b='''                    Matrix.translateM(world, 0, a[0], a[1] + petBob, a[2]);'''
    if s.count(a) != 1: raise ValueError('Java world translation anchor missing/ambiguous')
    s=s.replace(a,b)
    a='                    Matrix.rotateM(world, 0, orientationYaw, 0f, 1f, 0f);'
    b='''                    Matrix.rotateM(world, 0, orientationYaw + petYaw, 0f, 1f, 0f);
                    Matrix.rotateM(world, 0, petRoll, 0f, 0f, 1f);'''
    if s.count(a) != 1: raise ValueError('Java yaw anchor missing/ambiguous')
    return s.replace(a,b)

def patch_bridge(s: str) -> str:
    if TAG in s: return s
    a='    public static void ConfigureHdr(Java.Lang.Object config)'
    b='''    // HUSH_PET_REACTION_B99_V1: one JNI event per real pet, not a per-frame call.
    public static void TriggerPetReaction(bool isStroke)
    {
        if (!_installed) return;
        try
        {
            var clazz = JNIEnv.FindClass(JavaName);
            try
            {
                var method = JNIEnv.GetStaticMethodID(clazz, "reactToPet", "(Z)V");
                JNIEnv.CallStaticVoidMethod(clazz, method, new JValue(isStroke));
            }
            finally { JNIEnv.DeleteLocalRef(clazz); }
        }
        catch (Exception e) { Warn(e); }
    }

'''
    if s.count(a) != 1: raise ValueError('C# bridge configure anchor missing/ambiguous')
    return s.replace(a,b+a)

def patch_activity(s: str) -> str:
    if TAG in s: return s
    a='        System.Threading.Interlocked.Exchange(ref _reactionStartedAt, now);'
    b='''        // HUSH_PET_REACTION_B99_V1: legacy OpenGL already reads _reactionStartedAt.
        // Tell Filament too, so its HD GLBs move rather than only changing text.
        if (_filamentRequested) HushFilamentBridge.TriggerPetReaction(isStroke);
'''
    if s.count(a) != 1: raise ValueError('PetAnimal anchor missing/ambiguous')
    if 'private void PetAnimal(bool isStroke)' not in s: raise ValueError('PetAnimal method not found')
    return s.replace(a,a+'\n'+b)

PATCHERS={'java':patch_java,'bridge':patch_bridge,'activity':patch_activity}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--project', type=Path, default=Path.cwd(), help='Solution root containing WhiskerHunt')
    ap.add_argument('--check',action='store_true',help='Validate applicability without modifying files')
    ap.add_argument('--restore',type=Path,help='Restore from specific backup folder')
    args=ap.parse_args()
    project=args.project.resolve()
    if args.restore:
        bk=args.restore.resolve()
        manifest=bk/'manifest.json'
        if not manifest.exists(): raise SystemExit('Backup manifest not found')
        saved=json.loads(manifest.read_text(encoding='utf-8'))
        for relative in saved['files']:
            src=bk/relative
            dest=project/relative
            if not src.is_file() or not dest.parent.is_dir(): raise SystemExit('Cannot restore '+relative)
            shutil.copy2(src,dest)
            print('Restored',relative)
        return
    if not (project/'WhiskerHunt.sln').is_file():
        raise SystemExit('Could not find WhiskerHunt.sln in '+str(project))
    originals={}
    patched={}
    for key,path in REQUIRED.items():
        target=project/path
        if not target.is_file(): raise SystemExit('Missing: '+str(target))
        original=target.read_text(encoding='utf-8-sig')
        revised=PATCHERS[key](original)
        originals[path]=original
        patched[path]=revised
    needed=[p for p in patched if patched[p]!=originals[p]]
    for p in patched: print(('Will update: ' if p in needed else 'Already patched: ') + str(p))
    if args.check or not needed:
        print('Validation OK; changed:',len(needed));return
    folder=project/'HushHunt_Petting_Backups'/('Petting_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    for p in needed:
        (folder/p).parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(project/p,folder/p)
    (folder/'manifest.json').write_text(json.dumps({'files':[str(p).replace('\\','/') for p in needed]},indent=2),encoding='utf-8')
    try:
        for p in needed: (project/p).write_text(patched[p],encoding='utf-8')
    except Exception:
        for p in needed:
            if (folder/p).exists(): shutil.copy2(folder/p,project/p)
        raise
    print('\nApplied pet reaction bridge to',len(needed),'source files.')
    print('BACKUP:',folder)
    print('Clean/Rebuild and deploy over the existing app; DO NOT uninstall the app.')

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print('PATCH ABORTED:',exc,file=sys.stderr)
        sys.exit(1)
