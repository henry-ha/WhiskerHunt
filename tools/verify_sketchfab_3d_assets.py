"""Non-destructive Hush Hunt 3D asset and renderer sanity report (stdlib only)."""
from __future__ import annotations
import json, struct, hashlib, csv, sys
from pathlib import Path

SLOTS = {
    'cat-sumpitueslag-cat.glb': 'Sumpitueslag Cat',
    'cat-cat-in-motion.glb': 'Cat in Motion',
    'bird-bald-eagle-catching-fish.glb': 'Bald Eagle Catching Fish',
    'dog-jack-russell-puppy.glb': 'Jack Russell Puppy',
    'fantasy-phoenix-bird.glb': 'Phoenix Bird'
}


def validate(path:Path):
    # Header and JSON parse only: no expensive mesh allocation or source edits.
    with path.open('rb') as fp:
        header=fp.read(20)
        if len(header)<20:raise ValueError('truncated header')
        magic,version,size,json_len,kind=struct.unpack('<5I',header)
        if magic!=0x46546C67 or version!=2 or kind!=0x4E4F534A:raise ValueError('not glTF 2.0 GLB')
        if size!=path.stat().st_size: raise ValueError('GLB header/file size mismatch')
        if json_len<=0 or json_len>size-20:raise ValueError('bad JSON chunk length')
        data=json.loads(fp.read(json_len))
    extensions=data.get('extensionsRequired',[])
    return {
        'status':'VALID','bytes':size,'materials':len(data.get('materials',[])),
        'embedded_images':sum('bufferView' in i for i in data.get('images',[])),
        'meshes':len(data.get('meshes',[])),
        'animations':len(data.get('animations',[])),
        'required_extensions':';'.join(extensions),
        'large_model_warning':size > 24*1024*1024
    }


def main():
    root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
    model_dir=root/'WhiskerHunt'/'Resources'/'Raw'/'ar_models'
    if not model_dir.exists():
        model_dir=root/'Resources'/'Raw'/'ar_models'
    if not model_dir.exists():
        print('ERROR: Pass the solution root containing WhiskerHunt/Resources/Raw/ar_models.')
        return 2
    java=root/'WhiskerHunt'/'Platforms'/'Android'/'Java'/'com'/'hushhunt'/'filament'/'HushFilamentOverlay.java'
    if not java.exists():java=root/'Platforms'/'Android'/'Java'/'com'/'hushhunt'/'filament'/'HushFilamentOverlay.java'
    rows=[]
    for file,name in SLOTS.items():
        path=model_dir/file
        row={'animal':name,'file':file}
        if not path.is_file():row['status']='MISSING'
        else:
            try:row.update(validate(path))
            except Exception as exc:row['status']='ERROR: '+str(exc)
        rows.append(row)
    print('Hush Hunt: 5 Sketchfab source assets')
    for r in rows:
        print('  %-30s %-8s %8.1f MiB %2s embedded images'%(r['animal'],r['status'],r.get('bytes',0)/1048576,r.get('embedded_images','?')))
    if java.exists():
        j=java.read_text(encoding='utf-8')
        print('\nRenderer source:',java)
        print('  64 MiB asset guard:', '64 * 1024 * 1024' in j)
        print('  GPU readback stops after visible frame:', '!visibleAnimalPixels && nanos - lastPixelValidationNanos' in j)
        print('  neutral camera exposure:', 'camera.setExposure(4.0f, 1f / 80f, 100f)' in j)
    else: print('Renderer source not found (source installation not verified).')
    path=root/'HushHunt_Sketchfab_Asset_Audit.json'
    path.write_text(json.dumps(rows,indent=2),encoding='utf-8')
    print('\nSaved:',path)
    return 1 if any(r['status']!='VALID' for r in rows) else 0
if __name__=='__main__':sys.exit(main())
