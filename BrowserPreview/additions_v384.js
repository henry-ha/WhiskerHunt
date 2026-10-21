/* v3.8.4 Hush Hunt: visual species tools, wildlife Safari, species album, opt-in streets.
   All new UI uses the existing private data schema and retained application ID. */
const HUSH_SAFARI_STYLES={Cat:['#e7ad84','#ad6b53'],Dog:['#dab178','#a57445'],Snail:['#81ba79','#537a55'],Butterfly:['#f6a9d4','#9a76d9'],Moth:['#baa7da','#73649a'],Bee:['#ffd774','#d3a33d'],Ladybird:['#fd8290','#bd344e'],Beetle:['#65bb99','#287d72'],Dragonfly:['#90dfee','#479fad'],Ant:['#d19b79','#a46253'],Spider:['#c2b5ed','#795baf'],Bird:['#aad1ed','#6684b4'],Squirrel:['#e8aa71','#a86440'],Rabbit:['#f6ddbe','#c6aa8d'],Hedgehog:['#d5b287','#8b6957'],Frog:['#95d88c','#4f9964'],Other:['#e4c9fd','#8e83c1']};
const HUSH_AR_CATALOG=[];
for(const group of SPECIES.filter(x=>x!=='Cat')){
 for(const [i,label] of (FIELD_GUIDE_VARIETIES[group]||['Other']).entries()){
  if(label==='Not sure')continue;
  const colors=HUSH_SAFARI_STYLES[group]||HUSH_SAFARI_STYLES.Other;
  HUSH_AR_CATALOG.push({key:`wildlife-${slugifyText(group)}-${slugifyText(label)}`,name:label==='Other'?`Mystery ${group}`:label,species:group,speciesDetail:label,coat:'Other',base:colors[0],accent:colors[1],belly:'#ffefde',rarity:i<2?'common':i<5?'uncommon':'rare',breed:group});
 }
}
AR_CAT_MODELS.push(...HUSH_AR_CATALOG);
// Balanced species discovery rather than a cat-biased 120+ model pool.
const hushOldRandomArModel=randomArModel;
randomArModel=function(except=''){
 const groups=SPECIES.filter(g=>AR_CAT_MODELS.some(m=>(m.species||'Cat')===g && m.key!==except));
 const pickGroup=groups[Math.floor(Math.random()*groups.length)]||'Cat';
 const seen=new Set(s.cats.filter(c=>c.virtual).map(c=>c.arModelHint));
 const groupModels=AR_CAT_MODELS.filter(m=>(m.species||'Cat')===pickGroup && m.key!==except);
 const unseen=groupModels.filter(m=>!seen.has(m.key));
 const pool=unseen.length?unseen:groupModels;
 const weighted=pool.map(m=>({m,w:rarityWeight(m.rarity)}));
 let n=Math.random()*weighted.reduce((a,b)=>a+b.w,0);
 for(const x of weighted){n-=x.w;if(n<=0)return x.m}
 return pool[0]||hushOldRandomArModel(except);
};
const hushOldArSvg=renderArCatSvg;
renderArCatSvg=function(model,compact=false){
 if(!model.species||model.species==='Cat')return hushOldArSvg(model,compact);
 const icon=FIELD_GUIDE_EMOJI[model.species]||'🐾';
 const shade=model.base||'#a3c3a6';
 const contrast=model.accent||'#43596f';
 // Illustration emblem, not a photorealistic or world-tracked animal. Inline SVG
 // stays compositable in a local camera photo without loading a network asset.
 return `<svg class="ar-cat-svg ar-wildlife-svg" viewBox="0 0 200 160" role="img" aria-label="${esc(model.name)}"><ellipse cx="100" cy="146" rx="68" ry="9" fill="#00000033"/><circle cx="100" cy="73" r="67" fill="${shade}" stroke="${contrast}" stroke-width="5"/><circle cx="100" cy="72" r="58" fill="#ffffff33"/><text x="100" y="113" text-anchor="middle" font-family="sans-serif" font-size="91">${icon}</text><path d="M49 130 Q100 145 151 130" fill="none" stroke="${contrast}" stroke-width="5" opacity=".5" stroke-linecap="round"/></svg>`;
};
const hushOldArRefresh=refreshArEncounterUi;
refreshArEncounterUi=function(){
 hushOldArRefresh();
 const m=getArModel(s.arModelKey),group=m.species||'Cat';
 if(group!=='Cat'){
  const mount=$('encounter-ar-cat');if(mount)mount.innerHTML=`<img class="ar-wildlife-art" src="${fieldGuideArt(group,m.speciesDetail)}" alt="Illustrated ${esc(m.name)}">`;
 }
 const badge=$('ar-model-badge');if(badge)badge.textContent=`${speciesIcon(group)} Virtual ${group.toLowerCase()}: ${m.name}`;
 const tag=document.querySelector('.encounter-capture-tag');if(tag&&s.encounterAr)tag.textContent=`● LIVE · VIRTUAL ${group.toUpperCase()}`;
 const help=document.querySelector('.encounter-quick-help');if(help&&s.encounterAr)help.textContent=`✨ ${group} found! Drag the discovery token to collect it.`;
 const title=document.querySelector('.encounter-help p');if(title&&s.encounterAr)title.textContent='This is a stylised 2D creature overlay, not true world-tracked AR. Animals are fictional game encounters; no real wildlife is handled or disturbed.';
 const primary=$('throw-item');if(primary&&s.encounterAr&&!s.encounterCaptured){primary.innerHTML=group==='Cat'?whiskerPawSvgMarkup():`<span class="wild-tool-art" aria-hidden="true">${FIELD_TOOLS[group]?.icon||'🧭'}</span>`;primary.insertAdjacentHTML('beforeend','<span class="drag-prompt">DRAG</span>');primary.classList.toggle('wild-token',group!=='Cat');}
 const alt=$('tool-lure');if(alt&&s.encounterAr){const tool=FIELD_TOOLS[group]||FIELD_TOOLS.Cat;alt.querySelector('span').textContent=tool.altIcon;alt.querySelector('small').textContent=tool.secondary;alt.setAttribute('aria-label',`Switch to ${tool.secondary}`);}
};
const hushOldSafariName=showVirtualNamingForm;
showVirtualNamingForm=function(){hushOldSafariName();const m=getArModel(s.arModelKey);const group=m.species||'Cat';const label=document.querySelector('label[for="virtual-name"]');if(label)label.textContent=`${group} name`;const btn=$('virtual-save-final');if(btn)btn.textContent=`Keep this ${group.toLowerCase()} ${speciesIcon(group)}`;};
const hushOldVirtualGallery=renderVirtualGallery;
renderVirtualGallery=function(){return hushOldVirtualGallery().replace('My AR cats 🐾','My AR wildlife ✨').replace(/(\d+) cats<\/span>/,'$1 creatures</span>').replace('cats discovered','virtual creatures discovered').replace('cats are available','creatures are available').replace('a new cat in a new habitat','new wildlife friends in different habitats');};
const hushOldVirtualDetail=openVirtualCatDetail;
openVirtualCatDetail=function(cat){hushOldVirtualDetail(cat);const g=speciesOf(cat);const btn=$('virtual-find-more');if(btn)btn.textContent='✨ Find more virtual wildlife';const del=$('virtual-delete');if(del)del.textContent='Delete virtual discovery';};
// All 17 species get an illustrated, collectible challenge. The original Cat Bingo
// remains as a bonus challenge for existing users instead of losing old progress.
const hushOldDex=renderDex;
renderDex=function(){
 let html=hushOldDex();
 const real=s.cats.filter(c=>!c.virtual);
 const discoveredGroups=new Set(real.map(c=>speciesOf(c)));
 const tiles=SPECIES.map(group=>{
  const found=real.filter(c=>speciesOf(c)===group);
  const varieties=new Set(found.map(c=>group==='Cat'?(c.coat||'Other'):(c.speciesDetail||''))).size;
  const total=FIELD_GUIDE_VARIETIES[group]?.length||1;
  return `<button type="button" class="hush-challenge-tile ${found.length?'found':''}" data-filter="Species:${esc(group)}" aria-label="See ${esc(group)} discoveries"><img src="${fieldGuideArt(group)}" alt=""><strong>${esc(group)}</strong><small>${found.length?`${varieties} / ${total} kinds`:'Not found yet'}</small><span class="hush-tick">${found.length?'✓':'?'}</span></button>`;
 }).join('');
 const section=`<section class="hush-challenge"><div class="eyebrow">THE WORLD IS YOUR COLLECTION</div><div class="flex between"><h3>Wildlife Bingo 🌎</h3><span class="bingo-progress">${discoveredGroups.size} / ${SPECIES.length}</span></div><p class="dim">Discover each animal group, then collect its different varieties. Tap a picture to see your finds!</p><div class="hush-challenge-grid">${tiles}</div></section>`;
 html=html.replace('<div class="bingo">',section+'<div class="bingo">');
 html=html.replace('COAT COLLECTION CHALLENGE','BONUS · CAT COATS');
 return html;
};
// Switch discovery tools on the open live-camera screen, without restarting video.
function updateEncounterSpecies(group){
 if(s.encounterAr||s.encounterCaptured)return;
 s.wildTarget=FIELD_TOOLS[group]?group:'Unknown';s.spottedSpecies=s.wildTarget==='Unknown'?'Cat':s.wildTarget;
 s.encounterTool='ball';s.encounterLured=false;
 syncEncounterToolDock('ball');
 const label=document.querySelector('.encounter-quick-help'),tool=discoveryTool();
 if(label)label.textContent=`① Aim at the animal · ② Drag the ${tool.primary} · ③ Discover!`;
 const instructions=document.querySelector('.encounter-instructions');if(instructions)instructions.textContent=`Drag the ${tool.primary} onto the ring. You can change species anytime.`;
 const orb=$('encounter-orb');if(orb){orb.innerHTML=s.wildTarget==='Cat'?whiskerPawSvgMarkup('capture-paw'):`<span class="wild-orb-art">${tool.icon}</span>`;orb.classList.toggle('wild-token',s.wildTarget!=='Cat');}
 const picker=$('encounter-species');if(picker)picker.value=s.wildTarget;
 const tag=$('encounter-species-hint');if(tag)tag.textContent=`${tool.icon} ${tool.primary} · ${tool.altIcon} ${tool.secondary}`;
}
const hushOldShowEncounter=showEncounter;
showEncounter=function(image,quality,options={}){
 hushOldShowEncounter(image,quality,options);
 if(!$('encounter-stage'))return;
 if(s.encounterAr){refreshArEncounterUi();return}
 const anchor=document.querySelector('.encounter-quick-help');
 if(anchor && !$('encounter-species')){
  anchor.insertAdjacentHTML('beforebegin',`<div class="hush-live-species"><label for="encounter-species">🐾 Change animal while spotting</label><select id="encounter-species" class="select" aria-label="Change species live"><option value="Unknown">🧭 Not sure yet</option>${SPECIES.map(g=>`<option value="${esc(g)}">${speciesIcon(g)} ${esc(g)}</option>`).join('')}</select><small id="encounter-species-hint"></small></div>`);
  $('encounter-species').onchange=e=>updateEncounterSpecies(e.target.value);
 }
 updateEncounterSpecies(s.wildTarget);
};
// Enable explicit private-vs-online map choice. The opt-in is only in memory.
s.hushStreetEnabled=false;s.hushStreetZoom=14;s.hushStreetCenter=null;s.hushSelectedIndex=0;
function hushDistanceKm(a,b){const toRad=Math.PI/180,dLat=(b.lat-a.lat)*toRad,dLon=(b.lng-a.lng)*toRad;const k=Math.sin(dLat/2)**2+Math.cos(a.lat*toRad)*Math.cos(b.lat*toRad)*Math.sin(dLon/2)**2;return 12742*Math.asin(Math.min(1,Math.sqrt(k)))}
function hushDistanceText(km){return km<.2?'Same approximate area':`≈ ${km<10?km.toFixed(1):Math.round(km)} km straight-line`}
function hushProject(lat,lng,z){const n=256*2**z,clamped=Math.max(-85.05,Math.min(85.05,lat));const sin=Math.sin(clamped*Math.PI/180);return {x:(lng+180)/360*n,y:(.5-Math.log((1+sin)/(1-sin))/(4*Math.PI))*n}}
function hushUnproject(x,y,z){const n=256*2**z;return {lng:x/n*360-180,lat:Math.atan(Math.sinh(Math.PI*(1-2*y/n)))*180/Math.PI}}
const hushOldRenderExplore=renderExplore;
renderExplore=function(){
 const html=hushOldRenderExplore().replace('<h1>Cat map 🗺️</h1>','<h1>Wildlife map 🗺️</h1>');
 const geo=savedMapPoints();
 const map=`<section class="hush-street-section"><div class="flex between"><div><div class="eyebrow">OPTIONAL ONLINE MAP</div><h3>Explore the real streets 🗺️</h3></div><button id="hush-street-toggle" type="button" class="${s.hushStreetEnabled?'secondary':'primary'}">${s.hushStreetEnabled?'🔒 Private plot':'🌍 Street map'}</button></div><p class="dim">${s.hushStreetEnabled?'Street tiles are supplied by OpenStreetMap. Turn them off at any time.':'The private plot above stays completely offline. Enable street tiles only if you want to share the map area with OpenStreetMap.'}</p>${s.hushStreetEnabled&&geo.length?`<div id="hush-street-map" class="hush-street-map" aria-label="Interactive map with saved wildlife sightings"><div id="hush-tile-canvas" class="hush-tile-canvas"></div><div id="hush-street-pins"></div><div class="hush-map-controls"><button type="button" id="hush-zoom-in" aria-label="Zoom in">+</button><button type="button" id="hush-zoom-out" aria-label="Zoom out">−</button><button type="button" id="hush-map-reset" aria-label="Show all saved locations">⌖</button></div><span class="hush-osm-credit">© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a></span></div><div id="hush-map-distances" class="hush-map-distances" aria-live="polite"></div><small class="footnote">Distances are straight-line estimates between rounded, approximately 1 km pins—not walking distances or exact wildlife locations. Drag to pan, use +/− to zoom.</small>`:''}</section>`;
 return html.replace('<div class="map-foot">',map+'<div class="map-foot">');
};
function hushStreetSelection(i){
 const geo=savedMapPoints(),point=geo[i];if(!point)return;
 s.hushSelectedIndex=i;
 document.querySelectorAll('.hush-street-pin').forEach(b=>b.classList.toggle('chosen',Number(b.dataset.streetIndex)===i));
 document.querySelectorAll('[data-map-entry]').forEach(b=>b.classList.toggle('map-entry-selected',Number(b.dataset.mapEntry)===i));
 document.querySelectorAll('.map-pin[data-map-select]').forEach(b=>b.classList.toggle('map-pin-selected',Number(b.dataset.mapSelect)===i));
 const card=$('map-selected-card');if(card)card.innerHTML=`<img src="${point.photo}" alt=""><div><strong>${esc(point.name)}</strong><small>📍 Saved approximate area · ${dateDisplay(point.at)}</small></div>`;
 const panel=$('hush-map-distances');if(panel)panel.innerHTML=`<strong>📏 From ${esc(point.name)}</strong><p class="dim">${geo.length>1?'Approximate distance to your other sightings:':'Add another pinned sighting to compare distances.'}</p>${geo.filter((g,j)=>j!==i).slice(0,12).map(g=>`<div class="hush-distance-row"><span>${speciesIcon(g.species)} ${esc(g.name)}</span><b>${hushDistanceText(hushDistanceKm(point,g))}</b></div>`).join('')}`;
}
function hushDrawStreetMap(){
 const area=$('hush-street-map'),tiles=$('hush-tile-canvas'),pins=$('hush-street-pins');if(!area||!tiles||!pins||!s.hushStreetEnabled)return;
 const geo=savedMapPoints();if(!geo.length)return;
 const w=area.clientWidth||350,h=area.clientHeight||340,z=s.hushStreetZoom;
 const center=s.hushStreetCenter||{lat:geo.reduce((a,g)=>a+g.lat,0)/geo.length,lng:geo.reduce((a,g)=>a+g.lng,0)/geo.length};
 const world=hushProject(center.lat,center.lng,z),left=world.x-w/2,top=world.y-h/2;
 const tx0=Math.floor(left/256),tx1=Math.floor((left+w)/256),ty0=Math.floor(top/256),ty1=Math.floor((top+h)/256),limit=2**z;
 let tileHtml='';
 for(let tx=tx0;tx<=tx1;tx++)for(let ty=ty0;ty<=ty1;ty++){if(ty<0||ty>=limit)continue;const x=((tx%limit)+limit)%limit;tileHtml+=`<img class="hush-map-tile" alt="" draggable="false" style="left:${Math.round(tx*256-left)}px;top:${Math.round(ty*256-top)}px" src="https://tile.openstreetmap.org/${z}/${x}/${ty}.png">`}
 tiles.innerHTML=tileHtml;
 pins.innerHTML=geo.map((g,i)=>{const p=hushProject(g.lat,g.lng,z);const near=geo.slice(0,i).filter(o=>o.lat===g.lat&&o.lng===g.lng).length;let x=p.x-left+near*13,y=p.y-top+near*13;return `<button type="button" class="hush-street-pin ${i===s.hushSelectedIndex?'chosen':''}" data-street-index="${i}" style="left:${x}px;top:${y}px" aria-label="Show ${esc(g.name)} on map"><span>${speciesIcon(g.species)}</span><small>${esc(g.name)}</small></button>`}).join('');
 pins.querySelectorAll('[data-street-index]').forEach(btn=>btn.onclick=()=>hushStreetSelection(Number(btn.dataset.streetIndex)));
 hushStreetSelection(Math.min(s.hushSelectedIndex,geo.length-1));
}
function hushOpenStreetConsent(){openModal(`<div class="sheet-head"><h2>See street tiles? 🗺️</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p>To show an interactive map inside Hush Hunt, your phone will download map tiles from <strong>OpenStreetMap</strong>.</p><p class="dim">OpenStreetMap may see your IP address and which approximate map areas you browse. We do not upload your photos, collection or complete list of pins. Zooming and panning may request more tiles. Ask a trusted adult if you're unsure.</p><div class="actions"><button type="button" class="secondary" id="hush-map-cancel">Stay private</button><button type="button" class="primary" id="hush-map-accept">Show street map</button></div>`);$('hush-map-cancel').onclick=closeModal;$('hush-map-accept').onclick=()=>{s.hushStreetEnabled=true;s.hushStreetCenter=null;closeModal();render()};}
function hushWireStreet(){
 const toggle=$('hush-street-toggle');if(!toggle)return;
 toggle.onclick=()=>{if(s.hushStreetEnabled){s.hushStreetEnabled=false;render()}else hushOpenStreetConsent()};
 const area=$('hush-street-map');if(!area)return;
 hushDrawStreetMap();
 $('hush-zoom-in').onclick=()=>{s.hushStreetZoom=Math.min(18,s.hushStreetZoom+1);hushDrawStreetMap()};
 $('hush-zoom-out').onclick=()=>{s.hushStreetZoom=Math.max(10,s.hushStreetZoom-1);hushDrawStreetMap()};
 $('hush-map-reset').onclick=()=>{s.hushStreetCenter=null;s.hushStreetZoom=14;hushDrawStreetMap()};
 let start=null,moved=false;
 area.addEventListener('pointerdown',e=>{if(e.target.closest('button,a'))return;const c=s.hushStreetCenter||(()=>{const g=savedMapPoints();return {lat:g.reduce((a,x)=>a+x.lat,0)/g.length,lng:g.reduce((a,x)=>a+x.lng,0)/g.length}})();start={x:e.clientX,y:e.clientY,center:hushProject(c.lat,c.lng,s.hushStreetZoom)};moved=false;try{area.setPointerCapture(e.pointerId)}catch{}});
 area.addEventListener('pointermove',e=>{if(!start)return;const dx=e.clientX-start.x,dy=e.clientY-start.y;if(Math.abs(dx)+Math.abs(dy)>4)moved=true;const p=hushUnproject(start.center.x-dx,start.center.y-dy,s.hushStreetZoom);s.hushStreetCenter={lat:Math.max(-85,Math.min(85,p.lat)),lng:((p.lng+540)%360)-180};hushDrawStreetMap()});
 area.addEventListener('pointerup',()=>{start=null});area.addEventListener('pointercancel',()=>{start=null});
 // Map interactions are not intended to track the player's real-time location.
}
const hushOldWireScreen=wireScreen;
wireScreen=function(){hushOldWireScreen();if(s.screen==='explore')hushWireStreet();};
const hushOldSelectPin=selectPrivateMapPin;
selectPrivateMapPin=function(i){hushOldSelectPin(i);hushStreetSelection(i)};
