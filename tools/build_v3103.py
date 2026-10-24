"""Hush Hunt v3.10.3: offline educational guide, full-screen viewer, improve weak tiles.
This intentionally makes NO changes to the IndexedDB/JSON data schema or Android package ID.
"""
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
import re,json,shutil,html
root=Path(__file__).resolve().parents[1]
web=root/'BrowserPreview'; raw=root/'WhiskerHunt/Resources/Raw'
# Child-friendly ID observations, not claims of computer vision species verification.
group_facts={
 'Cat':'Look at fur colour, markings, ear shape and tail. Coat patterns are not the same as breeds.',
 'Dog':'Look at size, ear shape, coat and muzzle. Many dogs are mixes and cannot be identified by looks alone.',
 'Snail':'Check the shell shape, colour, bands and habitat. Never pull a snail off a surface.',
 'Butterfly':'Notice wing colour and patterns on both sides. Photograph butterflies without catching them.',
 'Moth':'Moths vary widely in shape and colour. Some fly by day; look at wing patterns and antennae.',
 'Bee':'Notice body shape, hairiness and markings. Watch bees from a distance and leave flowers undisturbed.',
 'Ladybird':'Count spots only as one clue. Pattern, size and head markings can matter more.',
 'Beetle':'Beetles have hard wing cases. Look at body shape, antennae and colours.',
 'Dragonfly':'Dragonflies have four long wings and large eyes. Check abdomen shape, colour and habitat.',
 'Ant':'Ants have elbowed antennae and narrow waists. Colours vary; many look alike.',
 'Spider':'Spiders have eight legs and no antennae. Look at their web, markings and body shape.',
 'Bird':'Look at beak, size, wing bars and tail as well as colour. Listen for calls without approaching nests.',
 'Squirrel':'Look at ears, tail, size and coat colour. Coat colours can vary within a species.',
 'Rabbit':'Wild rabbits and pet rabbit breeds can look different. Look at ear shape, size and setting.',
 'Hedgehog':'Look for a rounded body, pointed snout and spines. Observe without touching or disturbing it.',
 'Frog':'Look at skin, colour, leg length and habitat. Patterns vary and some species are hard to distinguish.',
 'Other':'For an unfamiliar animal, photograph it safely and record where you saw it. It is fine to say “Not sure”.'
}
# Identification pointers: commonly seen visual clues, not a scientific identification decision.
facts={
'Cat':{
'Tabby':'Often has stripes, swirls or spots; look for the M-shaped mark on the forehead.',
'Ginger':'Orange or reddish coat; many ginger cats also show faint or bold tabby stripes.',
'Brown':'A brown coat can be solid or patterned; check whether stripes are visible.',
'Black':'Looks mostly black, though sunlight may reveal faint markings.',
'White':'Mostly white fur; eye colour can be blue, green, amber or mixed.',
'Cream':'Pale warm beige colouring; compare with the deeper orange of ginger.',
'Tuxedo':'Usually black with white on the chest, paws or face, like a little suit.',
'Calico':'Distinct areas of white, orange and dark fur; a coat pattern, not a breed.',
'Tortoiseshell':'Mottled black and orange or brown patches, usually with very little white.',
'Grey':'Cool grey or blue-looking coat; may be solid or tabby-patterned.',
'Colourpoint':'Paler body with darker ears, face, paws and tail.',
'Other':'If the markings do not fit, describe the colours and pattern in your notes.'},
'Dog':{
'Labrador':'Sturdy body, short dense coat and broad head; black, yellow or chocolate are common.',
'Golden Retriever':'Medium-large dog with a feathered golden coat and hanging ears.',
'Poodle':'Curly coat, narrow muzzle and long legs; sizes vary widely.',
'Terrier':'Often lively-looking with a wiry or smooth coat; many different terrier breeds exist.',
'Spaniel':'Usually has soft floppy ears and a silky or wavy coat.',
'Bulldog':'Stocky build, broad head, short muzzle and skin folds.',
'Dachshund':'Long body, short legs and drooping ears.',
'Husky':'Thick double coat, upright ears and bushy tail; eyes may be blue or brown.',
'Mixed Breed':'A mixed-breed dog may combine features of several breeds; looks alone cannot confirm ancestry.'},
'Snail':{
'Garden Snail':'Rounded brown shell often with flecks or mottling; typically found in damp gardens.',
'Grove Snail':'Smooth shell may be yellow, pinkish or brown, sometimes with dark spiral bands.',
'Roman Snail':'A relatively large, rounded, pale shell with many visible growth lines.',
'Glass Snail':'Thin, glossy, often translucent shell; the body may be visible through it.',
'Amber Snail':'Small amber-coloured shell with a large opening, often near damp plants.',
'Pond Snail':'Aquatic snail with a taller pointed shell, typically in fresh water.',
'Other Snail':'Check shell shape and location; different species can look very similar.'},
'Butterfly':{
'Peacock':'A large eye-shaped spot on each reddish-brown wing is the key clue.',
'Red Admiral':'Dark wings with bright red-orange bands and white markings near the tips.',
'Small Tortoiseshell':'Orange wings with black and yellow patches and blue crescents at the edges.',
'Painted Lady':'Orange and brown wings with black tips and small white spots.',
'Comma':'Orange-brown wings with deeply scalloped edges; the underside has a tiny white C mark.',
'Large White':'Mainly white wings with dark tips and sometimes black spots.',
'Common Blue':'Males often look bright blue above; females are usually brown with orange edge spots.',
'Brimstone':'Leaf-shaped, pale yellow-green wings; females are often paler.'},
'Moth':{
'Emperor Moth':'Large furry moth with bold round eye-spots on each wing.',
'Elephant Hawk-moth':'Often pink and olive green, with a streamlined body.',
'Hummingbird Hawk-moth':'Hovers in front of flowers and has orange hindwings.',
'Garden Tiger':'Bold cream-and-brown forewings, often with bright orange hindwings.',
'Jersey Tiger':'Dark forewings with creamy stripes and bright orange or red hindwings.',
'Six-spot Burnet':'Dark iridescent wings with pairs of red spots; often found on flowers.',
'Silver Y':'Mottled grey-brown forewings with a small silver Y-shaped marking.'},
'Bee':{
'Honeybee':'Brown-and-gold banded abdomen and slimmer shape than many bumblebees.',
'Buff-tailed Bumblebee':'Rounded, furry bee with yellow bands and a pale buff or off-white tail.',
'Red-tailed Bumblebee':'Black fuzzy body with a rusty red or orange tail.',
'White-tailed Bumblebee':'Black-and-yellow bands with a clean-looking white tail.',
'Common Carder Bee':'Ginger or brown furry thorax; banding can be subtle.',
'Leafcutter Bee':'Often carries pollen on hairs under the abdomen and cuts neat circles from leaves.',
'Mining Bee':'Many species nest in soil; often furry, small to medium, and hard to distinguish.'},
'Ladybird':{
'Seven-spot':'Typically red with seven black spots; three on each wing case and one by the centre.',
'Two-spot':'Often red with two black spots, but darker forms also exist.',
'Harlequin':'Highly variable colours; often a pale W-shaped marking behind the head.',
'Fourteen-spot':'Usually yellow with rectangular black markings that can merge into a checkerboard.',
'Pine Ladybird':'Mostly dark with red spots shaped a little like commas.',
'Twenty-two-spot':'Bright yellow with many small black spots; usually found near mildew.'},
'Beetle':{
'Stag Beetle':'Large beetle; males have antler-like jaws, while females have smaller jaws.',
'Rose Chafer':'Shiny metallic green beetle, often seen feeding on flowers.',
'Ground Beetle':'Often dark, fast-running and found beneath stones or logs.',
'Weevil':'Many have a long snout with antennae set partway along it.',
'Soldier Beetle':'Soft-looking, elongated body; often red or orange on summer flowers.',
'Click Beetle':'Long narrow body; can make a click to spring itself upright.',
'Longhorn Beetle':'Often has antennae as long as, or longer than, its body.',
'Dung Beetle':'Often rounded, sturdy and found around animal dung.'},
'Dragonfly':{
'Emperor Dragonfly':'Large dragonfly with vivid blue abdomen and green thorax, especially in males.',
'Broad-bodied Chaser':'A broad, flattened abdomen; mature males often look powdery blue.',
'Southern Hawker':'Large patterned dragonfly; males show blue and green markings.',
'Common Darter':'Small dragonfly that often perches; mature males are frequently reddish.',
'Four-spotted Chaser':'Look for four distinct dark spots near the middle of the wings.',
'Golden-ringed Dragonfly':'Very long black-and-yellow ringed body and green eyes.'},
'Ant':{
'Black Garden Ant':'Small, dark brown or black ant commonly seen on paths and in gardens.',
'Red Ant':'Often reddish with a darker abdomen; several different species share this name.',
'Wood Ant':'Usually reddish-brown and dark, often near large mound nests in woodland.',
'Yellow Meadow Ant':'Small yellowish ant that spends much of its life underground.',
'Pavement Ant':'Tiny dark ants often nesting in cracks between stones.',
'Other Ant':'Look at size, colour and nesting place; close-up details may be needed.'},
'Spider':{
'Garden Spider':'Rounded abdomen with a pale cross-shaped pattern; often in circular webs.',
'House Spider':'Long-legged brown spider; many species occur inside buildings.',
'Jumping Spider':'Compact body and very large front-facing eyes; moves in short jumps.',
'Zebra Spider':'Tiny jumping spider with clear black-and-white stripes.',
'Wolf Spider':'Fast ground hunter with a robust body, often seen without a web.',
'Crab Spider':'Front legs held sideways like a crab; often waits on flowers.',
'Cellar Spider':'Very long thin legs and a small body; often hangs upside down indoors.'},
'Bird':{
'Robin':'Orange-red face and chest, with a brown back; often hops near gardens.',
'Blackbird':'Adult males are black with a yellow-orange bill; females are browner.',
'House Sparrow':'Small, chunky brown bird; adult males have a grey crown and black throat.',
'Blue Tit':'Blue cap, yellow underside and white cheeks with a dark eye stripe.',
'Great Tit':'Black head with white cheeks and a central black stripe on a yellow belly.',
'Magpie':'Long tail and bold black-and-white body with an iridescent sheen.',
'Wood Pigeon':'Large plump grey pigeon with white neck patches.',
'Starling':'Dark, glossy bird that can sparkle green-purple and show pale speckles.',
'Crow':'Large black bird with a strong dark bill; several crow species look similar.',
'Seagull':'Gulls vary with age; look at size, beak and wing markings.',
'Parakeet':'Bright green body, long pointed tail and red beak in a ring-necked parakeet.',
'Duck':'Broad flat bill and webbed feet; plumage depends on species and sex.',
'Swan':'Very large waterbird with a long neck; British mute swans usually have orange bills.',
'Owl':'Rounded or heart-shaped face, forward-facing eyes and often silent flight.'},
'Squirrel':{
'Grey Squirrel':'Usually grey-brown with a white belly and broad bushy tail.',
'Red Squirrel':'Often russet red with a paler belly; some have ear tufts, especially in winter.',
'Flying Squirrel':'Has a skin membrane between front and back legs for gliding; not native to Britain.',
'Ground Squirrel':'Typically lives in burrows and spends more time on the ground.',
'Other Squirrel':'Squirrels can be black, grey or reddish; colour alone does not prove species.'},
'Rabbit':{
'Wild Rabbit':'Brown-grey coat, short fluffy tail and upright ears; lives in warrens.',
'Lop-eared':'Domestic rabbit with ears that hang beside its face.',
'Dutch Rabbit':'Domestic breed with clear patches of contrasting coat colour.',
'Lionhead':'Domestic rabbit with a distinctive mane of longer fur around the head.',
'Netherland Dwarf':'Small, compact pet rabbit with short ears.',
'Flemish Giant':'Very large domestic rabbit with a long, sturdy body.'},
'Hedgehog':{
'European Hedgehog':'Brown-and-cream spines, pointed face and small ears; native to Britain.',
'African Pygmy Hedgehog':'Smaller, often pale-faced pet hedgehog; not native to Britain.',
'Long-eared Hedgehog':'Has noticeably larger ears; native to parts of Asia and the Middle East.',
'Other Hedgehog':'Check face, ears and where it was seen before choosing a type.'},
'Frog':{
'Common Frog':'Variable brown or olive skin with a dark patch behind the eye; found near ponds.',
'Pool Frog':'Usually greenish-brown with spots; close identification can be difficult.',
'Marsh Frog':'Large greenish frog with dark spots, often near water.',
'Tree Frog':'Many have toe pads for climbing and bright green skin.',
'Bullfrog':'Large frog with a broad head; not native to Britain.',
'Other Frog':'Patterns vary a lot; a photo and the habitat are useful clues.'},
'Other':{
'Fox':'Pointed muzzle, triangular ears and a long bushy tail.',
'Deer':'Hoofed mammal; size, antlers and rump pattern vary among deer species.',
'Mouse':'Small rodent with a pointed muzzle, whiskers and long thin tail.',
'Bat':'The only mammals capable of sustained powered flight; wings are skin membranes.',
'Lizard':'Scaly skin, long tail and usually four legs; some look snake-like.',
'Worm':'Long, soft segmented body; earthworms help mix and aerate soil.',
'Slug':'Soft shell-less-looking mollusc; often active in damp conditions.',
'Fish':'Fins and gills are key clues; look at body shape and fin placement.',
'Tortoise':'Land-dwelling reptile with a protective shell and stout legs.',
'Other Animal':'If it does not fit the groups, take a clear photo and add a description.'}
}
source=(web/'app.js').read_text()
found=re.search(r'const FIELD_GUIDE_VARIETIES=(\{.*?\});',source)
assert found
varieties=json.loads(found.group(1))
assert set(varieties)==set(facts)==set(group_facts)
for group,names in varieties.items():
    assert set(names)==set(facts[group]),(group,set(names)^set(facts[group]))
