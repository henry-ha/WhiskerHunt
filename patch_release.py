from pathlib import Path
import re
root=Path('/mnt/data/hush_v3111')
JS=r'''

/* v3.10.11 / 74 — immersive rotating themes, neutral mystery capture and compact controls.
 * Theme settings live separately from the animal database; no migration or reset.
 */
const HUSH_THEMES_74=[
 {id:'twilight-fox',name:'Purple fox twilight',accent:'#d37ce7',live:'#159d87',ar:'#7064ec'},
 {id:'blue-morpho-garden',name:'Blue Morpho garden',accent:'#59ddd7',live:'#158e80',ar:'#367be7'},
 {id:'mountain-deer',name:'Mountain deer',accent:'#e8c58f',live:'#3e9052',ar:'#4388bb'},
 {id:'robin-woodland',name:'Robin woodland',accent:'#b2d980',live:'#219b67',ar:'#4988ce'},
 {id:'moonlit-owl',name:'Moonlit owl',accent:'#bcb1fa',live:'#317f85',ar:'#7266e7'},
 {id:'butterfly-meadow',name:'Butterfly meadow',accent:'#efbf75',live:'#3a9b6b',ar:'#487ee1'}
];
function hushReadTheme74(){
 try{const v=JSON.parse(localStorage.getItem('hush.theme.settings.v74')||'{}');
  return {mode:v.mode==='static'?'static':'dynamic',theme:HUSH_THEMES_74.some(t=>t.id===v.theme)?v.theme:'twilight-fox',motion:v.motion===true};
 }catch{return {mode:'dynamic',theme:'twilight-fox',motion:false};}
}
let hushThemePrefs74=hushReadTheme74();
function hushSelectLaunchTheme74(){
 if(hushThemePrefs74.mode==='static')return hushThemePrefs74.theme;
 let previous=-1;
 try{previous=Number(localStorage.getItem('hush.theme.last.v74')||'-1');}catch{}
 // Make each launch different from the last one. Rerenders do not shuffle.
 const leap=1+Math.floor(Math.random()*(HUSH_THEMES_74.length-1));
 const index=((previous>=0?previous:Math.floor(Math.random()*HUSH_THEMES_74.length))+leap)%HUSH_THEMES_74.length;
 try{localStorage.setItem('hush.theme.last.v74',String(index));}catch{}
 return HUSH_THEMES_74[index].id;
}
let hushLaunchTheme74=hushSelectLaunchTheme74();
function hushCurrentTheme74(){return HUSH_THEMES_74.find(t=>t.id===(hushThemePrefs74.mode==='static'?hushThemePrefs74.theme:hushLaunchTheme74))||HUSH_THEMES_74[0];}
function hushApplyTheme74(){
 const theme=hushCurrentTheme74(),hero=document.querySelector('.hush-story-hero');
 if(!hero)return;
 hero.style.setProperty('--hush-wallpaper',`url("themes_v74/${theme.id}.webp")`);
 hero.style.setProperty('--hush-theme-accent',theme.accent);
 hero.style.setProperty('--hush-live',theme.live);
 hero.style.setProperty('--hush-ar',theme.ar);
 hero.classList.toggle('hush-motion',hushThemePrefs74.motion);
}
function hushPersistTheme74(){
 try{localStorage.setItem('hush.theme.settings.v74',JSON.stringify(hushThemePrefs74));}catch{toast('Theme changes may not persist in private mode.');}
 hushApplyTheme74();
}
function hushThemeSettings74(){
 const optionMarkup=HUSH_THEMES_74.map(t=>`<button type="button" data-hush-theme-id="${t.id}" class="hush-theme-choice ${hushCurrentTheme74().id===t.id?'active':''}" aria-pressed="${hushCurrentTheme74().id===t.id}"><img src="themes_v74/${t.id}.webp" alt=""><span>${esc(t.name)}</span></button>`).join('');
 openModal(`<div class="sheet-head"><h2>🎨 Home screen themes</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim">Choose a new wildlife adventure each time you open Hush Hunt, or keep a favourite scene.</p>
 <div class="hush-theme-mode" role="group" aria-label="Theme behaviour"><button id="hush-theme-dynamic" class="secondary ${hushThemePrefs74.mode==='dynamic'?'active':''}" aria-pressed="${hushThemePrefs74.mode==='dynamic'}">🔀 Dynamic</button><button id="hush-theme-static" class="secondary ${hushThemePrefs74.mode==='static'?'active':''}" aria-pressed="${hushThemePrefs74.mode==='static'}">📌 Static</button></div>
 <p class="footnote" id="hush-theme-explanation">${hushThemePrefs74.mode==='dynamic'?'Dynamic rotates to a different scene whenever you reopen the app.':'Static keeps the selected scene on every launch.'}</p>
 <h3>Wildlife scenes</h3><div class="hush-theme-grid">${optionMarkup}</div>
 <label class="check-row hush-motion-setting"><input id="hush-theme-motion" type="checkbox" ${hushThemePrefs74.motion?'checked':''}><span>Subtle background motion (off by default; respects reduced-motion settings)</span></label>
 <div class="actions"><button type="button" class="primary" id="hush-theme-done">Save theme</button></div>`,false,'hush-theme-sheet');
 const mode=(kind)=>{
  hushThemePrefs74.mode=kind;
  if(kind==='static')hushThemePrefs74.theme=hushCurrentTheme74().id;
  hushPersistTheme74();
  $('hush-theme-dynamic').setAttribute('aria-pressed',String(kind==='dynamic'));
  $('hush-theme-static').setAttribute('aria-pressed',String(kind==='static'));
  $('hush-theme-dynamic').classList.toggle('active',kind==='dynamic');
  $('hush-theme-static').classList.toggle('active',kind==='static');
  $('hush-theme-explanation').textContent=kind==='dynamic'?'Dynamic rotates to a different scene whenever you reopen the app.':'Static keeps the selected scene on every launch.';
 };
 $('hush-theme-dynamic').onclick=()=>mode('dynamic');
 $('hush-theme-static').onclick=()=>mode('static');
 document.querySelectorAll('[data-hush-theme-id]').forEach(btn=>btn.onclick=()=>{
  hushThemePrefs74.theme=btn.dataset.hushThemeId;
  hushLaunchTheme74=btn.dataset.hushThemeId;
  if(hushThemePrefs74.mode!=='static')mode('static');
  hushPersistTheme74();
  document.querySelectorAll('[data-hush-theme-id]').forEach(b=>{const on=b===btn;b.classList.toggle('active',on);b.setAttribute('aria-pressed',String(on))});
 });
 $('hush-theme-motion').onchange=e=>{hushThemePrefs74.motion=e.target.checked;hushPersistTheme74()};
 $('hush-theme-done').onclick=()=>{hushPersistTheme74();closeModal();render()};
}
renderHome=function(){
 const total=allSightings().length,discovered=visibleWildlife().length,badges=medals().filter(m=>m.ok).length;
 const current=hushCurrentTheme74();
 return `<section class="hush-story-home"><div class="hush-story-hero hush-immersive-home" style="--hush-wallpaper:url('themes_v74/${current.id}.webp');--hush-theme-accent:${current.accent};--hush-live:${current.live};--hush-ar:${current.ar}">
 <div class="hush-story-topbar"><button id="hush-theme-open-home" type="button" class="hush-story-icon" aria-label="Change home theme">⚙️</button><button type="button" class="hush-story-icon" data-go="quests" aria-label="Achievements">🏆</button></div>
 <div class="hush-story-brand"><span class="hush-story-paw" aria-hidden="true">🐾</span><h1>Hush <em>Hunt</em></h1><p>EXPLORE · DISCOVER · LEARN</p></div>
 <div class="hush-home-hero-spacer" aria-hidden="true"></div>
 <div class="hush-home-action-zone"><p class="hush-theme-tag">${esc(current.name)}</p><div class="hush-story-main-actions"><button type="button" id="hush-direct-live" class="hush-story-main hush-story-main-live"><span class="emoji">📷</span><strong>Live Capture</strong><small>Find real wildlife</small></button><button type="button" id="hush-direct-ar" class="hush-story-main hush-story-main-ar"><span class="emoji">✨</span><strong>AR Safari</strong><small>Explore virtual wildlife</small></button></div>
 <div class="hush-story-mini-actions"><button type="button" class="hush-story-mini" data-go="dex"><span>🖼️</span><strong>Collection</strong></button><button type="button" class="hush-story-mini" data-go="explore"><span>📍</span><strong>Map</strong></button><button type="button" class="hush-story-mini" data-go="quests"><span>🏆</span><strong>Quests</strong></button></div></div></div>
 <div class="hush-story-stats"><div><strong>${discovered}</strong><span>Discoveries</span></div><div><strong>${total}</strong><span>Sightings</span></div><div><strong>${badges}</strong><span>Badges</span></div></div><p class="hush-release-caption">v${WHISKER_BUILD} · build ${WHISKER_BUILD_NUMBER}</p></section>`;
};
const hushProfileBefore74=renderProfile;
renderProfile=function(){return hushProfileBefore74().replace('<div class="profile-actions">','<div class="profile-actions"><button id="hush-theme-open-profile" class="secondary" type="button">🎨 &nbsp; Home screen theme <span>›</span></button>')};
const hushWireBefore74=wireScreen;
wireScreen=function(){
 hushWireBefore74();
 $('hush-theme-open-home')?.addEventListener('click',hushThemeSettings74);
 $('hush-theme-open-profile')?.addEventListener('click',hushThemeSettings74);
 $('hush-direct-live')?.addEventListener('click',hushFastLiveCapture);
 $('hush-direct-ar')?.addEventListener('click',()=>startArEncounter());
 hushApplyTheme74();
};

// Only one fallback per species, named Other. Old saved "Not sure" records stay readable.
const hushFormerVarieties74=renderFieldGuideVarieties;
renderFieldGuideVarieties=function(){
 hushFormerVarieties74();
 const grid=$('field-guide-types');if(!grid)return;
 const group=s.spottedSpecies;
 // Existing 'Other Snail', 'Other Frog', etc. are legacy catch-all records.
 grid.querySelectorAll('[data-guide-type]').forEach(tile=>{
  const kind=tile.dataset.guideType;
  if(kind==='Not sure'||/^Other(?:\s|$)/.test(kind))tile.remove();
 });
 const tile=document.createElement('button');tile.type='button';tile.className='field-guide-tile hush-other-tile';tile.setAttribute('data-guide-type','Other');
 tile.setAttribute('aria-pressed',String(!s.spottedDetail||/^Other|Not sure$/.test(s.spottedDetail)));
 if(!s.spottedDetail||/^Other|Not sure$/.test(s.spottedDetail))tile.classList.add('chosen');
 tile.innerHTML=`<span class="field-guide-figure"><img src="field_art_v74/other-other.webp" loading="lazy" alt="" width="136" height="136"></span><span>Other</span>`;
 tile.onclick=()=>{
  s.spottedDetail='Other';const input=$('wildlife-detail');if(input)input.value='Other';
  if(group==='Cat'){const coat=$('cat-coat');if(coat)coat.value='Other';}
  grid.querySelectorAll('[data-guide-type]').forEach(b=>{b.classList.toggle('chosen',b===tile);b.setAttribute('aria-pressed',String(b===tile))});
  if(typeof hushRefreshIdentifiedPanel==='function')hushRefreshIdentifiedPanel();
 };
 grid.appendChild(tile);
 const hint=grid.parentElement?.querySelector('.field-help');
 if(hint&&hint.textContent.includes('Not sure'))hint.textContent='Choose Other if none of the examples match. Add a description in the notes.';
};
const hushFormerEditGuide74=renderEditFieldGuide;
renderEditFieldGuide=function(){
 hushFormerEditGuide74();const grid=$('edit-visual-types');if(!grid)return;
 grid.querySelectorAll('[data-guide-type]').forEach(btn=>{if(btn.dataset.guideType==='Not sure'||/^Other(?:\s|$)/.test(btn.dataset.guideType))btn.remove()});
 const other=document.createElement('button');other.type='button';other.className='field-guide-tile';other.dataset.guideType='Other';other.innerHTML='<span class="field-guide-figure"><img src="field_art_v74/other-other.webp" alt=""></span><span>Other</span>';
 other.onclick=()=>{const species=$('edit-species')?.value;const el=species==='Cat'?$('edit-coat'):$('edit-species-detail');if(el)el.value='Other';renderEditFieldGuide()};grid.appendChild(other);
};
const hushOldGuideRender74=hushGuideRender;
hushGuideRender=function(){hushOldGuideRender74();const screen=$('hush-fullscreen-guide');if(!screen)return;
 screen.querySelectorAll('.hush-guide-reference').forEach(tile=>{
  const kind=tile.dataset.hushGuideType;
  if(/^Other(?:\s|$)/.test(kind))tile.remove();
 });
 const note=screen.querySelector('.hush-guide-disclaimer');if(note)note.textContent='Illustrations are learning examples, not verified identifications. If the type is uncertain, choose Other and describe what you saw. Never disturb wildlife.';
};

// Mystery captures must not display a cat/species label before a person identifies it.
const hushPreviousForm74=showCatForm;
showCatForm=function(photo){
 const result=hushPreviousForm74(photo);
 const select=$('wildlife-species');
 if(select && !s.revisitId && (!s.wildTarget||s.wildTarget==='Unknown')){
  s.spottedSpecies='Other';s.spottedDetail='Other';hushCaptureCategory='Other wildlife';
  select.value='Other';select.dispatchEvent(new Event('change',{bubbles:true}));
 }
 const panel=$('hush-identified-panel');
 if(panel){
  const h=$('hush-id-title'),sub=$('hush-id-subtitle'),tags=$('hush-id-tags'),features=$('hush-id-features');
  if(h && select?.value==='Other')h.textContent='Mystery discovery';
  if(sub && select?.value==='Other')sub.textContent='What did you spot? Choose a wildlife family below.';
  if(tags && select?.value==='Other')tags.innerHTML='<span>Unidentified</span><span>Live photo</span>';
  if(features && select?.value==='Other')features.innerHTML='<li>Look at body shape, colour, wings or legs.</li><li>Pick a species only when you recognise its features.</li>';
  // Do not claim image recognition without an actual on-device classifier.
  const info=document.createElement('p');info.className='hush-mystery-help';info.textContent='No automatic species match is claimed. Use the guide photos to identify your discovery safely.';
  panel.querySelector('.hush-identified-card')?.appendChild(info);
  $('hush-id-audio')?.remove();
 }
 const title=document.querySelector('#modal-layer .sheet-head h2');if(title)title.textContent='Your discovery';
 const change=$('change-species');if(change){change.textContent='⇄ Change animal';change.setAttribute('aria-label','Change animal');}
 return result;
};
const hushRefreshPanelBefore74=hushRefreshIdentifiedPanel;
hushRefreshIdentifiedPanel=function(){
 hushRefreshPanelBefore74();
 const group=s.spottedSpecies,title=$('hush-id-title'),sub=$('hush-id-subtitle');
 if(group==='Other'&&title){title.textContent='Mystery discovery';if(sub)sub.textContent='Choose a wildlife family to identify your photo.';}
};

// Live camera UI: safe, uncluttered default; game tokens are opt-in.
const hushEncounterBefore74=showEncounter;
showEncounter=function(image,quality,options={}){
 const result=hushEncounterBefore74(image,quality,options);
 if(options.live===true&&options.ar!==true){
  const sheet=document.querySelector('#modal-layer .sheet'),stage=$('encounter-stage');
  if(!sheet||!stage)return result;
  sheet.classList.add('hush-camera-clean');
  const tag=stage.querySelector('.encounter-capture-tag');if(tag)tag.textContent='● LIVE';
  const toggle=document.createElement('button');toggle.type='button';toggle.id='hush-game-toggle';toggle.className='hush-game-toggle';toggle.textContent='🐾 Game';toggle.setAttribute('aria-pressed','false');
  toggle.onclick=()=>{const on=sheet.classList.toggle('hush-game-open');toggle.setAttribute('aria-pressed',String(on));toggle.textContent=on?'✕ Close game':'🐾 Game'};
  stage.appendChild(toggle);
  const zoomHint=stage.querySelector('.hush-pinch-hint');if(zoomHint)zoomHint.textContent='Pinch inward to zoom out · Spread to zoom in';
  const title=document.querySelector('#modal-layer .sheet-head h2');if(title)title.textContent='Live Capture';
 }
 return result;
};
'''
# overlay JS file at both locations, use same source; update art ref URL in existing for new pack (w/o duplicating content)
for folder in [root/'BrowserPreview',root/'WhiskerHunt/Resources/Raw']:
 p=folder/'app_v73.js';t=p.read_text()
 t=t.replace("const WHISKER_BUILD='3.10.10', WHISKER_BUILD_NUMBER=73;","const WHISKER_BUILD='3.10.11', WHISKER_BUILD_NUMBER=74;")
 t=t.replace("return 'field_art_v73/'+", "return 'field_art_v74/'+")
 t+=JS
 (folder/'app_v74.js').write_text(t)
 (folder/'app.js').write_text(t)
 p.unlink()
 for filename in ['index_v73.html','index.html']:
  h=folder/filename
  if h.exists():
   html=h.read_text().replace('3.10.10-73','3.10.11-74').replace('app_v73.js','app_v74.js').replace('style_v73.css','style_v74.css')
   (folder/'index_v74.html').write_text(html)
   (folder/'index.html').write_text(html)
   if filename=='index_v73.html':h.unlink()
# app xaml release
main=root/'WhiskerHunt/MainPage.xaml';main.write_text(main.read_text().replace('index_v73.html','index_v74.html'))
proj=root/'WhiskerHunt/WhiskerHunt.csproj';proj.write_text(proj.read_text().replace('<ApplicationDisplayVersion>3.10.10</ApplicationDisplayVersion>','<ApplicationDisplayVersion>3.10.11</ApplicationDisplayVersion>').replace('<ApplicationVersion>73</ApplicationVersion>','<ApplicationVersion>74</ApplicationVersion>'))
print('App script patched')
