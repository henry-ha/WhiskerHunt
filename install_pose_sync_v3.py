#!/usr/bin/env python3
'''Hush Hunt Build99: pose-aligned frame pacing and lower render-thread overhead.
Source-only, fail-closed, check/install/rollback, backed-up atomically.
'''
import argparse, datetime, os, re, sys, tempfile, hashlib, json
from pathlib import Path

TAG='HUSH_B99_POSESYNC_PERF_V3_20261028'
JAVA=Path('WhiskerHunt/Platforms/Android/Java/com/hushhunt/filament/HushFilamentOverlay.java')
ACT=Path('WhiskerHunt/Platforms/Android/HushArCoreActivity.cs')
FILES=(JAVA,ACT)
BACKUPS='HushHunt_PoseSync_Performance_Backups'

def one(source, old, new, description):
    n=source.count(old)
    if n != 1: raise ValueError(f'{description}: expected once, found {n}; no project files changed')
    return source.replace(old,new,1)

def java_patch(s):
    if TAG in s:
        if 'cameraWorldScratch' not in s or 'lastLightNanos' not in s:
            raise ValueError('Partial Java performance patch: no changes made')
        return s
    for marker in ('class HushFilamentOverlay', 'Choreographer.FrameCallback',
                   'public static void submitFrame(', 'renderer.beginFrame(swapChain, nanos)',
                   'private float[] viewSnapshot;', 'private void scheduleFrame()'):
        if marker not in s:raise ValueError('Unsupported renderer source: '+marker)
    already_synced = 'private long frameGeneration;' in s and 'private long renderedGeneration;' in s
    scratch = '''    // HUSH_B99_POSESYNC_PERF_V3_20261028
    // Reuse matrices instead of allocating every camera frame.
    private final float[] cameraWorldScratch = new float[16];
    private final float[] worldScratch = new float[16];
    private final double[] projectionScratch = new double[16];
    private final float[] lastProjection = new float[16];
    private boolean projectionIsCached;
    private long lastLightNanos;
    private int cachedRootInstance;
'''
    if already_synced:
        # Current B99 already has generation-based frame synchronisation;
        # keep its established logic instead of installing a second guard.
        s=one(s,'    private float[] viewSnapshot;',scratch+'    private float[] viewSnapshot;', 'Java scratch fields')
    else:
        scratch += '''    // AR frame serial prevents stale frames being recomposited as new poses.
    private long poseSerial;
    private long paintedPoseSerial = -1;
'''
        s=one(s,'    private float[] viewSnapshot;',scratch+'    private float[] viewSnapshot;', 'Java scratch and pose fields')
        s=one(s,'            item.animalScale = Math.max(.5f, Math.min(3f, scale));',
              '''            item.animalScale = Math.max(.5f, Math.min(3f, scale));
            item.poseSerial++;''','Java pose publication')
        s=one(s,'            float scale;\n            synchronized (snapshotLock) {',
              '''            float scale;
            long frameNumber;
            synchronized (snapshotLock) {''','Pose capture header')
        s=one(s,'                d = lightDirection; intensity = lightIntensity; scale = animalScale;',
              '''                d = lightDirection; intensity = lightIntensity; scale = animalScale;
                frameNumber = poseSerial;''','Pose capture')
        s=one(s,'            if (v != null && p != null && a != null) {',
              '''            if (v == null || p == null || a == null || frameNumber == paintedPoseSerial) {
                scheduleFrame();
                return;
            }
            if (v != null && p != null && a != null) {''','Skip stale frame')
        s=one(s,'                renderer.render(view);\n                renderer.endFrame();',
              '''                renderer.render(view);
                renderer.endFrame();
                paintedPoseSerial = frameNumber;''','Mark rendered frame')
    # In newer code the pose generation was marked rendered BEFORE beginFrame,
    # even when beginFrame skipped it due to GPU backlog. Mark only after success.
    if already_synced:
        s=one(s,'            renderedGeneration = generation;\n','', 'Defer marking rendered generation')
        s=one(s,'                renderer.render(view);\n                renderer.endFrame();',
              '''                renderer.render(view);
                renderer.endFrame();
                renderedGeneration = generation;''','Mark successfully rendered generation')
    if '.castShadows(true)' in s:
        s=one(s,'.castShadows(true)',
              '''// Existing AR floor silhouette handles contact shadows; avoid
                // a second heavyweight Filament shadow pass.
                .castShadows(false)''','Duplicate shadow map removal')
    elif '.castShadows(false)' not in s:
        raise ValueError('Unsupported light setup, no shadow map anchor')
    s=one(s,'            unitScale = targetSize / max;',
          '''            unitScale = targetSize / max;
            cachedRootInstance = engine.getTransformManager().getInstance(asset.getRoot());''','Cache root transform')
    matches=list(re.finditer(r'(?s)                float\[\] cameraWorld = new float\[16\];.*?tm\.setTransform\(instance, world\);',s))
    if len(matches)!=1:
        raise ValueError(f'Matrix transform differs from supported B99 source ({len(matches)} matches); no changes made')
    m=matches[0]
    old=m.group(0)
    # Keep added yaw/pitch and animal reaction Matrix.rotateM statements unchanged.
    new=old
    new=one(new,'                float[] cameraWorld = new float[16];\n','', 'Camera matrix allocation')
    new=one(new,'Matrix.invertM(cameraWorld, 0, v, 0)','Matrix.invertM(cameraWorldScratch, 0, v, 0)','Camera inversion')
    new=one(new,'camera.setModelMatrix(cameraWorld);','camera.setModelMatrix(cameraWorldScratch);','Camera pose')
    proj='''                    double[] proj = new double[16];
                    for (int i = 0; i < 16; i++) proj[i] = p[i];
                    camera.setCustomProjection(proj, .1, 80.0);'''
    proj_new='''                    boolean projectionChanged = !projectionIsCached;
                    if (!projectionChanged) {
                        for (int i = 0; i < 16; i++) {
                            if (Math.abs(p[i] - lastProjection[i]) > 0.00001f) {
                                projectionChanged = true;
                                break;
                            }
                        }
                    }
                    if (projectionChanged) {
                        for (int i = 0; i < 16; i++) {
                            lastProjection[i] = p[i];
                            projectionScratch[i] = p[i];
                        }
                        camera.setCustomProjection(projectionScratch, .1, 80.0);
                        projectionIsCached = true;
                    }'''
    new=one(new,proj,proj_new,'Projection cache')
    new=one(new,'                    float[] world = new float[16];\n','','World matrix allocation')
    new=re.sub(r'\bworld\b','worldScratch',new)
    new=one(new,'''                    TransformManager tm = engine.getTransformManager();
                    int instance = tm.getInstance(asset.getRoot());
                    tm.setTransform(instance, worldScratch);''',
            '                    engine.getTransformManager().setTransform(cachedRootInstance, worldScratch);',
            'Root transform cache')
    s=s[:m.start()]+new+s[m.end():]
    if 'nanos - lastAmbientUpdate > 1_000_000_000L' in s:
        s=one(s,'nanos - lastAmbientUpdate > 1_000_000_000L',
              'nanos - lastAmbientUpdate > 4_000_000_000L','Amortise ambient environment rebuild')
    if '                    if (d.length >= 3 && intensity.length >= 3) {' in s:
        s=one(s,'                    if (d.length >= 3 && intensity.length >= 3) {',
              '''                    // HDR does not require an expensive JNI update every display frame.
                    if (d.length >= 3 && intensity.length >= 3 &&
                        nanos - lastLightNanos >= 250_000_000L) {
                        lastLightNanos = nanos;''','Throttle HDR direction')
    else:
        raise ValueError('Cannot identify light update block')
    s=one(s,'            view.setViewport(new Viewport(0, 0, width, height));',
          '''            view.setViewport(new Viewport(0, 0, width, height));
            projectionIsCached = false;''', 'Refresh projection on new surface')
    # Only newer variants artificially cap heavy models at 30fps.
    # Native Filament beginFrame already handles GPU backlog. Do not force an
    # extra app-level cadence limiter; model lighting/detail remain untouched.
    if 'frameBudgetNanos = bytes.length > 24 * 1024 * 1024' in s:
        # Allow user to keep the 30fps cap on very slow devices if necessary by
        # manually re-enabling it; here we use native Filament pacing.
        s=re.sub(r'frameBudgetNanos = bytes\.length > 24 \* 1024 \* 1024\s*\?[^;]+;',
                 'frameBudgetNanos = 0L; // Filament beginFrame handles backlog',s,count=1)
    return s

