#!/usr/bin/env python3
"""Safe source patch: lower latency HD overlay + shape-correct world-anchored shadow.
Fail closed on incompatible project, backup first, atomically write source, rollback.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,shutil,sys,tempfile
from pathlib import Path
from datetime import datetime
from generate_shadow_masks import generate

TAG='HUSH_B99_SURFACEVIEW_SILHOUETTE_AR_20261028'
JAVA=Path('WhiskerHunt/Platforms/Android/Java/com/hushhunt/filament/HushFilamentOverlay.java')
ACT=Path('WhiskerHunt/Platforms/Android/HushArCoreActivity.cs')
SHADOW=Path('WhiskerHunt/Platforms/Android/HushFloorShadow.cs')
ANIMAL=Path('WhiskerHunt/Platforms/Android/HushGlbAnimal3D.cs')
FILES=[JAVA,ACT,SHADOW,ANIMAL]

def one(s,o,n,why):
    count=s.count(o)
    if count!=1: raise ValueError(f'{why}: expected 1 occurrence of source anchor, saw {count}. Source unchanged.')
    return s.replace(o,n,1)

def patch_java(s):
    if TAG in s:return s
    for value in ('class HushFilamentOverlay','TextureView.SurfaceTextureListener','new TextureView(',
                  'swapChain = engine.createSwapChain(surface);','public void onSurfaceTextureAvailable(SurfaceTexture st, int width, int height)',
                  'public void onSurfaceTextureSizeChanged(SurfaceTexture st, int w, int h)'):
        if value not in s:raise ValueError('Unexpected Filament Java: '+value)
    s=one(s,'import android.graphics.SurfaceTexture;','import android.graphics.PixelFormat;','PixelFormat import')
    s=one(s,'import android.view.TextureView;','import android.view.SurfaceView;\nimport android.view.SurfaceHolder;','SurfaceHolder imports')
    s=one(s,'TextureView.SurfaceTextureListener,','SurfaceHolder.Callback,','SurfaceHolder interface')
    # Constructor setup is checked per statement, not as one exact five-line block.
    # This supports additional callbacks / formatting in later Build 99 patches.
    field = re.search(r'\bprivate\s+final\s+TextureView\s+([\w$]+)\s*;', s)
    if field is None:
        raise ValueError('TextureView field not found. Send current HushFilamentOverlay.java. Source unchanged.')
    field_name = field.group(1)
    if field_name != 'textureView':
        s = re.sub(r'\b'+re.escape(field_name)+r'\b', 'textureView', s)
    s=one(s,'private final TextureView textureView;','private final SurfaceView surfaceView;','surface field')
    constructor = r'\btextureView\s*=\s*new\s+TextureView\s*\([^;]*\)\s*;'
    matches = list(re.finditer(constructor, s))
    if len(matches) != 1:
        raise ValueError('TextureView constructor cannot be identified uniquely; send HushFilamentOverlay.java. Source unchanged.')
    s = re.sub(constructor, '''surfaceView = new SurfaceView(activity);
        // HUSH_B99_SURFACEVIEW_SILHOUETTE_AR_20261028
        // Transparent AR overlay above the ARCore camera surface.
        surfaceView.setZOrderMediaOverlay(true);
        surfaceView.getHolder().setFormat(PixelFormat.TRANSLUCENT);''', s, count=1)
    # TextureView-only calls cannot remain after conversion.
    s = re.sub(r'\btextureView\s*\.\s*setOpaque\s*\(\s*(?:true|false)\s*\)\s*;', '', s)
    listener = r'\btextureView\s*\.\s*setSurfaceTextureListener\s*\(\s*this\s*\)\s*;'
    if len(re.findall(listener, s)) != 1:
        raise ValueError('SurfaceTextureListener differs from supported setup; send HushFilamentOverlay.java. Source unchanged.')
    s = re.sub(listener, 'surfaceView.getHolder().addCallback(this);', s, count=1)
    if re.search(r'\btextureView\s*\.\s*(?:setSurfaceTextureListener|getSurfaceTexture|setOpaque)\s*\(', s):
        raise ValueError('Additional TextureView-only calls found. Source unchanged; send HushFilamentOverlay.java.')
    s=s.replace('textureView','surfaceView')
    s=one(s,'@Override public void onSurfaceTextureAvailable(SurfaceTexture st, int width, int height) {',
            '@Override public void surfaceCreated(SurfaceHolder holder) {\n        int width = Math.max(1, surfaceView.getWidth()), height = Math.max(1, surfaceView.getHeight());','surface callback')
    s=one(s,'surface = new Surface(st);','surface = holder.getSurface();','swapchain surface')
    s=one(s,'@Override public void onSurfaceTextureSizeChanged(SurfaceTexture st, int w, int h) {',
            '@Override public void surfaceChanged(SurfaceHolder holder, int format, int w, int h) {','resizing callback')
    s=one(s,'@Override public boolean onSurfaceTextureDestroyed(SurfaceTexture st) {\n        shutdownGpu();\n        return true;\n    }\n    @Override public void onSurfaceTextureUpdated(SurfaceTexture st) {}',
            '@Override public void surfaceDestroyed(SurfaceHolder holder) {\n        shutdownGpu();\n    }','destroy callback')
    s=one(s,'if (surface != null) { surface.release(); surface = null; }',
            '// SurfaceHolder owns its Surface; do not release it here.\n            surface = null;','surface ownership')
    if 'TextureView' in s and 'TextureView\'s' not in s:
        # Comments are harmless; only code references are forbidden.
        if 'new TextureView(' in s or 'import android.view.TextureView' in s:raise ValueError('Leftover TextureView references')
    return s

def patch_activity(s):
    if TAG in s:
        if '_filamentTargetMetres = metres;' not in s or '_floorShadow.Initialise(_host,' not in s:
            raise ValueError('Partially installed C# patch: refusing duplicate edits')
        return s
    if 'private HushFloorShadow? _floorShadow;' not in s: raise ValueError('HushArCoreActivity lacks HushFloorShadow reference')
    if 'private float _yawDegrees, _pitchDegrees;' not in s: raise ValueError('Yaw controls not installed')
    s=one(s,'private float _animalScale = 1f;', 'private float _animalScale = 1f;\n    private float _filamentTargetMetres = .65f; // HUSH_B99_SURFACEVIEW_SILHOUETTE_AR_20261028: shadow shares HD model normalisation','model size field')
    s=one(s,'_filamentRequested = modernHdAsset && HushFilamentBridge.TryInstall(this, _root, filename!, metres);',
          '_filamentTargetMetres = metres;\n        _filamentRequested = modernHdAsset && HushFilamentBridge.TryInstall(this, _root, filename!, metres);','target metres')
    s=one(s,'if (_animal is null)\n            {\n                try\n                {\n                    _floorShadow = new HushFloorShadow();\n                    _floorShadow.Initialise();',
          'if (_host._filamentRequested || _animal is not null)\n            {\n                try\n                {\n                    _floorShadow = new HushFloorShadow();\n                    _floorShadow.Initialise(_host, HushGlbAnimal3D.ResolveBundledFilename(_host._model, _host._species, _host._animalName));',
          'silhouette initialization')
    s=one(s,'_floorShadow?.Draw(_view, _projection, pos, .17f * scale);',
            '_floorShadow?.Draw(_view, _projection, pos, .5f * _host._filamentTargetMetres * scale, _host._yawDegrees);',
            'silhouette placement')
    # Latest version already avoids doing full legacy drawing when the HD renderer
    # is ready; replace generic fallback shadow with our matching footprint instead.
    # Preserve the legacy model's screen bounds (used for petting), but avoid
    # its ellipse contact shadow when an HD Filament silhouette is available.
    if 'shadowOnly: filamentReady,' not in s:
        raise ValueError('Expected standard/HD model switch and bounds projection')
    s=one(s,'shadowOnly: filamentReady,',
          'shadowOnly: filamentReady, hideShadow: true,',
          'suppress old ellipse only for HD')
    match=re.search(r'(?m)^([ \t]*)_animal\.Draw\(_view, _projection, pos, scale, petProgress,[\s\S]*?pitchDegrees: _host\._pitchDegrees\);',s)
    if not match:raise ValueError('Legacy draw block does not match B99')
    pos=match.end()
    s=s[:match.start()]+match.group(1)+'_floorShadow?.Draw(_view, _projection, pos, .5f * _host._filamentTargetMetres * scale, _host._yawDegrees);\n'+s[match.start():]
    return s

def patch_animal(s):
    if TAG in s:
        if 'hideShadow: filamentReady' in s: raise ValueError('Unexpected Activity named argument in model source')
        return s
    original='bool shadowOnly=false, float yawDegrees=0f, float pitchDegrees=0f)'
    revised='bool shadowOnly=false, float yawDegrees=0f, float pitchDegrees=0f, bool hideShadow=false) // HUSH_B99_SURFACEVIEW_SILHOUETTE_AR_20261028'
    s=one(s,original,revised,'legacy renderer signature')
    s=one(s,'GLES.GlDrawArrays(GLES.GlTriangleStrip,0,4);','if (!hideShadow) GLES.GlDrawArrays(GLES.GlTriangleStrip,0,4);','skip old generic shadow')
    return s

def atomic(path:Path,data:bytes):
    fd,tmp=tempfile.mkstemp(prefix='.hush_latency_shape_',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def main():
    ap=argparse.ArgumentParser(description='Hush Hunt: responsive HD AR overlay and animal-shaped shadows')
    ap.add_argument('--check',action='store_true')
    ap.add_argument('--rollback',action='store_true')
    args=ap.parse_args();root=Path.cwd().resolve()
    if not (root/'WhiskerHunt.sln').is_file():raise ValueError('Extract into solution folder containing WhiskerHunt.sln')
    backups=root/'HushHunt_AR_Performance_Backups'
    if args.rollback:
        cand=sorted([p for p in backups.glob('SurfaceSilhouette_*') if (p/'manifest.json').is_file()],reverse=True)
        if not cand:raise ValueError('No SurfaceSilhouette rollback found')
        saved=cand[0];manifest=json.loads((saved/'manifest.json').read_text(encoding='utf-8'))
        for rel in FILES:
            file=saved/rel
            if not file.exists():raise ValueError('Missing backup file: '+str(file))
        # leave the generated PNGs only if installed earlier; previous originals preserved
        for rel in FILES:atomic(root/rel,(saved/rel).read_bytes())
        print('RESTORED four source files from:',saved)
        print('Generated PNG silhouettes may remain; they are inert without this renderer.')
        return
    src={p:(root/p).read_bytes() for p in FILES}
    s={p:src[p].decode('utf-8-sig') for p in FILES}
    shadow=(Path(__file__).parent/'HushFloorShadow.cs.txt').read_text(encoding='utf-8')
    modified={JAVA:patch_java(s[JAVA]),ACT:patch_activity(s[ACT]),SHADOW:shadow,ANIMAL:patch_animal(s[ANIMAL])}
    # The tag guards repeat runs and makes the project version auditable.
    if TAG not in modified[JAVA] or '_floorShadow?.Draw' not in modified[ACT]:raise ValueError('Incomplete upgrade')
    changed=[p for p in FILES if s[p]!=modified[p]]
    print('PROJECT:',root)
    print('Validated Java SurfaceView and ARCore silhouette source changes.')
    for p in FILES:print('  '+('WOULD CHANGE ' if p in changed else 'UNCHANGED ')+str(p))
    if args.check:
        print('CHECK PASSED. No source files modified; GLBs and saves untouched.')
        return
    if changed:
        backup=backups/('SurfaceSilhouette_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
        for p in FILES:
            f=backup/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(src[p])
        (backup/'manifest.json').write_text(json.dumps({'tag':TAG,'original_sha256':{str(p):hashlib.sha256(src[p]).hexdigest() for p in FILES}},indent=2),encoding='utf-8')
        touched=[]
        try:
            for p in changed:
                buf=modified[p].encode('utf-8');atomic(root/p,buf);touched.append(p)
        except Exception:
            for p in touched:atomic(root/p,src[p])
            raise
        print('SOURCES PATCHED. Backup at:',backup)
    else:print('Already installed; source unchanged.')
    print('Generating optional animal footprint masks from installed GLBs (does not change original GLBs).')
    generate(root)
    print('COMPLETED. Visual Studio: Clean/Rebuild and deploy over existing installed app.')

if __name__=='__main__':
    try:main()
    except Exception as e:print('PATCH ABORTED:',e,file=sys.stderr);sys.exit(1)
