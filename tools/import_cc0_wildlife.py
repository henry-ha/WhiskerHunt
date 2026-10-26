#!/usr/bin/env python3
"""Hush Hunt - optional, explicit CC0 species-accurate 3D asset installer.

Run on an internet-connected dev computer, from the extracted project root:
    py -m pip install trimesh Pillow numpy
    py tools/import_cc0_wildlife.py --download

3DAssets.dev states these packs are CC0 1.0. Review the output images/geometry
before distributing. This installer does not mislabel a model if its title isn't
found, and it never replaces locally authored models. Requires user network.
"""
import argparse, io, json, os, re, struct, sys, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'WhiskerHunt'/'Resources'/'Raw'
MODELS=RAW/'ar_models'
JS=RAW/'app_v95.js'
CAT=ROOT/'tools'/'cc0_candidate_species.json'
MARKER='/* BEGIN GENERATED NATIVE 3D CHOICES (tools/import_cc0_wildlife.py) */'
END_MARKER='/* END GENERATED NATIVE 3D CHOICES */'

# Existing native GLBs are not downloaded/replaced. You may select any model
# from a licensing-cleared source if its filename matches catalog spelling.
INITIAL={
    'wildlife-snail-garden-snail':('🐌','Garden Snail'),
    'wildlife-snail-amber-snail':('🐌','Amber Snail'),
    'wildlife-ladybird-seven-spot':('🐞','Seven-spot Ladybird'),
    'wildlife-spider-garden-spider':('🕷️','Garden Spider'),
    'wildlife-other-slug':('🐌','Garden Slug'),
}
PACKS={
    'pets':'https://3dassets.dev/api/v1/packs/companion-animals-and-pet-home',
    'pets_hd':'https://3dassets.dev/api/v1/packs/pets-and-companions-hd',
    'wild':'https://3dassets.dev/api/v1/packs/exotic-wildlife-hd',
}

def fetch(url, timeout=28, limit=25*1024*1024):
    if not (url.startswith('https://3dassets.dev/') or url.startswith('https://cdn.3dassets.dev/')):
        raise ValueError('Source domain is not on the approved list')
    req=urllib.request.Request(url,headers={'User-Agent':'HushHuntCC0AssetImporter/1.0'})
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        data=resp.read(limit+1)
    if len(data)>limit: raise ValueError('Model download exceeds 25 MB')
    return data

def check_glb(data):
    if len(data)<20 or data[:4]!=b'glTF' or struct.unpack_from('<II',data,4)!=(2,len(data)):
        raise ValueError('Invalid GLB 2.0 binary header')
    return True

def json_glb(data):
    check_glb(data)
    ln,tag=struct.unpack_from('<I4s',data,12)
    if tag!=b'JSON': raise ValueError('Missing GLB JSON chunk')
    return json.loads(data[20:20+ln].decode('utf-8'))

def verify_native_compatible(data):
    root=json_glb(data)
    blocked={'KHR_draco_mesh_compression','EXT_meshopt_compression','KHR_mesh_quantization',
             'EXT_texture_webp','KHR_texture_basisu'}
    unsupported=blocked.intersection(root.get('extensionsRequired',[])+root.get('extensionsUsed',[]))
    if unsupported: raise ValueError('Needs normalization: '+', '.join(sorted(unsupported)))
    for a in root.get('accessors',[]):
        # Current ARCore renderer only supports float position/normal/UV.
        if a.get('type','').startswith('VEC') and a.get('componentType') != 5126:
            raise ValueError('Non-float vector accessor remains')
    for node in root.get('nodes',[]):
        if 'skin' in node: raise ValueError('Rigged model; bake pose first')
    if not root.get('meshes'):raise ValueError('No mesh')
    return True

def convert_to_native(data):
    # trimesh imports the transform hierarchy and material texture, re-exports
    # unquantized GLB positions/UV and embedded PNG/JPEG. This makes it compatible
    # with the current native GLB renderer without adding a new Android SDK.
    import trimesh
    loaded=trimesh.load(io.BytesIO(data),file_type='glb',force='scene',process=False)
    if not isinstance(loaded,trimesh.Scene) or not loaded.geometry:
        raise ValueError('GLB contained no supported static geometry')
    for mesh in loaded.geometry.values():
        if not isinstance(mesh,trimesh.Trimesh): raise ValueError('Non-triangle geometry')
    converted=loaded.export(file_type='glb',include_normals=True)
    check_glb(converted)
    verify_native_compatible(converted)
    if len(converted)>24*1024*1024:raise ValueError('Converted file exceeds native 24 MB limit')
    return converted

def key_to_filename(key):
    if not re.fullmatch(r'wildlife-[a-z0-9-]+',key): raise ValueError('Bad key')
    return key.removeprefix('wildlife-')+'.glb'

