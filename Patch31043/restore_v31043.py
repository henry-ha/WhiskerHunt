#!/usr/bin/env python3
"""Safely restore Hush Hunt 3.10.43 using the full backup directory printed by installer.
Defaults to a dry run. Never overwrites user edits made after installation.
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil,sys

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--project-root',required=True);p.add_argument('--backup',required=True);p.add_argument('--restore',action='store_true');args=p.parse_args()
    root=Path(args.project_root).resolve();folder=Path(args.backup).resolve()
    path=folder/'backup_manifest.json'
    if not path.is_file():sys.exit('NOT RESTORED: missing backup manifest')
    m=json.loads(path.read_text(encoding='utf-8'))
    if not m.get('complete'):sys.exit('NOT RESTORED: installation backup was incomplete')
    if str(root)!=m.get('root'):sys.exit('NOT RESTORED: backup targets a different project folder')
    for rel,info in m['files'].items():
        before=folder/rel;current=root/rel
        if not before.is_file() or sha(before)!=info['original_sha256']:
            sys.exit('NOT RESTORED: original backup failed checksum: '+rel)
        expected=info['new_sha256']
        if expected is None:
            if current.exists():sys.exit('NOT RESTORED: a deleted asset has since been recreated: '+rel)
        elif not current.is_file() or sha(current)!=expected:
            sys.exit('NOT RESTORED: file changed after update, refuses to overwrite: '+rel)
    if not args.restore:
        print('RESTORE DRY RUN SUCCESS:',len(m['files']),'files can be restored. Add --restore to proceed.');return
    for rel in m['files']:
        original=folder/rel;dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        temp=dest.with_name(dest.name+'.hush31043.restore.tmp')
        shutil.copy2(original,temp);os.replace(temp,dest)
    print('RESTORED SUCCESSFULLY: Hush Hunt source + wildlife GLBs reverted to exact backup state.')
if __name__=='__main__':main()
