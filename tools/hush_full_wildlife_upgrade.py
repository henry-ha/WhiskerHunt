#!/usr/bin/env python3
"""Review-first 61-slot Hush Hunt GLB upgrade tool. Python 3.9+ stdlib only.

Does NOT claim a mesh is attractive merely because it parses. No model is installed
without explicit human approval and backup. No third-party GLBs redistributed here.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import urllib.parse
import urllib.request

BASE = Path(__file__).resolve().parent.parent
CATALOGUE = json.loads((BASE / 'WILDLIFE_61_SLOTS.json').read_text(encoding='utf-8'))
SLOTS = {entry['slot']: entry for entry in CATALOGUE['animals']}
CANDIDATES = BASE / 'Wildlife_Review_Queue'
BACKUPS = BASE / 'Wildlife_Backups'
LOG = BASE / 'Wildlife_Install_Log.jsonl'
REPORT = BASE / 'Wildlife_Upgrade_Status.csv'
MAX_SIZE = 150 * 1024 * 1024


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def glb_info(path: Path) -> dict:
    """Strict-ish binary structural checks; no claim about rendered anatomy."""
    if not path.is_file(): raise ValueError('File missing')
    size = path.stat().st_size
    if not (28 <= size <= MAX_SIZE): raise ValueError('GLB invalid or over 150 MB')
    with path.open('rb') as file:
        hdr = file.read(12)
        magic, version, declared = struct.unpack('<4sII', hdr)
        if magic != b'glTF' or version != 2 or declared != size:
            raise ValueError('Invalid GLB 2.0 header/declared size')
        n, chunk_type = struct.unpack('<I4s', file.read(8))
        if chunk_type != b'JSON' or n > 32 * 1024 * 1024 or n <= 0:
            raise ValueError('Missing or oversized JSON chunk')
        doc = json.loads(file.read(n).decode('utf-8'))
        if str(doc.get('asset', {}).get('version', '')) != '2.0':
            raise ValueError('Not a glTF 2.0 asset')
        textures = doc.get('images', [])
        meshes = doc.get('meshes', [])
        materials = doc.get('materials', [])
        extensions = doc.get('extensionsRequired', [])
        accessors = doc.get('accessors', [])
        triangles = 0
        for mesh in meshes:
            for prim in mesh.get('primitives', []):
                if prim.get('mode', 4) != 4: continue
                idx = prim.get('indices', prim.get('attributes', {}).get('POSITION'))
                if isinstance(idx, int) and 0 <= idx < len(accessors):
                    triangles += accessors[idx].get('count', 0) // 3
        for img in textures:
            if 'uri' in img and not img['uri'].startswith('data:'):
                raise ValueError('External texture image not bundled in GLB')
        for buffer in doc.get('buffers', []):
            if 'uri' in buffer and not buffer['uri'].startswith('data:'):
                raise ValueError('External buffer not bundled in GLB')
        if triangles < 150: raise ValueError('No meaningful triangle geometry')
        if len(textures) < 1: raise ValueError('Untextured candidate: realistic models require images')
        if not materials: raise ValueError('No GLB materials')
        issues = []
        if triangles > 180_000: issues.append('High triangle count; optimise for Android')
        if size > 35 * 1024 * 1024: issues.append('Large model (>35 MB)')
        if any(x in extensions for x in ('KHR_draco_mesh_compression','EXT_meshopt_compression')):
            issues.append('Compressed geometry extension; test Filament/Android')
        if 'KHR_mesh_quantization' in extensions:
            issues.append('Quantised geometry; legacy OpenGL loader may fail')
        if not doc.get('animations', []): issues.append('STATIC model; no natural walking animation')
        alpha = sum(1 for mat in materials if mat.get('alphaMode', 'OPAQUE') != 'OPAQUE')
        if alpha: issues.append(f'{alpha} alpha material(s); verify fur cards render correctly')
        return {'bytes': size, 'sha256': digest(path), 'triangles': triangles, 'images': len(textures),
                'materials': len(materials), 'skins': len(doc.get('skins', [])),
                'animations': len(doc.get('animations', [])), 'extensions_required': extensions,
                'warnings': issues}


def candidate_dir(slot: str) -> Path:
    return CANDIDATES / slot.removesuffix('.glb')


def project_models(path: str | None) -> Path:
    root = Path(path).resolve() if path else BASE
    targets = [root / 'WhiskerHunt' / 'Resources' / 'Raw' / 'ar_models',
               root / 'Resources' / 'Raw' / 'ar_models']
    for target in targets:
        if target.is_dir(): return target
    raise ValueError('Could not find ar_models directory. Extract into the solution root or pass --project.')


def write_stage(slot: str, source: Path, publisher: str, licence: str, page: str, notes: str) -> None:
    info = glb_info(source)
    folder = candidate_dir(slot)
    folder.mkdir(parents=True, exist_ok=True)
    staged = folder / 'candidate.glb'
    if source.resolve() != staged.resolve(): shutil.copy2(source, staged)
    meta = {'slot': slot, 'species': SLOTS[slot]['species'], 'source': publisher,
            'license': licence, 'page': page, 'notes': notes,
            'file_sha256': info['sha256'], 'quality_review_approved': False,
            'inspected': info, 'staged_utc': datetime.utcnow().isoformat() + 'Z'}
    (folder / 'review.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    print(f'STAGED: {SLOTS[slot]["species"]} - {info["triangles"]:,} tris, {info["images"]} embedded images')
    for warning in info['warnings']: print('  NOTE:', warning)
    print('Preview/inspect animal eyes, paws, proportions, fur and scene props BEFORE approval.')


def fetch(slot: str) -> bool:
    d = SLOTS[slot].get('direct_candidate')
    if not d:
        print('NO VERIFIED DIRECT DOWNLOAD:', SLOTS[slot]['species'], '- supply a licensed GLB manually.')
        return False
    url = d['url']
    origin = urllib.parse.urlsplit(url)
    if origin.scheme != 'https' or origin.netloc != 'assets.stoicsoft.com':
        raise ValueError('Unapproved download host')
    candidate_dir(slot).mkdir(parents=True, exist_ok=True)
    part = candidate_dir(slot) / 'download.partial'
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'HushHuntWildlifeReview/1.0'})
        with urllib.request.urlopen(request, timeout=50) as response, part.open('wb') as out:
            resolved = urllib.parse.urlsplit(response.geturl())
            if resolved.scheme != 'https' or resolved.netloc != 'assets.stoicsoft.com':
                raise ValueError('Download redirected to an unexpected host')
            size = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk: break
                size += len(chunk)
                if size > MAX_SIZE: raise ValueError('Download over 150 MB')
                out.write(chunk)
        write_stage(slot, part, '1DesignTool', d['license'], d['page'], d['notes'])
        return True
    except Exception as e:
        print('DOWNLOAD FAILED:', slot, e)
        return False
    finally:
        if part.exists(): part.unlink()


def read_stage(slot: str) -> tuple[Path, dict, dict]:
    folder = candidate_dir(slot)
    path = folder / 'candidate.glb'
    meta = json.loads((folder / 'review.json').read_text(encoding='utf8'))
    info = glb_info(path)
    if meta.get('slot') != slot or meta.get('file_sha256') != info['sha256']:
        raise ValueError('Candidate has changed since staging; re-stage and review')
    return path, meta, info


def approve(slot: str, yes: bool) -> None:
    path, meta, info = read_stage(slot)
    if not yes:
        raise ValueError('Approval requires --yes-i-reviewed-anatomy to confirm visual inspection and licence.')
    if not meta.get('license') or not meta.get('source'):
        raise ValueError('Missing source/licence provenance')
    meta['quality_review_approved'] = True
    meta['approved_at_utc'] = datetime.utcnow().isoformat() + 'Z'
    (candidate_dir(slot) / 'review.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    print('APPROVED:', SLOTS[slot]['species'], '(you confirmed visual/licence review; app test still required)')


def install(slots: list[str], models: Path, dry_run: bool) -> tuple[int, int]:
    installed = skipped = 0
    for slot in slots:
        try:
            src, meta, info = read_stage(slot)
            if not meta.get('quality_review_approved'):
                raise ValueError('Not visually approved')
            dst = models / slot
            if not dst.is_file():
                raise ValueError('Missing original slot; will not create a new animal silently')
            if digest(dst) == info['sha256']:
                print('ALREADY INSTALLED:', slot)
                skipped += 1
                continue
            if dry_run:
                print('WOULD INSTALL:', slot, 'current', digest(dst)[:12], '->', info['sha256'][:12])
                installed += 1
                continue
            stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            backup = BACKUPS / slot.removesuffix('.glb') / stamp
            backup.mkdir(parents=True, exist_ok=False)
            backup_file = backup / slot
            shutil.copy2(dst, backup_file)
            if digest(backup_file) != digest(dst): raise ValueError('Backup verification failure')
            fd, tmpname = tempfile.mkstemp(prefix='hush_install_', suffix='.glb', dir=str(models))
            os.close(fd)
            tmp = Path(tmpname)
            try:
                shutil.copy2(src, tmp)
                if digest(tmp) != info['sha256']: raise ValueError('Install candidate verification failed')
                os.replace(tmp, dst)
            finally:
                if tmp.exists(): tmp.unlink()
            record = {'slot': slot, 'backup': str(backup_file), 'source': meta['source'],
                      'licence': meta['license'], 'source_page': meta['page'],
                      'new_sha256': info['sha256'], 'previous_sha256': digest(backup_file),
                      'installed_at': datetime.now().isoformat(), 'kind': 'install'}
            (backup / 'install.json').write_text(json.dumps(record, indent=2), encoding='utf8')
            with LOG.open('a', encoding='utf8') as file: file.write(json.dumps(record) + '\n')
            installed += 1
            print('INSTALLED:', slot, '| backup:', backup_file)
        except Exception as err:
            skipped += 1
            print('SKIPPED:', slot, '-', err)
    return installed, skipped


def rollback(slot: str, models: Path, yes: bool) -> None:
    if not yes: raise ValueError('Use --yes to confirm restoring the prior model')
    versions = list((BACKUPS / slot.removesuffix('.glb')).glob('*/install.json'))
    if not versions: raise ValueError('No backups available for ' + slot)
    meta = json.loads(max(versions, key=lambda p: p.parent.name).read_text(encoding='utf8'))
    backup_path = Path(meta['backup'])
    if not backup_path.exists(): raise ValueError('Backup is missing')
    if digest(backup_path) != meta['previous_sha256']:
        raise ValueError('Backup sha256 does not match manifest')
    target = models / slot
    # Guard against accidentally overwriting an unexpected newer edit.
    if target.exists() and digest(target) != meta['new_sha256']:
        raise ValueError('Current installed file changed after the recorded upgrade; manual review required')
    fd, name = tempfile.mkstemp(prefix='hush_restore_', suffix='.glb', dir=str(models))
    os.close(fd)
    tmp = Path(name)
    try:
        shutil.copy2(backup_path, tmp)
        os.replace(tmp, target)
    finally:
        if tmp.exists(): tmp.unlink()
    with LOG.open('a', encoding='utf8') as file: file.write(json.dumps({'slot':slot,'kind':'restore','at':datetime.now().isoformat()})+'\n')
    print('RESTORED:', slot)


def audit(models: Path | None) -> None:
    import csv
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    stats={'slots':len(SLOTS),'staged':0,'approved':0,'missing':0,'installed_exact':0}
    with REPORT.open('w', newline='', encoding='utf-8-sig') as file:
        writer=csv.writer(file)
        writer.writerow(['slot','species','current_exists','staged','approved','candidate_triangles','images','animations','source_page','source','license','installed_match'])
        for slot, entry in SLOTS.items():
            meta = None;info=None
            if (candidate_dir(slot) / 'review.json').exists():
                try: _, meta, info = read_stage(slot)
                except Exception as e:print('INVALID staged model',slot,e)
            if meta:
                stats['staged']+=1
                if meta.get('quality_review_approved'):stats['approved']+=1
            found = (models / slot).exists() if models is not None else False
            if models is not None and not found:stats['missing']+=1
            match = bool(found and info and digest(models / slot) == info['sha256'])
            if match:stats['installed_exact']+=1
            writer.writerow([slot,entry['species'],found,bool(meta),bool(meta and meta.get('quality_review_approved')),
                             info['triangles'] if info else '',info['images'] if info else '', info['animations'] if info else '',
                             meta.get('page','') if meta else '',meta.get('source','') if meta else '',meta.get('license','') if meta else '',match])
    print('REPORT:', REPORT)
    print('61 slots; staged:',stats['staged'],'approved:',stats['approved'],'installed candidates:',stats['installed_exact'],'missing current:',stats['missing'])


def main():
    parser=argparse.ArgumentParser(description='Safe full-library 61-slot wildlife GLB upgrade: stages and backs up, never silently replaces')
    parser.add_argument('--project', help='Solution folder (contains WhiskerHunt subfolder or is WhiskerHunt project root)')
    sub=parser.add_subparsers(dest='action', required=True)
    sub.add_parser('list',help='Show every project slot and known automatic downloads')
    sub.add_parser('audit',help='Write CSV status for all 61 slots')
    p=sub.add_parser('fetch',help='Download one verified public GLB or all five, STAGING ONLY')
    p.add_argument('slot',nargs='?',default='all')
    p=sub.add_parser('stage',help='Stage a legally obtained local GLB for a specific slot')
    p.add_argument('slot');p.add_argument('file');p.add_argument('--source',required=True);p.add_argument('--license',required=True);p.add_argument('--page',default='');p.add_argument('--notes',default='')
    p=sub.add_parser('inspect',help='Inspect a staged slot or a local GLB')
    p.add_argument('path')
    p=sub.add_parser('approve',help='Approve staged candidate AFTER external visual + rights review')
    p.add_argument('slot');p.add_argument('--yes-i-reviewed-anatomy',action='store_true')
    p=sub.add_parser('install',help='Install only approved candidates, with timestamped backups')
    p.add_argument('slot',help='one filename slot or all');p.add_argument('--yes',action='store_true');p.add_argument('--dry-run',action='store_true')
    p=sub.add_parser('restore',help='Restore latest backup for slot')
    p.add_argument('slot');p.add_argument('--yes',action='store_true')
    args=parser.parse_args()
    if args.action in ('fetch','stage','inspect','approve','install','restore') and hasattr(args,'slot') and args.slot != 'all' and args.slot not in SLOTS:
        parser.error('Unknown slot; run list to see exact names')
    if args.action=='list':
        for slot, entry in SLOTS.items():
            print(f'{slot:<39} {entry["species"]:<26} ' + ('DIRECT-DOWNLOAD AVAILABLE' if entry['direct_candidate'] else 'manual model required'))
    elif args.action=='fetch':
        selections=list(x for x,e in SLOTS.items() if e['direct_candidate']) if args.slot=='all' else [args.slot]
        successes=sum(fetch(slot) for slot in selections)
        print('STAGED',successes,'of',len(selections),'; ZERO models installed.');
    elif args.action=='stage':
        write_stage(args.slot,Path(args.file),args.source,args.license,args.page,args.notes)
    elif args.action=='inspect':
        path= candidate_dir(args.path) / 'candidate.glb' if args.path in SLOTS else Path(args.path)
        print(json.dumps(glb_info(path),indent=2))
    elif args.action=='approve':approve(args.slot,args.yes_i_reviewed_anatomy)
    elif args.action=='audit':
        try:models=project_models(args.project)
        except ValueError:models=None
        audit(models)
    elif args.action=='install':
        if not args.yes and not args.dry_run:parser.error('Actual installs require --yes; use --dry-run first')
        selections=list(SLOTS) if args.slot=='all' else [args.slot]
        changed, skipped=install(selections,project_models(args.project),args.dry_run)
        print('Processed:',changed,'eligible',skipped,'skipped. Remember to CLEAN + REBUILD app without uninstalling.')
    elif args.action=='restore':rollback(args.slot,project_models(args.project),args.yes)

if __name__=='__main__':
    try:main()
    except (ValueError,FileNotFoundError,json.JSONDecodeError) as exc:
        print('ERROR:',exc,file=sys.stderr);sys.exit(2)
