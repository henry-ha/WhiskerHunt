#!/usr/bin/env python3
"""Report all packaged native AR animal models and whether they contain textures.

Python only. Never modifies app assets or saved collection.
"""
import hashlib,json,sys
from pathlib import Path
from hush_glb_compat import unpack_glb

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'WhiskerHunt'/'Resources'/'Raw'/'ar_models'

def main():
    manifest=json.loads((RAW/'installed_species.json').read_text(encoding='utf-8'))
    audit_path=ROOT/'realistic_asset_provenance.json'
    audit=json.loads(audit_path.read_text(encoding='utf-8')) if audit_path.exists() else []
    approved={x['file']:x for x in audit if isinstance(x,dict) and x.get('file')}
    print('HUSH HUNT - 3D ANIMAL ASSET AUDIT')
    print('Every catalog entry is checked; a GLB file alone does not imply realism.')
    totals={'slots':0,'missing':0,'textured':0,'untextured':0,'upgrades':0}
    rows=[]
    for item in manifest:
        f=RAW/item['file'];totals['slots']+=1
        row={'species':item['name'],'file':f.name,'installed':f.exists()}
        if not f.exists():
            totals['missing']+=1
            print(f"MISSING  {f.name}")
        else:
            try:
                doc,_=unpack_glb(f.read_bytes())
                acc=doc.get('accessors',[])
                tris=0
                for m in doc.get('meshes',[]):
                    for p in m.get('primitives',[]):
                        ix=p.get('indices',p.get('attributes',{}).get('POSITION'))
                        if isinstance(ix,int) and 0<=ix<len(acc):tris+=acc[ix].get('count',0)//3
                row.update(triangles=tris,images=len(doc.get('images',[])),animations=len(doc.get('animations',[])),
                    requiredExtensions=doc.get('extensionsRequired',[]),hash=hashlib.sha256(f.read_bytes()).hexdigest()[:12],
                    licenceSource=approved.get(f.name,{}).get('source','unverified original'))
                is_textured=row['images']>0
                totals['textured' if is_textured else 'untextured']+=1
                if f.name in approved:totals['upgrades']+=1
                print(f"{'TEXTURED' if is_textured else 'FLAT    '}  {f.name:33}  {tris:>7,} tris  {row['images']:>2} images  {row['animations']} anim")
            except Exception as e:
                print(f'INVALID  {f.name}: {e}');row['error']=str(e)
        rows.append(row)
    print('SUMMARY:',totals)
    (ROOT/'wildlife_quality_audit.json').write_text(json.dumps({'summary':totals,'models':rows},indent=2)+'\n',encoding='utf-8')
    print('Written wildlife_quality_audit.json. The audit does NOT rate anatomy, fur, or visual accuracy.')
    return 0 if not totals['missing'] else 1

if __name__=='__main__':sys.exit(main())
