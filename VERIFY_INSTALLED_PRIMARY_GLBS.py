from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parent
MODEL_DIR=ROOT/'WhiskerHunt'/'Resources'/'Raw'/'ar_models'
MANIFEST=json.loads((ROOT/'HUSH_HUNT_REPAIRED_GLB_SHA256.json').read_text(encoding='utf-8'))
missing=[];wrong=[];good=[]
for name,meta in MANIFEST.items():
    p=MODEL_DIR/name
    if not p.exists():missing.append(name);continue
    data=p.read_bytes()
    if hashlib.sha256(data).hexdigest()!=meta['sha256']:
        wrong.append(name)
    else:good.append(name)
print('Correct repaired primary GLBs:',len(good),'/',len(MANIFEST))
if missing:print('MISSING:',', '.join(missing))
if wrong:print('DIFFERENT (possibly old/unrepaired):',', '.join(wrong))
print('Project folder:',MODEL_DIR)
print('Next: rebuild and inspect Logcat tag HushHuntAR for MODEL SOURCE: ... [PRIMARY]')
if missing or wrong:sys.exit(1)
