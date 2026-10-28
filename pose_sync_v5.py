#!/usr/bin/env python3
"""Hush Hunt B99 V5: defensive multi-variant AR performance patch.
Never change a matrix transform whose source form is not recognised.
"""
import argparse, datetime, hashlib, json, os, re, sys, tempfile
from pathlib import Path

TAG='HUSH_B99_POSESYNC_V5_20261028'
JAVA=Path('WhiskerHunt/Platforms/Android/Java/com/hushhunt/filament/HushFilamentOverlay.java')
CS=Path('WhiskerHunt/Platforms/Android/HushArCoreActivity.cs')
TARGETS=(JAVA,CS)
BACKUP_DIR='HushHunt_PoseSync_V5_Backups'

def sha(b): return hashlib.sha256(b).hexdigest()
def fmt(b):
    bom=b'\xef\xbb\xbf' if b.startswith(b'\xef\xbb\xbf') else b''
    text=b[len(bom):].decode('utf-8')
    return bom,text.replace('\r\n','\n'),'\r\n' if '\r\n' in text else '\n'
def encode(parts,text): return parts[0]+text.replace('\n',parts[2]).encode('utf-8')
def atomic_write(path,data):
    fd,temp=tempfile.mkstemp(prefix='.hush_v5_',suffix='.tmp',dir=str(path.parent))
    try:
        with os.fdopen(fd,'wb') as out:out.write(data);out.flush();os.fsync(out.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp): os.unlink(temp)

def once(s,old,new):
    if s.count(old)!=1: return s,False
    return s.replace(old,new,1),True