def act_patch(s):
    if TAG in s:
        if '_lastPlaneCheck' not in s:raise ValueError('Partial C# patch marker: source unchanged')
        return s
    for marker in ('private sealed class ArRenderer', 'HasNearbyTrackablePlane(frame, _width, _height)'):
        if marker not in s:raise ValueError('Unsupported C# ARCore source: '+marker)
    if 'var pos = new float[3]; anchor.Pose.GetTranslation(pos, 0);' in s:
        s=one(s,'        private readonly float[] _view = new float[16], _projection = new float[16];',
              '        // '+TAG+': reused ARCore pose buffer.\n        private readonly float[] _anchorPositionScratch = new float[3];\n        private readonly float[] _view = new float[16], _projection = new float[16];',
              'C# pose scratch field')
        s=one(s,'var pos = new float[3]; anchor.Pose.GetTranslation(pos, 0);',
              'var pos = _anchorPositionScratch;\n                    anchor.Pose.GetTranslation(pos, 0);',
              'C# pose reuse')
    elif 'var pos = _host.AnimalPosition(anchor);' in s:
        # Newer versions interpolate between two ARCore anchors for WALK.
        # Avoid allocating up to three float[3] arrays on EVERY camera frame.
        marker='    internal float[] AnimalPosition(Anchor current)'
        fields=('    // '+TAG+': reused exclusively on the ARCore GL thread.\n'
                '    private readonly float[] _walkStartPositionScratch = new float[3];\n'
                '    private readonly float[] _walkEndPositionScratch = new float[3];\n')
        s=one(s,marker,fields+marker,'Modern walking pose scratch fields')
        s=one(s,'        float[] start = new float[3];\n        current.Pose.GetTranslation(start, 0);',
              '        float[] start = _walkStartPositionScratch;\n        current.Pose.GetTranslation(start, 0);',
              'Reuse current anchor translation')
        s=one(s,'        float[] end = new float[3];\n        destination.Pose.GetTranslation(end, 0);',
              '        float[] end = _walkEndPositionScratch;\n        destination.Pose.GetTranslation(end, 0);',
              'Reuse walking destination translation')
        s=one(s,'        var pos = new float[3];\n        for (int i = 0; i < 3; i++) pos[i] = start[i] + (end[i] - start[i]) * eased;',
              '        for (int i = 0; i < 3; i++) start[i] += (end[i] - start[i]) * eased;',
              'Interpolate in place on GL thread')
        s=one(s,'        return pos;\n    }\n\n    // ARCore can create',
              '        return start;\n    }\n\n    // ARCore can create',
              'Return interpolated scratch pose')
    else:
        raise ValueError('AR camera position method changed; no files touched')
    old='if (System.Environment.TickCount64-_lastPlaneCheck>380)'
    if old in s:
        s=one(s,old,'if (_host._anchor is null && System.Environment.TickCount64-_lastPlaneCheck>380)',
              'Stop plane hit testing once animal placed')
    elif re.search(r'if\s*\(\s*_host\._anchor\s+is\s+null\s*&&[^)]*_lastPlaneCheck',s):
        pass
    else:
        raise ValueError('Plane-detection condition changed; no source modifications')
    return s

