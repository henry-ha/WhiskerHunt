#!/usr/bin/env python3
"""Hush Hunt realistic wildlife candidates: manual-review-first downloader/importer.
Uses only the standard Python library; does not alter existing app data.
Files from 1DesignTool are downloaded on the owner's own computer and are not
redistributed in this tool package per https://1designtool.com/3d/license.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import urllib.request

SOURCES = {
 "red-panda": dict(name="Red Panda", slot="other-red-panda.glb", url="https://assets.stoicsoft.com/1designtool/3d/models/red-panda/b6d19ad658/model.glb", page="https://1designtool.com/3d/models/red-panda", expected_triangles=111432, notes="Static; contains a mossy log. Do NOT use for walk animation without removing log/rigging."),
 "zebra": dict(name="Plains Zebra", slot="other-plains-zebra.glb", url="https://assets.stoicsoft.com/1designtool/3d/models/plains-zebra/5a3fc109e4/model.glb", page="https://1designtool.com/3d/models/plains-zebra", expected_triangles=93816, notes="Static; striped PBR textures and eyes. Evaluate in 3D viewer."),
 "wolf": dict(name="Gray Wolf", slot="other-grey-wolf.glb", url="https://assets.stoicsoft.com/1designtool/3d/models/gray-wolf/86f3f0dfb8/model.glb", page="https://1designtool.com/3d/models/gray-wolf", expected_triangles=94521, notes="Static; fur cards; may require correct alpha MASK handling."),
 "fox": dict(name="Red Fox", slot="other-fox.glb", url="https://assets.stoicsoft.com/1designtool/3d/models/red-fox/ef36760168/model.glb", page="https://1designtool.com/3d/models/red-fox", expected_triangles=116808, notes="Static sitting fox. Not suitable for walking without new animation/rig."),
 "kangaroo": dict(name="Red Kangaroo", slot="other-red-kangaroo.glb", url="https://assets.stoicsoft.com/1designtool/3d/models/red-kangaroo/55373afdfe/model.glb", page="https://1designtool.com/3d/models/red-kangaroo", expected_triangles=104260, notes="Static standing pose. Not suitable for hopping without rigging."),
}
LICENSE_PAGE = "https://1designtool.com/3d/license"
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT = SCRIPT_DIR.parent
STAGING = PROJECT / "HushHunt_Realistic_Model_Candidates"
BACKUPS = PROJECT / "HushHunt_Realistic_Asset_Backups"
MODELS = PROJECT / "WhiskerHunt" / "Resources" / "Raw" / "ar_models"


def inspect_glb(path):
    path = Path(path)
    with path.open("rb") as f:
        raw = f.read(12)
        if len(raw) != 12:
            raise ValueError("GLB header is too short")
        magic, version, length = struct.unpack("<4sII", raw)
        if magic != b"glTF" or version != 2:
            raise ValueError("Not a binary glTF 2.0 file")
        if length != path.stat().st_size:
            raise ValueError(f"GLB declared size {length} differs from actual {path.stat().st_size}")
        ch = f.read(8)
        if len(ch) < 8: raise ValueError("Missing JSON chunk")
        jsonlen, jsontype = struct.unpack("<I4s", ch)
        if jsontype != b"JSON" or jsonlen > 30*1024*1024:
            raise ValueError("Invalid or oversized JSON chunk")
        doc = json.loads(f.read(jsonlen).decode("utf-8"))
        if 'asset' not in doc or not str(doc['asset'].get('version', '')).startswith('2'):
            raise ValueError("Missing glTF 2 asset information")
        triangles = 0
        accessors = doc.get('accessors', [])
        for mesh in doc.get('meshes', []):
            for prim in mesh.get('primitives', []):
                if prim.get('mode', 4) == 4:
                    idx = prim.get('indices')
                    if isinstance(idx, int) and idx < len(accessors):
                        triangles += accessors[idx].get('count', 0) // 3
                    else:
                        p = prim.get('attributes', {}).get('POSITION', -1)
                        if isinstance(p, int) and p < len(accessors):
                            triangles += accessors[p].get('count',0)//3
        image_count = len(doc.get('images', []))
        material_count = len(doc.get('materials', []))
        named_eyes = [n.get('name','') for n in doc.get('nodes', []) if 'eye' in n.get('name','').lower()]
        alpha_materials = [m.get('name','') or '(unnamed)' for m in doc.get('materials', []) if m.get('alphaMode','OPAQUE') != 'OPAQUE']
        return {"path":str(path), "bytes":path.stat().st_size, "sha256":_hash(path), "triangles":triangles, "images":image_count,
                "materials":material_count, "animations":len(doc.get('animations',[])), "skins":len(doc.get('skins',[])),
                "extensionsRequired":doc.get('extensionsRequired',[]), "eye_nodes":named_eyes, "transparent_materials":alpha_materials}


def _hash(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def report(species, model_path, label):
    try: data = inspect_glb(model_path)
    except Exception as e: print(f'  {label}: INVALID - {e}');return None
    print(f'  {label}: {data["triangles"]:,} tris, {data["images"]} images, {data["materials"]} materials, {data["animations"]} animations, {data["skins"]} skins')
    if not data['images']:print('  WARNING: No embedded texture images; may look unpainted')
    if data['extensionsRequired']:print('  Requires extensions:', ', '.join(data['extensionsRequired']))
    if data['transparent_materials']:print('  Transparency materials:',len(data['transparent_materials']),'; ensure alpha MASK/BLEND handled')
    print(f'  SHA256 {data["sha256"]}')
    return data


def download_one(key):
    spec=SOURCES[key]
    STAGING.mkdir(parents=True,exist_ok=True)
    target=STAGING/spec['slot']
    print('\n' + spec['name'] + ': downloading publisher GLB (staging only)')
    print('Source:',spec['page'])
    if target.exists():
        print('Already staged:',target)
        if report(key,target,'staged'): return
        print('Invalid existing staging file; replacing')
    req=urllib.request.Request(spec['url'], headers={'User-Agent':'Mozilla/5.0 (HushHunt asset review; user initiated)'})
    part=target.with_suffix('.glb.partial')
    try:
        with urllib.request.urlopen(req,timeout=50) as response, part.open('wb') as out:
            final_url = response.geturl()
            if not final_url.startswith('https://assets.stoicsoft.com/'):
                raise ValueError('Unexpected download host: '+final_url)
            size=0
            while True:
                block=response.read(1024*1024)
                if not block: break
                size+=len(block)
                if size>100*1024*1024: raise ValueError('Download exceeds 100 MB safety limit')
                out.write(block)
        check=inspect_glb(part)
        if not check['triangles'] or check['images'] < 1:
            raise ValueError('Model missing triangles or embedded images')
        part.replace(target)
        report(key,target,'downloaded')
        print('STAGED ONLY (not installed):',target)
    except Exception as exc:
        print('DOWNLOAD FAILED:',exc)
    finally:
        if part.exists(): part.unlink()


def install_one(key, from_path=None):
    spec=SOURCES[key]
    candidate=Path(from_path) if from_path else STAGING/spec['slot']
    if not candidate.is_file():
        print('Candidate not found:',candidate,'(run fetch first, or supply --file for a licensed model)');return
    check=report(key,candidate,'candidate')
    if not check:return
    if check['images']<1:
        print('REFUSED: untextured candidate.');return
    if not MODELS.is_dir():
        print('REFUSED: project model folder not found:',MODELS);return
    target=MODELS/spec['slot']
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backupdir=BACKUPS/key/stamp
    backupdir.mkdir(parents=True,exist_ok=False)
    if target.is_file():
        shutil.copy2(target,backupdir/target.name)
        print('Backup:',backupdir/target.name)
    shutil.copy2(candidate,target)
    manifest={"species":key,"slot":spec['slot'],"original_sha256":_hash(backupdir/target.name) if (backupdir/target.name).exists() else None,
              "installed_sha256":_hash(target),"source_page":spec['page'] if from_path is None else 'user-licensed local file',
              "installed_at":datetime.datetime.now().isoformat(),"limitations":spec['notes'],"license":LICENSE_PAGE if from_path is None else 'check user-purchased licence'}
    (backupdir/'restore_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('INSTALLED:',target)
    print('WARNING: You must rebuild and deploy app. This model is static unless it contains animations. Do not uninstall app.')
    print('To restore, copy backup GLB back to',target)


def audit():
    if not MODELS.is_dir():print('Project models folder missing:',MODELS);return
    print('Auditing current five replacement slots ...')
    rows=[]
    for key,s in SOURCES.items():
        print('\n'+s['name'])
        p=MODELS/s['slot']
        result=report(key,p,'installed') if p.exists() else None
        rows.append({"species":key,"model_slot":s['slot'],"audit":result})
    output=PROJECT/'HushHunt_Realistic_Asset_Audit.json'
    output.write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
    print('\nSaved',output)


def main():
    ap=argparse.ArgumentParser(description='Download vetted GLBs to staging, inspect, and optionally install them. No downloads included in ZIP.');
    ap.add_argument('action',choices=['list','fetch','audit','install'])
    ap.add_argument('species',nargs='?',choices=list(SOURCES)+['all'],default='all')
    ap.add_argument('--file',help='Owned, correctly licensed local GLB (install with a named species only)')
    ap.add_argument('--yes',action='store_true',help='Confirm intentional overwrite of app source GLB with backup')
    args=ap.parse_args()
    if args.action=='list':
        for key,s in SOURCES.items():
            print(f'{key:12s} {s["slot"]}\n   {s["page"]}\n   {s["notes"]}')
        print('\nFor professionally animated models and marketplace options see REALISM_SOURCES.md.')
    elif args.action=='audit': audit()
    elif args.action=='fetch':
        for key in SOURCES if args.species=='all' else [args.species]:download_one(key)
    elif args.action=='install':
        if args.species=='all':ap.error('Install animals individually after inspecting each model visually; specify a species.')
        if not args.yes: ap.error('Use --yes to confirm overwriting a model slot (backup is created).')
        install_one(args.species,args.file)

if __name__=='__main__': main()
