#!/usr/bin/env python3
"""Non-destructive GLB 2.0 validator for Hush Hunt's installed 3D wildlife.

Examines *your local project files*. It does not fetch models, overwrite GLBs,
replace animal geometry, or claim to repair broken meshes.

Optional --prepare-webp prepares a separate GLB with WebP textures embedded as
PNG while preserving original mesh buffers, skinning, scene hierarchy, and PBR.
Needs Pillow ONLY if a WebP texture is present:
   py -m pip install Pillow
"""
from __future__ import annotations
import argparse, hashlib, json, struct, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MODELS=ROOT/'WhiskerHunt'/'Resources'/'Raw'/'ar_models'
FALLBACK=ROOT/'WhiskerHunt'/'Resources'/'Raw'/'ar_fallback'
OUT=ROOT/'HushHunt_GLB_Quality_Report.json'
TXT=ROOT/'HushHunt_GLB_Quality_Report.txt'
PREPARED=ROOT/'HushHunt_PBR_Review_Only'


def parse_glb(blob:bytes):
    if len(blob)<20 or blob[:4]!=b'glTF':
        raise ValueError('Missing GLB magic (glTF). This may not be a GLB file.')
    version,length=struct.unpack_from('<II',blob,4)
    if version!=2:raise ValueError('Expected glTF 2.0, version '+str(version))
    if length!=len(blob):raise ValueError(f'Header size {length} differs from actual {len(blob)}')
    p=12; chunks=[]
    while p+8<=len(blob):
        n,tag=struct.unpack_from('<I4s',blob,p);p+=8
        if n%4:raise ValueError('GLB chunk is not 4-byte aligned')
        if p+n>len(blob):raise ValueError('GLB chunk exceeds file length')
        chunks.append((tag,blob[p:p+n]));p+=n
    if p!=len(blob):raise ValueError('Trailing or partial GLB chunk data')
    if not chunks or chunks[0][0]!=b'JSON':raise ValueError('First GLB chunk must be JSON')
    doc=json.loads(chunks[0][1].decode('utf-8'))
    if not isinstance(doc,dict):raise ValueError('GLB JSON root is not an object')
    binary=next((data for tag,data in chunks if tag==b'BIN\x00'),b'')
    buffers=doc.get('buffers',[])
    if buffers and len(buffers)==1 and not buffers[0].get('uri'):
        declared=int(buffers[0].get('byteLength',0))
        if declared>len(binary):raise ValueError('Declared embedded buffer length exceeds BIN chunk')
    for i,v in enumerate(doc.get('bufferViews',[])):
        if v.get('buffer',0)==0 and (v.get('byteOffset',0)+v.get('byteLength',0))>len(binary):
            raise ValueError(f'BufferView {i} extends past embedded BIN data')
    return doc,binary


def describe(path:Path):
    record={'file':path.name,'bytes':path.stat().st_size,'sha256':None,'valid_glb':False,
            'status':'','issues':[],'warnings':[],'notes':[]}
    try:
        blob=path.read_bytes()
        record['sha256']=hashlib.sha256(blob).hexdigest()
        doc,binary=parse_glb(blob)
        record['valid_glb']=True
        meshes=doc.get('meshes',[])
        tri=0
        for mesh in meshes:
            for prim in mesh.get('primitives',[]):
                if prim.get('mode',4)!=4:continue
                ix=prim.get('indices')
                if isinstance(ix,int) and ix<len(doc.get('accessors',[])):
                    count=doc['accessors'][ix].get('count',0)
                else:
                    pos=prim.get('attributes',{}).get('POSITION')
                    count=doc['accessors'][pos].get('count',0) if isinstance(pos,int) and pos<len(doc.get('accessors',[])) else 0
                tri+=count//3
        imgs=doc.get('images',[]);mats=doc.get('materials',[])
        exts=sorted(set(doc.get('extensionsRequired',[])))
        used=sorted(set(doc.get('extensionsUsed',[])))
        alpha=[x.get('alphaMode','OPAQUE') for x in mats]
        textured=sum(bool(m.get('pbrMetallicRoughness',{}).get('baseColorTexture')) for m in mats)
        image_types=[(img.get('mimeType') or ('external URI' if img.get('uri') else 'unspecified')) for img in imgs]
        record.update(triangles=tri,meshes=len(meshes),images=len(imgs),image_formats=image_types,
            pbr_base_color_textured_materials=textured,materials=len(mats),alpha_modes=alpha,
            skins=len(doc.get('skins',[])),animations=len(doc.get('animations',[])),
            extensions_required=exts,extensions_used=used)
        if not meshes or tri<=0:record['issues'].append('NO_RENDERABLE_TRIANGLE_MESH')
        if len(imgs)==0:record['warnings'].append('NO_IMAGE_TEXTURES: flat-looking fallback likely')
        if textured==0 and mats:record['warnings'].append('NO_PBR_BASE_COLOR_TEXTURE: coat/eye detail may be absent')
        if any(img.get('uri') for img in imgs):record['issues'].append('EXTERNAL_IMAGE_URI: binary GLB may be missing required textures')
        if any(b.get('uri') for b in doc.get('buffers',[])):record['issues'].append('EXTERNAL_BUFFER_URI: GLB is not self-contained')
        if 'EXT_texture_webp' in used or 'image/webp' in image_types:
            record['warnings'].append('WEBP_TEXTURE: some viewers/renderers cannot decode this; try --prepare-webp')
        if 'KHR_texture_basisu' in used or 'image/ktx2' in image_types:
            record['warnings'].append('KTX2_BASISU: requires a compatible decoder; PNG conversion not supported by this utility')
        for ext in ('EXT_meshopt_compression','KHR_draco_mesh_compression'):
            if ext in used:record['warnings'].append('COMPRESSED_MESH_'+ext+': requires mesh decompression in viewer/loader')
        if 'KHR_mesh_quantization' in used:
            record['notes'].append('Quantised mesh: normal glTF 2.0 extension; not supported by Hush Hunt legacy renderer')
        if any(mode in ('MASK','BLEND') for mode in alpha):
            record['notes'].append('Transparent/cutout fur cards need correct alpha blending and material rendering')
        if doc.get('skins') or doc.get('animations') or any(prim.get('targets') for mesh in meshes for prim in mesh.get('primitives',[])):
            record['notes'].append('Rigging/animation/morph targets present; static fallback conversion can lose anatomical details')
        if not record['issues']:record['status']='STRUCTURALLY_VALID; rendering not proven'
        else:record['status']='STRUCTURALLY_VALID_BUT_DEPENDENCIES_OR_MESH_ISSUES'
    except Exception as err:
        record['status']='INVALID_OR_UNREADABLE'
        record['issues'].append(type(err).__name__+': '+str(err))
    return record