def safe_write(path, data):
    fd,tmp=tempfile.mkstemp(dir=str(path.parent),prefix='.hush_pose_v3_',suffix='.tmp')
    try:
        with os.fdopen(fd,'wb') as f: f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def decode(data):
    bom=b'\xef\xbb\xbf' if data.startswith(b'\xef\xbb\xbf') else b''
    content=data[len(bom):].decode('utf-8')
    nl='\r\n' if '\r\n' in content else '\n'
    return bom,content.replace('\r\n','\n'),nl

def main():
    a=argparse.ArgumentParser()
    mode=a.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true')
    mode.add_argument('--install',action='store_true')
    mode.add_argument('--rollback',action='store_true')
    a.add_argument('--root',type=Path,default=Path.cwd())
    args=a.parse_args(); root=args.root.resolve()
    if not (root/'WhiskerHunt.sln').is_file():raise ValueError('WhiskerHunt.sln not found in '+str(root))
    for rel in FILES:
        if not (root/rel).is_file():raise ValueError('Missing: '+str(root/rel))
    backup_root=root/BACKUPS
    if args.rollback:
        backups=sorted((x for x in backup_root.glob('PoseSync_*') if (x/'manifest.json').is_file()), reverse=True)
        if not backups:raise ValueError('No previous PoseSync V3 backup found.')
        selected=backups[0]
        manifest=json.loads((selected/'manifest.json').read_text(encoding='utf-8'))
        for rel in FILES:
            bak=selected/rel
            if not bak.is_file():raise ValueError('Incomplete backup; nothing changed.')
            installed_sha=manifest['installed_sha256'][str(rel)]
            current=hashlib.sha256((root/rel).read_bytes()).hexdigest()
            if current!=installed_sha:raise ValueError('Source changed after installation: '+str(rel)+'; refusing to overwrite it.')
        for rel in FILES:safe_write(root/rel,(selected/rel).read_bytes())
        print('ROLLBACK COMPLETE. Previous sources restored, GLBs unchanged.')
        return
    before={p:(root/p).read_bytes() for p in FILES}
    original={p:decode(before[p]) for p in FILES}
    after={JAVA:java_patch(original[JAVA][1]),ACT:act_patch(original[ACT][1])}
    result={p:original[p][0]+after[p].replace('\n',original[p][2]).encode('utf-8') for p in FILES}
    changed=[p for p in FILES if before[p]!=result[p]]
    for p in FILES:print(('Would update: ' if p in changed else 'Already patched: ')+str(p))
    if args.check:
        print('CHECK PASSED. No files modified.')
        return
    if not changed:
        print('INSTALL COMPLETED. Already installed.');return
    folder=backup_root/('PoseSync_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    for rel in FILES:
        dest=folder/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(before[rel])
    manifest={'tag':TAG,'installed_sha256':{str(p):hashlib.sha256(result[p]).hexdigest() for p in FILES},'original_sha256':{str(p):hashlib.sha256(before[p]).hexdigest() for p in FILES}}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    touched=[]
    try:
        for rel in changed:
            safe_write(root/rel,result[rel]);touched.append(rel)
    except Exception:
        for rel in touched:safe_write(root/rel,before[rel])
        raise
    print('INSTALL COMPLETED - source optimised. Backups:',folder)
    print('Clean Solution, Rebuild Solution, deploy onto installed Android app.')

if __name__=='__main__':
    try:main()
    except Exception as e:print('PATCH ABORTED: '+str(e),file=sys.stderr);sys.exit(1)
