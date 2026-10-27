#!/usr/bin/env python3
"""Hush Hunt: install quality-gated, legally reusable realistic GLBs.

Run from the extracted project root on an INTERNET-CONNECTED Windows PC:
    No external Python libraries are required for local GLB validation.
    py tools/upgrade_realistic_wildlife.py --download

Or manually download a licence-cleared GLB and install it:
    py tools/upgrade_realistic_wildlife.py --local deer C:\\path\\red-deer.glb

The shipped placeholder animals are *not* magically improved by this script:
models replace existing ones only when validation succeeds. Each original GLB
is backed up outside the Android app assets. No collection data is touched.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, struct, sys, urllib.parse, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MODELS=ROOT/'WhiskerHunt'/'Resources'/'Raw'/'ar_models'
BACKUPS=ROOT/'RealisticAssetBackups'
AUDIT=ROOT/'realistic_asset_provenance.json'
API='https://3dassets.dev/api/v1/assets'

# Only select the exact intended species or breed. No fox substituted for tabby,
# red squirrel for grey, or golden retriever for labrador.
# All 23 packaged native AR variants are now upgrade candidates, not only
# deer / Labrador / ginger tabby / squirrel. These are *exact-match* searches;
# absent species remain unchanged (never mislabel a similar animal).
TARGETS = {
    'garden-snail': dict(file='snail-garden-snail.glb',display='Garden snail',need=('garden','snail'),query='garden snail',min_tri=3000),
    'amber-snail': dict(file='snail-amber-snail.glb',display='Amber snail',need=('amber','snail'),query='amber snail',min_tri=3000),
    'seven-spot-ladybird': dict(file='ladybird-seven-spot.glb',display='Seven spot ladybird',need=('seven','spot','ladybird'),query='seven spot ladybird',min_tri=3000),
    'garden-spider': dict(file='spider-garden-spider.glb',display='Garden spider',need=('garden','spider'),query='garden spider',min_tri=4000),
    'slug': dict(file='other-slug.glb',display='Slug',need=('slug',),query='garden slug',min_tri=3000),
    'fox': dict(file='other-fox.glb',display='Red fox',need=('red','fox'),query='red fox',min_tri=9000),
    'wild-rabbit': dict(file='rabbit-wild-rabbit.glb',display='Wild rabbit',need=('rabbit',),query='wild rabbit',min_tri=7000),
    'grey-squirrel': dict(file='squirrel-grey-squirrel.glb',display='Grey squirrel',need=('grey','squirrel'),query='grey squirrel',min_tri=7000),
    'european-hedgehog': dict(file='hedgehog-european-hedgehog.glb',display='European hedgehog',need=('hedgehog',),query='european hedgehog',min_tri=7000),
    'common-frog': dict(file='frog-common-frog.glb',display='Common frog',need=('frog',),query='common frog',min_tri=5000),
    'labrador': dict(file='dog-labrador.glb',display='Labrador retriever',need=('labrador',),query='labrador retriever',min_tri=9000),
    'ginger-tabby': dict(file='cat-ginger-tabby.glb',display='Ginger tabby cat',need=('ginger','tabby'),query='ginger tabby',min_tri=9000),
    'robin': dict(file='bird-robin.glb',display='European robin',need=('robin',),query='european robin',min_tri=5000),
    'owl': dict(file='bird-owl.glb',display='Owl',need=('owl',),query='owl',min_tri=6000),
    'peacock-butterfly': dict(file='butterfly-peacock.glb',display='Peacock butterfly',need=('peacock','butterfly'),query='peacock butterfly',min_tri=4000),
    'honeybee': dict(file='bee-honeybee.glb',display='Honeybee',need=('honeybee',),query='honeybee',min_tri=4000),
    'stag-beetle': dict(file='beetle-stag-beetle.glb',display='Stag beetle',need=('stag','beetle'),query='stag beetle',min_tri=4000),
    'emperor-dragonfly': dict(file='dragonfly-emperor-dragonfly.glb',display='Emperor dragonfly',need=('emperor','dragonfly'),query='emperor dragonfly',min_tri=4000),
    'black-garden-ant': dict(file='ant-black-garden-ant.glb',display='Black garden ant',need=('ant',),query='black garden ant',min_tri=4000),
    'deer': dict(file='other-deer.glb',display='Red deer stag',need=('red','deer'),min_tri=12000,
                 slug='exotic-wildlife-hd-red-deer-stag-82f8d92a'),
    'mouse': dict(file='other-mouse.glb',display='Wood mouse',need=('wood','mouse'),query='wood mouse',min_tri=6000),
    'tortoise': dict(file='other-tortoise.glb',display='Tortoise',need=('tortoise',),query='tortoise',min_tri=5000),
    'bat': dict(file='other-bat.glb',display='Bat',need=('bat',),query='common bat',min_tri=5000),
}


def read_url(url,max_bytes=27*1024*1024):
    parts=urllib.parse.urlparse(url)
    if parts.scheme!='https' or parts.hostname not in ('3dassets.dev','cdn.3dassets.dev'):
        raise ValueError('Refusing unknown download domain')
    req=urllib.request.Request(url,headers={'User-Agent':'HushHuntRealisticAssetUpgrade/1.0','Accept':'application/json, model/gltf-binary, */*'})
    with urllib.request.urlopen(req,timeout=35) as r:
        data=r.read(max_bytes+1)
    if len(data)>max_bytes:raise ValueError('Asset exceeds allowed size')
    return data

def obj(x):
    if isinstance(x,dict) and isinstance(x.get('data'),dict):return x['data']
    if isinstance(x,dict) and isinstance(x.get('asset'),dict):return x['asset']
    return x

def meta(url):return obj(json.loads(read_url(url,max_bytes=2*1024*1024)))

def title_of(x):return str(x.get('title') or x.get('name') or '')

def slug_of(x):return str(x.get('slug') or '')

def valid_title(t,target):
    txt=re.sub(r'[^a-z0-9]+',' ',t.casefold()).strip()
    return all(re.search(r'\b'+re.escape(w)+r'\b',txt) for w in target['need'])

def cc0(asset):
    lic=asset.get('license')
    if isinstance(lic,dict): lic=' '.join(str(lic.get(k) or '') for k in ('slug','id','name','title'))
    lic=str(lic or '').lower()
    return 'cc0' in lic or 'creative commons zero' in lic or 'public domain' in lic

def asset_meta(key):
    target=TARGETS[key]
    if target.get('slug'):
        candidate=meta(API+'/'+target['slug'])
        if not isinstance(candidate,dict) or not valid_title(title_of(candidate),target):
            raise ValueError('Published deer metadata did not match exact animal')
        return candidate
    query=urllib.parse.urlencode({'q':target['query'],'category':'animals','style':'realistic','limit':60})
    reply=json.loads(read_url(API+'?'+query,max_bytes=4*1024*1024))
    raw=reply.get('data',reply) if isinstance(reply,dict) else reply
    hits=(raw.get('assets') or raw.get('results') or raw.get('items') or []) if isinstance(raw,dict) else raw
    matches=[]
    for x in hits:
        if not isinstance(x,dict) or not valid_title(title_of(x),target): continue
        slug=slug_of(x)
        if not slug:continue
        try:
            candidate=meta(API+'/'+urllib.parse.quote(slug,safe='-'))
            if valid_title(title_of(candidate),target) and cc0(candidate):matches.append(candidate)
        except Exception as e:print('  Skipping candidate',slug,':',e)
    if not matches:
        raise ValueError('No confirmed exact high-detail CC0 match for '+target['display']+'. Previous model preserved.')
    # Prefer models with more documented triangles, not names that merely contain a breed.
    matches.sort(key=lambda a:int(a.get('triangles') or a.get('triangleCount') or a.get('stats',{}).get('triangles') or 0),reverse=True)
    return matches[0]

def glb_json(data):
    if len(data)<28 or data[:4]!=b'glTF' or struct.unpack_from('<II',data,4)!=(2,len(data)):
        raise ValueError('File is not a GLB 2.0 binary')
    n,tag=struct.unpack_from('<I4s',data,12)
    if tag!=b'JSON' or n>len(data)-20:raise ValueError('Invalid GLB JSON chunk')
    return json.loads(data[20:20+n].decode('utf8'))

def convert_and_check(data,min_tri):
    """Validate a single embedded GLB without throwing away PBR or rig animation.

    The former OpenGL renderer required Trimesh to freeze the animal into a
    static shape. Filament gltfio supports modern glTF materials, quantised
    geometry, PBR maps and skins, so the ORIGINAL GLB should be retained.
    """
    from hush_glb_compat import normalize_webp
    # Filament's prebuilt Android gltfio often has no WebP decoder. Re-embed
    # PNG textures while preserving geometry, PBR material links and animations.
    data, converted = normalize_webp(data)
    if converted: print(f'  Converted {converted} embedded WebP texture(s) to PNG for Filament compatibility.')
    parsed=glb_json(data)
    required=set(parsed.get('extensionsRequired', []))
    # Draco/meshopt are not guaranteed by the packaged stock gltfio AAR.
    unsupported={'KHR_draco_mesh_compression','EXT_meshopt_compression'}
    if required & unsupported:
        raise ValueError('Compressed GLB requires a Draco/meshopt preprocessing step: '+str(required & unsupported))
    if len(data)>24*1024*1024:
        raise ValueError('GLB exceeds 24 MB Android asset loading budget after texture conversion')
    images=parsed.get('images',[])
    pbr_textures=sum(bool(m.get('pbrMetallicRoughness',{}).get('baseColorTexture')) for m in parsed.get('materials',[]))
    if len(images)<1 or pbr_textures<1:
        raise ValueError('Model has no embedded image and PBR base colour texture; it risks looking like the balloon models')
    if any(img.get('uri') and not img['uri'].startswith('data:') for img in parsed.get('images',[])):
        raise ValueError('External image resources must be embedded into the GLB')
    if any(i.get('uri') and not i['uri'].startswith('data:') for i in parsed.get('buffers',[])):
        raise ValueError('External buffer resources must be embedded into the GLB')
    accessors=parsed.get('accessors',[])
    total=0
    for mesh in parsed.get('meshes',[]):
        for primitive in mesh.get('primitives',[]):
            if primitive.get('mode',4)!=4:
                raise ValueError('Non-triangle mesh primitive, not supported by this importer')
            ix=primitive.get('indices')
            if ix is None:
                attr=primitive.get('attributes',{})
                a=attr.get('POSITION')
                if a is None or a>=len(accessors): raise ValueError('Missing position accessor')
                count=accessors[a].get('count',0)
            else:
                if ix < 0 or ix>=len(accessors): raise ValueError('Invalid index accessor')
                count=accessors[ix].get('count',0)
            total+=int(count)//3
    if total<min_tri:
        raise ValueError(f'Model has {total} triangles, below quality gate {min_tri}. Old model remains installed.')
    if total>220000:
        raise ValueError('Model too heavy for the current mobile performance target')
    return data,total

def install(key,data,source,license_name,detail):
    dest=MODELS/TARGETS[key]['file']
    normalized,triangles=convert_and_check(data,TARGETS[key]['min_tri'])
    MODELS.mkdir(parents=True,exist_ok=True)
    BACKUPS.mkdir(parents=True,exist_ok=True)
    backup=BACKUPS/dest.name
    if dest.exists() and not backup.exists():shutil.copy2(dest,backup)
    tmp=dest.with_suffix('.glb.pending')
    tmp.write_bytes(normalized)
    os.replace(tmp,dest)
    history=[]
    if AUDIT.exists():
        try:history=json.loads(AUDIT.read_text(encoding='utf-8'))
        except (ValueError,OSError):history=[]
    history=[i for i in history if i.get('target')!=key]
    from hush_glb_compat import unpack_glb
    doc,_=unpack_glb(normalized)
    history.append(dict(target=key,file=dest.name,source=source,license=license_name,
                        triangles=triangles,materials=len(doc.get('materials',[])),images=len(doc.get('images',[])),
                        animations=len(doc.get('animations',[])),sha256=hashlib.sha256(normalized).hexdigest(),
                        backup=str(backup.relative_to(ROOT)),detail=detail))
    AUDIT.write_text(json.dumps(history,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('INSTALLED',TARGETS[key]['display'],'-',triangles,'triangles ->',dest)

def download(key):
    target=TARGETS[key]
    # Prevent repeat installer runs from overwriting previously installed HD assets.
    destination=MODELS/target['file']
    if destination.exists() and AUDIT.exists():
        try:
            registered=json.loads(AUDIT.read_text(encoding='utf-8'))
            for record in registered:
                if record.get('target')==key and record.get('sha256')==hashlib.sha256(destination.read_bytes()).hexdigest():
                    print('ALREADY UPGRADED',target['display'],'- preserving current HD file')
                    return
        except (OSError,ValueError,TypeError):
            pass
    entry=asset_meta(key)
    if not cc0(entry):raise ValueError('No verified CC0 metadata; nothing replaced')
    if not valid_title(title_of(entry),target):raise ValueError('Wrong species; nothing replaced')
    url=entry.get('cdnUrl') or entry.get('downloadUrl') or entry.get('url')
    if not isinstance(url,str):raise ValueError('No downloadable GLB URL')
    if not url.startswith('https://cdn.3dassets.dev/') and not url.startswith('https://3dassets.dev/download/'):
        raise ValueError('Unexpected GLB URL')
    print('Candidate:',title_of(entry),'from',url)
    install(key,read_url(url),'https://3dassets.dev/assets/'+slug_of(entry),'CC0-1.0',
            'Original licensed GLB retained for Google Filament PBR, skins and animation')

def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--download',action='store_true',help='Search & install exact animal replacements from CC0 online catalogues')
    group.add_argument('--local',nargs=2,metavar=('ANIMAL','FILE'),help='Install a locally downloaded, rights-cleared GLB')
    group.add_argument('--restore',choices=list(TARGETS),help='Restore one of the original bundled models')
    group.add_argument('--list',action='store_true',help='Show target animal names and current filenames')
    args=parser.parse_args()
    if args.list:
        for key,t in TARGETS.items():print(key,'->',t['file'],'|',t.get('page', 'https://3dassets.dev/assets?category=animals&style=realistic'))
        return 0
    if args.restore:
        dest=MODELS/TARGETS[args.restore]['file'];backup=BACKUPS/dest.name
        if not backup.exists():print('No backed-up model found:',backup);return 1
        shutil.copy2(backup,dest);print('RESTORED',dest);return 0
    if args.local:
        key,filename=args.local
        if key not in TARGETS:parser.error('Unknown animal: '+key)
        print('IMPORTANT: Confirm licence/rights before distributing the supplied model.')
        install(key,Path(filename).read_bytes(),str(Path(filename)),'User-supplied: verify permission','Manual local import')
        return 0
    failures=[]
    for key in TARGETS:
        try:download(key)
        except Exception as e:
            print('NOT INSTALLED',TARGETS[key]['display'],':',str(e))
            failures.append(key)
    print('Complete:',len(TARGETS)-len(failures),'upgraded,',len(failures),'unchanged.')
    if failures:print('Unchanged animals:',', '.join(failures))
    print('NOTICE: High-detail output is a candidate, not human-approved realism. Preview each model for coat/anatomy before publishing.')
    print('Rebuild solution AFTER installing; do not uninstall the existing app.')
    return 0 if not failures else 2

if __name__=='__main__':sys.exit(main())
