"""Lossless glTF structure migration: WebP textures -> PNG within a GLB.

Preserves mesh accessors, skins, animations, PBR slots and every unknown
extension except EXT_texture_webp. Does not alter vertex geometry.
Requires Pillow (py -m pip install Pillow) only when WebP images are present.
"""
from __future__ import annotations
import io, json, struct


def unpack_glb(blob:bytes):
    if len(blob)<20 or blob[:4]!=b'glTF' or struct.unpack_from('<II',blob,4)!=(2,len(blob)):
        raise ValueError('GLB 2.0 header/length mismatch')
    i=12; chunks=[]
    while i+8<=len(blob):
        size,tag=struct.unpack_from('<I4s',blob,i);i+=8
        if i+size>len(blob):raise ValueError('GLB chunk overrun')
        chunks.append((tag,blob[i:i+size]));i+=size
    if i!=len(blob) or not chunks or chunks[0][0]!=b'JSON':raise ValueError('GLB JSON chunk missing')
    doc=json.loads(chunks[0][1]);binary=next((v for tag,v in chunks if tag==b'BIN\0'),b'')
    return doc,bytearray(binary)


def pack_glb(doc:dict,binary:bytes):
    js=json.dumps(doc,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    js+=b' '*((-len(js))%4)
    binary+=b'\0'*((-len(binary))%4)
    length=12+8+len(js)+8+len(binary)
    return b'glTF'+struct.pack('<II',2,length)+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(binary),b'BIN\0')+binary


def normalize_webp(blob:bytes):
    doc,binary=unpack_glb(blob)
    images=doc.get('images',[]);textures=doc.get('textures',[])
    webp_indices=set(i for i,img in enumerate(images) if img.get('mimeType')=='image/webp')
    for texture in textures:
        e=texture.get('extensions',{}).get('EXT_texture_webp')
        if e and isinstance(e.get('source'),int):webp_indices.add(e['source'])
    if not webp_indices:return blob,0
    try:
        from PIL import Image
    except ImportError as e:
        raise RuntimeError('Pillow is required for Filament WebP compatibility: py -m pip install Pillow') from e
    converted={}
    for idx in sorted(webp_indices):
        if idx<0 or idx>=len(images):raise ValueError('Invalid WebP image reference')
        img=images[idx]
        view_idx=img.get('bufferView')
        if not isinstance(view_idx,int):raise ValueError('External WebP textures cannot be embedded without downloading resources')
        view=doc['bufferViews'][view_idx]
        if view.get('buffer',0)!=0:raise ValueError('WebP in an external GLB buffer')
        start=view.get('byteOffset',0);length=view.get('byteLength',0)
        if start<0 or length<=0 or start+length>len(binary):raise ValueError('Invalid WebP buffer view')
        with Image.open(io.BytesIO(binary[start:start+length])) as source:
            out=io.BytesIO()
            source.convert('RGBA').save(out,'PNG',optimize=True)
            png=out.getvalue()
        binary.extend(b'\0'*(-len(binary)%4))
        pos=len(binary);binary.extend(png)
        img['bufferView']=len(doc['bufferViews']);img['mimeType']='image/png'
        doc['bufferViews'].append({'buffer':0,'byteOffset':pos,'byteLength':len(png)})
        converted[idx]=True
    for texture in textures:
        extensions=texture.get('extensions',{})
        webp=extensions.pop('EXT_texture_webp',None)
        if webp and isinstance(webp.get('source'),int):texture['source']=webp['source']
        if not extensions:texture.pop('extensions',None)
    for key in ['extensionsUsed','extensionsRequired']:
        if key in doc:
            doc[key]=[e for e in doc[key] if e!='EXT_texture_webp']
            if not doc[key]:doc.pop(key)
    if 'buffers' not in doc or len(doc['buffers'])!=1:
        raise ValueError('Expected single embedded GLB buffer')
    doc['buffers'][0]['byteLength']=len(binary)
    out=pack_glb(doc,bytes(binary))
    checked,_=unpack_glb(out)
    assert 'EXT_texture_webp' not in checked.get('extensionsRequired',[])
    return out,len(converted)