def run(prepare=False):
    if not MODELS.is_dir():
        raise SystemExit('Cannot find Resources/Raw/ar_models. Extract this patch to the Hush Hunt project root.')
    models=sorted(MODELS.glob('*.glb'))
    result={'title':'Hush Hunt original-versus-fallback GLB inspection','original_dir':str(MODELS),
            'note':'This is a structural audit, not a visual model QA approval. It never overwrites original GLBs.',
            'model_count':len(models),'models':[]}
    lines=['HUSH HUNT - GLB COMPATIBILITY AND QUALITY CHECK',
           'No model files were overwritten. Structure OK does NOT mean that anatomy, eyes, materials or render are correct.',
           f'Original animal files checked: {len(models)}','']
    if prepare:PREPARED.mkdir(exist_ok=True)
    for path in models:
        item=describe(path)
        other=FALLBACK/path.name
        if other.is_file():
            back=describe(other)
            item['fallback']={k:back.get(k) for k in ('status','bytes','triangles','images','materials','pbr_base_color_textured_materials','skins','animations','issues','warnings')}
            if (item.get('images',0)>back.get('images',0) or
                item.get('pbr_base_color_textured_materials',0)>back.get('pbr_base_color_textured_materials',0)):
                item['issues'].append('DEGRADED_FALLBACK: fallback lost one or more original textures/PBR materials')
            if item.get('skins',0)>back.get('skins',0) or item.get('animations',0)>back.get('animations',0):
                item['issues'].append('DEGRADED_FALLBACK: fallback lost skinning/animation')
        if prepare and item['valid_glb'] and any('WEBP_TEXTURE' in w for w in item['warnings']):
            try:
                from hush_glb_compat import normalize_webp
                result_bytes,n=normalize_webp(path.read_bytes())
                parse_glb(result_bytes)
                dest=PREPARED/path.name
                if dest.exists():
                    item['prepared_copy']='ALREADY_EXISTS (not overwritten): '+str(dest)
                else:
                    dest.write_bytes(result_bytes)
                    item['prepared_copy']=str(dest)
                    item['converted_webp_images']=n
            except Exception as exc:
                item['issues'].append('WEBP_PREPARATION_FAILED: '+str(exc))
        result['models'].append(item)
        lines.append(path.name+f" | {item['status']} | triangles={item.get('triangles','?')} | images={item.get('images','?')}")
        for problem in item['issues']:lines.append('  ISSUE: '+problem)
        for warning in item['warnings']:lines.append('  WARNING: '+warning)
        if 'prepared_copy' in item:lines.append('  REVIEW COPY: '+item['prepared_copy'])
    issues=sum(bool(x['issues']) for x in result['models'])
    result['models_with_issues']=issues
    lines+=['',f'{issues} / {len(models)} models have structural issues or potentially degraded fallbacks.',
            'Use the original GLB for Filament; do not replace it with an unverified simplified fallback.',
            'WebP review copies stay in HushHunt_PBR_Review_Only, NOT in the app asset folder.',
            'If a model does not render in AR, capture Logcat messages tagged HushFilament.',
            'For visible anatomy / missing eyes / fur problems, inspect original GLB in Blender or a glTF-compatible viewer.']
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    TXT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines[:25]));print('\nFull reports:',OUT,TXT)
    return 0

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--prepare-webp',action='store_true',help='Create separate WebP-to-PNG copies without touching installed models')
    args=parser.parse_args()
    sys.exit(run(args.prepare_webp))
