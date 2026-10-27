#!/usr/bin/env python3
"""Hush Hunt extra wildlife GLB manager.

The source archive deliberately contains NO downloaded third-party meshes.
On the user's internet-connected Windows PC:
   py tools/expand_realistic_wildlife.py --download-extras
   py tools/expand_realistic_wildlife.py --import-local african-lion C:/models/lion.glb --license CC0 --source https://...
   py tools/expand_realistic_wildlife.py --refresh-picker
   py tools/expand_realistic_wildlife.py --report

Only identifiable CC0 assets from the publisher API are automatically fetched.
The new AR picker is regenerated only for files that have passed validation.
"""
from __future__ import annotations
import argparse, hashlib, html, json, os, re, sys, urllib.parse
from pathlib import Path

from hush_glb_compat import unpack_glb
from upgrade_realistic_wildlife import MODELS, ROOT, read_url, convert_and_check, cc0, title_of, meta

RAW=ROOT/'WhiskerHunt'/'Resources'/'Raw'
JS=RAW/'app_v99.js'
MANIFEST=MODELS/'installed_species.json'
LEDGER=ROOT/'wildlife_extra_sources.json'
STATUS=ROOT/'wildlife_expansion_report.json'
# The original 23 must remain stable between repeated installs and picker refreshes.
BASE_KEYS = {
 'wildlife-snail-garden-snail','wildlife-snail-amber-snail','wildlife-ladybird-seven-spot',
 'wildlife-spider-garden-spider','wildlife-other-slug','wildlife-other-fox',
 'wildlife-rabbit-wild-rabbit','wildlife-squirrel-grey-squirrel',
 'wildlife-hedgehog-european-hedgehog','wildlife-frog-common-frog',
 'wildlife-dog-labrador','ginger-tabby','wildlife-bird-robin','wildlife-bird-owl',
 'wildlife-butterfly-peacock','wildlife-bee-honeybee','wildlife-beetle-stag-beetle',
 'wildlife-dragonfly-emperor-dragonfly','wildlife-ant-black-garden-ant',
 'wildlife-other-deer','wildlife-other-mouse','wildlife-other-tortoise','wildlife-other-bat'
}
PACKS=(
 'exotic-wildlife-hd',
 'pets-and-companions-hd',
 'rainforest-and-jungle-fauna',
 'reptiles-amphibians-and-minibeasts',
)
# Approved known-species targets, not arbitrary catalogue imports.
# The model's *published title* must match ALL tokens in `match` and avoid forbidden words.
SPECIES={
 'domestic-shorthair':dict(name='Domestic Shorthair',match=['domestic','shorthair','cat','sitting'],deny=[],pack='pets-and-companions-hd',min_tri=9000,emoji='🐈',group='Cat'),
 'african-lion':dict(name='African Lion',match=['african','lion'],deny=['cub','lioness','lying','sitting'],pack='exotic-wildlife-hd',min_tri=9000,emoji='🦁'),
 'lioness':dict(name='African Lioness',match=['african','lioness'],deny=['lying'],pack='exotic-wildlife-hd',min_tri=9000,emoji='🦁'),
 'bengal-tiger':dict(name='Bengal Tiger',match=['bengal','tiger'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🐅'),
 'cheetah':dict(name='Cheetah',match=['cheetah'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🐆'),
 'jaguar':dict(name='Jaguar',match=['jaguar'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🐆'),
 'grey-wolf':dict(name='Grey Wolf',match=['grey','wolf'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🐺'),
 'grizzly-bear':dict(name='Grizzly Bear',match=['grizzly','bear'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🐻'),
 'polar-bear':dict(name='Polar Bear',match=['polar','bear'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🐻‍❄️'),
 'plains-zebra':dict(name='Plains Zebra',match=['plains','zebra'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🦓'),
 'giraffe':dict(name='Reticulated Giraffe',match=['reticulated','giraffe'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🦒'),
 'black-rhinoceros':dict(name='Black Rhinoceros',match=['black','rhinoceros'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🦏'),
 'hippopotamus':dict(name='Hippopotamus',match=['hippopotamus'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🦛'),
 'snow-leopard':dict(name='Snow Leopard',match=['snow','leopard'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🐆'),
 'dromedary-camel':dict(name='Dromedary Camel',match=['dromedary','camel'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🐪'),
 'red-panda':dict(name='Red Panda',match=['red','panda'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🐾'),
 'giant-anteater':dict(name='Giant Anteater',match=['giant','anteater'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🐾'),
 'african-elephant':dict(name='African Elephant',match=['african','elephant','bull'],deny=['calf'],pack='exotic-wildlife-hd',min_tri=9000,emoji='🐘'),
 'gorilla':dict(name='Silverback Gorilla',match=['silverback','gorilla'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🦍'),
 'chimpanzee':dict(name='Chimpanzee',match=['chimpanzee'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🐒'),
 'orangutan':dict(name='Orangutan',match=['orangutan'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🦧'),
 'ring-tailed-lemur':dict(name='Ring-tailed Lemur',match=['ring','tailed','lemur'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🐾'),
 'meerkat':dict(name='Meerkat',match=['meerkat','standing'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🐾'),
 'red-kangaroo':dict(name='Red Kangaroo',match=['red','kangaroo'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🦘'),
 'komodo-dragon':dict(name='Komodo Dragon',match=['komodo','dragon'],deny=[],pack='exotic-wildlife-hd',min_tri=9000,emoji='🦎'),
 'bearded-dragon':dict(name='Bearded Dragon',match=['bearded','dragon'],deny=[],pack='reptiles-amphibians-and-minibeasts',min_tri=4000,emoji='🦎'),
 'leopard-gecko':dict(name='Leopard Gecko',match=['leopard','gecko'],deny=[],pack='reptiles-amphibians-and-minibeasts',min_tri=4000,emoji='🦎'),
 'chameleon':dict(name='Veiled Chameleon',match=['veiled','chameleon'],deny=[],pack='reptiles-amphibians-and-minibeasts',min_tri=4000,emoji='🦎'),
}

def norm(s):return ' '.join(re.findall('[a-z0-9]+',str(s).lower()))

def matching(title,sp):
 t=norm(title).split();return all(x in t for x in sp['match']) and not any(x in t for x in sp['deny'])

def records(node):
 """Tolerate published pack API's possible root / nested collection shapes."""
 if isinstance(node,list):
  for x in node:
   if isinstance(x,dict):yield x
  return
 if not isinstance(node,dict):return
 for k in ('assets','items','models','results','entries'):
  val=node.get(k)
  if isinstance(val,list):yield from records(val)
 for k in ('pack','data'):
  if isinstance(node.get(k),(dict,list)):yield from records(node[k])

def api_asset(entry):
 data=entry.get('asset') if isinstance(entry.get('asset'),dict) else (entry.get('model') if isinstance(entry.get('model'),dict) else entry)
 if not isinstance(data,dict):return None
 slug=data.get('slug')
 if not isinstance(slug,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,140}',slug):return None
 return meta('https://3dassets.dev/api/v1/assets/'+slug)

def get_candidates():
 grouped={}
 for pack in PACKS:
  endpoint=f'https://3dassets.dev/api/v1/packs/{pack}'
  try:
   payload=json.loads(read_url(endpoint,max_bytes=5*1024*1024))
   found=list(records(payload))
   print(f'Pack {pack}: {len(found)} catalogue entries')
  except Exception as exc:
   print('COULD NOT QUERY',pack,':',exc);continue
  grouped[pack]=found
 return grouped

def downloaded_urls(rec):
 for obj in (rec,rec.get('asset') if isinstance(rec.get('asset'),dict) else {},rec.get('model') if isinstance(rec.get('model'),dict) else {}):
  if isinstance(obj,dict):
   for k in ('cdnUrl','downloadUrl'):
    v=obj.get(k)
    if isinstance(v,str) and v.startswith('https://cdn.3dassets.dev/'):return v
 return None

def validate_and_install(key,blob,source,lic):
 spec=SPECIES[key]
 data,tri=convert_and_check(blob,spec['min_tri'])
 parsed,_=unpack_glb(data)
 # Additional anti-balloon checks: real image, material and exact-name review still needed.
 mats=parsed.get('materials',[])
 if not any(m.get('pbrMetallicRoughness',{}).get('baseColorTexture') for m in mats):
  raise ValueError('Model lacks PBR base-colour image texture')
 name=spec['name']; slug=norm(name).replace(' ','-')
 group=spec.get('group','Other')
 filename=group.lower()+'-'+slug+'.glb'; keyname='wildlife-'+group.lower()+'-'+slug
 destination=MODELS/filename
 MODELS.mkdir(parents=True,exist_ok=True)
 # Do not overwrite 23 originals; for extra animals, retain version backup as needed.
 if destination.exists():
  back=ROOT/'RealisticAssetBackups'/'extra-'+filename
  back.parent.mkdir(exist_ok=True)
  if not back.exists():back.write_bytes(destination.read_bytes())
 tmp=destination.with_suffix('.glb.part');tmp.write_bytes(data);os.replace(tmp,destination)
 ledger=[]
 if LEDGER.exists():
  try:ledger=json.loads(LEDGER.read_text(encoding='utf8'))
  except Exception:ledger=[]
 ledger=[r for r in ledger if r.get('key')!=keyname]
 ledger.append(dict(key=keyname,filename=filename,display=name,species=group,source=source,license=lic,
                    triangles=tri,images=len(parsed.get('images',[])),animations=len(parsed.get('animations',[])),
                    sha256=hashlib.sha256(data).hexdigest(),status='imported_not_visual_approved'))
 LEDGER.write_text(json.dumps(ledger,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
 print('INSTALLED (visual approval needed):',name,tri,'triangles,',len(parsed.get('images',[])),'images ->',filename)
 return filename

def download_extras():
 grouped=get_candidates();report=[]
 for key,sp in SPECIES.items():
  entries=grouped.get(sp['pack'],[])
  listed=[]
  for e in entries:
   obj=e.get('asset') if isinstance(e.get('asset'),dict) else (e.get('model') if isinstance(e.get('model'),dict) else e)
   if not isinstance(obj,dict):continue
   title=title_of(obj)
   if not title: title=title_of(e)
   if matching(title,sp):listed.append((e,title))
  if not listed:
   report.append(dict(species=sp['name'],status='not_found',pack=sp['pack']))
   print('UNCHANGED',sp['name'],'(no exact published pack entry)');continue
  good=False
  for entry,title in listed[:3]:
   try:
    detail=api_asset(entry)
    if not isinstance(detail,dict) or not matching(title_of(detail),sp):
     raise ValueError('Exact species could not be confirmed against asset metadata')
    if not cc0(detail):raise ValueError('Licence is not explicitly CC0')
    url=downloaded_urls(detail)
    if not url:raise ValueError('No direct verified CDN URL')
    slug=detail.get('slug','')
    source='https://3dassets.dev/assets/'+slug
    validate_and_install(key,read_url(url),source,'CC0-1.0')
    report.append(dict(species=sp['name'],status='imported_not_visual_approved',url=source));good=True;break
   except Exception as exc:print('SKIPPED',sp['name'],title,':',exc)
  if not good:report.append(dict(species=sp['name'],status='failed_validation'))
 refresh_picker()
 STATUS.write_text(json.dumps({'date':'2026-10-27','entries':report,'note':'Images not visually inspected; installed source assets need on-device approval.'},indent=2)+'\n',encoding='utf8')
 print('EXTRA SPECIES:',sum(x['status']=='imported_not_visual_approved' for x in report),'installed,',sum(x['status']!='imported_not_visual_approved' for x in report),'not installed.')
 return 0

def refresh_picker():
 base=json.loads(MANIFEST.read_text(encoding='utf8'))
 # Keep the original 23 and reconcile only our CC0 extras; avoid duplicate entries.
 original=[x for x in base if x.get('key') in BASE_KEYS]
 existing=[x for x in base if x.get('key') not in BASE_KEYS and x.get('file') and (MODELS/x['file']).exists()]
 entries={x['key']:x for x in original+existing}
 approved=json.loads(LEDGER.read_text(encoding='utf8')) if LEDGER.exists() else []
 for r in approved:
  if (MODELS/r['filename']).exists() and r.get('license') in ('CC0','CC0-1.0','CC-BY-4.0'):
   entries[r['key']]=dict(key=r['key'],file=r['filename'],name=r['display'],species=r['species'],source=r['source'],license=r['license'])
 all_items=list(entries.values());MANIFEST.write_text(json.dumps(all_items,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
 extras=[e for e in all_items if e['key'] not in BASE_KEYS]
 from fix_ar_safari import repair_picker
 result=repair_picker(MANIFEST,JS)
 print('Updated native 3D picker:',result['installed'],'installed entries;',len(extras),'extras')

def main():
 p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
 a=p.add_mutually_exclusive_group(required=True)
 a.add_argument('--download-extras',action='store_true')
 a.add_argument('--refresh-picker',action='store_true')
 a.add_argument('--report',action='store_true')
 a.add_argument('--import-local',nargs=2,metavar=('SPECIES_KEY','GLB_FILE'))
 p.add_argument('--license',choices=['CC0','CC0-1.0','CC-BY-4.0'])
 p.add_argument('--source',help='Original creator/publisher URL for manual files')
 args=p.parse_args()
 if args.download_extras:return download_extras()
 if args.refresh_picker:refresh_picker();return 0
 if args.report:
  print('Available target extras:');[print(' ',k,'->',v['name'],'('+v['pack']+')') for k,v in SPECIES.items()]
  print('Installed:\n',LEDGER.read_text(encoding='utf8') if LEDGER.exists() else 'No additions yet');return 0
 key,path=args.import_local
 if key not in SPECIES:p.error('Unknown species key; see --report')
 if not args.license or not args.source or not args.source.startswith('https://'):
  p.error('Manual asset requires --license CC0 or CC-BY-4.0 and --source https://publisher URL')
 print('Importing user-provided model. You must verify licence authenticity and creator attribution before redistribution.')
 validate_and_install(key,Path(path).read_bytes(),args.source,args.license)
 refresh_picker();return 0

if __name__=='__main__':sys.exit(main())
