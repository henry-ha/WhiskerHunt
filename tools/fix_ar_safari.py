#!/usr/bin/env python3
"""Restore species-specific icons and 3D picker without replacing imported assets.

Idempotent: reads the ACTUAL installed_species.json on the developer's PC.
Never downloads models, deletes any GLB, or edits user collections.
"""
from __future__ import annotations
import html
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
RAW=ROOT/'WhiskerHunt'/'Resources'/'Raw'
MANIFEST=RAW/'ar_models'/'installed_species.json'
APP=RAW/'app_v99.js'
BEGIN='/* BEGIN GENERATED NATIVE 3D CHOICES (verified bundled assets) */'
END='/* END GENERATED NATIVE 3D CHOICES */'
ORIGINAL_KEYS={
 'wildlife-snail-garden-snail','wildlife-snail-amber-snail','wildlife-ladybird-seven-spot',
 'wildlife-spider-garden-spider','wildlife-other-slug','wildlife-other-fox',
 'wildlife-rabbit-wild-rabbit','wildlife-squirrel-grey-squirrel',
 'wildlife-hedgehog-european-hedgehog','wildlife-frog-common-frog',
 'wildlife-dog-labrador','ginger-tabby','wildlife-bird-robin','wildlife-bird-owl',
 'wildlife-butterfly-peacock','wildlife-bee-honeybee','wildlife-beetle-stag-beetle',
 'wildlife-dragonfly-emperor-dragonfly','wildlife-ant-black-garden-ant',
 'wildlife-other-deer','wildlife-other-mouse','wildlife-other-tortoise','wildlife-other-bat'
}
# Names override broad "Other" category; emoji fallback never assumes every wild animal has paws.
EXACT={
 'garden snail':'🐌','amber snail':'🐌','seven-spot':'🐞','garden spider':'🕷️',
 'slug':'🐌','fox':'🦊','wild rabbit':'🐇','grey squirrel':'🐿️',
 'european hedgehog':'🦔','common frog':'🐸','labrador':'🐕',
 'ginger tabby':'🐈','domestic shorthair':'🐈','robin':'🐦','owl':'🦉',
 'peacock':'🦋','honeybee':'🐝','stag beetle':'🪲',
 'emperor dragonfly':'🪰','black garden ant':'🐜','deer':'🦌',
 'mouse':'🐭','tortoise':'🐢','bat':'🦇',
 'african lion':'🦁','african lioness':'🦁','bengal tiger':'🐅',
 'cheetah':'🐆','jaguar':'🐆','grey wolf':'🐺',
 'grizzly bear':'🐻','polar bear':'🐻‍❄️','plains zebra':'🦓',
 'reticulated giraffe':'🦒','black rhinoceros':'🦏','hippopotamus':'🦛',
 'snow leopard':'🐆','dromedary camel':'🐪','red panda':'🐼',
 'giant anteater':'🐾','african elephant':'🐘',
 'silverback gorilla':'🦍','chimpanzee':'🐒','orangutan':'🦧',
 'ring-tailed lemur':'🐒','meerkat':'🐾','red kangaroo':'🦘',
 'komodo dragon':'🦎','bearded dragon':'🦎','leopard gecko':'🦎',
 'veiled chameleon':'🦎',
}
GROUP={
 'Snail':'🐌','Ladybird':'🐞','Spider':'🕷️','Slug':'🐌',
 'Fox':'🦊','Rabbit':'🐇','Squirrel':'🐿️','Hedgehog':'🦔',
 'Frog':'🐸','Dog':'🐕','Cat':'🐈','Bird':'🐦',
 'Butterfly':'🦋','Bee':'🐝','Beetle':'🪲',
 'Dragonfly':'🪰','Ant':'🐜','Tortoise':'🐢','Bat':'🦇',
 'Other':'🌿',
}