def choose_asset(assets, keywords):
    def norm(x):return re.sub('[^a-z0-9]+',' ',x.casefold()).strip()
    for needle in keywords:
        q=norm(needle)
        matches=[a for a in assets if norm(a.get('title','')).startswith(q) and a.get('category',{}).get('slug')=='animals']
        if len(matches)==1:return matches[0]
    return None

def write_picker():
    # Iterate only files that actually exist and are valid GLB. Never advertise
    # absent models: there is a strict 2D fallback for everything else.
    choices=[]
    mapping={d['key']:(d.get('emoji','🐾'),d['display']) for d in json.loads(CAT.read_text(encoding='utf-8'))}
    mapping.update(INITIAL)
    for key, (emoji,display) in mapping.items():
        path=MODELS/key_to_filename(key)
        if path.is_file():
            try: verify_native_compatible(path.read_bytes())
            except ValueError as e: print('SKIP invalid',path.name,str(e));continue
            choices.append((key,emoji,display))
    if not choices:raise RuntimeError('No compatible models in Resources/Raw/ar_models')
    if not JS.exists():raise FileNotFoundError(JS)
    js=JS.read_text(encoding='utf-8')
    if js.count(MARKER)!=1 or js.count(END_MARKER)!=1:raise RuntimeError('Native 3D choice markers missing')
    buttons=''.join(f'<button data-ar-model="{key}" type="button">{emoji} {display}</button>' for key,emoji,display in choices)
    keys='['+','.join(json.dumps(key) for key,_,_ in choices)+']'
    # Keep one generic selector; no fake species substitutions.
    block=MARKER+'\nconst HUSH_NATIVE_3D_STARTERS='+keys+';\nconst HUSH_NATIVE_3D_BUTTONS='+json.dumps(buttons,ensure_ascii=False)+';\n'+END_MARKER
    before,rest=js.split(MARKER,1);_,after=rest.split(END_MARKER,1)
    JS.write_text(before+block+after,encoding='utf-8')
    manifest=[{'key':key,'file':key_to_filename(key),'name':name} for key,_,name in choices]
    (MODELS/'installed_species.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    print('Ready for ARCore:',len(choices),'exactly matched species:',', '.join(n for _,_,n in choices))
    return len(choices)

def run(download):
    MODELS.mkdir(parents=True,exist_ok=True)
    if download:
        candidates=json.loads(CAT.read_text(encoding='utf-8'))
        manifests={}
        for source,url in PACKS.items():
            try:
                manifest=json.loads(fetch(url,limit=4*1024*1024))
                manifests[source]=manifest.get('data',manifest).get('assets',[])
                print('Read',len(manifests[source]),'candidates from',source)
            except Exception as e: print('Cannot read',source,'pack:',e)
        # Preserve provenance from previous successful runs. On a retry we skip
        # already-installed GLBs, so starting from an empty attribution list
        # would otherwise erase their source/license metadata.
        attribution_path=MODELS/'third_party_sources.json'
        attribution_by_key={}
        if attribution_path.is_file():
            try:
                previous=json.loads(attribution_path.read_text(encoding='utf-8'))
                for entry in previous:
                    if isinstance(entry,dict) and entry.get('key'):
                        attribution_by_key[entry['key']]=entry
            except (OSError,ValueError,TypeError) as ex:
                print('WARNING: could not read existing third-party sources:',str(ex))
        for d in candidates:
            path=MODELS/key_to_filename(d['key'])
            if path.exists():continue
            opts=manifests.get(d['pack'],[])
            asset=choose_asset(opts,d['titles'])
            if not asset:
                print('NOT AVAILABLE (no exact wildlife match):',d['display']);continue
            try:
                if asset.get('license',{}).get('slug')!='cc0-1.0':
                    raise ValueError('License is not CC0 1.0')
                payload=fetch(asset['cdnUrl'])
                normalized=convert_to_native(payload)
                path.write_bytes(normalized)
                attribution_by_key[d['key']]={'key':d['key'],'name':d['display'],'source':asset.get('url'),
                                    'creator':asset.get('contributor',{}).get('name'),
                                    'license':'CC0-1.0','changes':'Static GLB normalized to Hush Hunt Android renderer'}
                print('INSTALLED',d['display'],len(normalized)//1024,'KB')
            except Exception as e:print('SKIPPED',d['display'],type(e).__name__,str(e)[:170])
        attribution_path.write_text(json.dumps(list(attribution_by_key.values()),indent=2,ensure_ascii=False),encoding='utf-8')
    count=write_picker()
    print('Rebuild the Android project. The app shows ONLY the',count,'bundled models; other 2D wildlife stays available.')

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--download',action='store_true',help='Download confirmed CC0 models over the network and normalize to compatible GLB')
    args=ap.parse_args()
    try:run(args.download)
    except Exception as ex:print('ERROR:',ex,file=sys.stderr);sys.exit(1)
