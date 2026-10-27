#!/usr/bin/env python3
"""One-pass, licence-aware wildlife asset replacement candidate sweep for Hush Hunt.

All 61 slots are visited in one invocation. Models that cannot pass basic validation
are NEVER silently installed. This tool does NOT manufacture artistic quality, claim
visual realism from triangles, or download marketplace models without permission.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, re, shutil, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hush_full_wildlife_upgrade import SLOTS, glb_info, digest, MAX_SIZE

DIRECT = {k: v['direct_candidate'] for k,v in SLOTS.items() if v.get('direct_candidate')}
# These are independently sourced models, NOT the original 3DAssets.dev files.
DIRECT.update({
 'other-grizzly-bear.glb': {
  'url':'https://assets.stoicsoft.com/1designtool/3d/models/brown-bear/a1ca81d9fd/model.glb',
  'page':'https://1designtool.com/3d/models/brown-bear',
  'license':'1DesignTool: embedding in apps allowed; raw model-pack redistribution restricted',
  'notes':'Adult brown/grizzly bear. Static, fur cards. Review alpha and anatomy.'},
 'bird-owl.glb': {
  'url':'https://assets.stoicsoft.com/1designtool/3d/models/snowy-owl/7c0c80f116/model.glb',
  'page':'https://1designtool.com/3d/models/snowy-owl',
  'license':'1DesignTool: embedding in apps allowed; raw model-pack redistribution restricted',
  'notes':'Snowy owl includes fence post; only suitable if intended owl is snowy owl; review-only.'},
 'other-reticulated-giraffe.glb': {
  'url':'https://assets.stoicsoft.com/1designtool/3d/models/giraffe/4436d1c540/model.glb',
  'page':'https://1designtool.com/3d/models/giraffe',
  'license':'1DesignTool: embedding in apps allowed; raw model-pack redistribution restricted',
  'notes':'MASAI giraffe not RETICULATED giraffe; explicitly species/subspecies mismatch; never auto-install.'}
})
STAGE = ROOT/'Wildlife_Review_Queue'
REPORTS = ROOT/'Wildlife_One_Sweep_Reports'
IMPORTS = ROOT/'USER_LICENSED_GLBS'   # user can put licensed GLBs named exactly like target slots here
BACKUPS = ROOT/'Wildlife_Backups'
LOG = ROOT/'Wildlife_Install_Log.jsonl'
LIST_FILE = ROOT/'WILDLIFE_61_SLOTS.json'
EXACT_REVIEW_ONLY = {'bird-owl.glb','other-reticulated-giraffe.glb'}
HOSTS = {'assets.stoicsoft.com'}


def utc():return datetime.now(timezone.utc).isoformat()


def resolve_models(project):
    base=Path(project).resolve() if project else ROOT
    for path in [base/'WhiskerHunt'/'Resources'/'Raw'/'ar_models', base/'Resources'/'Raw'/'ar_models']:
        if path.is_dir():return path
    return None


def check_candidate(path):
    info=glb_info(path)
    errors=[]
    if info['images'] < 2: errors.append('Insufficient texture images for high-realism shortlist')
    if info['triangles'] < 10000: errors.append('Low geometry detail for close-up AR')
    if info['triangles'] > 130000: errors.append('High triangle count; test Android FPS and make LOD')
    if info['animations'] == 0: errors.append('No animation: WALK would glide')
    if 'KHR_mesh_quantization' in info['extensions_required']:errors.append('Quantised geometry requires supported renderer')
    return info, errors


def download(slot, source, timeout, retry=1):
    url=source['url'];host=urllib.parse.urlsplit(url)
    if host.scheme!='https' or host.hostname not in HOSTS: raise ValueError('Download host not whitelisted')
    folder=STAGE / Path(slot).stem;folder.mkdir(parents=True, exist_ok=True)
    dest=folder/'candidate.glb';partial=folder/'candidate.part'
    for attempt in range(retry+1):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'HushHuntOneSweep/2.0'})
            with urllib.request.urlopen(req,timeout=timeout) as response, open(partial,'wb') as out:
                redirect=urllib.parse.urlsplit(response.geturl())
                if redirect.scheme!='https' or redirect.hostname not in HOSTS:
                    raise ValueError('Untrusted redirected host')
                size=0
                while True:
                    b=response.read(1024*1024)
                    if not b:break
                    size+=len(b)
                    if size>MAX_SIZE:raise ValueError('Model over 150 MB')
                    out.write(b)
            info,flags=check_candidate(partial)
            os.replace(partial,dest)
            return info,flags,None
        except (OSError,HTTPError,URLError,ValueError,TimeoutError) as ex:
            if partial.exists():partial.unlink()
            if attempt<retry:time.sleep(1.0)
            else:return None,[],str(ex)


def stage_user_model(slot, src):
    folder=STAGE / Path(slot).stem;folder.mkdir(parents=True, exist_ok=True)
    dest=folder/'candidate.glb'
    info,flags=check_candidate(src)
    if src.resolve()!=dest.resolve():shutil.copy2(src,dest)
    return info,flags


def candidate_manifest(slot, info, flags, src, srcurl, license_note, exact, previous_sha=None):
    return {'slot':slot,'species':SLOTS[slot]['species'],'status':'STAGED_NEEDS_VISUAL_APPROVAL',
        'source':src,'source_url':srcurl,'license':license_note,'exact_species_match':exact,
        'sha256':info['sha256'],'comparison_original_sha256':previous_sha,
        'quality_notes':flags, 'inspection':info,'staged_utc':utc(),
        'approved':False,'visual_review_method':'OPEN GLB in Blender or Windows 3D viewer, check eyes, paws, coats, cutout fur, model scale, props'}


def search_urls(species):
    q=re.sub(r'\s*\(species to verify\)','',species,flags=re.I)
    return {
      'sketchfab':'https://sketchfab.com/search?q='+urllib.parse.quote(q+' realistic')+'&type=models&features=downloadable',
      'fab':'https://www.fab.com/search?q='+urllib.parse.quote(q+' realistic animal'),
      'cgtrader':'https://www.cgtrader.com/3d-models?keywords='+urllib.parse.quote(q+' realistic'),
      '3dassets_same_style':'https://3dassets.dev/assets?category=animals&style=realistic&q='+urllib.parse.quote(q)
    }


def write_reports(rows):
    REPORTS.mkdir(exist_ok=True)
    (REPORTS/'FULL_61_SWEEP_RESULTS.json').write_text(json.dumps({'created_utc':utc(),'results':rows},indent=2),encoding='utf8')
    cols=['slot','species','status','source','license','candidate_triangles','candidate_images','candidate_animations','warning','sketchfab_search','fab_search','cgtrader_search']
    with (REPORTS/'FULL_61_SWEEP_RESULTS.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,cols);w.writeheader()
        for r in rows:
            a=r.get('info') or {}; urls=search_urls(r['species'])
            w.writerow(dict(slot=r['slot'],species=r['species'],status=r['status'],source=r.get('source',''),
               license=r.get('license',''),candidate_triangles=a.get('triangles',''),candidate_images=a.get('images',''),
               candidate_animations=a.get('animations',''),warning='; '.join(r.get('warnings',[]))[:1500],
               sketchfab_search=urls['sketchfab'],fab_search=urls['fab'],cgtrader_search=urls['cgtrader']))
    def e(s):return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')
    cards=[]
    for r in rows:
        url=search_urls(r['species'])
        cards.append('<div class="animal"><b>'+e(r['species'])+'</b><small>'+e(r['slot'])+'</small><p>'+e(r['status'])+'</p><p>'+e('; '.join(r.get('warnings',[])))+'</p><nav><a href="'+e(url['sketchfab'])+'">Sketchfab</a> <a href="'+e(url['fab'])+'">Fab</a> <a href="'+e(url['cgtrader'])+'">CGTrader</a></nav></div>')
    html='''<!doctype html><html><head><meta charset="UTF-8"><title>Hush Hunt — All 61 Model Sweep</title><style>body{font:15px/1.45 system-ui;background:#111925;color:#f2f5ff;padding:25px}h1{font-size:26px}header{max-width:900px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px}.animal{background:#222c3c;border:1px solid #52627a;border-radius:12px;padding:15px}.animal b{display:block;font-size:17px}.animal small{color:#a7b7c7}.animal p{margin:9px 0}a{color:#8ce8d6}</style></head><body><header><h1>Hush Hunt • One Sweep • 61 Slots</h1><p>All 61 slots are included. STAGED does not mean the model looks realistic or works on Android. Unsuitable models remain untouched. Search links are references, not downloadable/licensed files.</p></header><main>'''+''.join(cards)+'</main></body></html>'
    (REPORTS/'OPEN_61_MODEL_REVIEW.html').write_text(html,encoding='utf8')


def sweep(args):
    models=resolve_models(args.project)
    rows=[]
    for i,(slot,entry) in enumerate(SLOTS.items(),1):
        print(f'[{i:02d}/61] {entry["species"]}:',end=' ',flush=True)
        status='NEEDS_BETTER_LICENSED_SOURCE';source='';note='';licence='';info=None;flags=[]
        modelsha=digest(models/slot) if models and (models/slot).is_file() else None
        local=IMPORTS/slot
        if local.is_file():
            try:
                info,flags=stage_user_model(slot,local);source='USER_LICENSED_GLBS';licence='Rights supplied by user — must verify before distribution'
                status='STAGED_USER_MODEL_NEEDS_REVIEW'
                if modelsha==info['sha256']:
                    status='UNCHANGED_SAME_MODEL';flags.append('Same SHA256 as current installed model')
            except Exception as ex:status='USER_MODEL_INVALID';flags=[str(ex)]
        elif slot in DIRECT and not args.offline:
            d=DIRECT[slot];source='1DesignTool';licence=d['license']
            info,flags,err=download(slot,d,args.timeout)
            if err:status='DOWNLOAD_FAILED';flags=[err]
            else:
                status='STAGED_LICENSED_ALTERNATIVE_REVIEW_REQUIRED'
                if slot in EXACT_REVIEW_ONLY:status='SPECIES_OR_SCENERY_MISMATCH_REVIEW_REQUIRED'
                if modelsha==info['sha256']:
                    status='UNCHANGED_SAME_MODEL';flags.append('File already installed; no improvement')
            note=d['notes']
        else:
            status='NO_VERIFIED_DIFFERENT_REALISTIC_MODEL'
            flags.append('Source search needed; prior 3DAssets.dev pack appears to be the current source and is not an upgrade')
        if info and status not in ('UNCHANGED_SAME_MODEL','USER_MODEL_INVALID'):
            review=candidate_manifest(slot,info,flags,source,(DIRECT.get(slot) or {}).get('page',''),licence,slot not in EXACT_REVIEW_ONLY,modelsha)
            (STAGE/Path(slot).stem/'review.json').write_text(json.dumps(review,indent=2),encoding='utf8')
        if note:flags.append(note)
        rows.append({'slot':slot,'species':entry['species'],'status':status,'source':source,'license':licence,
                     'info':info,'warnings':flags,'prior_sha256':modelsha})
        print(status)
    write_reports(rows)
    staged=sum(r['status'].startswith('STAGED') for r in rows)
    unresolved=sum('NO_VERIFIED' in r['status'] for r in rows)
    errors=sum(r['status'] in ('DOWNLOAD_FAILED','USER_MODEL_INVALID') for r in rows)
    print('\nCOMPLETE: all 61 slots checked,',staged,'alternative candidates staged,',unresolved,'missing verified alternative,',errors,'download/validation failures')
    print('Report:',REPORTS/'OPEN_61_MODEL_REVIEW.html')
    print('Existing GLBs preserved. NO animal overwritten; visible model approval and rights still required.')


def install_approved(args):
    models=resolve_models(args.project)
    if models is None:raise ValueError('Project Resources/Raw/ar_models folder not found')
    rows=[]; changed=0
    for slot,entry in SLOTS.items():
        p=STAGE/Path(slot).stem/'candidate.glb';m=STAGE/Path(slot).stem/'review.json'
        if not (p.is_file() and m.is_file()):continue
        meta=json.loads(m.read_text('utf8'))
        if not meta.get('approved'):continue
        if meta.get('exact_species_match') is not True:print('SKIP DIFFERENT SPECIES',slot);continue
        info,_=check_candidate(p)
        if info['sha256']!=meta['sha256']:raise ValueError('Candidate modified since approved: '+slot)
        target=models/slot
        if not target.is_file():print('SKIP MISSING SLOT',slot);continue
        if digest(target)==info['sha256']:continue
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        backup=BACKUPS/Path(slot).stem/stamp;backup.mkdir(parents=True,exist_ok=False)
        shutil.copy2(target,backup/slot)
        if digest(target)!=digest(backup/slot):raise ValueError('Backup verification failed: '+slot)
        tmp=target.with_suffix('.glb.pending')
        try:
            shutil.copy2(p,tmp)
            if digest(tmp)!=info['sha256']:raise ValueError('New checksum failed: '+slot)
            os.replace(tmp,target)
        finally:
            if tmp.exists():tmp.unlink()
        record={'slot':slot,'old_sha256':digest(backup/slot),'new_sha256':info['sha256'],
            'backup_file':str(backup/slot),'source':meta['source'],'timestamp':utc()}
        (backup/'install.json').write_text(json.dumps(record,indent=2),encoding='utf8')
        LOG.open('a',encoding='utf8').write(json.dumps(record)+'\n')
        changed+=1
    print('Installed',changed,'visually approved models in ONE pass; all originals backed up. Rebuild/deploy without uninstalling.')


def main():
    p=argparse.ArgumentParser(description='Single-run 61-slot alternative wildlife sweep. Never silently replaces animals.')
    p.add_argument('--project',default=None,help='Hush Hunt solution or project directory')
    p.add_argument('--offline',action='store_true',help='Check all 61 slots without downloading')
    p.add_argument('--timeout',type=int,default=35)
    p.add_argument('--install-approved',action='store_true',help='Install pre-approved staged models, in one batch with backups')
    p.add_argument('--yes',action='store_true',help='Confirm installing the already-reviewed models')
    args=p.parse_args()
    if args.install_approved:
        if not args.yes:p.error('--install-approved requires --yes')
        install_approved(args)
    else:sweep(args)
if __name__=='__main__':
    try:main()
    except Exception as e:
        print('ERROR:',str(e),file=sys.stderr)
        sys.exit(2)