def icon_for(item:dict)->str:
    label=str(item.get('name','')).strip().lower()
    group=str(item.get('species','')).strip()
    if label in EXACT:return EXACT[label]
    for term,icon in (
        ('snail','🐌'),('slug','🐌'),('ladybird','🐞'),('butterfly','🦋'),
        ('dragonfly','🪰'),('spider','🕷️'),('beetle','🪲'),('ant','🐜'),
        ('bee','🐝'),('squirrel','🐿️'),('deer','🦌'),('hedgehog','🦔'),
        ('mouse','🐭'),('frog','🐸'),('tortoise','🐢'),('fox','🦊'),
        ('zebra','🦓'),('lion','🦁'),('tiger','🐅'),('giraffe','🦒'),
        ('elephant','🐘'),('owl','🦉'),('wolf','🐺'),('bear','🐻'),
        ('leopard','🐆'),('monkey','🐒'),('penguin','🐧'),('rabbit','🐇'),
    ):
        if term in label:return icon
    return GROUP.get(group,'🌿')

def repair_picker(manifest:Path=MANIFEST, js_path:Path=APP)->dict:
    entries=json.loads(manifest.read_text(encoding='utf8'))
    if not isinstance(entries,list):raise ValueError('installed_species.json must be a list')
    installed=[];missing=[];seen=set()
    for obj in entries:
        if not isinstance(obj,dict):continue
        key=obj.get('key');file=obj.get('file');name=obj.get('name');species=obj.get('species','Other')
        if not all(isinstance(x,str) and x for x in (key,file,name,species)):continue
        if key in seen:continue
        seen.add(key)
        if '/' in file or '\\' in file or '..' in file:raise ValueError('Unexpected asset filename: '+file)
        if not (manifest.parent/file).is_file():
            missing.append(name);continue
        installed.append({'key':key,'file':file,'name':name,'species':species})
    if not installed:raise ValueError('No installed 3D model files found; leaving picker unchanged')
    extras=[{ 'key':e['key'],'name':e['name'],'species':e['species'] } for e in installed if e['key'] not in ORIGINAL_KEYS]
    buttons=''.join(
        '<button data-ar-model="'+html.escape(e['key'],quote=True)+'" data-ar-group="'+html.escape(e['species'],quote=True)+'" type="button">'+
        icon_for(e)+' '+html.escape(e['name'])+'</button>'
        for e in installed)
    generated='\n'.join([
        BEGIN,
        'const HUSH_NATIVE_EXTRAS='+json.dumps(extras,ensure_ascii=False,separators=(',',':'))+';',
        'const HUSH_NATIVE_3D_STARTERS='+json.dumps([e['key'] for e in installed],ensure_ascii=False,separators=(',',':'))+';',
        'const HUSH_NATIVE_3D_BUTTONS='+json.dumps(buttons,ensure_ascii=False)+';',
        END,
    ])
    src=js_path.read_text(encoding='utf8')
    if src.count(BEGIN)!=1 or src.count(END)!=1:raise ValueError('Cannot safely locate exactly one generated-picker block')
    first=src.index(BEGIN);last=src.index(END,first)+len(END)
    result=src[:first]+generated+src[last:]
    if 'const extra=(typeof HUSH_NATIVE_EXTRAS' not in result:
        anchor=" const found=AR_CAT_MODELS.find(m=>m.key===key);\n if(found)return found;"
        if anchor not in result:raise ValueError('New-species lookup missing; refusing unsafe rewrite')
        result=result.replace(anchor,anchor+"\n const extra=HUSH_NATIVE_EXTRAS.find(m=>m.key===key);\n if(extra)return {key:extra.key,name:extra.name,species:extra.species,coat:'Other',base:'#898f8f',belly:'#fafafa',accent:'#616161',eye:'#363636'};",1)
    if result!=src:js_path.write_text(result,encoding='utf8')
    info={'installed':len(installed),'new_species':len(extras),'missing_files':missing,'changed':result!=src}
    return info

if __name__=='__main__':
    print(json.dumps(repair_picker(),indent=2,ensure_ascii=False))
