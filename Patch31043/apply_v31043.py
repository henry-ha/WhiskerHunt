#!/usr/bin/env python3
"""Hush Hunt v3.10.43 wildlife materials / animation pacing / duplicate catalogue fix.
Dry-run unless --apply. Backups include original GLBs. Python standard library only.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,os,re,shutil,sys,codecs
from model_materials import plan as glb_plan, update as glb_update

JAVA='Platforms/Android/Java/com/hushhunt/filament/HushFilamentOverlay.java'
BRIDGE='Platforms/Android/HushFilamentBridge.cs'
AR='Platforms/Android/HushArCoreActivity.cs'
CAT='Platforms/Android/HushWildlifeCatalog.cs'
WEB='Resources/Raw/app_v99.js'
WEB_ALT='Resources/Raw/app.js'
INDEX='Resources/Raw/index_v99.html'
MANIFEST='Resources/Raw/wildlife/manifest.json'
PROJ='WhiskerHunt.csproj'
FILES=[JAVA,BRIDGE,AR,CAT,WEB,WEB_ALT,INDEX,MANIFEST,PROJ]
REMOVED=['lion.glb','kangaroo_mouse_alternate.glb']
MARK='HUSH_31043_STEADY_ANIMATION'

def one(s,old,new,context):
    n=s.count(old)
    if n!=1:raise ValueError(f'{context}: expected one match, found {n}; no changes made')
    return s.replace(old,new,1)

def decode(raw):return raw.decode('utf-8-sig').replace('\r\n','\n')
def encode(s,orig):
    if b'\r\n' in orig:s=s.replace('\n','\r\n')
    b=s.encode('utf-8')
    if orig.startswith(codecs.BOM_UTF8):b=codecs.BOM_UTF8+b
    return b

def java_patch(s):
    if MARK in s:return s
    if 'HUSH_31042_COLOR_FRAME_COST' not in s:raise ValueError('Requires v3.10.42 Filament source; cannot safely patch this Java version')
    s=one(s,'    private long animationStartNanos;',
'''    // HUSH_31043_STEADY_ANIMATION: ensure animations advance while a camera pose is unchanged.
    private long animationStartNanos;
    private long lastLongFrameLogNanos;''','animation fields')
    s=one(s,'''            frameBudgetNanos = packagedGlbBytes >= 18 * 1024 * 1024
                ? 41_000_000L : 33_000_000L;  // ~24fps heavy, ~30fps other''',
'''            // 41ms against a 60Hz display quantises to 3 VSync intervals (~20fps).
            // Use 33ms for both paths; Filament's beginFrame handles GPU backlog.
            frameBudgetNanos = 33_000_000L;''','20fps stutter cadence')
    s=one(s,'''            if (generation == renderedGeneration || v == null || p == null || a == null) {
                scheduleFrame();
                return;
            }''',
'''            if (v == null || p == null || a == null) {
                scheduleFrame();
                return;
            }
            // With a valid anchor, a skinned animal can continue playing its
            // clip even when ARCore hasn't delivered another camera pose yet.
            // Static assets still avoid wasteful redraws of identical poses.
            if (generation == renderedGeneration && animationClipCount == 0) {
                scheduleFrame();
                return;
            }''','animation update gate')
    s=one(s,'''                // For single-clip walk exports, play gently in place when idle
                // rather than freezing. Proper idle clips run at normal speed.
                float speed = (!isWalking && idleClip == walkClip) ? .40f : 1f;''',
'''                // Most Meshy exports have exactly one 1-second baked clip.
                // The previous .40x speed made their motion appear to stop.
                float speed = 1f;''','animation playback speed')
    s=one(s,'''                renderer.render(view);
                renderer.endFrame();
                renderedGeneration = generation;''',
'''                renderer.render(view);
                renderer.endFrame();
                renderedGeneration = generation;
                if (nanos - lastRenderedNanos > 180_000_000L &&
                    nanos - lastLongFrameLogNanos > 3_000_000_000L && lastRenderedNanos != 0L) {
                    lastLongFrameLogNanos = nanos;
                    Log.w(TAG, "AR_OVERLAY_STALL_MS=" +
                        ((nanos - lastRenderedNanos) / 1_000_000L) + " animal=" + assetName);
                }''','render diagnostics')
    return s

def bridge_patch(s):
    if 'HUSH_31043_JNI_CACHE' in s:return s
    if 'internal static class HushFilamentBridge' not in s:raise ValueError('Unexpected bridge source')
    s=one(s,'    private static bool _installed;',
'''    // HUSH_31043_JNI_CACHE: cache the runtime-managed GLOBAL class ref and
    // method ID; avoid FindClass/GetStaticMethodID on the ARCore thread every frame.
    private static IntPtr _frameClass = IntPtr.Zero;
    private static IntPtr _frameMethod = IntPtr.Zero;
    private static bool _installed;''','JNI fields')
    s=one(s,'''                _installed = JNIEnv.CallStaticBooleanMethod(clazz, method,
                    new JValue(activity), new JValue(container), new JValue(text), new JValue(modelMetres));''',
'''                _installed = JNIEnv.CallStaticBooleanMethod(clazz, method,
                    new JValue(activity), new JValue(container), new JValue(text), new JValue(modelMetres));
                if (_installed && _frameMethod == IntPtr.Zero)
                {
                    _frameClass = clazz; // FindClass returns a managed global ref.
                    _frameMethod = JNIEnv.GetStaticMethodID(clazz, "submitFrame",
                        "([F[F[FFLjava/lang/Object;)V");
                }''','prepare cached method')
    s=one(s,'''            var clazz = JNIEnv.FindClass(JavaName);
            var method = JNIEnv.GetStaticMethodID(clazz, "submitFrame", "([F[F[FFLjava/lang/Object;)V");''',
'''            var clazz = _frameClass;
            var method = _frameMethod;
            if (clazz == IntPtr.Zero || method == IntPtr.Zero)
            {
                clazz = JNIEnv.FindClass(JavaName);
                method = JNIEnv.GetStaticMethodID(clazz, "submitFrame", "([F[F[FFLjava/lang/Object;)V");
                _frameClass = clazz;
                _frameMethod = method;
            }''','per-frame JNI method lookup')
    s=one(s,'''                JNIEnv.CallStaticVoidMethod(clazz, method, new JValue(isStroke));
            }
            finally { JNIEnv.DeleteLocalRef(clazz); }''',
'''                JNIEnv.CallStaticVoidMethod(clazz, method, new JValue(isStroke));
            }
            finally { /* FindClass is a managed global, not a local ref. */ }''','prevent deleting global JNI ref')
    return s

def ar_patch(s):
    if 'HUSH_31043_GEOMETRY_CACHE' in s:return s
    if 'HUSH_31042_COLOR_FRAME_COST' not in s:raise ValueError('Requires v3.10.42 AR source')
    s=one(s,'''        private bool _textureBound;''',
'''        private bool _textureBound;
        // HUSH_31043_GEOMETRY_CACHE: native display geometry changes only on resize/rotation.
        private int _lastGeometryRotation = -1, _lastGeometryW = -1, _lastGeometryH = -1;
        private long _lastArStallWarningMs;''','geometry cache fields')
    s=one(s,'''            _textureBound = false;
            _modelInitialised = false;''',
'''            _textureBound = false;
            _lastGeometryRotation = -1; // Rebind geometry after ARCore surface/session recreation.
            _modelInitialised = false;''','reset geometry on GL surface recreation')
    s=one(s,'''                session.SetDisplayGeometry((int)_host.WindowManager!.DefaultDisplay!.Rotation, _width, _height);
                var frame = session.Update();''',
'''                int rotation = (int)_host.WindowManager!.DefaultDisplay!.Rotation;
                if (rotation != _lastGeometryRotation || _width != _lastGeometryW || _height != _lastGeometryH)
                {
                    session.SetDisplayGeometry(rotation, _width, _height);
                    _lastGeometryRotation = rotation;
                    _lastGeometryW = _width;
                    _lastGeometryH = _height;
                }
                long arUpdateStart = System.Environment.TickCount64;
                var frame = session.Update();
                long arUpdateMs = System.Environment.TickCount64 - arUpdateStart;
                if (arUpdateMs > 90 && arUpdateStart - _lastArStallWarningMs > 3000)
                {
                    _lastArStallWarningMs = arUpdateStart;
                    JLog.Warn("HushHuntAR", $"ARCORE_UPDATE_STALL_MS={arUpdateMs}");
                }''','avoid redundant SetDisplayGeometry')
    return s

def catalog_patch(s):
    if 'HUSH_31043_CATALOG_86' in s:return s
    s=one(s,'    private static readonly Dictionary<string, Entry> Entries = new(StringComparer.Ordinal)',
'''    // HUSH_31043_CATALOG_86: Lion uses the requested alternate animated GLB.
    private static readonly Dictionary<string, Entry> Entries = new(StringComparer.Ordinal)''','catalog marker')
    s=one(s,'"wildlife/models/lion.glb", true),','"wildlife/models/lion_alternate.glb", true),','prefer alternate lion mesh')
    lines=s.splitlines(keepends=True)
    for term in ['["hh3d-lion-alternate"]','["hh3d-kangaroo-mouse-alternate"]']:
        hits=[i for i,line in enumerate(lines) if term in line]
        if len(hits)!=1:raise ValueError('Catalog duplicate entry '+term+' found '+str(len(hits)))
        lines.pop(hits[0])
    s=''.join(lines)
    return s

def web_patch(s,is_active):
    marker='const HUSH_3D_WILDLIFE'
    if marker not in s:raise ValueError('HUSH_3D_WILDLIFE missing from web selector')
    def replace_catalog(match):
        entries=json.loads(match.group(1))
        if len(entries)==86 and not any(e['key'] in ('hh3d-lion-alternate','hh3d-kangaroo-mouse-alternate') for e in entries):return match.group(0)
        if len(entries)!=88:raise ValueError(f'Expected 88 UI entries; found {len(entries)}')
        updated=[e for e in entries if e['key'] not in ('hh3d-lion-alternate','hh3d-kangaroo-mouse-alternate')]
        assert len(updated)==86
        return match.group(0).replace(match.group(1),json.dumps(updated,separators=(',',':'),ensure_ascii=False))
    pattern=r'(?:const HUSH_3D_WILDLIFE\s*=\s*)(\[[^\n]*\])'
    s,n=re.subn(pattern,replace_catalog,s,count=1)
    if n!=1:raise ValueError('Cannot locate web wildlife array')
    if is_active:
        s=one(s,"const WHISKER_BUILD='3.10.37', WHISKER_BUILD_NUMBER=100;",
            "const WHISKER_BUILD='3.10.43', WHISKER_BUILD_NUMBER=106;",'visible app build stamp') if "const WHISKER_BUILD='3.10.37', WHISKER_BUILD_NUMBER=100;" in s else s
    return s

def index_patch(s):
    return s.replace('content="3.10.38-101"','content="3.10.43-106"')

def manifest_patch(s):
    j=json.loads(s)
    animals=j.get('animals',[])
    if len(animals)==86:return s
    if len(animals)!=88:raise ValueError(f'Expected 88 manifest animals; found {len(animals)}')
    by={x['id']:x for x in animals}
    for id in ['lion','lion_alternate','kangaroo_mouse','kangaroo_mouse_alternate']:
        if id not in by:raise ValueError('Missing manifest '+id)
    preserved=by['lion'].copy(); alternate=by['lion_alternate']
    for key,value in alternate.items():
        if key not in ('id','name'):preserved[key]=value
    preserved['name']='Lion'
    animals=[preserved if x['id']=='lion' else x for x in animals if x['id'] not in ('lion_alternate','kangaroo_mouse_alternate')]
    j['animals']=animals
    j['modelCount']=len(animals)
    j['animatedModelCount']=sum(x.get('animated',False) for x in animals)
    j['staticModelCount']=len(animals)-j['animatedModelCount']
    j['releaseTarget']='Hush Hunt 3.10.43: 86 nonduplicate wildlife models'
    j['materialRepair']='base-color textures preserved, excessive emissive/specular factors normalised; elephant grey untextured fallback'
    return json.dumps(j,indent=2,ensure_ascii=False)+'\n'

def project_patch(s):
    if '<ApplicationDisplayVersion>3.10.43</ApplicationDisplayVersion>' in s:return s
    s=one(s,'<ApplicationDisplayVersion>3.10.42</ApplicationDisplayVersion>',
      '<ApplicationDisplayVersion>3.10.43</ApplicationDisplayVersion>','version label')
    return one(s,'<ApplicationVersion>105</ApplicationVersion>',
      '<ApplicationVersion>106</ApplicationVersion>','Android version code')

PATCH={JAVA:java_patch,BRIDGE:bridge_patch,AR:ar_patch,CAT:catalog_patch,
       WEB:lambda s:web_patch(s,True),WEB_ALT:lambda s:web_patch(s,False),
       INDEX:index_patch,MANIFEST:manifest_patch,PROJ:project_patch}

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for buf in iter(lambda:f.read(1024*1024),b''):h.update(buf)
    return h.hexdigest()

def main():
    pa=argparse.ArgumentParser(description=__doc__)
    pa.add_argument('--project-root',required=True,help='INNER folder containing WhiskerHunt.csproj')
    pa.add_argument('--apply',action='store_true',help='Apply after successful dry run')
    args=pa.parse_args()
    root=Path(args.project_root).resolve()
    if not (root/PROJ).is_file():sys.exit('NOT APPLIED: project root must contain WhiskerHunt.csproj')
    originals={};edited={}
    try:
        for name in FILES:
            raw=(root/name).read_bytes();originals[name]=raw
            edited[name]=encode(PATCH[name](decode(raw)),raw)
    except Exception as e:sys.exit('NOT APPLIED (source mismatch): '+str(e))
    changed=[name for name in FILES if edited[name]!=originals[name]]
    models=root/'Resources/Raw/wildlife/models'
    try:
        if not models.is_dir():raise ValueError('wildlife/models folder missing')
        present={p.name:p for p in models.glob('*.glb')}
        if not set(REMOVED).issubset(present) and not (len(present)==86 and not any(x in present for x in REMOVED)):
            raise ValueError('Unexpected wildlife model set; must have 88 baseline or 86 already-updated models')
        missing=set(REMOVED)-set(present)
        if len(present) not in (88,86):raise ValueError('Expected 88 or 86 GLBs; found '+str(len(present)))
        remaining=[p for k,p in sorted(present.items()) if k not in REMOVED]
        repairs=[x for x in remaining if glb_plan(x)['materials_changed']>0]
    except Exception as e:sys.exit('NOT APPLIED (models mismatch): '+str(e))
    print('Project:',root)
    print('Source changes:',len(changed),'/',len(FILES))
    print('GLBs:',len(present),'normalisations:',len(repairs),'duplicates removed:',len(REMOVED)-len(missing))
    print('New catalog: 86 animals. Preferred Lion = original Lion (Alternate) animated. Original scale settings unchanged.')
    print('Elephant: non-emissive matte-grey fallback; original model has no embedded texture.')
    if not args.apply:
        print('DRY RUN SUCCESS. Add --apply. Backup needs approximately 1GB free disk.');return
    if not changed and not repairs and missing==set(REMOVED):print('ALREADY INSTALLED.');return
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup=root.parent/'.hush_v31043_backup'/stamp
    backup.mkdir(parents=True,exist_ok=False)
    paths=changed+[str(x.relative_to(root)).replace('\\','/') for x in repairs]+[
        str(present[x].relative_to(root)).replace('\\','/') for x in REMOVED if x in present]
    paths=list(dict.fromkeys(paths))
    manifest={'root':str(root),'created':stamp,'files':{},'version':'3.10.43','complete':False}
    try:
        for rel in paths:
            target=root/rel;dest=backup/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(target,dest)
            manifest['files'][rel]={'original_sha256':sha(dest),'new_sha256':None}
        (backup/'backup_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        touched=[]
        for rel in changed:
            p=root/rel;tmp=p.with_name(p.name+'.hush31043.tmp')
            tmp.write_bytes(edited[rel]);os.replace(tmp,p);touched.append(rel)
        for item in repairs:
            rel=str(item.relative_to(root)).replace('\\','/')
            tmp=item.with_name(item.name+'.hush31043.tmp')
            glb_update(item,tmp);os.replace(tmp,item);touched.append(rel)
        for name in REMOVED:
            if name in present:
                p=present[name];rel=str(p.relative_to(root)).replace('\\','/')
                p.unlink();touched.append(rel)
        for rel in paths:
            current=root/rel
            manifest['files'][rel]['new_sha256']=sha(current) if current.is_file() else None
        manifest['complete']=True
        (backup/'backup_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    except Exception as e:
        for rel in paths:
            original=backup/rel;destination=root/rel
            if original.is_file():destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,destination)
        print('FAILED and originals restored:',e)
        sys.exit(1)
    print('APPLIED SUCCESSFULLY. Backup:',backup)
    print('In Visual Studio: Clean Solution, Rebuild Solution, deploy to phone. Check HushFilament / HushHuntAR Logcat.')

if __name__=='__main__':main()