assert sum(map(len,varieties.values()))==128

# Replace the cartoon-only illustration and vague/misleading generic-category thumbnails.
# Generic photos use a photographic montage with no species claim, not a false single-animal match.
for dest in (web/'field_art_v66',raw/'field_art_v66'):
    shutil.copytree(dest.parent/'field_art_v65',dest,dirs_exist_ok=True)
    def portrait(name):return Image.open(dest/(name+'.webp')).convert('RGB')
    def montage(names, label):
        can=Image.new('RGB',(480,480),'#f5efe3')
        for i,n in enumerate(names):
            im=portrait(n)
            if im.size[0]!=im.size[1]: im=ImageOps.fit(im,(210,210))
            else: im=im.resize((210,210))
            im=im.crop((0,0,210,165))
            x=25+(i%2)*217; y=27+(i//2)*185
            can.paste(im,(x,y))
        draw=ImageDraw.Draw(can)
        draw.rounded_rectangle((22,405,460,466),radius=12,fill='#f4f0e6')
        draw.text((48,426),label,fill='#17372f')
        return can
    montage(['other-fox','bird-robin','frog-common-frog','beetle-rose-chafer'],'Wildlife').resize((256,256)).save(dest/'other-group.webp',quality=90)
    montage(['other-mouse','other-lizard','other-bat','other-tortoise'],'Another animal').resize((256,256)).save(dest/'other-other-animal.webp',quality=90)
    # neutral nature-photo tile, no confusing older cartoon question mark
    uncertain=ImageOps.fit(portrait('other-fox'),(256,256))
    uncertain=uncertain.filter(ImageFilter.GaussianBlur(radius=19))
    mask=Image.new('RGBA',(256,256),(6,24,29,96)); uncertain=Image.alpha_composite(uncertain.convert('RGBA'),mask)
    d=ImageDraw.Draw(uncertain);d.rounded_rectangle((37,37,219,219),radius=32,fill=(236,248,236,229));d.text((109,76),'?',fill=(28,88,73,255),stroke_width=1)
    d.text((81,150),'Not sure',fill=(28,88,73,255))
    uncertain.convert('RGB').save(dest/'other-not-sure.webp',quality=90)
    # Leave the existing illustrative Peacock until a licensed, correctly identified reference image is available:
    # do not substitute a photo of the similarly named peacock bird or a different butterfly.

# Write guide facts into source directly: works offline in .NET MAUI WebView and browser preview.
js_data={'groups':group_facts,'types':facts}
(web/'field_guide_facts_v66.json').write_text(json.dumps(js_data,ensure_ascii=False,indent=2)+'\n')
(raw/'field_guide_facts_v66.json').write_text(json.dumps(js_data,ensure_ascii=False,indent=2)+'\n')
addon=r'''
/* v3.10.3 • educational Field Guide: browser/native offline, no changes to saved data. */
const HUSH_FIELD_EDUCATION=__FACTS__;
const hushFieldPreviousHome=renderHome;
renderHome=function(){
 const html=hushFieldPreviousHome();
 return html.replace('<div class="stats">','<div class="hush-guide-cta"><button type="button" id="hush-guide-from-home" class="hush-guide-entry">📖 Open full-screen Field Guide <span aria-hidden="true">↗</span></button><small>Learn how to recognise wildlife — even before a sighting</small></div><div class="stats">');
};
const hushFieldPreviousDex=renderDex;
renderDex=function(){return '<div class="hush-guide-cta"><button type="button" id="hush-guide-from-dex" class="hush-guide-entry">📖 Full-screen Field Guide ↗</button><small>Compare pictures and learn the clues for each kind</small></div>'+hushFieldPreviousDex()};
const hushFieldPreviousVarieties=renderFieldGuideVarieties;
renderFieldGuideVarieties=function(){
 hushFieldPreviousVarieties();
 const grid=$('field-guide-types');if(!grid)return;
 const parent=grid.parentElement;
 if(parent&&!parent.querySelector('#hush-guide-from-form')){
   const button=document.createElement('button');button.type='button';button.id='hush-guide-from-form';button.className='hush-guide-entry';button.textContent='📖 Open full-screen guide · see identification clues';parent.insertBefore(button,grid);
 }
 let tip=parent.querySelector('#hush-inline-tip');
 if(!tip){tip=document.createElement('p');tip.id='hush-inline-tip';tip.className='hush-inline-tip';grid.insertAdjacentElement('afterend',tip)}
 const refresh=()=>{
  const group=s.spottedSpecies;const selection=group==='Cat'?($('cat-coat')?.value||'Other'):(s.spottedDetail||'Not sure');
  tip.textContent='Look for: '+(HUSH_FIELD_EDUCATION.types[group]?.[selection]||HUSH_FIELD_EDUCATION.groups[group]||HUSH_FIELD_EDUCATION.groups.Other);
 };
 grid.querySelectorAll('[data-guide-type]').forEach(button=>button.addEventListener('click',refresh));refresh();
};
const hushFieldPreviousEdit=renderEditFieldGuide;
renderEditFieldGuide=function(){
 hushFieldPreviousEdit();
 const grid=$('edit-visual-types');if(!grid)return;
 if(!grid.parentElement.querySelector('.hush-edit-guide-entry')){
  const button=document.createElement('button');button.type='button';button.className='hush-guide-entry hush-edit-guide-entry';button.textContent='📖 Full-screen identification guide';grid.before(button);
 }
};
const hushFieldPreviousWire=wireScreen;
wireScreen=function(){hushFieldPreviousWire();};
let hushGuideContext=null;
function hushGuideHasForm(){return !!($('wildlife-species')||$('edit-species'))}
function hushGuideOpen(group,type){
 if(document.querySelector('#hush-fullscreen-guide'))return;
 const fromEdit=!!$('edit-species'),fromCapture=!!$('wildlife-species');
 hushGuideContext={fromEdit,fromCapture,focus:document.activeElement,overflow:document.body.style.overflow,group:FIELD_GUIDE_VARIETIES[group]?group:'Cat',type:type||null};
 const screen=document.createElement('section');screen.id='hush-fullscreen-guide';screen.className='hush-fullscreen-guide';screen.setAttribute('role','dialog');screen.setAttribute('aria-modal','true');screen.setAttribute('aria-label','Wildlife Field Guide');
 document.body.appendChild(screen);document.body.style.overflow='hidden';hushGuideRender();
 screen.querySelector('#hush-guide-close')?.focus();
}
function hushGuideClose(){const screen=$('hush-fullscreen-guide');if(!screen)return;screen.remove();if(hushGuideContext){document.body.style.overflow=hushGuideContext.overflow;hushGuideContext.focus?.focus?.()}hushGuideContext=null;}
function hushGuideRender(){
 const screen=$('hush-fullscreen-guide'),ctx=hushGuideContext;if(!screen||!ctx)return;
 const group=ctx.group,types=FIELD_GUIDE_VARIETIES[group]||[],type=types.includes(ctx.type)?ctx.type:null;
 const detail=type?HUSH_FIELD_EDUCATION.types[group]?.[type]:HUSH_FIELD_EDUCATION.groups[group];
 const chips=SPECIES.map(g=>`<button type="button" data-hush-guide-group="${esc(g)}" class="hush-guide-chip ${g===group?'active':''}" aria-pressed="${g===group}">${FIELD_GUIDE_EMOJI[g]||'🐾'} ${esc(g)}</button>`).join('');
 const cards=types.map(name=>`<button type="button" class="hush-guide-reference ${name===type?'active':''}" data-hush-guide-type="${esc(name)}" aria-pressed="${name===type}"><img src="${fieldGuideArt(group,name)}" alt="Illustrated reference for ${esc(name)}" loading="lazy"><strong>${esc(name)}</strong><small>${esc(HUSH_FIELD_EDUCATION.types[group]?.[name]||'Observe carefully and compare several features.')}</small></button>`).join('');
 const image=fieldGuideArt(group,type);
 const chosenAction=hushGuideHasForm()&&(ctx.fromCapture||ctx.fromEdit);
 screen.innerHTML=`<header class="hush-guide-top"><div><div class="hush-guide-kicker">HUSH HUNT • LITTLE EXPLORERS</div><h2>Wildlife Field Guide</h2><p>Study the clues, then decide what you really saw.</p></div><button type="button" id="hush-guide-close" class="hush-guide-close" aria-label="Close field guide">✕</button></header>
 <div class="hush-guide-scroll"><div class="hush-guide-chips" role="group" aria-label="Wildlife groups">${chips}</div>
 <article class="hush-guide-feature"><img src="${image}" alt="Field-guide reference image for ${esc(type||group)}"><div><div class="hush-guide-kicker">${esc(group)} • ${type?'KIND':'FAMILY'}</div><h3>${esc(type||group)}</h3><p>${esc(detail)}</p>${type?`<p class="hush-guide-small">Also check: ${esc(HUSH_FIELD_EDUCATION.groups[group])}</p>`:''}${chosenAction?`<button type="button" id="hush-guide-use" class="hush-guide-use">Use this ${type?'identification':'animal group'} ✓</button>`:''}</div></article>
 <h3 class="hush-guide-subtitle">Compare ${esc(group.toLowerCase())} kinds <span>${types.length} examples</span></h3>
 <div class="hush-guide-references">${cards}</div><p class="hush-guide-disclaimer">These are illustrative teaching references, not verified diagnostic photographs. Colour and appearance can vary. No live automatic identification is performed. When unsure, save your own observation as “Not sure”. Never chase, handle or disturb wildlife.</p></div>`;
 screen.querySelector('#hush-guide-close').onclick=hushGuideClose;
 screen.querySelectorAll('[data-hush-guide-group]').forEach(b=>b.onclick=()=>{ctx.group=b.dataset.hushGuideGroup;ctx.type=null;hushGuideRender()});
 screen.querySelectorAll('[data-hush-guide-type]').forEach(b=>b.onclick=()=>{ctx.type=b.dataset.hushGuideType;hushGuideRender();screen.querySelector('.hush-guide-feature')?.scrollIntoView({block:'nearest',behavior:'smooth'})});
 const use=screen.querySelector('#hush-guide-use');if(use)use.onclick=hushGuideUse;
}
function hushGuideUse(){
 const ctx=hushGuideContext;if(!ctx)return;
 const group=ctx.group,type=ctx.type;
 if(ctx.fromCapture){
  const species=$('wildlife-species');if(species){species.value=group;species.dispatchEvent(new Event('change',{bubbles:true}));}
  if(type){if(group==='Cat'){$('cat-coat').value=type;s.coatChoice=type;}else{s.spottedDetail=type;const field=$('wildlife-detail');if(field)field.value=type;}}
  renderFieldGuideVarieties();
 }else if(ctx.fromEdit){
  const species=$('edit-species');if(species){species.value=group;species.dispatchEvent(new Event('change',{bubbles:true}));}
  if(type){if(group==='Cat'){const coat=$('edit-coat');if(coat)coat.value=type}else{const detail=$('edit-species-detail');if(detail)detail.value=type;}}
  renderEditFieldGuide();
 }
 hushGuideClose();
}
document.addEventListener('click',event=>{
 const target=event.target?.closest?.('#hush-guide-from-home,#hush-guide-from-dex,#hush-guide-from-form,.hush-edit-guide-entry');
 if(!target)return;
 if(target.matches('#hush-guide-from-form'))hushGuideOpen(s.spottedSpecies,s.spottedSpecies==='Cat'?$('cat-coat')?.value:s.spottedDetail);
 else if(target.matches('.hush-edit-guide-entry'))hushGuideOpen($('edit-species')?.value||'Cat',$('edit-species')?.value==='Cat'?$('edit-coat')?.value:$('edit-species-detail')?.value);
 else hushGuideOpen('Cat',null);
});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&$('hush-fullscreen-guide')){e.preventDefault();hushGuideClose()} });
'''
addon=addon.replace('__FACTS__',json.dumps(js_data,ensure_ascii=False,separators=(',',':')))
for target in (web/'app.js',raw/'app.js'):
    js=target.read_text()
    js=js.replace("const WHISKER_BUILD='3.10.1', WHISKER_BUILD_NUMBER=64;","const WHISKER_BUILD='3.10.3', WHISKER_BUILD_NUMBER=66;")
    js=js.replace('field_art_v65/','field_art_v66/')
    js=js.replace('ART PACK 62','REALISTIC FIELD GUIDE 66')
    assert js!=target.read_text()
    target.write_text(js+'\n'+addon+'\n')
css=r'''
/* v3.10.3 full-screen educational wildlife guide */
.hush-guide-cta{margin:12px 0 20px;padding:12px 14px;border-radius:18px;background:#213a3c;border:1px solid #81e4bf55;display:grid;gap:4px}
.hush-guide-cta small{font-size:11px;color:#d1eae0}
.hush-guide-entry{display:block;width:100%;border:1px solid #86ead4;border-radius:13px;background:#1e534e;color:#f1fff8;text-align:center;font-size:13px;font-weight:800;padding:14px 9px;cursor:pointer}
.hush-guide-entry:focus-visible,.hush-fullscreen-guide button:focus-visible{outline:3px solid #f8e69f;outline-offset:2px}
.hush-inline-tip{background:#203b38;border-left:3px solid #89eed0;padding:10px 12px;border-radius:8px;color:#ddf8ec;font-size:12px;line-height:1.45;margin:5px 0 12px}
.hush-fullscreen-guide{position:fixed;z-index:75;inset:0;background:#101f24;color:#f7f8ed;display:flex;flex-direction:column;overflow:hidden;font-family:inherit;padding-top:env(safe-area-inset-top)}
.hush-guide-top{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;padding:20px max(16px,calc((100vw - 1040px)/2)) 14px;background:linear-gradient(130deg,#143831,#123840 63%,#172b32);border-bottom:1px solid #8ac9b533}
.hush-guide-kicker{font-size:10px;text-transform:uppercase;font-weight:900;letter-spacing:1.1px;color:#a7ecce}
.hush-guide-top h2{font-size:25px;margin:4px 0}.hush-guide-top p{font-size:12px;margin:0;color:#d2e7db}
.hush-guide-close{border:1px solid #d2e6da44;color:#fff;background:#30534d;border-radius:14px;padding:10px 15px;font-size:20px;cursor:pointer}
.hush-guide-scroll{overflow-y:auto;overscroll-behavior:contain;padding:17px max(16px,calc((100vw - 1040px)/2)) calc(30px + env(safe-area-inset-bottom));height:100%}
.hush-guide-chips{display:flex;overflow-x:auto;gap:8px;scroll-snap-type:x proximity;padding:0 2px 14px}
.hush-guide-chip{flex:0 0 auto;scroll-snap-align:start;padding:10px 12px;border:1px solid #81a9a35c;border-radius:999px;background:#1b3b3e;color:#e5f4f0;font-weight:750;font-size:12px}
.hush-guide-chip.active{background:#d6f3d6;color:#16372e;border-color:#d6f3d6}
.hush-guide-feature{display:grid;grid-template-columns:minmax(112px,220px) 1fr;gap:16px;align-items:center;padding:14px;background:#1d3435;border:1px solid #528e7f6b;border-radius:22px;margin:3px 0 20px}
.hush-guide-feature img{display:block;width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:14px;background:#efe9d8}
.hush-guide-feature h3{font-size:23px;margin:7px 0}.hush-guide-feature p{line-height:1.5;font-size:14px;margin:7px 0}.hush-guide-small{color:#b8d5c8;font-size:12px!important}
.hush-guide-use{border:0;border-radius:12px;background:#b6f2cb;color:#12372d;padding:13px;font-weight:850;cursor:pointer;margin:6px 0 0}
.hush-guide-subtitle{display:flex;align-items:center;gap:12px;justify-content:space-between;margin:18px 2px 14px;font-size:17px}.hush-guide-subtitle span{font-size:11px;color:#b4d5c7}
.hush-guide-references{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}
.hush-guide-reference{border:1px solid #7daa9959;background:#234044;border-radius:15px;overflow:hidden;display:flex;flex-direction:column;text-align:left;padding:0 0 13px;color:#f3f9ee;cursor:pointer}
.hush-guide-reference.active{outline:3px solid #baf0c3;outline-offset:-3px;background:#31544a}
.hush-guide-reference img{width:100%;aspect-ratio:1/1;object-fit:cover;background:#e4dfd2}
.hush-guide-reference strong{padding:10px 11px 0;font-size:14px}.hush-guide-reference small{padding:6px 11px 0;font-size:11px;line-height:1.45;color:#d1e5dd}
.hush-guide-disclaimer{color:#b3d1c4;font-size:11px;line-height:1.5;margin:20px 0}
@media(max-width:480px){.hush-guide-top h2{font-size:21px}.hush-guide-feature{grid-template-columns:110px minmax(0,1fr);gap:12px}.hush-guide-feature h3{font-size:17px}.hush-guide-feature p{font-size:12px}.hush-guide-kicker{font-size:9px}.hush-guide-references{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.hush-guide-feature img{align-self:start}}
@media(prefers-reduced-motion:reduce){.hush-guide-chips{scroll-snap-type:none}}
'''
for target in (web/'style.css',raw/'style.css'):
    target.write_text(target.read_text()+'\n'+css)
# bump versioned static assets in both stores and their HTML references to avoid old cached art.
for folder in (web,raw):
    shutil.copy2(folder/'app.js',folder/'app_v66.js')
    shutil.copy2(folder/'style.css',folder/'style_v66.css')
    for filename in ['index.html','index_v64.html']:
        path=folder/filename
        if path.exists():
            txt=path.read_text().replace('3.10.1-64','3.10.3-66').replace('app_v64.js','app_v66.js').replace('style_v64.css','style_v66.css')
            path.write_text(txt)
    if (folder/'index_v64.html').exists(): shutil.copy2(folder/'index_v64.html', folder/'index_v66.html')
    sw=folder/'sw.js'
    if sw.exists(): sw.write_text(sw.read_text().replace('shell-v64','shell-v66').replace('index_v64.html','index_v66.html').replace('app_v64.js','app_v66.js').replace('style_v64.css','style_v66.css'))
    manifest=folder/'manifest.webmanifest'
    if manifest.exists():
        m=manifest.read_text().replace('3.10.1','3.10.3');manifest.write_text(m)
proj=root/'WhiskerHunt/WhiskerHunt.csproj';proj.write_text(proj.read_text().replace('<ApplicationDisplayVersion>3.10.1','<ApplicationDisplayVersion>3.10.3').replace('<ApplicationVersion>64','<ApplicationVersion>66'))
(root/'HushHunt_v3.10.3_CHANGELOG.md').write_text('# Hush Hunt v3.10.3 · Build 66\n\n- Full-screen offline educational field guide with animal-group filter, photographs-style comparison cards, detailed identification clues, close/back and safe return.\n- 17 animal-group descriptions plus 128 individually written variety tips. The field guide never claims automatic species identification.\n- Guide accessible on Home, in Collection, in live sighting save, and in Edit discovery; optional “Use this identification” fills existing fields without touching stored records.\n- Replaced misleading generic Other-group tiles with mixed-realistic wildlife montages, replacing the cartoon Not sure tile with a neutral photographic-background illustration.\n- Peacock butterfly tile is still illustrative, not a verified photograph: a correctly licensed field photo is needed to replace it safely.\n- Both native MAUI and browser resources updated to field_art_v66, app_v66, style_v66. Cache updated.\n- Existing Android application ID, storage and backup v1 format unchanged. No uninstall or data clearing.\n')
(root/'README_v3.10.3.md').write_text('# Hush Hunt v3.10.3 — Build 66\n\nOpen `WhiskerHunt.sln` in Visual Studio, restore and deploy over the existing installed app. Do not uninstall the app.\n\nNew full-screen educational field guide available from Home, Collection, and real sighting create/edit flows. All reference imagery and information available offline. Identification requires the user to choose; no recognition AI is claimed.\n\nThe guide drawings and AI-generated photorealistic illustrations are *not authenticated species photographs*. Some may not show diagnostic traits reliably. The original Peacock butterfly cartoon remains labelled as an illustration until a properly licensed, reviewed species image is integrated.\n\nNo saved collections, map pins, photos, or backups are changed.\n')
print('Updated',sum(map(len,varieties.values())),'identification tips',len(varieties),'groups')
