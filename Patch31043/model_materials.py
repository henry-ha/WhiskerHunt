#!/usr/bin/env python3
"""Lossless-to-mesh GLB material normalization, Python standard library only.
Does not touch BIN payload, vertex positions, skeleton, animation channels or texture pixels.
"""
from pathlib import Path
import json,struct,shutil,hashlib

MAGIC=b'glTF'

def read_info(path):
    with open(path,'rb') as f:
        header=f.read(20)
        if len(header)!=20: raise ValueError('GLB header too short: '+str(path))
        magic,version,total,json_len,kind=struct.unpack('<4sIIII',header)
        if magic!=MAGIC or version!=2 or kind!=0x4E4F534A: raise ValueError('Invalid GLB 2.0: '+str(path))
        if total!=Path(path).stat().st_size or json_len<2 or json_len>32*1024*1024:
            raise ValueError('Invalid GLB length: '+str(path))
        j=json.loads(f.read(json_len))
    return j,json_len,total

def adjust(j,stem):
    count=0
    for m in j.get('materials',[]):
        orig=json.dumps(m,sort_keys=True)
        fantasy= any(t in stem for t in ('phoenix','dragon','celestial','nebula','thunderbird'))
        if 'emissiveFactor' in m:
            m['emissiveFactor']=[0.12,0.12,0.12] if fantasy and 'emissiveTexture' in m else [0,0,0]
        ext=m.get('extensions',{}).get('KHR_materials_specular')
        if ext and 'specularColorFactor' in ext:
            ext['specularColorFactor']=[min(1.0,max(0.0,float(v))) for v in ext['specularColorFactor']]
        # The original Elephant is genuinely textureless and has a pure white
        # base colour + full-strength emission. Make it matte grey rather than
        # claiming to recreate a photographic texture that never existed.
        if stem=='elephant':
            if j.get('images'):raise ValueError('Elephant has real images; refusing grey override')
            pbr=m.setdefault('pbrMetallicRoughness',{})
            pbr['baseColorFactor']=[0.43,0.46,0.49,1.0]
            pbr['metallicFactor']=0.0
            pbr['roughnessFactor']=0.94
            m['emissiveFactor']=[0,0,0]
        if json.dumps(m,sort_keys=True)!=orig:count+=1
    return count

def plan(path):
    j,old_json_len,total=read_info(path)
    name=Path(path).stem.lower()
    count=adjust(j,name)
    return {'path':str(path),'materials_changed':count,'old_json_len':old_json_len,'total_bytes':total,
            'images':len(j.get('images',[])),'animations':len(j.get('animations',[]))}

def update(path,outpath):
    path=Path(path); outpath=Path(outpath)
    j,old_json_len,total=read_info(path)
    changed=adjust(j,path.stem.lower())
    if not changed:
        shutil.copy2(path,outpath)
        return False
    jb=json.dumps(j,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    jb+=b' ' *((-len(jb))%4)
    delta=len(jb)-old_json_len
    outpath.parent.mkdir(parents=True,exist_ok=True)
    with open(path,'rb') as src,open(outpath,'wb') as dst:
        src.seek(20+old_json_len)
        dst.write(struct.pack('<4sI',MAGIC,2))
        dst.write(struct.pack('<I',total+delta))
        dst.write(struct.pack('<II',len(jb),0x4E4F534A))
        dst.write(jb)
        shutil.copyfileobj(src,dst,1024*1024)
    read_info(outpath)
    return True

if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser();a.add_argument('file');a.add_argument('out');args=a.parse_args()
    print('Changed:',update(args.file,args.out))
