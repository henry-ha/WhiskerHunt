#!/usr/bin/env python3
"""Hush Hunt 3D Safari Sketchfab additions — additive, safe and repeatable.
Uses Python standard library only. Keep this script at the extracted ZIP root.
"""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import struct
import sys
from datetime import datetime

HERE = Path(__file__).resolve().parent
MODELS = json.loads((HERE / 'models.json').read_text(encoding='utf-8'))

def digest(file: Path) -> str:
    with file.open('rb') as source:
        sha = hashlib.sha256()
        while True:
            b = source.read(1024*1024)
            if not b: break
            sha.update(b)
        return sha.hexdigest()

def check_glb(file: Path):
    with file.open('rb') as f:
        head=f.read(20)
        if len(head)<20: raise ValueError(f'{file}: incomplete GLB header')
        magic, version, length, json_len, kind = struct.unpack('<4sIIII', head)
        if magic != b'glTF' or version != 2 or kind != 0x4E4F534A or length != file.stat().st_size:
            raise ValueError(f'{file}: invalid GLB v2 signature/chunk/size')
        graph = json.loads(f.read(json_len))
        if not graph.get('meshes'): raise ValueError(f'{file}: no GLB meshes')
        if graph.get('extensionsRequired'): raise ValueError(f'{file}: requires extensions: {graph["extensionsRequired"]}')
        return graph

def parse_assignment(js: str, name: str):
    # The real Hush Hunt builder generates one JSON-compatible constant per line.
    match=re.search(r'(?m)^(\s*const\s+'+re.escape(name)+r'\s*=)([^\r\n]*?);\s*$',js)
    if not match: raise ValueError(f'Could not find {name} in app_v99.js (the file was left unchanged)')
    try: value=json.loads(match.group(2).strip())
    except json.JSONDecodeError as e: raise ValueError(f'{name} has an unexpected format: {e}')
    return match, value

def replace_assignment(js: str, name: str, value):
    m, old = parse_assignment(js,name)
    replacement=m.group(1)+json.dumps(value,ensure_ascii=False,separators=(',',':'))+';'
    return js[:m.start()] + replacement + js[m.end():]

def make_button(item):
    key=html.escape(item['key'],quote=True)
    group=html.escape(item['species'],quote=True)
    label=html.escape(item['picker'],quote=False)
    return f'<button data-ar-model="{key}" data-ar-group="{group}" type="button">{item["icon"]} {label}</button>'

def find_project(arg: str | None):
    candidates=([Path(arg).expanduser().resolve()] if arg else [HERE, HERE.parent,Path.cwd()])
    for candidate in candidates:
        for p in (candidate,candidate/'WhiskerHunt'):
            if (p/'Resources/Raw/app_v99.js').is_file():return p
    raise FileNotFoundError('Could not locate WhiskerHunt/Resources/Raw/app_v99.js. Extract the ZIP to your solution root or supply --project PATH')

def backup(path:Path, suffix:str):
    if path.exists():
        dest=path.with_name(path.name+'.before-sketchfab-'+suffix+'.bak')
        shutil.copy2(path,dest)
        return dest
    return None

def atomic_write(path:Path,content:bytes):
    tmp=path.with_name(path.name+'.sketchfab-temp')
    try:
        tmp.write_bytes(content)
        os.replace(tmp,path)
    finally:
        if tmp.exists(): tmp.unlink()

