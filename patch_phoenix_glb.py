#!/usr/bin/env python3
"""Targeted Hush Hunt phoenix transparency/depth repair. Stdlib only; reversible."""
import argparse, json, struct, os, shutil, hashlib
from pathlib import Path

def glb_chunks(blob):
    if len(blob)<20 or blob[:4]!=b'glTF' or struct.unpack_from('<I',blob,4)[0]!=2 or struct.unpack_from('<I',blob,8)[0]!=len(blob):
        raise ValueError('Not a valid GLB v2 (header/length mismatch). Original file unchanged.')
    pos=12; chunks=[]
    while pos<len(blob):
        n,t=struct.unpack_from('<II',blob,pos);pos+=8
        if n<0 or n%4 or pos+n>len(blob):raise ValueError('Malformed GLB chunk. Original unchanged.')
        chunks.append((t,blob[pos:pos+n]));pos+=n
    if not chunks or chunks[0][0]!=0x4e4f534a:raise ValueError('Missing GLB JSON. Original unchanged.')
    return chunks

def patch_glb(blob):
    chunks=glb_chunks(blob)
    doc=json.loads(chunks[0][1])
    names=[]
    for mat in doc.get('materials',[]):
        if mat.get('alphaMode','OPAQUE')=='BLEND':
            mat['alphaMode']='MASK'
            mat['alphaCutoff']=0.38
            names.append(mat.get('name','unnamed'))
    if not names:return blob,names
    data=json.dumps(doc,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    data+=b' '*((-len(data))%4)
    chunks[0]=(chunks[0][0],data)
    result=bytearray(b'glTF'+struct.pack('<II',2,0))
    for kind, chunk in chunks:result+=struct.pack('<II',len(chunk),kind)+chunk
    struct.pack_into('<I',result,8,len(result))
    result=bytes(result)
    reparse=glb_chunks(result)
    if [x for x in reparse[1:]]!=[x for x in chunks[1:]]:
        raise AssertionError('Unexpected binary modification: aborting')
    if any(x.get('alphaMode')=='BLEND' for x in json.loads(reparse[0][1]).get('materials',[])):
        raise AssertionError('Transparency repair validation failed')
    return result,names

def find_target(root):
    root=root.resolve()
    options=[root/'WhiskerHunt'/'Resources'/'Raw'/'ar_models'/'fantasy-phoenix-bird.glb',
             root/'Resources'/'Raw'/'ar_models'/'fantasy-phoenix-bird.glb']
    found=[p for p in options if p.is_file()]
    if len(found)!=1:
        raise FileNotFoundError('Expected exactly one fantasy-phoenix-bird.glb in a WhiskerHunt/Resources/Raw/ar_models folder under '+str(root)+'; found '+str(len(found))+'. Specify --root correctly.')
    return found[0]

def main():
    parser=argparse.ArgumentParser(description='Fix phoenix GLB depth sorting without changing textures, meshes or animations')
    parser.add_argument('--root',default=r'E:\inetpub\wwwroot\WhiskerHunt')
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check',action='store_true')
    group.add_argument('--install',action='store_true')
    group.add_argument('--restore',action='store_true')
    args=parser.parse_args()
    path=find_target(Path(args.root)); backup=path.with_name(path.name+'.pre_depthfix_backup')
    if args.restore:
        if not backup.exists():raise FileNotFoundError('No original backup at '+str(backup))
        glb_chunks(backup.read_bytes())
        shutil.copy2(backup,path)
        print('RESTORED:',path);return
    before=path.read_bytes(); chunks=glb_chunks(before)
    doc=json.loads(chunks[0][1]); print('MODEL:',path)
    print('MATERIALS:',[(m.get('name'),m.get('alphaMode','OPAQUE')) for m in doc.get('materials',[])])
    after,changes=patch_glb(before)
    print('BLENDED MATERIALS REQUIRING MASKED DEPTH:',changes)
    if args.check:
        print('CHECK PASSED. Already repaired.' if not changes else 'CHECK PASSED. Ready to repair '+str(len(changes))+' materials.')
        return
    if not changes:
        print('ALREADY REPAIRED; no changes made.');return
    if not backup.exists():shutil.copy2(path,backup)
    temp=path.with_name(path.name+'.depthfix_tmp')
    try:
        temp.write_bytes(after)
        check=glb_chunks(temp.read_bytes());assert check[1:]==chunks[1:]
        os.replace(temp,path)
        print('INSTALL PASSED:',path)
        print('BACKUP:',backup)
        print('Changed material alphaMode BLEND -> MASK, alphaCutoff 0.38; preserved texture files, geometry, skin and animation data.')
        print('Now CLEAN/REBUILD in Visual Studio and test Phoenix at 1x first.')
    finally:
        if temp.exists():temp.unlink()

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('PATCH ABORTED:',type(exc).__name__+':',exc)
        raise SystemExit(1)