def java_change(source):
    notes=[]; s=source
    mandatory=('public final class HushFilamentOverlay', 'submitFrame(', 'renderer.beginFrame(swapChain, nanos)', 'void doFrame(long nanos)')
    if not all(x in s for x in mandatory):
        raise ValueError('HushFilamentOverlay.java is not recognised as a Filament B99 renderer. Source unchanged.')
    if TAG in s:
        notes.append('Already applied V5 Java optimisations')
        return s,notes
    # Move generation acknowledgement until the GPU actually presents the frame.
    # Older builds acknowledge before beginFrame, which skips frames on overload.
    if 'frameGeneration' in s and 'renderedGeneration' in s:
        body_start=s.index('void doFrame(long nanos)')
        begin=s.find('renderer.beginFrame(swapChain, nanos)',body_start)
        before=s.find('renderedGeneration = generation;',body_start,begin)
        if before>=0 and s.count('renderedGeneration = generation;')==1:
            edited=s[:before]+s[before+len('renderedGeneration = generation;'):]
            anchor='                renderer.endFrame();'
            if edited.count(anchor)==1:
                s=edited.replace(anchor,anchor+'\n                renderedGeneration = generation;',1)
                notes.append('Frame sync: acknowledge pose only after successful Filament endFrame')
            else:
                notes.append('Skipped frame-acknowledgement change: unsupported render block')
        else:
            notes.append('Frame sync: already deferred or source differs')
    else:
        notes.append('Frame sync: no generation fields; existing renderer cadence preserved')
    # Remove artificial HD frame-budget cap only when this known assignment exists.
    rule=r'(frameBudgetNanos\s*=\s*bytes\.length\s*>\s*24\s*\*\s*1024\s*\*\s*1024\s*\?[^;]+;)'
    matches=list(re.finditer(rule,s,re.S))
    if len(matches)==1:
        s=s[:matches[0].start()]+'frameBudgetNanos = 0L; // V5: Filament controls skipped GPU frames'+s[matches[0].end():]
        notes.append('Removed additional large-GLB 30 FPS limiter')
    elif 'frameBudgetNanos' in s:
        notes.append('Left existing frame budget unchanged (custom variant)')
    # Move only exact known buffer allocations into re-usable fields.
    field_anchor='    private float[] viewSnapshot;'
    if field_anchor in s:
        fields=[]
        for var,decl in [
            ('cameraWorldScratch','    private final float[] cameraWorldScratch = new float[16];'),
            ('worldScratch','    private final float[] worldScratch = new float[16];'),
            ('projectionScratch','    private final double[] projectionScratch = new double[16];'),
            ('lastProjection','    private final float[] lastProjection = new float[16];'),
        ]:
            if not re.search(r'\b'+var+r'\b',s):fields.append(decl)
        if fields:
            s=s.replace(field_anchor,'\n'.join(fields)+'\n'+field_anchor,1)
    # Camera matrix: independent of where/how model transform is implemented.
    cam='float[] cameraWorld = new float[16];'
    if s.count(cam)==1 and s.count('Matrix.invertM(cameraWorld, 0, v, 0)')==1 and s.count('camera.setModelMatrix(cameraWorld);')==1 and 'cameraWorldScratch' in s:
        s=s.replace(cam,'// V5: reuse cameraWorldScratch',1)
        s=s.replace('Matrix.invertM(cameraWorld, 0, v, 0)','Matrix.invertM(cameraWorldScratch, 0, v, 0)',1)
        s=s.replace('camera.setModelMatrix(cameraWorld);','camera.setModelMatrix(cameraWorldScratch);',1)
        notes.append('Reused AR camera matrix without allocations')
    elif 'Matrix.invertM(cameraWorldScratch, 0, v, 0)' in s:
        notes.append('Camera matrix: already cached')
    else:
        notes.append('Matrix transform differs: CAMERA matrix left unchanged safely')
    # World transform: only change a well-recognised transform; no changes to yaw/pitch/petting.
    world='float[] world = new float[16];'
    world_start=s.find(world)
    if s.count(world)==1 and world_start>=0 and 'worldScratch' in s:
        world_end=s.find('tm.setTransform(instance, world);',world_start)
        if world_end>=0 and world_end-world_start<2200 and 'Matrix.setIdentityM(world, 0)' in s[world_start:world_end]:
            sl=s[world_start:world_end+len('tm.setTransform(instance, world);')]
            sl=sl.replace(world,'// V5: reuse worldScratch',1)
            sl=re.sub(r'\bworld\b','worldScratch',sl)
            s=s[:world_start]+sl+s[world_end+len('tm.setTransform(instance, world);'):]
            notes.append('Reused model world matrix; preserved original transform order')
        else:notes.append('Matrix transform differs: WORLD matrix left unchanged safely')
    elif 'Matrix.setIdentityM(worldScratch, 0)' in s:
        notes.append('World matrix: already cached')
    else:
        notes.append('Matrix transform differs: WORLD matrix left unchanged safely')
    # Projection matrix: safe exact known sequence; skip differing variants.
    proj_re=re.compile(r'double\[\]\s+proj\s*=\s*new double\[16\];\s*for\s*\(int i = 0; i < 16; i\+\+\) proj\[i\] = p\[i\];\s*camera\.setCustomProjection\(proj, \.1, 80\.0\);')
    seq=list(proj_re.finditer(s))
    if len(seq)==1 and 'projectionScratch' in s and 'lastProjection' in s:
        block='''boolean projectionChanged = !projectionIsCached;
                    if (!projectionChanged) {
                        for (int i = 0; i < 16; i++) {
                            if (Math.abs(p[i] - lastProjection[i]) > 0.00001f) {
                                projectionChanged = true; break;
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
        s=s[:seq[0].start()]+block+s[seq[0].end():]
        if not re.search(r'\bboolean\s+projectionIsCached\b',s):
            s=s.replace(field_anchor,'    private boolean projectionIsCached;\n'+field_anchor,1)
        notes.append('Cached unchanging camera projection')
        # viewport resize invalidates projection; explicit state reset when surface initializes
        pattern='view.setViewport(new Viewport(0, 0, width, height));'
        if s.count(pattern)==1:
            s=s.replace(pattern,pattern+'\n            projectionIsCached = false;',1)
        resize='view.setViewport(new Viewport(0, 0, w, h));'
        if resize in s and 'projectionIsCached = false;' not in s[s.find('onSurfaceTextureSizeChanged'):s.find('onSurfaceTextureDestroyed') if 'onSurfaceTextureDestroyed' in s else len(s)]:
            s=s.replace(resize,resize+'\n        projectionIsCached = false;',1)
    elif 'camera.setCustomProjection(projectionScratch,' in s:
        notes.append('Projection: already cached')
    else:notes.append('Projection transform differs: left unchanged safely')
    # Avoid introducing brittle root handle caching: preserve renderable asset lifetime.
    # Light setting JNI on the main thread: safe recognised source shape.
    light='if (d.length >= 3 && intensity.length >= 3) {'
    if s.count(light)==1 and 'nanos - lastLightNanos' not in s:
        s=s.replace(light,'''if (d.length >= 3 && intensity.length >= 3 &&
                        nanos - lastLightNanos >= 250_000_000L) {
                        lastLightNanos = nanos;''',1)
        if 'private long lastLightNanos;' not in s:
            s=s.replace(field_anchor,'    private long lastLightNanos;\n'+field_anchor,1)
        notes.append('Limited HDR directional light JNI updates to 4 per second')
    elif 'lastLightNanos' in s:notes.append('HDR lighting already throttled')
    else:notes.append('HDR lighting differs: left unchanged')
    # Unlike V4, do not alter shadow casting or replace the existing species shadow.
    if s!=source and TAG not in s:
        s=s.replace('public final class HushFilamentOverlay', '// '+TAG+'\npublic final class HushFilamentOverlay',1)
    return s,notes

def csharp_change(source):
    notes=[];s=source
    if 'class HushArCoreActivity' not in s or 'class ArRenderer' not in s:
        raise ValueError('HushArCoreActivity.cs is not recognised as B99 ARCore source; nothing changed')
    if TAG in s:return s,['Already applied V5 ARCore optimisations']
    # Remove repeated hit testing only after a tracked model has been placed.
    condition='if (System.Environment.TickCount64-_lastPlaneCheck>380)'
    if s.count(condition)==1:
        s=s.replace(condition,'if (_host._anchor is null && System.Environment.TickCount64-_lastPlaneCheck>380)',1)
        notes.append('Stopped repeated plane scans after animal placement')
    elif re.search(r'if\s*\(\s*_host\._anchor\s+is\s+null\s*&&\s*System\.Environment\.TickCount64\s*-\s*_lastPlaneCheck',s):
        notes.append('Plane scans already placement-gated')
    else:notes.append('Plane-scan condition differs: unchanged')
    # Legacy source translation: avoid tiny float[3] allocations per frame.
    translation='var pos = new float[3]; anchor.Pose.GetTranslation(pos, 0);'
    anchor='private readonly float[] _view = new float[16], _projection = new float[16];'
    if s.count(translation)==1 and s.count(anchor)==1:
        s=s.replace(anchor,'private readonly float[] _anchorPositionV5 = new float[3];\n        '+anchor,1)
        s=s.replace(translation,'var pos = _anchorPositionV5; anchor.Pose.GetTranslation(pos, 0);',1)
        notes.append('Reused 3D anchor position array each ARCore camera frame')
    elif '_anchorPositionV5' in s or '_walkStartPositionScratch' in s:
        notes.append('ARCore anchor translation already reused')
    else:notes.append('Pose translation differs: left unchanged')
    if s!=source:
        s=s.replace('namespace WhiskerHunt;', 'namespace WhiskerHunt;\n// '+TAG,1)
    return s,notes

def find_root(path):
    p=path.resolve()
    for folder in [p,*p.parents]:
        if (folder/'WhiskerHunt.sln').is_file():return folder
    raise ValueError('WhiskerHunt.sln not found in patch folder or --root. Place package alongside .sln.')

def main():
    parser=argparse.ArgumentParser(description='Safe B99 AR frame performance checks')
    exclusive=parser.add_mutually_exclusive_group(required=True)
    for name in ('check','install','rollback'):exclusive.add_argument('--'+name,action='store_true')
    parser.add_argument('--root',type=Path,default=Path(__file__).parent)
    a=parser.parse_args();root=find_root(a.root)
    paths={f:root/f for f in TARGETS}
    if any(not f.is_file() for f in paths.values()):
        raise ValueError('Missing HushFilamentOverlay.java or HushArCoreActivity.cs in '+str(root))
    save_root=root/BACKUP_DIR
    if a.rollback:
        candidates=sorted((x for x in save_root.glob('V5_*') if (x/'manifest.json').is_file()),reverse=True)
        if not candidates:raise ValueError('No V5 rollback backup available')
        selected=candidates[0];meta=json.loads((selected/'manifest.json').read_text(encoding='utf-8'))
        for rel,path in paths.items():
            if not (selected/rel).is_file():raise ValueError('Incomplete backup; refusing rollback')
            if sha(path.read_bytes())!=meta['installed'][str(rel)]:
                raise ValueError('Source changed since patch: '+str(rel)+'; manual reconciliation needed')
        for rel,path in paths.items():atomic_write(path,(selected/rel).read_bytes())
        print('ROLLBACK COMPLETE - original source restored; models/app data untouched')
        return
    originals={f:path.read_bytes() for f,path in paths.items()}
    pieces={f:fmt(data) for f,data in originals.items()}
    updated={};report={}
    for f,fn in ((JAVA,java_change),(CS,csharp_change)):
        changed,notes=fn(pieces[f][1]);updated[f]=encode(pieces[f],changed);report[str(f)]=notes
    print('HUSH HUNT B99 POSE-SYNC V5 - '+('CHECK' if a.check else 'INSTALL'))
    print('Project:',root)
    for f in TARGETS:
        print(('UPDATE ' if updated[f]!=originals[f] else 'UNCHANGED ')+str(f))
        for note in report[str(f)]: print('  - '+note)
    if all(originals[f]==updated[f] for f in TARGETS):
        print('NO SOURCE UPDATES available for this source version. Send HushFilamentOverlay.java for a tailored patch.')
        return
    if a.check:
        print('CHECK PASSED: edits simulated, no project files changed.')
        return
    bk=save_root/('V5_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    for f,data in originals.items():
        dest=bk/f;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    manifest={'tag':TAG,'installed':{str(f):sha(updated[f]) for f in TARGETS},'original':{str(f):sha(originals[f]) for f in TARGETS},'notes':report}
    (bk/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    touched=[]
    try:
        for f,path in paths.items():
            if originals[f]!=updated[f]:atomic_write(path,updated[f]);touched.append(f)
    except BaseException:
        for f in touched:atomic_write(paths[f],originals[f])
        raise
    print('INSTALL COMPLETE. Backup:',bk)
    print('Clean, Rebuild, and deploy to your existing installed Android app.')
if __name__=='__main__':
    try:main()
    except Exception as exc:print('PATCH ABORTED: '+str(exc),file=sys.stderr);sys.exit(1)