def main():
    arg=argparse.ArgumentParser(description=__doc__)
    arg.add_argument('--project',help='Path to WhiskerHunt project folder or enclosing solution')
    arg.add_argument('--check-only',action='store_true',help='Check models and display intended changes without installing')
    opts=arg.parse_args()
    project=find_project(opts.project)
    raw=project/'Resources'/'Raw'; assets=raw/'ar_models'; js_path=raw/'app_v99.js'; manifest_path=assets/'installed_species.json'
    print('Project:',project)
    for item in MODELS:
        src=HERE/'staged_glbs'/item['file']
        if not src.is_file() or digest(src)!=item['sha256']:
            raise ValueError('Missing or modified Sketchfab asset: '+str(src))
        graph=check_glb(src)
        print(' VALID',item['name'],'—',len(graph.get('meshes',[])),'mesh(es),',len(graph.get('images',[])),'embedded images',str(round(src.stat().st_size/1048576,1))+' MiB')
    source=js_path.read_text(encoding='utf-8-sig')
    if 'const extra=(typeof HUSH_NATIVE_EXTRAS' not in source:
        raise ValueError('Missing getArModel native extras hook: cannot safely add choices to this JS version')
    _, old_extras=parse_assignment(source,'HUSH_NATIVE_EXTRAS')
    _, starters=parse_assignment(source,'HUSH_NATIVE_3D_STARTERS')
    _, buttons=parse_assignment(source,'HUSH_NATIVE_3D_BUTTONS')
    if not isinstance(old_extras,list) or not isinstance(starters,list) or not isinstance(buttons,str):
        raise TypeError('Unexpected Hush Hunt 3D picker data type')
    extras=list(old_extras); starter_keys=list(starters); content=buttons
    keys={x.get('key') for x in extras if isinstance(x,dict)}
    for item in MODELS:
        if item['key'] not in keys:
            extras.append({'key':item['key'],'name':item['name'],'species':item['species']});keys.add(item['key'])
        if item['key'] not in starter_keys: starter_keys.append(item['key'])
        if 'data-ar-model="'+item['key']+'"' not in content:
            content+=make_button(item)
    modified=replace_assignment(source,'HUSH_NATIVE_EXTRAS',extras)
    modified=replace_assignment(modified,'HUSH_NATIVE_3D_STARTERS',starter_keys)
    modified=replace_assignment(modified,'HUSH_NATIVE_3D_BUTTONS',content)
    # Verify the final file round-trips before copying anything.
    for variable in ('HUSH_NATIVE_EXTRAS','HUSH_NATIVE_3D_STARTERS','HUSH_NATIVE_3D_BUTTONS'):
        parse_assignment(modified,variable)
    current=[]
    if manifest_path.exists():
        current=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
        if not isinstance(current,list): raise TypeError('installed_species.json is not a list; will not overwrite')
    else:
        print('CAUTION: installed_species.json is missing. A new file will be created with these five models only.')
    existing={i.get('key') for i in current if isinstance(i,dict)}
    newmanifest=list(current)
    for item in MODELS:
        if item['key'] not in existing:
            newmanifest.append({k:item[k] for k in ('key','file','name','species')})
    # Do not overwrite unrelated existing models in the destination.
    for item in MODELS:
        destination=assets/item['file']
        if destination.exists() and digest(destination)!=item['sha256']:
            raise FileExistsError(f'{destination} already exists with different content. Keep the existing file and investigate manually.')
    print('Picker species:',len(starters),'->',len(starter_keys))
    print('Manifest species:',len(current),'->',len(newmanifest))
    if opts.check_only:
        print('CHECK ONLY: no files were changed.')
        return 0
    tag=datetime.now().strftime('%Y%m%d-%H%M%S')
    assets.mkdir(parents=True,exist_ok=True)
    backups=[]
    if modified!=source:
        backed=backup(js_path,tag)
        if backed:backups.append(str(backed))
    new_json=(json.dumps(newmanifest,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
    if not manifest_path.exists() or manifest_path.read_bytes()!=new_json:
        backed=backup(manifest_path,tag)
        if backed: backups.append(str(backed))
    for item in MODELS:
        d=assets/item['file']
        if not d.exists():shutil.copy2(HERE/'staged_glbs'/item['file'],d)
    if modified!=source:atomic_write(js_path,modified.encode('utf-8'))
    if not manifest_path.exists() or manifest_path.read_bytes()!=new_json:atomic_write(manifest_path,new_json)
    # log permanent trace / licensing still unverified
    report={'date':datetime.now().isoformat(),'project':str(project),'assets':[{'file':i['file'],'key':i['key'],'sha256':i['sha256'],'original_filename':i['source'],'licence':'verify on original Sketchfab listing'} for i in MODELS],'backup_files':backups}
    (HERE/'SKETCHFAB_FIVE_INSTALL_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('\nINSTALLED: 5 new species, existing GLBs and saved collection untouched.')
    print('BACKUP FILES:',len(backups))
    print('Clean + rebuild + deploy over existing app. Do not uninstall.')
    print('NOTE: User-supplied Sketchfab model licence/attribution has not been independently verified.')
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        print('INSTALL FAILED:',type(exc).__name__,str(exc),file=sys.stderr)
        sys.exit(1)
