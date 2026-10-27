#!/usr/bin/env python3
"""Report exactly which models are installed as the primary Android assets.

Run: py tools\\check_installed_hd_assets.py
No network access or extra packages needed. Does not modify files.
"""
from pathlib import Path
import json, struct, hashlib
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'WhiskerHunt'/'Resources'/'Raw'
FILES={
 'Red Deer Stag':'other-deer.glb',
 'Labrador Retriever':'dog-labrador.glb',
 'Ginger Tabby':'cat-ginger-tabby.glb',
 'Grey Squirrel':'squirrel-grey-squirrel.glb'
}

def inspect(path):
    b=path.read_bytes()
    if len(b)<28 or b[:4]!=b'glTF' or struct.unpack_from('<II',b,4)!=(2,len(b)):
        return None
    n,tag=struct.unpack_from('<I4s',b,12)
    if tag!=b'JSON' or n>len(b)-20:return None
    d=json.loads(b[20:20+n])
    acc=d.get('accessors',[])
    tris=0
    for mesh in d.get('meshes',[]):
        for primitive in mesh.get('primitives',[]):
            idx=primitive.get('indices')
            pos=primitive.get('attributes',{}).get('POSITION')
            i=idx if idx is not None else pos
            if isinstance(i,int) and 0<=i<len(acc): tris+=acc[i].get('count',0)//3
    return dict(size=len(b),triangles=tris,materials=len(d.get('materials',[])),images=len(d.get('images',[])),animations=len(d.get('animations',[])),sha=hashlib.sha256(b).hexdigest()[:12],extensions=d.get('extensionsRequired',[]))

def main():
    for name,file in FILES.items():
        target=BASE/'ar_models'/file
        old=BASE/'ar_fallback'/file
        print('\n'+name+' ('+file+')')
        info=inspect(target) if target.exists() else None
        if info is None: print('  PRIMARY: MISSING OR INVALID FILE')
        else:
            print('  PRIMARY: {:,} triangles; {} materials; {} images; {} animations; {:,} bytes; SHA {}'.format(info['triangles'],info['materials'],info['images'],info['animations'],info['size'],info['sha']))
            print('  Required GLB extensions:', ', '.join(info['extensions']) or 'none')
            if info['images'] == 0:
                print('  QUALITY: no embedded image textures; likely flat-colour or procedural, NOT a textured realistic model')
            else:
                print('  QUALITY: embedded image textures present; inspect the model for believable anatomy and markings')
            if info['animations'] == 0: print('  ANIMATION: static model (tap reactions are procedural only)')
            print('  NOTE: triangle count is not a photorealism rating; check real animal anatomy/materials')
        if old.exists(): print('  Legacy OpenGL backup: yes')
        else: print('  Legacy OpenGL backup: none')
    print('\nIf your installed HD assets are listed above, Clean/Rebuild/Deploy without reinstalling the app.')

if __name__=='__main__':main()
