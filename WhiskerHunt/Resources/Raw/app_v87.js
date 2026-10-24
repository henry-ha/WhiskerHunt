/* Whisker Hunt 2.7 — offline-first, no accounts, no tracking, no server. */
'use strict';
const WHISKER_BUILD='3.10.24', WHISKER_BUILD_NUMBER=87;
const DATABASE='whiskerhunt_local_v1', DB_VERSION=1;
const COATS=['Tabby','Ginger','Brown','Black','White','Cream','Tuxedo','Calico','Tortoiseshell','Grey','Colourpoint','Other'];
const PERSONALITIES=['Unknown','Curious','Sleepy','Playful','Shy','Friendly','Adventurous'];
const PERSONALITY_EMOJI={Unknown:'🐱',Curious:'🔎',Sleepy:'💤',Playful:'🧶',Shy:'🌙',Friendly:'💗',Adventurous:'🧭'};
const EMOJIS={Tabby:'🐯',Ginger:'🧡',Black:'🖤',White:'🤍',Tuxedo:'🎩',Calico:'🎨',Grey:'🌫️',Brown:'🤎',Cream:'🥛',Tortoiseshell:'🍁',Colourpoint:'🎭',Other:'🐱'};
const similarityCache=new Map();
let matchRequest=0;
let encounterEpoch=0;
let encounterCropEpoch=0;
let photoSelectionEpoch=0;
let nativePhotoRequestSequence=0, nativePhotoRequestToken=null;
let encounterResizeObserver=null;
let liveCamera=null;
let liveRequestEpoch=0;
let captureShots=[]; // Ephemeral review options only; never saved to Collection or backups.
const s={cats:[],profile:{name:'Hush Explorer',xp:0,claimed:[]},screen:'home',filter:'All',search:'',dexSort:'recent',image:'',cardBase64:'',catchMode:'new',selectedId:'',revisitId:'',journalFilter:'All',journalSearch:'',busy:false,db:null,native:false,storageBlocked:false,recoveryApproved:false,encounterLive:false,pendingApproxLocation:null,pendingApproxLocationAt:0};
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const id=()=>globalThis.crypto?.randomUUID?.()??String(Date.now())+Math.random().toString(36).slice(2);
const dateKey=d=>{const x=new Date(d);return [x.getFullYear(),String(x.getMonth()+1).padStart(2,'0'),String(x.getDate()).padStart(2,'0')].join('-')};
const today=()=>dateKey(new Date());
const dateDisplay=x=>new Date(x).toLocaleDateString(undefined,{day:'numeric',month:'short',year:'numeric'});
const catches=c=>c.sightings?.length??1;
const safePin=v=>Number.isFinite(Number(v))&&Number(v)>=-180&&Number(v)<=180;
const friendlyScore=c=>Math.min(100, 20+Math.max(0,catches(c)-1)*16);
const friendLabel=c=>catches(c)>=6?'Best buddies':catches(c)>=3?'Getting acquainted':'New friend';
const allSightings=()=>s.cats.filter(c=>!c.virtual).flatMap(c=>c.sightings||[]);
const level=()=>Math.floor(s.profile.xp/200)+1;
const levelTitle=()=>['Curious Scout','Street Spotter','Nature Noticer','Trail Seeker','Little Explorer','Field Observer','Wildlife Guide','Nature Keeper','Legendary Spotter','Hush Guardian'][Math.min(level()-1,9)];
// The Android WebView can handle native actions even when the Collection is using
// legacy IndexedDB storage. NEVER use this as a reason to switch databases:
// doing so can hide collections/photos saved by older app versions.
function hasAndroidActionBridge(){return window.whiskerNativeBridge===true || window.whiskerAndroidShell===true || window.whiskerNativeReady===true}
// Android ships a private native JSON Collection; only obsolete service worker caches
// are cleared. Never clear IndexedDB, application files, or user photos.
async function retireAndroidShellWorker(){
 if(!window.whiskerAndroidShell)return;
 try{if(navigator.serviceWorker?.getRegistrations){
  const registrations=await navigator.serviceWorker.getRegistrations();
  await Promise.all(registrations.filter(r=>new URL(r.scope).origin===location.origin).map(r=>r.unregister()));
 }}catch(error){console.debug('SW cleanup deferred',error)}
 try{if(globalThis.caches?.keys){
  const names=await caches.keys();
  await Promise.all(names.filter(n=>n.startsWith('whisker-hunt-shell-')).map(n=>caches.delete(n)));
 }}catch(error){console.debug('Shell cache cleanup deferred',error)}
}
function toast(msg){const el=$('toast');el.textContent=msg;el.classList.remove('hidden');clearTimeout(toast.timeout);toast.timeout=setTimeout(()=>el.classList.add('hidden'),3600)}
function openDb(){return new Promise((resolve,reject)=>{const r=indexedDB.open(DATABASE,DB_VERSION);r.onupgradeneeded=()=>{const d=r.result;if(!d.objectStoreNames.contains('cats'))d.createObjectStore('cats',{keyPath:'id'});if(!d.objectStoreNames.contains('meta'))d.createObjectStore('meta',{keyPath:'key'})};r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)})}
function transact(store,mode,method,value){return new Promise((resolve,reject)=>{
 const tx=s.db.transaction(store,mode);let result;const req=tx.objectStore(store)[method](value);
 req.onsuccess=()=>{result=req.result};tx.oncomplete=()=>resolve(result);
 tx.onerror=()=>reject(tx.error||req.error||new Error('Local storage transaction failed'));
 tx.onabort=()=>reject(tx.error||new Error('Local storage transaction aborted'));
})}
// Commit cat and XP together in browsers. Native mode syncs a single JSON snapshot.
function persistCatchAtomic(cat){if(s.native)return nativeSync();return new Promise((resolve,reject)=>{
 const tx=s.db.transaction(['cats','meta'],'readwrite');tx.objectStore('cats').put(cat);
 tx.objectStore('meta').put({key:'profile',value:s.profile});
 tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error||new Error('Catch save failed'));
 tx.onabort=()=>reject(tx.error||new Error('Catch save aborted'));
})}

// Each native write is acknowledged only after Android has validated and atomically
// replaced the snapshot. Queuing requests prevents out-of-order saves and lost edits.
let nativeSyncSequence=0, nativeSyncQueue=Promise.resolve();
const nativeSyncPending=new Map();
window.whiskerNativeSyncResult=function(token,ok){
 const pending=nativeSyncPending.get(String(token));if(!pending)return;
 nativeSyncPending.delete(String(token));clearTimeout(pending.timer);
 if(ok)pending.resolve();else pending.reject(new Error('Android could not save your collection'));
};
window.whiskerRequestNativeSync=function(token,allowEmpty=false){location.href='whiskerhunt://sync?request='+encodeURIComponent(token)+(s.recoveryApproved?'&recover=1':'')+(allowEmpty?'&allow-empty=1':'')};
function nativeSync(allowEmpty=false){
 if(s.storageBlocked&&!s.recoveryApproved)return Promise.reject(new Error('Android recovery required before saving'));
 if(!s.native)return Promise.resolve();
 if(!window.whiskerNativeReady)return Promise.reject(new Error('Android storage is not ready'));
 const run=()=>new Promise((resolve,reject)=>{
  const token=String(++nativeSyncSequence);
  const timer=setTimeout(()=>{
   nativeSyncPending.delete(token);reject(new Error('Android save timed out'));
  },15000);
  nativeSyncPending.set(token,{resolve,reject,timer});
  try{window.whiskerRequestNativeSync(token,allowEmpty)}
  catch(e){clearTimeout(timer);nativeSyncPending.delete(token);reject(e)}
 });
 const task=nativeSyncQueue.then(run,run);
 nativeSyncQueue=task.catch(()=>{});
 return task;
}
async function saveCat(c){if(s.native)return nativeSync();await transact('cats','readwrite','put',c)}
async function removeCat(c){if(s.native)return nativeSync(s.cats.length===0);await transact('cats','readwrite','delete',c.id)}
async function saveProfile(){if(s.native)return nativeSync();await transact('meta','readwrite','put',{key:'profile',value:s.profile})}
async function boot(){if(window.whiskerAndroidShell){
  // Native shell must never open IndexedDB: it can contain unrelated browser data.
  s.db=null;s.native=true;
  $('view').innerHTML='<div class="feature-empty"><div class="big">🐾</div><h3>Loading your Collection…</h3><p>Checking your private collection on this device.</p></div>';
 }else{try{s.db=await openDb();s.cats=await transact('cats','readonly','getAll');const p=await transact('meta','readonly','get','profile');if(p?.value){s.profile={...s.profile,...p.value}}}catch(e){console.error(e);toast('Local storage unavailable. Check browser privacy settings.')}render();}$('nav-catch').addEventListener('click',startCatch);document.querySelectorAll('[data-nav]').forEach(b=>b.addEventListener('click',()=>navigate(b.dataset.nav)));$('head-profile').addEventListener('click',()=>navigate('profile'));$('image-input').addEventListener('change',inputPhoto);$('library-input').addEventListener('change',inputPhoto);$('backup-input').addEventListener('change',importBackup);if(window.whiskerAndroidShell)retireAndroidShellWorker();else if('serviceWorker'in navigator&&location.protocol.startsWith('http'))navigator.serviceWorker.register('sw.js').catch(()=>{});window.whiskerBootComplete=true;
 if(window.whiskerAndroidShell){
  const requestReady=()=>{if(window.whiskerRequestNativeReady)window.whiskerRequestNativeReady();else location.href='whiskerhunt://ready'};
  requestReady();
  setTimeout(()=>{if(!window.whiskerNativeReady&&!s.storageBlocked){$('view').innerHTML='<div class="feature-empty"><div class="big">⚠️</div><h3>Collection did not load</h3><p>Your data has not been changed. Please retry.</p><button class="primary" id="retry-native-load">Retry loading</button></div>';$('retry-native-load').onclick=requestReady}},12000);
 }else if(window.whiskerPendingNativeData!==undefined)window.whiskerUseNativeStorage(window.whiskerPendingNativeData);
}
function navigate(page){closeModal();s.screen=page;window.scrollTo(0,0);document.querySelectorAll('[data-nav]').forEach(b=>b.classList.toggle('current',b.dataset.nav===page));render()}
function render(){const views={home:renderHome,dex:renderDex,explore:renderExplore,quests:renderQuests,profile:renderProfile,journal:renderJournal};$('view').innerHTML=(views[s.screen]||renderHome)();wireScreen()}
function wireScreen(){document.querySelectorAll('[data-go]').forEach(b=>b.addEventListener('click',()=>navigate(b.dataset.go)));document.querySelectorAll('[data-cat]').forEach(b=>b.addEventListener('click',()=>openDetail(b.dataset.cat)));document.querySelectorAll('[data-claim]').forEach(b=>b.addEventListener('click',()=>claimQuest(b.dataset.claim)));document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{s.filter=b.dataset.filter;render()}));if($('dex-search')){$('dex-search').value=s.search;$('dex-search').addEventListener('input',e=>{s.search=e.target.value;updateDexGrid()})}if($('dex-sort')){$('dex-sort').value=s.dexSort;$('dex-sort').addEventListener('change',e=>{s.dexSort=e.target.value;updateDexGrid()})}document.querySelectorAll('[data-map-select]').forEach(b=>b.addEventListener('click',()=>selectPrivateMapPin(Number(b.dataset.mapSelect))));document.querySelectorAll('[data-action]').forEach(b=>b.addEventListener('click',()=>action(b.dataset.action)));document.querySelectorAll('[data-journal-catch]').forEach(b=>b.addEventListener('click',startCatch));document.querySelectorAll('[data-journal-filter]').forEach(b=>b.addEventListener('click',()=>{s.journalFilter=b.dataset.journalFilter;render()}));if($('journal-search')){$('journal-search').value=s.journalSearch;$('journal-search').addEventListener('input',e=>{s.journalSearch=e.target.value;updateJournalCards()})}}
function section(label,link='',go=''){return `<div class="section-title"><h2>${label}</h2>${link?`<button class="text-btn" data-go="${go}">${link} →</button>`:''}</div>`}
function renderHome(){const total=allSightings().length;const daily=dailyQuests()[0];const latest=[...s.cats].sort((a,b)=>b.createdAt.localeCompare(a.createdAt)).slice(0,6);return `<div class="intro"><div class="eyebrow">YOUR CAT-CHASING ADVENTURE</div><h1>Hello, explorer <span>👋</span></h1><p class="dim no-margin" style="font-size:13px">Every whisker has a story. Find yours.</p></div><section class="hero"><span class="pill lime">✦ THE WORLD IS YOUR CATDEX</span><div class="hero-title">See a cat?<br>Catch the moment.</div><p class="hero-desc">Meet real cats, level up and build your own legendary collection.</p><button id="hero-catch" class="primary">📸 Catch a cat →</button><span class="hero-cat" aria-hidden="true">🐈</span></section><div class="stats"><div class="stat"><strong>${s.cats.length}</strong><span>Unique cats</span></div><div class="stat"><strong>${total}</strong><span>Sightings</span></div><div class="stat"><strong>${streak()}</strong><span>Day streak</span></div></div><div class="level-card"><div class="level-top"><span class="level-num">✦ LEVEL ${level()}</span><span class="level-name">${levelTitle()}</span></div><div class="progress"><b style="width:${s.profile.xp%200/2}%"></b></div><p class="progress-copy">${s.profile.xp%200} / 200 XP to your next level · ${s.profile.xp} total XP</p></div>${section('Today\'s challenge','All quests','quests')}<div class="quest-card"><div class="quest-top"><div class="quest-icon">${daily.icon}</div><div class="quest-details"><h3>${daily.title}</h3><p>${daily.description}</p></div><div class="quest-reward">+${daily.xp} XP</div></div><div class="quest-bar"><span style="width:${Math.min(100,100*daily.progress/daily.target)}%"></span></div><div class="flex between" style="margin-top:9px"><span class="count-label">${Math.min(daily.progress,daily.target)} / ${daily.target}</span>${questAction(daily)}</div></div>${section('Your cat collection','View Collection','dex')}${latest.length?`<div class="cat-strip">${latest.map(c=>`<button class="mini-cat" data-cat="${esc(c.id)}"><img src="${c.photo}" alt="${esc(c.name)}"><strong>${esc(c.name)}</strong><small>${speciesIcon(speciesOf(c))} ${esc(speciesOf(c))}${c.speciesDetail?' · '+esc(c.speciesDetail):speciesOf(c)==='Cat'?' · '+esc(c.coat):''} · ${catches(c)} sighting${catches(c)!==1?'s':''}</small></button>`).join('')}</div>`:`<div class="feature-empty"><div class="big">🐈‍⬛</div><h3>Your adventure starts here</h3><p>Found a friendly-looking feline? Snap your first cat and bring your Collection to life.</p><button id="empty-catch" class="secondary">Catch your first cat</button></div>`}`}
function renderDex(){const realCats=s.cats.filter(c=>!c.virtual&&(c.species||'Cat')==='Cat');const coats=new Set(realCats.map(c=>c.coat));return `<div class="page-head"><div class="eyebrow">YOUR COLLECTION</div><h1>The Collection 🐈</h1><p class="subtitle">${realCats.length} real cats · ${s.cats.filter(c=>c.virtual).length} virtual friends</p></div>${renderVirtualGallery()}<div class="bingo"><div class="flex between"><div><div class="eyebrow">COAT COLLECTION CHALLENGE</div><h3>Cat Bingo</h3></div><span class="bingo-progress">${coats.size} / ${COATS.length}</span></div><div class="bingo-grid">${COATS.map(c=>`<button class="bingo-tile ${coats.has(c)?'found':''}" data-filter="${c}" aria-label="Filter ${c} cats"><span>${EMOJIS[c]}</span><small>${c}</small>${coats.has(c)?'<b>✓</b>':'<b>?</b>'}</button>`).join('')}</div><p class="bingo-sub">${coats.size===COATS.length?'🎉 Your coat collection is complete!':'Meet cats with different coats to fill your album. Tap a tile to filter.'}</p></div><input class="search-input" id="dex-search" aria-label="Search cats" placeholder="⌕   Search your feline friends..."><div class="chips">${['All','Favourites',...COATS].map(c=>`<button class="chip ${s.filter===c?'selected':''}" data-filter="${c}">${c==='All'?'✦ ':c==='Favourites'?'♥ ':''}${c}</button>`).join('')}</div><div class="dex-sort-row"><label for="dex-sort">Sort your collection</label><select id="dex-sort" class="select" aria-label="Sort cats"><option value="recent">Recently discovered</option><option value="last">Last seen</option><option value="name">Name A–Z</option><option value="visits">Most sightings</option><option value="favourites">Favourites first</option></select></div><div id="dex-grid">${dexGrid()}</div>`}
function dexGrid(){const q=s.search.toLowerCase();const cs=s.cats.filter(c=>!c.virtual).filter(c=>(s.filter==='All'||(s.filter==='Favourites'&&c.fav)||c.coat===s.filter)&&(c.name.toLowerCase().includes(q)||c.coat.toLowerCase().includes(q))).sort((a,b)=>{const last=c=>Math.max(0,...(c.sightings||[]).map(v=>Date.parse(v.at)||0));switch(s.dexSort){case 'name':return a.name.localeCompare(b.name);case 'last':return last(b)-last(a);case 'visits':return catches(b)-catches(a)||a.name.localeCompare(b.name);case 'favourites':return Number(b.fav)-Number(a.fav)||last(b)-last(a);default:return b.createdAt.localeCompare(a.createdAt)}});return cs.length?`<div class="cat-grid">${cs.map(c=>`<button class="cat-tile" data-cat="${esc(c.id)}"><img class="cat-img" src="${c.photo}" alt="${esc(c.name)}"><div class="cat-info"><strong>${esc(c.name)}</strong><small>${esc(c.coat)} · ${catches(c)} sightings${c.personality&&c.personality!=='Unknown'?' · '+esc(c.personality):''}</small><div class="tagline"><span class="tag">${rank(c)}</span><span class="badge-heart">${c.fav?'♥':'♡'}</span></div></div></button>`).join('')}</div>`:`<div class="feature-empty empty-dex"><div class="big">🐱</div><h3>No cats found (yet!)</h3><p>${s.cats.length?'Try another filter or search.':'Every great collection begins with one curious cat.'}</p><button class="primary" id="dex-catch">📸 Catch a cat</button></div>`}
function updateDexGrid(){const node=$('dex-grid');if(node){node.innerHTML=dexGrid();node.querySelectorAll('[data-cat]').forEach(el=>el.addEventListener('click',()=>openDetail(el.dataset.cat)));const b=$('dex-catch');if(b)b.addEventListener('click',startCatch)}}
function rank(cat){const n=catches(cat);return n>=5?'👑 Local legend':n>=3?'★ Old friend':'✦ New friend'}
function streak(){const days=[...new Set(allSightings().map(x=>dateKey(x.at)))].sort().reverse();if(!days.length)return 0;const start=new Date();if(!days.includes(dateKey(start))){start.setDate(start.getDate()-1);if(!days.includes(dateKey(start)))return 0}let count=0;while(days.includes(dateKey(start))){count++;start.setDate(start.getDate()-1)}return count}
function weekKey(){const d=new Date();d.setHours(12,0,0,0);d.setDate(d.getDate()-((d.getDay()+6)%7));return dateKey(d)}
function weeklyQuests(){const entries=s.cats.filter(c=>!c.virtual&&(c.species||'Cat')==='Cat').flatMap(c=>c.sightings||[]).filter(v=>dateKey(v.at)>=weekKey());const newCats=s.cats.filter(c=>!c.virtual&&(c.species||'Cat')==='Cat'&&dateKey(c.createdAt)>=weekKey());const repeatIds=new Set(s.cats.filter(c=>!c.virtual&&(c.species||'Cat')==='Cat'&&c.sightings.some((v,i)=>i>0&&dateKey(v.at)>=weekKey())).map(c=>c.id));return [{id:'weekly-new',weekly:true,icon:'🧭',title:'Neighbourhood explorer',description:'Discover 3 different cats this week',progress:newCats.length,target:3,xp:200},{id:'weekly-friends',weekly:true,icon:'💜',title:'Familiar faces',description:'Log a repeat sighting for 2 different cats',progress:repeatIds.size,target:2,xp:150},{id:'weekly-days',weekly:true,icon:'📆',title:'Adventure days',description:'Spot cats on 3 different days this week',progress:new Set(entries.map(v=>dateKey(v.at))).size,target:3,xp:150}]}
function questMarker(q){return (q.weekly?weekKey():today())+':'+q.id}
function renderQuestCard(q){return `<div class="quest-card ${s.profile.claimed.includes(questMarker(q))?'complete':''}"><div class="quest-top"><div class="quest-icon">${q.icon}</div><div class="quest-details"><h3>${q.title}</h3><p>${q.description}</p></div><div class="quest-reward">+${q.xp} XP</div></div><div class="quest-bar"><span style="width:${Math.min(100,100*q.progress/q.target)}%"></span></div><div class="flex between" style="margin-top:9px"><span class="count-label">${Math.min(q.progress,q.target)} / ${q.target}</span>${questAction(q)}</div></div>`}
function dailyQuests(){const todaySightings=s.cats.filter(c=>!c.virtual&&(c.species||'Cat')==='Cat').flatMap(c=>c.sightings||[]).filter(a=>dateKey(a.at)===today());const todayNew=s.cats.filter(c=>!c.virtual&&(c.species||'Cat')==='Cat'&&dateKey(c.createdAt)===today());const coats=new Set(todayNew.map(c=>c.coat));return [{id:'first',icon:'📷',title:'First whisker of the day',description:'Record a cat sighting today',progress:todaySightings.length,target:1,xp:35},{id:'double',icon:'🐾',title:'Double pawprints',description:'Record two cat encounters today',progress:todaySightings.length,target:2,xp:60},{id:'discover',icon:'✨',title:'New face in town',description:'Meet one new cat today',progress:todayNew.length,target:1,xp:75},{id:'variety',icon:'🌈',title:'Coat collector',description:'Meet two different coat types today',progress:coats.size,target:2,xp:100}]}
function questAction(q){if(s.profile.claimed.includes(questMarker(q)))return `<span class="complete-word">✓ CLAIMED</span>`;if(q.progress>=q.target)return `<button class="text-btn" data-claim="${q.id}">Claim reward ✦</button>`;return `<span class="count-label">In progress</span>`}
function medals(){const cs=s.cats.filter(c=>!c.virtual&&(c.species||'Cat')==='Cat');const coats=new Set(cs.map(c=>c.coat));return [{icon:'🥇',name:'First Pawprint',desc:'Find your first cat',ok:cs.length>=1},{icon:'🐾',name:'Whisker Whisperer',desc:'Find 5 different cats',ok:cs.length>=5},{icon:'🌈',name:'Colour Collector',desc:'Discover 4 coat types',ok:coats.size>=4},{icon:'⭐',name:'Old Friends',desc:'Spot the same cat 3 times',ok:cs.some(c=>catches(c)>=3)},{icon:'👑',name:'Neighbourhood Legend',desc:'Spot one cat 5 times',ok:cs.some(c=>catches(c)>=5)},{icon:'🔥',name:'Dedicated Explorer',desc:'Reach a 3-day streak',ok:streak()>=3}]}
function renderQuests(){const qs=dailyQuests();return `<div class="page-head"><div class="eyebrow">DAILY & WEEKLY ADVENTURES</div><h1>Quests & rewards ✨</h1><p class="subtitle">Earn XP by exploring naturally. No need to disturb cats or visit private property.</p></div><div class="soft-card"><div class="flex between"><div><div class="eyebrow">TOTAL EXPERIENCE</div><h2 style="font-size:29px;margin:6px 0 0">${s.profile.xp} <small style="color:#c7abec;font-size:13px">XP</small></h2></div><div class="icon-round">🏆</div></div></div>${section('Daily quests')}<p class="quest-hint">Reset daily at local midnight.</p><div class="quest-grid">${qs.map(renderQuestCard).join('')}</div>${section('Weekly adventures')}<p class="quest-hint">Reset every Monday. Previous rewards remain yours.</p><div class="quest-grid">${weeklyQuests().map(renderQuestCard).join('')}</div>${section('Your badges')}<div class="medal-grid">${medals().map(m=>`<div class="medal ${m.ok?'unlocked':''}"><span>${m.icon}</span><strong>${m.name}</strong><small>${m.ok?'✓ Unlocked':m.desc}</small></div>`).join('')}</div>`}
function savedMapPoints(){
 return s.cats.flatMap(cat=>(cat.sightings||[]).filter(x=>x &&
    typeof x.lat==='number' && Number.isFinite(x.lat) && Math.abs(x.lat)<=90 &&
    typeof x.lng==='number' && Number.isFinite(x.lng) && Math.abs(x.lng)<=180)
  .map((entry)=>({lat:entry.lat,lng:entry.lng,at:entry.at,catId:cat.id,sightingId:entry.id,name:cat.name,photo:entry.photo||cat.photo,virtual:cat.virtual===true,species:speciesOf(cat)})))
  .sort((a,b)=>Date.parse(b.at)-Date.parse(a.at));
}
// A deliberately private coordinate plot, not map tiles: drawing it doesn't transmit GPS.
// Keep a marker clearly visible even when there is only one saved place.
function privatePlotPosition(point,points,index){
 if(points.length===1)return {x:50,y:50};
 const minLat=Math.min(...points.map(p=>p.lat)),maxLat=Math.max(...points.map(p=>p.lat));
 const minLng=Math.min(...points.map(p=>p.lng)),maxLng=Math.max(...points.map(p=>p.lng));
 let x=maxLng===minLng?50:22+56*(point.lng-minLng)/(maxLng-minLng);
 let y=maxLat===minLat?50:22+56*(maxLat-point.lat)/(maxLat-minLat);
 // Distinguish discoveries saved to the same rounded (approximately 1 km) cell.
 const duplicateRank=points.slice(0,index).filter(p=>p.lat===point.lat && p.lng===point.lng).length;
 if(duplicateRank){const angle=duplicateRank*2.4,offset=12*Math.min(duplicateRank,2);x+=Math.cos(angle)*offset;y+=Math.sin(angle)*offset}
 return {x:Math.max(13,Math.min(87,x)),y:Math.max(22,Math.min(78,y))};
}
function renderExplore(){
 const geo=savedMapPoints(),pins=geo.map((g,i)=>{
  const {x,y}=privatePlotPosition(g,geo,i);
  return `<button type="button" class="map-pin map-pin-v43 ${i===0?'map-pin-selected':''}" style="left:${x.toFixed(1)}%;top:${y.toFixed(1)}%" data-map-select="${i}" aria-label="Show ${esc(g.name)} on your private discovery plot"><span class="map-pin-icon">${speciesIcon(g.species)}</span><span class="map-pin-label">${esc(g.name)}</span></button>`;
 }).join('');
 const latest=geo[0];
 return `<div class="page-head"><div class="eyebrow">YOUR PRIVATE TRAIL</div><h1>Cat map 🗺️</h1><p class="subtitle">Your saved discoveries appear here. Viewing this private plot never sends your location anywhere.</p></div>
 <div class="map-board map-board-v43" id="private-map-board" role="group" aria-label="Private plot of ${geo.length} saved cat location${geo.length===1?'':'s'}">
  <div class="map-plot-caption">📍 ${geo.length} saved location${geo.length===1?'':'s'}</div>
  ${pins||`<div class="map-no-pins"><span>🐾</span><p>No location pins yet</p></div>`}
  ${latest?`<div id="map-selected-card" class="map-selected-card"><img src="${latest.photo}" alt=""><div><strong>${esc(latest.name)}</strong><small>📍 Saved approximate area · ${dateDisplay(latest.at)}</small></div></div>`:''}
 </div>
 <div class="map-foot"><span>🔒</span><div>This is a <strong>private location plot</strong>, not a street map. Tap a paw to see its saved discovery. For real streets, choose <strong>Open street map</strong> below; that requires your permission.</div></div>
 ${section(`Saved locations (${geo.length})`)}
 ${geo.length?geo.slice(0,40).map((g,i)=>`<div class="map-entry map-entry-v43 ${i===0?'map-entry-selected':''}" data-map-entry="${i}"><img src="${g.photo}" alt=""><div><strong>${esc(g.name)}</strong><small>${dateDisplay(g.at)} · Private ${g.virtual?'approximate':'saved'} location</small></div><button type="button" class="text-btn" data-map-select="${i}">Show pin</button><button type="button" class="text-btn map-street-btn" data-action="osm:${g.lat},${g.lng}">Street map ↗</button></div>`).join(''):
 `<div class="feature-empty"><div class="big">📍</div><h3>No saved places yet</h3><p>When you save a sighting, you can optionally add a private area. Never follow cats onto private property.</p></div>`}
 <div class="info-note">OpenStreetMap is an external website. We ask before sharing any selected approximate coordinates with it.</div>`;
}
function selectPrivateMapPin(index){
 const geo=savedMapPoints(),g=geo[index];if(!g)return;
 document.querySelectorAll('[data-map-select]').forEach(el=>el.classList.toggle('map-pin-selected',el.classList.contains('map-pin') && Number(el.dataset.mapSelect)===index));
 document.querySelectorAll('[data-map-entry]').forEach(el=>el.classList.toggle('map-entry-selected',Number(el.dataset.mapEntry)===index));
 const card=$('map-selected-card');
 if(card)card.innerHTML=`<img src="${g.photo}" alt=""><div><strong>${esc(g.name)}</strong><small>📍 Saved approximate area · ${dateDisplay(g.at)}</small></div>`;
 const board=$('private-map-board');board?.scrollIntoView?.({behavior:'smooth',block:'center'});
}
function askOpenStreetMap(lat,lng){
 if(!Number.isFinite(lat)||Math.abs(lat)>90||!Number.isFinite(lng)||Math.abs(lng)>180)return;
 const url=`https://www.openstreetmap.org/?mlat=${encodeURIComponent(lat)}&mlon=${encodeURIComponent(lng)}#map=16/${lat}/${lng}`;
 openModal(`<div class="sheet-head"><h2>Open a street map? 🗺️</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p>Whisker Hunt will open <strong>OpenStreetMap in your browser</strong>.</p><p class="dim">Only the selected saved <strong>approximate location</strong> is sent to OpenStreetMap. Your Collection photos and other discoveries stay on this device. Ask a trusted adult if you are unsure.</p><div class="actions"><button id="map-stay-private" type="button" class="secondary">Stay private</button><button id="map-open-browser" type="button" class="primary">Open street map ↗</button></div>`);
 $('map-stay-private').onclick=closeModal;
 $('map-open-browser').onclick=()=>{
  closeModal();
  if(hasAndroidActionBridge()){
   location.href='whiskerhunt://open?url='+encodeURIComponent(url);
  }else{
   const anchor=document.createElement('a');anchor.href=url;anchor.target='_blank';anchor.rel='noopener noreferrer';document.body.appendChild(anchor);anchor.click();anchor.remove();
  }
 };
}
window.whiskerExternalMapResult=function(success){
 if(!success)toast('No browser could open the street map. Your pin is still saved in Collection.');
};

function journalEntries(){return s.cats.flatMap(cat=>(cat.sightings||[]).map((entry,index)=>({cat,entry,isFirst:index===0}))).filter(x=>x.entry&&typeof x.entry.at==='string'&&Number.isFinite(Date.parse(x.entry.at))).sort((a,b)=>Date.parse(b.entry.at)-Date.parse(a.entry.at))}
function journalCards(){const query=s.journalSearch.trim().toLowerCase();const entries=journalEntries().filter(x=>(s.journalFilter==='All'||(s.journalFilter==='New cats'&&x.isFirst)||(s.journalFilter==='Reunions'&&!x.isFirst))&&(!query||[x.cat.name,x.cat.coat,x.entry.note||''].some(v=>String(v).toLowerCase().includes(query))));if(!entries.length)return `<div class="feature-empty"><div class="big">📖</div><h3>No matching memories</h3><p>Try another filter, or capture a cat to start your journal.</p><button class="secondary" data-journal-catch>📸 Catch a cat</button></div>`;let lastDay='';return entries.slice(0,100).map(({cat,entry,isFirst})=>{const day=dateKey(entry.at);const heading=day!==lastDay?`<h3 class="journal-day">${esc(dateDisplay(entry.at))}</h3>`:'';lastDay=day;return `${heading}<button class="journal-card" data-cat="${esc(cat.id)}"><img src="${entry.photo||cat.photo}" alt=""><span class="journal-card-body"><strong>${esc(cat.name)}</strong><small>${isFirst?'✨ First discovery':'🐾 Reunion'} · ${speciesIcon(speciesOf(cat))} ${esc(speciesOf(cat))}${cat.speciesDetail?" · "+esc(cat.speciesDetail):""}</small>${entry.note?`<span class="journal-note">${esc(entry.note)}</span>`:''}</span><span class="journal-arrow">›</span></button>`}).join('')+(entries.length>100?'<p class="footnote">Showing your 100 most recent matching sightings.</p>':'')}
function updateJournalCards(){const target=$('journal-results');if(!target)return;target.innerHTML=journalCards();target.querySelectorAll('[data-cat]').forEach(b=>b.addEventListener('click',()=>openDetail(b.dataset.cat)));const catchButton=target.querySelector('[data-journal-catch]');if(catchButton)catchButton.addEventListener('click',startCatch)}
function renderJournal(){const entries=journalEntries();const uniqueDays=new Set(entries.map(x=>dateKey(x.entry.at))).size;return `<div class="page-head"><div class="eyebrow">YOUR REAL-WORLD CAT ADVENTURES</div><h1>Sighting journal 📖</h1><p class="subtitle">${entries.length} encounters across ${uniqueDays} day${uniqueDays===1?'':'s'}. Your photos and memories stay private.</p></div><button class="text-btn journal-back" data-go="profile">← Back to profile</button><input class="search-input" id="journal-search" aria-label="Search sightings" placeholder="⌕   Search cats and memories..."><div class="chips">${['All','New cats','Reunions'].map(v=>`<button class="chip ${s.journalFilter===v?'selected':''}" data-journal-filter="${v}">${v}</button>`).join('')}</div><div id="journal-results">${journalCards()}</div>`}
function collectionInsights(){
 const entries=journalEntries(),coats=new Set(s.cats.filter(c=>!c.virtual&&(c.species||'Cat')==='Cat').map(c=>c.coat));
 const most=[...s.cats].sort((a,b)=>catches(b)-catches(a))[0];
 const latest=entries[0];const days=new Set(entries.map(x=>dateKey(x.entry.at))).size;
 const insight=(label,value,caption)=>`<div class="insight-card"><small>${label}</small><strong>${esc(value)}</strong><span>${esc(caption)}</span></div>`;
 return insight('📆 Adventure days',days,'Days with a sighting')+
  insight('🌈 Coat varieties',`${coats.size} / ${COATS.length}`,'Different appearances')+
  insight('👑 Most spotted',most?.name||'Not yet',most?`${catches(most)} encounters`:'Find your first cat')+
  insight('🐾 Last encounter',latest?dateDisplay(latest.entry.at):'Not yet',latest?latest.cat.name:'Start exploring');
}
function renderProfile(){return `<div class="page-head"><div class="eyebrow">YOUR JOURNEY</div><h1>Explorer profile ✦</h1></div><div class="profile-banner"><div class="profile-avatar">🐱</div><h2>${esc(s.profile.name)}</h2><p>Level ${level()} · ${levelTitle()}</p><div class="pill purple">${s.profile.xp} XP EARNED</div></div><div class="stats"><div class="stat"><strong>${s.cats.length}</strong><span>Cats</span></div><div class="stat"><strong>${allSightings().length}</strong><span>Moments</span></div><div class="stat"><strong>${medals().filter(m=>m.ok).length}</strong><span>Badges</span></div></div>${section('Your discovery insights')}<div class="insights-grid">${collectionInsights()}</div>${section('Your data')}<div class="profile-actions"><button class="secondary" data-go="journal">📖 &nbsp; Sighting journal <span>›</span></button><button class="secondary" data-action="rename-profile">✎ &nbsp; Change explorer name <span>›</span></button><button class="secondary" data-action="export">↧ &nbsp; Export collection backup <span>›</span></button><button class="secondary" data-action="import">↥ &nbsp; Restore a backup <span>›</span></button><button class="secondary" data-action="privacy-tools">🔒 &nbsp; Privacy & storage tools <span>›</span></button><button class="secondary" data-action="about">♡ &nbsp; Privacy & safety <span>›</span></button></div><p class="footnote">Offline-first. No account, analytics or external image uploads. Device/app data can be lost when uninstalled: export backups regularly.</p>`}
async function claimQuest(key){
 // A pending save must not award XP twice or overlap a catch/restore operation.
 if(s.busy||s.storageBlocked||!s.db)return;
 const q=[...dailyQuests(),...weeklyQuests()].find(x=>x.id===key);
 if(!q||q.progress<q.target)return;
 const marker=questMarker(q);
 if(!Array.isArray(s.profile.claimed))s.profile.claimed=[];
 if(s.profile.claimed.includes(marker))return;
 s.busy=true;
 const previousXp=s.profile.xp,previousClaimed=s.profile.claimed.slice();
 s.profile.claimed.push(marker);s.profile.xp+=q.xp;
 try{await saveProfile();toast(`🎉 Quest complete! +${q.xp} XP`);render()}
 catch(e){s.profile.xp=previousXp;s.profile.claimed=previousClaimed;toast('Unable to save quest reward. Please retry.');render()}
 finally{s.busy=false}
}
function openModal(content,keepLive=false){if(!keepLive)stopLiveCamera();encounterResizeObserver?.disconnect();encounterResizeObserver=null;const layer=$('modal-layer');layer.classList.remove('hidden');layer.setAttribute('aria-hidden','false');layer.innerHTML=`<div class="sheet" role="dialog" aria-modal="true"><div class="sheet-handle"></div><div class="whisker-build-stamp">Hush Hunt v${WHISKER_BUILD} · build ${WHISKER_BUILD_NUMBER}</div>${content}</div>`;layer.onclick=modalBackdrop;const b=layer.querySelector('[data-close]');if(b)b.addEventListener('click',closeModal)}
function modalBackdrop(e){if(e.target.id==='modal-layer')closeModal()}
function closeModal(){captureShots=[];nativePhotoRequestToken=null;liveRequestEpoch++;stopLiveCamera();encounterEpoch++;encounterCropEpoch++;photoSelectionEpoch++;encounterResizeObserver?.disconnect();encounterResizeObserver=null;const l=$('modal-layer');l.classList.add('hidden');l.setAttribute('aria-hidden','true');l.innerHTML=''}
function startCatch(catId=null){captureShots=[];nativePhotoRequestToken=null;photoSelectionEpoch++;if(s.busy)return toast('Please wait for the current save to finish.');if(s.storageBlocked)return toast('Restore your Collection backup before adding cats.');s.image='';s.encounterLive=false;s.revisitId=typeof catId==='string'&&s.cats.some(c=>c.id===catId)?catId:'';s.catchMode=s.revisitId?'repeat':'new';s.selectedId='';s.captureSummary=null;openModal(`<div class="sheet-head"><h2>Catch a cat! 📸</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim" style="font-size:13px">Start with a respectful photo, then play the capture encounter with a Whisker Paw or the Dangle Lure.</p><div class="capture-choice"><button id="live-photo" class="choice"><span>🎥</span><strong>Live encounter</strong><small>Drag tools over the live camera · beta</small></button><button id="take-photo" class="choice"><span>📸</span><strong>Take a photo</strong><small>Reliable camera fallback</small></button><button id="pick-photo" class="choice"><span>🖼️</span><strong>Choose a photo</strong><small>From your gallery</small></button></div><p class="footnote center">Live mode keeps only recent still frames in memory; it does not record video. Real cats only, please.</p>`);$('live-photo').onclick=startLiveEncounter;$('take-photo').onclick=()=>startMultiPhotoCapture();$('pick-photo').onclick=()=>requestEncounterPhoto(false)}
async function requestEncounterPhoto(capture){
 captureShots=[];
 const request=++liveRequestEpoch;
 // Invalidate an earlier Android picker *before* waiting for frame analysis.
 // Old picker callbacks must never replace a newer choice.
 nativePhotoRequestToken=null;
 photoSelectionEpoch++;
 // Freeze a safe still before invoking an external picker. If the user cancels,
 // the current encounter remains usable instead of showing a stopped video.
 if(liveCamera)await freezeLiveEncounter();
 if(request!==liveRequestEpoch)return;
 if(s.busy||s.storageBlocked)return toast('Please wait until storage is ready.');
 if(window.whiskerNativeReady){
  const token=String(++nativePhotoRequestSequence);
  nativePhotoRequestToken=token;
  location.href=(capture?'whiskerhunt://capture':'whiskerhunt://import')+'?request='+encodeURIComponent(token);
 }else $(capture?'image-input':'library-input').click();
}
async function inputPhoto(e){
 const file=e.target.files?.[0];e.target.value='';if(!file)return;
 nativePhotoRequestToken=null;
 const selection=++photoSelectionEpoch;
 if(!file.type.startsWith('image/'))return toast('Please choose an image file.');
 if(file.size>20*1024*1024)return toast('Please choose an image smaller than 20 MB.');
 try{
  const image=await resizePhoto(file);
  // Large images can finish decoding out of order. The newest selection wins.
  if(selection!==photoSelectionEpoch)return;
  deliverPhoto(image);
 }catch(err){if(selection===photoSelectionEpoch){console.error(err);toast('Could not read that photo. Try another JPG/PNG.')}}
}
async function resizePhoto(file){
 const bmp=await createImageBitmap(file);
 try{
  const k=Math.min(1,1100/Math.max(bmp.width,bmp.height)),canvas=document.createElement('canvas');
  canvas.width=Math.max(1,Math.round(bmp.width*k));canvas.height=Math.max(1,Math.round(bmp.height*k));
  const ctx=canvas.getContext('2d');ctx.drawImage(bmp,0,0,canvas.width,canvas.height);
  return canvas.toDataURL('image/jpeg',.84);
 }finally{bmp.close?.()}
}
window.whiskerNativePhoto=function(data,requestToken){
 // Android's picker can return after the player closes or retakes the encounter.
 // Only the most recently requested picker is permitted to update the screen.
 if(nativePhotoRequestToken===null||String(requestToken)!==nativePhotoRequestToken)return;
 nativePhotoRequestToken=null;
 if(!data?.startsWith('data:image/'))return toast('Native camera returned an invalid image.');
 const selection=++photoSelectionEpoch;
 const photo=new Image();photo.onload=()=>{
  if(selection!==photoSelectionEpoch)return;
  try{
   const canvas=document.createElement('canvas');const r=Math.min(1,1100/Math.max(photo.width,photo.height));
   canvas.width=Math.max(1,Math.round(photo.width*r));canvas.height=Math.max(1,Math.round(photo.height*r));
   canvas.getContext('2d').drawImage(photo,0,0,canvas.width,canvas.height);
   deliverPhoto(canvas.toDataURL('image/jpeg',.84));
  }catch(err){console.error(err);toast('Could not prepare that photo. Try again.')}
 };
 photo.onerror=()=>{if(selection===photoSelectionEpoch)toast('Camera photo could not be opened.')};
 photo.src=data;
};
window.whiskerNativePhotoCancelled=function(requestToken){
 if(nativePhotoRequestToken===null||String(requestToken)!==nativePhotoRequestToken)return;
 nativePhotoRequestToken=null;
 const status=$('encounter-status');
 if(status)status.textContent='Photo cancelled. Your previous cat photo is still here.';
 const feedback=$('picker-feedback');
 if(feedback)feedback.textContent='Photo cancelled. Choose live capture, camera, or gallery to try again.';
};
window.whiskerNativePhotoError=function(requestToken,message){
 if(nativePhotoRequestToken===null||String(requestToken)!==nativePhotoRequestToken)return;
 nativePhotoRequestToken=null;
 toast(String(message||'Camera photo could not be opened. Please try again.'));
};
window.whiskerNativeError=function(message){toast(String(message||'Permission was not granted.'))};
function photoSignature(data){/* identical resized photos; not face or individual-cat recognition */const canvas=document.createElement('canvas');return String(data.length)+':'+data.slice(0,48)+':'+data.slice(-80)}
// Local-only visual resemblance hint. dHash is a rough whole-photo fingerprint,
// NOT individual-cat recognition. Similar backgrounds or poses can cause false matches.
async function visualFingerprint(dataUri){
 return new Promise((resolve,reject)=>{
  const img=new Image();img.onload=()=>{
   try{const canvas=document.createElement('canvas');canvas.width=9;canvas.height=8;
    const ctx=canvas.getContext('2d',{willReadFrequently:true});if(!ctx)throw Error('Canvas unavailable');
    ctx.drawImage(img,0,0,9,8);const rgba=ctx.getImageData(0,0,9,8).data;
    let bits=0n;for(let y=0;y<8;y++)for(let x=0;x<8;x++){
     const a=4*(y*9+x),b=a+4;
     const left=rgba[a]*299+rgba[a+1]*587+rgba[a+2]*114;
     const right=rgba[b]*299+rgba[b+1]*587+rgba[b+2]*114;
     bits=(bits<<1n)|(left>right?1n:0n);
    }resolve(bits.toString(16).padStart(16,'0'));
   }catch(e){reject(e)}
  };img.onerror=()=>reject(Error('Cannot decode photo'));img.src=dataUri;
 });
}
function visualDistance(a,b){if(!/^[a-f0-9]{16}$/i.test(a||'')||!/^[a-f0-9]{16}$/i.test(b||''))return 64;let bits=BigInt('0x'+a)^BigInt('0x'+b),count=0;while(bits){count++;bits&=bits-1n}return count}
async function findPossibleMatches(image,request){
 const box=$('possible-matches');if(!box||!s.cats.length)return;
 try{
  const fingerprint=await visualFingerprint(image);
  if(request!==matchRequest||s.image!==image||!$('possible-matches'))return;
  // Avoid decoding thousands of full-size photos in one interaction.
  const recent=[...s.cats].sort((a,b)=>String(b.createdAt).localeCompare(String(a.createdAt))).slice(0,80);
  const matches=[];
  for(let i=0;i<recent.length;i++){
   if(request!==matchRequest||s.image!==image)return;
   const cat=recent[i];let hash=cat.visualHash||similarityCache.get(cat.id);
   if(!hash){try{hash=await visualFingerprint(cat.photo);similarityCache.set(cat.id,hash)}catch{continue}}
   const distance=visualDistance(fingerprint,hash);
   if(distance<=6)matches.push({cat,distance});
   if(i%8===7)await new Promise(resolve=>setTimeout(resolve,0));
  }
  if(request!==matchRequest||s.image!==image||!$('possible-matches'))return;
  matches.sort((a,b)=>a.distance-b.distance);
  box.innerHTML=matches.length?`<div class="match-notice"><strong>🐾 Have you met this cat before?</strong><p>These photos look similar. This is a visual hint, not cat identification. Check the cat yourself.</p><div class="match-list">${matches.slice(0,3).map(({cat})=>`<button type="button" class="match-choice" data-match="${esc(cat.id)}"><img src="${cat.photo}" alt=""><span>${esc(cat.name)}<small>${esc(cat.coat)} · ${catches(cat)} sighting${catches(cat)===1?'':'s'}</small></span><b>Use ↗</b></button>`).join('')}</div></div>`:'';
  box.querySelectorAll('[data-match]').forEach(button=>button.addEventListener('click',()=>{
   s.revisitId=button.dataset.match;s.catchMode='repeat';
   $('mode-repeat').click();$('repeat-cat').value=s.revisitId;
   box.innerHTML='<p class="match-confirm">✓ Selected an existing cat. Confirm the identity before saving.</p>';
  }));
 }catch(e){console.warn('Visual suggestion unavailable',e);if(request===matchRequest&&$('possible-matches'))$('possible-matches').innerHTML=''}
}

// Photo scoring is an approximate clarity estimate for ONE supplied photo,
// not burst-frame selection or reliable cat detection.
// Offline, single-photo exposure/detail hints, not an AI blur detector.
// A flat, dark or washed-out photo must not be labelled "Good" merely because
// it has enough pixels. These hints never block saving an important sighting.
async function assessPhotoQuality(dataUri){
 return new Promise(resolve=>{
  const img=new Image();img.onload=()=>{
   try{
    const canvas=document.createElement('canvas');const scale=Math.min(1,96/Math.max(img.width,img.height));
    canvas.width=Math.max(8,Math.round(img.width*scale));canvas.height=Math.max(8,Math.round(img.height*scale));
    const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.drawImage(img,0,0,canvas.width,canvas.height);
    const data=ctx.getImageData(0,0,canvas.width,canvas.height).data;
    const w=canvas.width,h=canvas.height,gray=new Float32Array(w*h);
    let sum=0,sumSquares=0,edge=0;
    for(let y=0;y<h;y++)for(let x=0;x<w;x++){
     const idx=y*w+x,i=idx*4,l=data[i]*.299+data[i+1]*.587+data[i+2]*.114;
     gray[idx]=l;sum+=l;sumSquares+=l*l;
    }
    for(let y=0;y<h;y++)for(let x=0;x<w;x++){
     const idx=y*w+x;if(x+1<w)edge+=Math.abs(gray[idx]-gray[idx+1]);
     if(y+1<h)edge+=Math.abs(gray[idx]-gray[idx+w]);
    }
    const n=w*h,brightness=sum/n,contrast=Math.sqrt(Math.max(0,sumSquares/n-brightness*brightness));
    const detail=edge/Math.max(1,(w-1)*h+(h-1)*w);
    const small=Math.min(img.width,img.height)<360;
    let label,note;
    if(brightness<55){label='Too dark';note='Try brighter natural light, without startling the cat.'}
    else if(brightness>211){label='Very bright';note='Avoid direct glare; check the cat is visible.'}
    else if(contrast<17||detail<3.5){label='Low detail';note='Check focus and distance. This image has few visible edges.'}
    else if(small){label='Small image';note='A larger photo may show more fur and face detail.'}
    else if(detail>11&&contrast>38){label='Clear-looking';note='Good visible detail, based on a simple offline estimate.'}
    else{label='Usable';note='Check the face and fur before saving; a steadier photo may help.'}
    const score=Math.round(captureClamp(detail*2+contrast*.4+(brightness>55&&brightness<211?18:0),0,99));
    resolve({score,label,note,brightness:Math.round(brightness),detail:Math.round(detail*10)/10,width:img.width,height:img.height});
   }catch{resolve({score:0,label:'Not assessed',note:'Please check the photo before saving.'})}
  };img.onerror=()=>resolve({score:0,label:'Not assessed',note:'Please check the photo before saving.'});img.src=dataUri;
 });
}
const captureClamp=(v,min,max)=>Math.max(min,Math.min(max,v));
function encounterToolLabel(kind){return kind==='lure'?'Dangle Lure':'Whisker Paw'}
const LIVE_FRAME_MAX=12,LIVE_SAMPLE_INTERVAL=260,LIVE_SAMPLE_SIZE=560,LIVE_CAPTURE_SIZE=960;
// Live camera uses the standard MediaStream API when available. No video is
// recorded or stored: up to four recent JPEG stills stay in memory only.
// The Android WebView may deny camera access; the native photo picker remains
// available as an explicit fallback without changing any saved Collection data.
function stopLiveCamera(){
 const session=liveCamera;liveCamera=null;
 if(!session)return;
 session.active=false;
 clearTimeout(session.timer);
 session.dragging=false;
 for(const track of session.stream?.getTracks?.()||[])track.stop();
 if(session.video){try{session.video.pause();session.video.srcObject=null}catch{}}
 session.frames.length=0;
}
function frameFromVideo(video,maxSize=950,quality=.82){
 if(!video||!video.videoWidth||!video.videoHeight)return null;
 const scale=Math.min(1,maxSize/Math.max(video.videoWidth,video.videoHeight));
 const canvas=document.createElement('canvas');
 canvas.width=Math.max(1,Math.round(video.videoWidth*scale));
 canvas.height=Math.max(1,Math.round(video.videoHeight*scale));
 const zoom=liveCamera?.video===video ? Math.max(1,liveCamera.digitalZoom||1):1;
 const sx=(video.videoWidth-video.videoWidth/zoom)/2,sy=(video.videoHeight-video.videoHeight/zoom)/2;
 canvas.getContext('2d').drawImage(video,sx,sy,video.videoWidth/zoom,video.videoHeight/zoom,0,0,canvas.width,canvas.height);
 return canvas.toDataURL('image/jpeg',quality);
}
async function sampleLiveFrame(session,options={}){
 const force=Boolean(options.force),maxSize=options.maxSize||LIVE_SAMPLE_SIZE,quality=options.quality??.68;
 if(!session?.active||session.sampling||session.video.readyState<2)return;
 if(!force&&document.visibilityState==='hidden')return; // Keep recent frames during an active tool throw.
 session.sampling=true;
 try{
  const image=frameFromVideo(session.video,maxSize,quality);
  if(!image||!session.active||session!==liveCamera)return;
  const now=Date.now();session.frames.push({image,quality:null,at:now});
  session.frames=session.frames.filter(frame=>now-frame.at<=3200).slice(-LIVE_FRAME_MAX);
  const label=$('live-frame-count');if(label)label.textContent=`${session.frames.length} recent frames`;
 }catch(error){console.debug('Frame sample skipped',error)}
 finally{session.sampling=false}
}
function scheduleLiveSampling(session){
 clearTimeout(session?.timer);
 if(!session?.active)return;
 session.timer=setTimeout(async()=>{
  // Lightweight previews only. Never force a sample during a drag or while hidden.
  // Subject/whole-frame analysis runs once, after the user finishes the catch.
  await sampleLiveFrame(session);
  scheduleLiveSampling(session);
 },LIVE_SAMPLE_INTERVAL);
}
function chooseBestLiveFrame(frames){
 // The clarity score is a simple whole-frame heuristic, not cat recognition.
 // Prefer reasonable exposure and sharp detail over an over/underexposed shot.
 const scored=frames.map((frame,i)=>({frame,i,rank:frame.quality?.score==null?
  -1:frame.quality.score-(frame.quality.brightness<55||frame.quality.brightness>211?35:0)}));
 scored.sort((a,b)=>b.rank-a.rank||b.i-a.i);
 return scored[0]?.frame||null;
}
// Crop the region the player marked as the cat. This is a *user-positioned*
// sharpness estimate, not automatic cat detection or a face recognition model.
// Keeping the crop in memory avoids changing the existing Collection photo schema.
function liveSubjectCrop(image,focus){
 return new Promise(resolve=>{
  const input=new Image();
  input.onload=()=>{
   try{
    const w=input.naturalWidth,h=input.naturalHeight;
    if(!(w>0&&h>0))return resolve(null);
    const side=Math.min(w,h)*.40;
    const x=captureClamp((focus?.x??.5)*w-side/2,0,w-side);
    const y=captureClamp((focus?.y??.4)*h-side/2,0,h-side);
    const canvas=document.createElement('canvas');canvas.width=360;canvas.height=360;
    canvas.getContext('2d').drawImage(input,x,y,side,side,0,0,360,360);
    resolve(canvas.toDataURL('image/jpeg',.8));
   }catch{resolve(null)}
  };
  input.onerror=()=>resolve(null);input.src=image;
 });
}
async function rankLiveFramesAtFocus(frames,focus){
 if(!frames?.length)return null;
 // Work on a snapshot: new samples and a user moving the target cannot mutate
 // the candidate list while the images are being assessed.
 const candidates=frames.slice(-12);
 const assessed=await Promise.all(candidates.map(async(frame,i)=>{
  try{
   const crop=await liveSubjectCrop(frame.image,focus);
   const [subjectQuality,wholeQuality]=await Promise.all([
    crop?assessPhotoQuality(crop):Promise.resolve(null),
    frame.quality?Promise.resolve(frame.quality):assessPhotoQuality(frame.image)
   ]);
   const overall=Number(wholeQuality?.score)||0;
   const subject=Number(subjectQuality?.score);
   const rank=Number.isFinite(subject)?subject*.75+overall*.25:overall;
   const exposure=subjectQuality?.brightness??frame.quality?.brightness;
   return {frame:{...frame,quality:wholeQuality,subjectQuality},i,rank:rank-(exposure<55||exposure>211?35:0)};
  }catch{return {frame,i,rank:Number(frame.quality?.score)||0}}
 }));
 assessed.sort((a,b)=>b.rank-a.rank||b.i-a.i);
 return assessed.map(x=>x.frame);
}
async function chooseBestLiveFrameAtFocus(frames,focus){
 return (await rankLiveFramesAtFocus(frames,focus))[0]||null;
}
// Keep the choice private and ephemeral. Only the confirmed still enters Collection.
function displayCaptureShotChoices(frames){
 const tray=$('encounter-shots');
 captureShots=frames.slice(0,6).filter(f=>typeof f?.image==='string'&&f.image.startsWith('data:image/'));
 if(!tray||captureShots.length<2){if(tray)tray.classList.add('hidden');return;}
 tray.classList.remove('hidden');
 tray.innerHTML=`<div class="shots-title"><strong>Choose your favourite shot</strong><small>${captureShots.length} best frames · tap to compare</small></div><div class="shots-row">${captureShots.map((f,i)=>`<button type="button" class="shot-option ${i===0?'selected':''}" data-shot="${i}" aria-pressed="${i===0}" aria-label="Choose ${i===0?'suggested':'alternate'} photo ${i+1}"><img src="${f.image}" alt="Shot ${i+1}"><span>${i===0?'✦ Best':`Shot ${i+1}`}</span></button>`).join('')}</div>`;
 tray.querySelectorAll('[data-shot]').forEach(button=>button.onclick=()=>selectCaptureShot(Number(button.dataset.shot)));
}
function selectCaptureShot(index){
 const choice=captureShots[index],tray=$('encounter-shots');
 if(!choice||!tray||!tray.isConnected||s.storageBlocked)return;
 s.image=choice.image;
 if(s.captureSummary){s.captureSummary.quality=choice.quality||s.captureSummary.quality;s.captureSummary.subjectQuality=choice.subjectQuality||null;}
 const photo=$('encounter-photo');if(photo)photo.src=choice.image;
 const quality=$('encounter-quality');if(quality)quality.innerHTML=`Selected shot ${index+1} of ${captureShots.length} · Target area: <strong>${esc(choice.subjectQuality?.label||'Not rated')}</strong> · Photo: <strong>${esc(choice.quality?.label||'Not rated')}</strong><small>Tap another thumbnail if you prefer it.</small>`;
 tray.querySelectorAll('[data-shot]').forEach((button,i)=>{button.classList.toggle('selected',i===index);button.setAttribute('aria-pressed',String(i===index));});
 const focus=s.encounterFocus||{x:.5,y:.4};
 encounterCrop(choice.image,focus.x,focus.y);
}
async function requestNativeLivePermission(){
 if(!window.whiskerNativeReady)return true;
 return new Promise(resolve=>{
  let settled=false;
  const finish=ok=>{if(settled)return;settled=true;clearTimeout(timer);window.whiskerNativeCameraPermission=null;resolve(Boolean(ok))};
  const timer=setTimeout(()=>finish(false),12000);
  window.whiskerNativeCameraPermission=finish;
  try{location.href='whiskerhunt://camera-permission'}catch{finish(false)}
 });
}
// Escape from live startup before launching an external camera. Keep a stable
// chooser underneath it so cancelling the Android camera cannot reveal a spinner.
function showSafeCameraChooser(){
 s.encounterLive=false;
 openModal(`<div class="sheet-head"><h2>Choose your camera</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim">Live capture stopped. Pick how to continue.</p><div class="capture-choice"><button id="retry-live" class="choice"><span>🎥</span><strong>Try live again</strong><small>Stay inside Whisker Hunt</small></button><button id="retry-normal" class="choice"><span>📸</span><strong>Normal camera</strong><small>Opens your phone camera</small></button><button id="retry-gallery" class="choice"><span>🖼️</span><strong>Gallery</strong><small>Use an existing photograph</small></button></div><p id="picker-feedback" class="footnote">If you cancel the phone camera, you can choose again here.</p>`);
 $('retry-live').onclick=startLiveEncounter;
 $('retry-normal').onclick=()=>requestEncounterPhoto(true);
 $('retry-gallery').onclick=()=>requestEncounterPhoto(false);
}
function useNormalCameraFromLiveStartup(){
 liveRequestEpoch++; // invalidate all pending permission / getUserMedia callbacks
 stopLiveCamera();
 showSafeCameraChooser();
 void requestEncounterPhoto(true);
}
// Backward-compatible cancellation hook for older bridge versions.
window.whiskerNativePickerCancelled=function(){
 if(nativePhotoRequestToken!==null)window.whiskerNativePhotoCancelled(nativePhotoRequestToken);
};
async function startLiveEncounter(){
 captureShots=[];
 if(s.busy||s.storageBlocked)return toast('Please wait until storage is ready.');
 nativePhotoRequestToken=null;photoSelectionEpoch++;
 s.encounterLive=true;
 const request=++liveRequestEpoch;stopLiveCamera();
 openModal(`<div class="sheet-head"><h2>Starting live camera…</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim">Requesting camera access. No video is saved or uploaded.</p><div class="live-loading" aria-live="polite">🎥 Preparing preview…</div><div class="actions"><button id="live-fallback" class="secondary">Cancel live camera</button></div>`);
 $('live-fallback').onclick=useNormalCameraFromLiveStartup;
 let stream=null;
 try{
  if(!navigator.mediaDevices?.getUserMedia||!globalThis.isSecureContext)throw Error('Live camera is not available in this WebView or browser context.');
  if(!await requestNativeLivePermission())throw Error('Camera permission was not granted.');
  if(request!==liveRequestEpoch||$('modal-layer')?.classList.contains('hidden'))return;
  stream=await navigator.mediaDevices.getUserMedia({audio:false,video:{facingMode:{ideal:'environment'},width:{ideal:800},height:{ideal:450},frameRate:{ideal:20,max:24}}});
  if(request!==liveRequestEpoch||$('modal-layer')?.classList.contains('hidden'))return;
  const video=document.createElement('video');video.autoplay=true;video.muted=true;video.playsInline=true;video.srcObject=stream;
  await Promise.race([video.play(),new Promise((_,reject)=>setTimeout(()=>reject(Error('Camera preview timed out.')),6000))]);
  if(!video.videoWidth||!video.videoHeight)await new Promise((resolve,reject)=>{
   const timer=setTimeout(()=>reject(Error('No camera frames received.')),4500);
   video.addEventListener('loadedmetadata',()=>{clearTimeout(timer);resolve()},{once:true});
  });
  if(request!==liveRequestEpoch||$('modal-layer')?.classList.contains('hidden'))return;
  const first=frameFromVideo(video,LIVE_SAMPLE_SIZE,.72);if(!first)throw Error('Camera did not provide a usable frame.');
  liveCamera={stream,video,frames:[],timer:null,active:true,sampling:false,dragging:false};stream=null;
  // Avoid decoding/analysing the same image twice before the first live frame.
  if(request!==liveRequestEpoch||!liveCamera?.active)return;
  beginEncounter(first,{live:true});
 }catch(error){
  if(request!==liveRequestEpoch)return;
  console.debug('Live camera unavailable',error);
  openModal(`<div class="sheet-head"><h2>Live camera unavailable</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim">${esc(error?.message||'Your camera could not be opened.')} Your Collection is safe. You can still take a normal photo or choose one from your gallery.</p><div class="actions"><button id="live-normal-camera" class="primary">📸 Take a photo</button><button id="live-normal-gallery" class="secondary">🖼️ Gallery</button></div>`);
  $('live-normal-camera').onclick=useNormalCameraFromLiveStartup;
  $('live-normal-gallery').onclick=()=>{s.encounterLive=false;requestEncounterPhoto(false)};
 }finally{
  if(stream)for(const track of stream.getTracks())track.stop();
 }
}
async function freezeLiveEncounter(){
 const session=liveCamera;if(!session)return;
 if(session.freezePromise)return session.freezePromise;
 session.freezePromise=finishLiveEncounter(session);
 return session.freezePromise;
}
async function finishLiveEncounter(session){
 if(!session.active||session!==liveCamera)return;
 if(s.encounterAr){
  const finalImage=frameFromVideo(session.video,LIVE_CAPTURE_SIZE,.8);
  if(finalImage)s.image=finalImage;
  const stage=$('encounter-stage');
  $('encounter-video')?.remove();stage?.classList.remove('live-encounter');
  stopLiveCamera();
  const label=$('encounter-quality');
  if(label)label.innerHTML='Virtual cat ready! <small>Displayed automatically in the camera view. Real surface tracking is not yet enabled.</small>';
  return;
 }
 // Always include a sharper release-time still. Earlier preview frames stay
 // small for responsiveness; the final frame is captured at higher quality.
 const still=frameFromVideo(session.video,LIVE_CAPTURE_SIZE,.84);
 if(still)session.frames.push({image:still,quality:null,at:Date.now()});
 session.frames=session.frames.slice(-LIVE_FRAME_MAX);
 const frames=session.frames.slice();
 if(!frames.length)return;
 const stage=$('encounter-stage'),focus={x:s.encounterFocus?.x??.5,y:s.encounterFocus?.y??.4};
 const qualityLabel=$('encounter-quality');
 if(qualityLabel)qualityLabel.textContent='Choosing your clearest wildlife photo…';
 const ranked=await rankLiveFramesAtFocus(frames,focus);
 const selected=ranked[0]||null;
 // Retake, modal close or a backgrounded app must never apply a stale result.
 if(!session.active||session!==liveCamera||!stage?.isConnected||stage!==$('encounter-stage'))return;
 if(selected){
  s.image=selected.image;
  if(s.captureSummary){s.captureSummary.quality=selected.quality;s.captureSummary.subjectQuality=selected.subjectQuality||null}
  const photo=$('encounter-photo');if(photo)photo.src=selected.image;
  if(qualityLabel)qualityLabel.innerHTML=`Best of ${frames.length} burst frames · Wildlife target: <strong>${esc(selected.subjectQuality?.label||'Not assessed')}</strong> · Full photo: ${esc(selected.quality?.label||'Not assessed')}. <small>Offline focus-area estimate; no automatic species recognition.</small>`;
 }
 $('encounter-video')?.remove();stage.classList.remove('live-encounter');
 stopLiveCamera();
 if(selected){setEncounterFocus(focus.x,focus.y,false);displayCaptureShotChoices(ranked);}
}
// Camera resources are released if the user backgrounds the app or changes tabs.
document.addEventListener('visibilitychange',()=>{
 if(document.visibilityState!=='hidden')return;
 // Also cancel a permission/getUserMedia request that is still pending.
 liveRequestEpoch++;
 if(!liveCamera)return;
 // Use the best already sampled frame; do not keep the camera running offscreen.
 const selected=chooseBestLiveFrame(liveCamera.frames);
 if(selected){s.image=selected.image;if(s.captureSummary)s.captureSummary.quality=selected.quality;
  const photo=$('encounter-photo');if(photo)photo.src=selected.image;
  const quality=$('encounter-quality');if(quality)quality.innerHTML=`Camera paused · Recent photo preserved. <small>Retake live capture to restart the camera.</small>`;}
 $('encounter-video')?.remove();$('encounter-stage')?.classList.remove('live-encounter');
 stopLiveCamera();
 const status=$('encounter-status');if(status)status.textContent='Camera paused for privacy. Finish with this photo or retake live capture.';
});
function beginEncounter(image,options={}){
 captureShots=[];
 if(!options.live)stopLiveCamera();
 const generation=++encounterEpoch;
 s.image=image;s.encounterLive=Boolean(options.live);s.encounterTool='ball';s.encounterLured=false;s.encounterCaptured=false;s.captureSummary=null;
 assessPhotoQuality(image).then(quality=>{
  if(generation!==encounterEpoch||s.image!==image)return;
  showEncounter(image,quality,options);
 }).catch(()=>toast('Could not prepare encounter image. Please try another photo.'));
}
// Provide a user-positioned photo crop as the encounter character.
// This is NOT an AI-generated 3D replica or automatic cat recognition.
// CSS object-fit:contain may letterbox a portrait/landscape photo. Work in
// original-image coordinates and convert to stage pixels before placing the
// target. Using percentages of the stage misplaces targets on portrait shots.
function encounterImageRect(image, elementBounds){
 const iw=image.videoWidth||image.naturalWidth||image.width, ih=image.videoHeight||image.naturalHeight||image.height;
 if(!(iw>0&&ih>0&&elementBounds.width>0&&elementBounds.height>0))return null;
 const scale=Math.min(elementBounds.width/iw,elementBounds.height/ih);
 const width=iw*scale,height=ih*scale;
 return {left:elementBounds.left+(elementBounds.width-width)/2,
         top:elementBounds.top+(elementBounds.height-height)/2,
         width,height};
}
function encounterImagePoint(clientX,clientY,image,bounds){
 const rect=encounterImageRect(image,bounds);
 if(!rect)return null;
 const x=(clientX-rect.left)/rect.width,y=(clientY-rect.top)/rect.height;
 return x>=0&&x<=1&&y>=0&&y<=1?{x,y}:null;
}
function encounterCrop(photo,x,y){
 const cropEpoch=++encounterCropEpoch;
 const input=new Image();input.onload=()=>{
  // Ignore stale asynchronous crops after another tap, photo or modal close.
  if(cropEpoch!==encounterCropEpoch||!$('encounter-stage')||s.image!==photo)return;
  const size=Math.max(1,Math.min(input.naturalWidth,input.naturalHeight)*.42);
  const left=captureClamp(x*input.naturalWidth-size/2,0,Math.max(0,input.naturalWidth-size));
  const top=captureClamp(y*input.naturalHeight-size/2,0,Math.max(0,input.naturalHeight-size));
  const canvas=document.createElement('canvas');canvas.width=220;canvas.height=220;
  canvas.getContext('2d').drawImage(input,left,top,size,size,0,0,220,220);
  const crop=$('encounter-cat-crop');if(crop)crop.src=canvas.toDataURL('image/jpeg',.82);
 };input.src=photo;
}
function positionEncounterFocus(){
 const cat=$('encounter-cat'),stage=$('encounter-stage'),photo=$('encounter-video')||$('encounter-photo');
 if(!cat||!stage||!photo||!s.encounterFocus)return;
 const stageBounds=stage.getBoundingClientRect();
 const rect=encounterImageRect(photo,photo.getBoundingClientRect());
 if(!rect)return;
 const {x,y}=s.encounterFocus;
 cat.style.left=(rect.left+rect.width*x-stageBounds.left)+'px';
 cat.style.top=(rect.top+rect.height*y-stageBounds.top)+'px';
}
function setEncounterFocus(x,y,announce=true){
 if(s.encounterCaptured)return;
 s.encounterFocus={x:captureClamp(x,0,1),y:captureClamp(y,0,1)};
 positionEncounterFocus();
 if(!liveCamera?.active)encounterCrop(s.image,s.encounterFocus.x,s.encounterFocus.y);
 if(announce&&$('encounter-status'))$('encounter-status').textContent='Target moved. Drag the Whisker Paw onto the cat, or try the Dangle Lure first.';
}
function showEncounter(image,quality,options={}){
 const liveMode=Boolean(options.live||s.encounterLive);
 s.encounterLive=liveMode;
 s.encounterFocus={x:.5,y:.40};
 s.captureSummary={quality,throwRating:null};
 openModal(`<div class="sheet-head"><h2>${liveMode?'Live encounter 🎥':'Encounter! 🐾'}</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="encounter-quick-help">① Tap the cat · ② Drag the paw · ③ Catch!</p><details class="encounter-help"><summary>How do the tools work?</summary><p>Tap your subject to place the target. Drag the Whisker Paw onto the target to catch it, or use the Dangle Lure first to make catching easier. Stay at a safe distance from real cats.</p></details><div id="encounter-aim-guide" class="encounter-aim-guide hidden" aria-hidden="true"></div><div id="encounter-stage" class="encounter-stage"><img id="encounter-photo" class="encounter-backdrop" src="${image}" alt="Your selected wildlife photo"><div class="encounter-vignette"></div><div id="encounter-cat" class="encounter-cat"><div class="encounter-cat-ring"></div><img id="encounter-cat-crop" src="${image}" alt="Selected wildlife photo crop"><span>Your wildlife target</span></div><div class="encounter-capture-tag">Capture preview</div><div class="encounter-tool-dock" aria-label="Capture tools"><button type="button" id="tool-ball" class="dock-tool selected" aria-pressed="true" title="Whisker Paw"><span>🐾</span><small>Paw</small></button><button type="button" id="tool-lure" class="dock-tool" aria-label="Switch to Lure" aria-pressed="false" title="Switch to Lure"><span>🪶</span><small>Lure</small></button><div id="throw-item" class="throw-item throw-ball" role="button" aria-label="Drag ${encounterToolLabel('ball')} to the cat" tabindex="0"><svg class="whisker-paw-svg" viewBox="0 0 100 110" aria-hidden="true" focusable="false"><defs><linearGradient id="whisker-paw-shine" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffe5f3"/><stop offset=".4" stop-color="#fb80b7"/><stop offset="1" stop-color="#8553d8"/></linearGradient></defs><g class="paw-digits"><ellipse cx="19" cy="34" rx="11" ry="15" transform="rotate(-23 19 34)"/><ellipse cx="40" cy="20" rx="11" ry="16" transform="rotate(-9 40 20)"/><ellipse cx="62" cy="19" rx="11" ry="16" transform="rotate(9 62 19)"/><ellipse cx="82" cy="32" rx="10" ry="15" transform="rotate(24 82 32)"/></g><path class="paw-center" d="M51 47 C65 45 71 55 80 65 C90 78 84 94 71 98 C62 101 57 95 51 95 C43 95 37 102 27 98 C12 95 10 79 20 66 C29 53 35 46 51 47Z"/><path class="paw-detail" d="M33 77 Q42 69 50 75 Q58 69 68 77"/></svg><span class="throw-stick">🎣</span><span class="throw-lure-body">🧶</span><span class="drag-prompt">DRAG</span></div></div><div id="encounter-orb" class="encounter-orb hidden"><svg class="whisker-paw-svg capture-paw" viewBox="0 0 100 110" aria-hidden="true" focusable="false"><defs><linearGradient id="whisker-paw-shine-captured" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffe5f3"/><stop offset=".4" stop-color="#fb80b7"/><stop offset="1" stop-color="#8553d8"/></linearGradient></defs><g class="paw-digits"><ellipse cx="19" cy="34" rx="11" ry="15" transform="rotate(-23 19 34)"/><ellipse cx="40" cy="20" rx="11" ry="16" transform="rotate(-9 40 20)"/><ellipse cx="62" cy="19" rx="11" ry="16" transform="rotate(9 62 19)"/><ellipse cx="82" cy="32" rx="10" ry="15" transform="rotate(24 82 32)"/></g><path class="paw-center" d="M51 47 C65 45 71 55 80 65 C90 78 84 94 71 98 C62 101 57 95 51 95 C43 95 37 102 27 98 C12 95 10 79 20 66 C29 53 35 46 51 47Z"/><path class="paw-detail" d="M33 77 Q42 69 50 75 Q58 69 68 77"/></svg></div><div id="encounter-status" class="encounter-status" role="status" aria-live="polite">Tap the animal to move the target. Then drag an item from the tool dock on the right.</div><div id="encounter-meow" class="encounter-meow hidden" aria-hidden="true">${arMode?'Meow!':'Nice shot!'}</div></div><div id="encounter-quality" class="encounter-quality">${liveMode?'🎥 Live preview · <span id="live-frame-count">1 recent frame</span> · Live burst samples recent frames during your throw and picks the clearest one near your target when you capture.':'Photo clarity estimate: <strong>'+esc(quality.label)+'</strong> · '+esc(quality.note)} <small>${liveMode?'No video recording or upload.':'Single-image heuristic; no cat recognition.'}</small></div><div id="encounter-shots" class="encounter-shots hidden" aria-label="Choose best frame"></div>${arMode?'':`<div class="encounter-photo-actions"><button type="button" id="encounter-retake" class="secondary">${liveMode?'🎥 Retake live capture':'📸 Retake photo'}</button><button type="button" id="encounter-replace" class="secondary">🖼️ Choose another</button></div>`}<div class="encounter-launch"><div class="encounter-instructions">Drag the paw from the right. A green ring means your throw is on target.</div></div><div class="actions">${arMode?'':`<button id="encounter-skip" class="secondary">Save photo without game</button>`}<button id="encounter-continue" class="primary hidden">${arMode?'Keep this creature ✨':'Continue to Collection →'}</button></div><p class="footnote">${liveMode?'Live camera is local to your device; only the selected still is saved. No automatic species recognition.':'Your target is a user-selected crop of your photo, not a live AI-generated cat.'} Stay a safe distance from real cats.</p>`,liveMode);
 if(liveMode&&liveCamera?.active){
  const stage=$('encounter-stage'),video=liveCamera.video;
  video.id='encounter-video';video.className='encounter-backdrop encounter-live-video';
  stage.prepend(video);stage.classList.add('live-encounter');
  const tag=stage.querySelector('.encounter-capture-tag');if(tag)tag.textContent='● LIVE · private';
  const crop=$('encounter-cat-crop');if(crop)crop.style.display='none';
  const status=$('encounter-status');if(status)status.textContent='Tap your subject to place the target, then drag a tool from the right.';
  scheduleLiveSampling(liveCamera);
 }
 const selectTool=kind=>{
  if(s.encounterCaptured)return;
  s.encounterTool=kind;
  $('tool-ball').classList.toggle('selected',kind==='ball');$('tool-lure').classList.toggle('selected',kind==='lure');
  $('tool-ball').setAttribute('aria-pressed',String(kind==='ball'));$('tool-lure').setAttribute('aria-pressed',String(kind==='lure'));
  const item=$('throw-item');item.classList.toggle('throw-ball',kind==='ball');item.classList.toggle('throw-lure',kind==='lure');
  item.setAttribute('aria-label','Drag '+encounterToolLabel(kind)+' to the cat');
  $('encounter-status').textContent=kind==='lure'?'Aim the Dangle Lure at the cat to enlarge the target.':'Drag the Whisker Paw onto the cat for a capture!';
 };
 $('tool-ball').onclick=()=>selectTool('ball');$('tool-lure').onclick=()=>selectTool('lure');
 if(!arMode)$('encounter-skip').onclick=async()=>{if(liveCamera)await freezeLiveEncounter();s.captureSummary=null;showCatForm(s.image)};
 $('encounter-continue').onclick=()=>arMode?showVirtualNamingForm():showCatForm(s.image);
 // Cancelling Android's picker or the browser file dialog keeps this photo.
 // A successful replacement restarts the encounter with a new quality report.
 $('encounter-retake').onclick=()=>s.encounterLive?startLiveEncounter():requestEncounterPhoto(true);
 $('encounter-replace').onclick=()=>{s.encounterLive=false;requestEncounterPhoto(false)};
 // A tap in the letterbox margins must not move the cat target.
 const stage=$('encounter-stage'),backdrop=$('encounter-photo');
 [stage,$('encounter-status'),$('encounter-quality'),$('encounter-meow'),$('tool-ball'),$('tool-lure'),$('throw-item')].filter(Boolean).forEach(el=>{el.oncontextmenu=e=>e.preventDefault();el.onselectstart=e=>e.preventDefault();el.ondragstart=()=>false;});
 stage.addEventListener('click',event=>{
  const visual=$('encounter-video')||backdrop;
  if(s.encounterCaptured||!(event.target===stage||event.target===backdrop||event.target===visual))return;
  const point=encounterImagePoint(event.clientX,event.clientY,visual,visual.getBoundingClientRect());
  if(point)setEncounterFocus(point.x,point.y);
 });
 // The backdrop's intrinsic dimensions can arrive after the modal is painted.
 // Reposition on load and on rotation/resize without changing the selected crop.
 backdrop.addEventListener('load',()=>positionEncounterFocus());
 encounterResizeObserver?.disconnect();
 encounterResizeObserver=typeof ResizeObserver==='function'?new ResizeObserver(()=>positionEncounterFocus()):null;
 encounterResizeObserver?.observe(stage);
 setEncounterFocus(s.encounterFocus.x,s.encounterFocus.y,false);
 setupEncounterDrag();
}
// The same release-position geometry powers both the preview and final hit.
// This prevents the green guide from claiming a hit that the game rejects.
function encounterAimAt(clientX,clientY,target){
 const bounds=target.getBoundingClientRect();
 const dx=clientX-(bounds.left+bounds.width/2),dy=clientY-(bounds.top+bounds.height/2);
 const radius=Math.max(1,Math.min(bounds.width,bounds.height)/2);
 const norm=Math.hypot(dx,dy)/radius;
 return {norm,hit:norm<=1.1};
}
function setupEncounterDrag(){
 const item=$('throw-item'),cat=$('encounter-cat'),guide=$('encounter-aim-guide');if(!item||!cat)return;
 let pointerId=null,startX=0,startY=0,moveFrame=0,latestMove=null,lastStatus='';
 const reset=()=>{
  if(moveFrame)cancelAnimationFrame(moveFrame);
  moveFrame=0;latestMove=null;lastStatus='';
  item.classList.remove('dragging');item.style.transform='';
  cat.classList.remove('aim-hit');
  guide?.classList.add('hidden');guide?.classList.remove('aim-hit');
  if(liveCamera?.active)liveCamera.dragging=false;
 };
 const guideTo=(x,y,hit)=>{
  if(!guide)return;
  const bounds=cat.getBoundingClientRect();const tx=bounds.left+bounds.width/2,ty=bounds.top+bounds.height/2;
  const dx=x-tx,dy=y-ty;
  guide.style.left=tx+'px';guide.style.top=ty+'px';
  guide.style.width=Math.hypot(dx,dy)+'px';
  guide.style.transform='rotate('+Math.atan2(dy,dx)+'rad)';
  guide.classList.remove('hidden');guide.classList.toggle('aim-hit',hit);
  cat.classList.toggle('aim-hit',hit);
 };
 item.onpointerdown=event=>{
  if(s.encounterCaptured||pointerId!==null||event.button>0)return;
  pointerId=event.pointerId;startX=event.clientX;startY=event.clientY;
  if(liveCamera?.active)liveCamera.dragging=true;
  item.classList.add('dragging');item.setPointerCapture(event.pointerId);
  event.preventDefault();
 };
 const paintMove=()=>{
  moveFrame=0;
  if(pointerId===null||!latestMove)return;
  const {x,y}=latestMove,travelled=Math.hypot(x-startX,y-startY);
  item.style.transform=`translate3d(${x-startX}px,${y-startY}px,0)`;
  const aim=encounterAimAt(x,y,cat);
  guideTo(x,y,aim.hit);
  const message=travelled<24?'Drag further to throw…':aim.hit?'On target! Release to use your '+encounterToolLabel(s.encounterTool)+'.':'Keep aiming for the glowing ring…';
  if(message!==lastStatus){const status=$('encounter-status');if(status)status.textContent=message;lastStatus=message}
 };
 item.onpointermove=event=>{
  if(event.pointerId!==pointerId)return;
  latestMove={x:event.clientX,y:event.clientY};
  if(!moveFrame)moveFrame=requestAnimationFrame(paintMove);
 };
 item.onpointerup=event=>{
  if(event.pointerId!==pointerId)return;
  const travelled=Math.hypot(event.clientX-startX,event.clientY-startY);
  const aim=encounterAimAt(event.clientX,event.clientY,cat);
  pointerId=null;reset();
  if(item.hasPointerCapture(event.pointerId))item.releasePointerCapture(event.pointerId);
  if(travelled<24){if($('encounter-status'))$('encounter-status').textContent='Hold and drag the selected tool towards the cat to throw.';return}
  if(aim.hit)handleEncounterHit(s.encounterTool,aim.norm);
  else if($('encounter-status'))$('encounter-status').textContent=`Missed with ${encounterToolLabel(s.encounterTool)}. Aim at the glowing ring and try again.`;
 };
 item.onpointercancel=()=>{pointerId=null;reset();if($('encounter-status'))$('encounter-status').textContent='Throw cancelled. Try again when ready.'};
 item.onlostpointercapture=()=>{if(pointerId!==null){pointerId=null;reset();if($('encounter-status'))$('encounter-status').textContent='Throw interrupted. Try again.'}};
 // Accessibility: keyboard users can activate the currently selected target.
 item.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();handleEncounterHit(s.encounterTool,.45)}};
}

function handleEncounterHit(kind,accuracy=.45){
 if(s.encounterCaptured||!$('encounter-status'))return;
 if(kind==='lure'){
  if(s.encounterLured){$('encounter-status').textContent='The cat is focused on the lure. Try your Whisker Paw.';return}
  s.encounterLured=true;$('encounter-cat')?.classList.add('curious');
  $('encounter-status').textContent='The toy caught the cat’s attention! Its target is now larger.';
  // Lure is a preparatory action; switch back to the capture item.
  $('tool-ball')?.click();return;
 }
 const rating=accuracy<=.23?'Purrfect!':accuracy<=.55?'Great!':'Nice!';
 s.captureSummary.throwRating=rating;
 runEncounterCapture();
}
async function runEncounterCapture(){
 if(s.encounterCaptured)return;s.encounterCaptured=true;
 const originalStage=$('encounter-stage'),originalEpoch=encounterEpoch;
 if(liveCamera)await freezeLiveEncounter();
 if(originalEpoch!==encounterEpoch||originalStage!==$('encounter-stage')||!originalStage?.isConnected)return;
 const cat=$('encounter-cat'),orb=$('encounter-orb'),status=$('encounter-status'),meow=$('encounter-meow');
 if(!cat?.isConnected)return;
 if(cat)cat.classList.add('captured','grabbed');if(orb){orb.classList.remove('hidden');orb.classList.add('active')}
 if(status)status.textContent=`${s.captureSummary.throwRating} catch!`;
 const stage=$('encounter-stage');
 setTimeout(()=>{if(stage?.isConnected&&status)status.textContent=s.encounterAr?'Discovery sparkle…':'Discovery in progress…';if(stage?.isConnected)orb?.classList.add('grab-1')},260);
 setTimeout(()=>{if(stage?.isConnected&&status)status.textContent='Holding on…';if(stage?.isConnected){orb?.classList.remove('grab-1');orb?.classList.add('grab-2');if(meow){meow.classList.remove('hidden');meow.classList.add('float')}}},650);
 setTimeout(()=>{if(!stage?.isConnected)return;orb?.classList.remove('grab-2');cat?.classList.remove('grabbed');if(meow)meow.classList.remove('float');if(status)status.textContent=`Moment captured! ${s.captureSummary.throwRating}`;stage.classList.add('hush-capture-complete');$('encounter-continue')?.classList.remove('hidden')},1180);
}
function showCatForm(image){s.image=image;const request=++matchRequest;openModal(`<div class="sheet-head"><h2>Nice spotting! 🐾</h2><button class="close-btn" data-close aria-label="Close">×</button></div><img class="photo-preview" src="${image}" alt="Your chosen cat photo">${s.captureSummary?`<div class="info-note"><strong>Encounter complete.</strong> Captured with ${esc(s.encounterLured?'the Dangle Lure + Whisker Paw combo':'a Whisker Paw')}. ${esc(s.captureSummary.throwRating||'Nice!')} Photo clarity: <strong>${esc(s.captureSummary.quality?.label||'Unrated')}</strong>.</div>`:''}<p class="dim" style="font-size:12px;margin-bottom:11px">Is this a new cat or one you've met before?</p><div class="chips" style="margin-top:0"><button id="mode-new" class="chip ${s.revisitId?'':'selected'}">✨ New cat</button><button id="mode-repeat" class="chip ${s.revisitId?'selected':''}">🐾 Seen before</button></div><div id="catch-extra"></div><div id="possible-matches" aria-live="polite"></div><label class="check-row"><input id="real-cat" type="checkbox"><span>I saw a real cat and took this picture without disturbing or approaching it unsafely.</span></label><label class="check-row"><input id="pin-check" type="checkbox"><span>Add an optional private location pin (never shared).</span></label><p id="pin-failure" class="pin-failure hidden" role="alert"></p><div id="pin-helper" class="location-helper hidden" aria-hidden="true"><p id="pin-helper-note">To add a private map pin, allow location on this device. Whisker Hunt stores only an approximate rounded area. Ask a parent or trusted adult if you are unsure.</p><div class="location-helper-actions"><button type="button" id="pin-allow" class="secondary">Allow location</button><button type="button" id="pin-settings" class="secondary">Open app settings</button><button type="button" id="pin-device-location" class="text-btn">Phone Location switch</button><button type="button" id="pin-retry" class="text-btn">Retry</button><button type="button" id="pin-status-check" class="text-btn">Check location status</button></div><p id="pin-diagnostics" class="location-diagnostics hidden" role="status"></p></div><div class="actions"><button id="save-catch" class="primary">Add to my Collection →</button></div><p class="footnote">Only the selected still image is saved to your Collection. Live mode compares recent frames locally when supported; no video is stored.</p>`);s.catchMode=s.revisitId?'repeat':'new';const drawExtra=()=>{const extra=$('catch-extra');if(s.catchMode==='new'){extra.innerHTML=`<div class="field-group"><label for="cat-name">Give your cat a name</label><input class="field" id="cat-name" maxlength="36" placeholder="e.g. Sir Pounce-a-lot" autocomplete="off"></div><div class="field-group"><label for="cat-coat">Coat / appearance</label><select class="select" id="cat-coat">${COATS.map(c=>`<option>${c}</option>`).join('')}</select></div><div class="field-group"><label for="cat-personality">Personality (your impression)</label><select class="select" id="cat-personality">${PERSONALITIES.map(t=>`<option>${t}</option>`).join('')}</select></div><div class="field-group"><label for="cat-note">Little memory (optional)</label><input class="field" id="cat-note" maxlength="140" placeholder="e.g. Sleeping in the café window"></div>`}else{extra.innerHTML=s.cats.length?`<div class="field-group"><label for="repeat-cat">Which cat did you see again?</label><select id="repeat-cat" class="select">${s.cats.filter(c=>!c.virtual).map(c=>`<option value="${esc(c.id)}" ${c.id===s.revisitId?'selected':''}>${esc(c.name)} (${esc(c.coat)})</option>`).join('')}</select></div><div class="field-group"><label for="repeat-note">Add a memory (optional)</label><input id="repeat-note" class="field" maxlength="140" placeholder="What was your friend up to?"></div>`:`<div class="info-note">No cats collected yet. Add your first new cat!</div>`}};drawExtra();$('mode-new').onclick=()=>{s.catchMode='new';$('mode-new').classList.add('selected');$('mode-repeat').classList.remove('selected');drawExtra();addDiceButton('cat-name','dice-name','name');addDiceButton('cat-note','dice-memory','memory')};$('mode-repeat').onclick=()=>{s.catchMode='repeat';$('mode-repeat').classList.add('selected');$('mode-new').classList.remove('selected');drawExtra();addDiceButton('repeat-note','dice-repeat-memory','memory')};$('save-catch').onclick=saveCatch;findPossibleMatches(image,request)}
function isUsableLocation(loc){return !!loc && Number.isFinite(loc.lat) && Number.isFinite(loc.lng) && Math.abs(loc.lat)<=90 && Math.abs(loc.lng)<=180}
function roundApproxLocation(loc){return isUsableLocation(loc)?{lat:Math.round(Number(loc.lat)*100)/100,lng:Math.round(Number(loc.lng)*100)/100}:null}
function hasFreshApproxLocation(){return isUsableLocation(s.pendingApproxLocation)&&Date.now()-(s.pendingApproxLocationAt||0)<120000}
function setPendingApproxLocation(loc){const rounded=roundApproxLocation(loc);s.pendingApproxLocation=rounded;s.pendingApproxLocationAt=rounded?Date.now():0;return rounded}
function showLocationHelper(prefix='pin',message='Location is optional. If your app permission is already allowed, check the phone Location switch. Ask an adult if you are unsure.'){
 const helper=$(prefix+'-helper');const note=$(prefix+'-helper-note');
 if(helper){helper.classList.remove('hidden');helper.setAttribute('aria-hidden','false')}
 if(note)note.textContent=message;
}
function hideLocationHelper(prefix='pin'){const helper=$(prefix+'-helper');if(helper){helper.classList.add('hidden');helper.setAttribute('aria-hidden','true')}}
const LOCATION_HELP={
 permission:'Location is not allowed yet. Tap Allow location, or check the Whisker Hunt permissions in Android settings.',
 disabled:'Your phone’s Location switch is off. Turn on device Location and tap Retry.',
 timeout:'Your phone could not find its position in time. Move near a window or outdoors and try again.',
 no_fix:'Location is allowed, but your phone has no usable position yet. Turn on device Location or try near a window.',
 unsupported:'This device cannot provide location right now. You may still save the cat without a map pin.',
 bridge:'The app could not contact Android location services. Close and reopen Whisker Hunt, then retry.',
 cancelled:'The location check was cancelled. Tap Retry when you are ready.',
 unknown:'Location is allowed but could not be read. Check the phone Location switch and try again.'
};
let locationLastError='';
let inFlightApproxLocation=null;
function locationFailureText(){return LOCATION_HELP[locationLastError]||LOCATION_HELP.unknown}
function showPinFailure(prefix='pin'){
 const el=$(prefix+'-failure')||$('pin-failure')||$('virtual-pin-failure');
 const wasHidden=Boolean(el?.classList.contains('hidden'));
 if(el){el.textContent=locationFailureText();el.classList.remove('hidden')}
 showLocationHelper(prefix,locationFailureText());
 // If Android says permission is missing, show its real native status rather
 // than repeatedly directing an already-authorised user to Settings.
 if(locationLastError==='permission'||locationLastError==='bridge')
  checkAndroidLocationStatus(prefix);
 if(wasHidden)toast('No map pin yet — check the help below.');
}
function clearPinFailure(prefix='pin'){const el=$(prefix+'-failure');if(el)el.classList.add('hidden')}
function openLocationSettings(){
 try{if(hasAndroidActionBridge()){location.href='whiskerhunt://app-settings';return}}catch(e){console.warn('Could not open Android app settings',e)}
 toast('Go to your device settings and allow Location for Whisker Hunt.');
}
function openDeviceLocationSettings(){
 try{if(hasAndroidActionBridge()){location.href='whiskerhunt://device-location-settings';return}}catch(e){console.warn('Could not open device Location settings',e)}
 toast('Open your phone Settings → Location and turn Location on.');
}
// Request tokens prevent stale GPS responses from placing a marker on a different cat.
let locationRequestSequence=0, activeLocationFinish=null;
async function locationPrompt(){
 if(activeLocationFinish)activeLocationFinish(null,'cancelled');
 const token=String(++locationRequestSequence);
 const androidShell=hasAndroidActionBridge();
 return new Promise(resolve=>{
  let settled=false;
  const finish=(coords,error='')=>{
   if(settled)return;
   settled=true;clearTimeout(timer);
   if(activeLocationFinish===finish){
    activeLocationFinish=null;
    window.whiskerNativeLocation=null;
    window.whiskerNativeLocationError=null;
    locationLastError=error;
   }
   resolve(roundApproxLocation(coords));
  };
  // Android may have to show a permission dialog before asking the provider
  // for a fix. The earlier 14-second JS timeout could expire first.
  const timer=setTimeout(()=>finish(null,'timeout'),androidShell?45000:23000);
  activeLocationFinish=finish;
  locationLastError='';
  if(androidShell){
   window.whiskerNativeLocation=(lat,lng,returnedToken)=>{
    if(String(returnedToken)!==token)return;
    const coords={lat:Number(lat),lng:Number(lng)};
    if(isUsableLocation(coords))finish(coords);
    else finish(null,'no_fix');
   };
   window.whiskerNativeLocationError=(returnedToken,reason='unknown')=>{
    if(String(returnedToken)!==token)return;
    finish(null,typeof reason==='string'?reason:'unknown');
   };
   try{location.href='whiskerhunt://location?request='+encodeURIComponent(token)}
   catch{finish(null,'bridge')}
   return;
  }
  if(!navigator.geolocation){finish(null,'unsupported');return}
  navigator.geolocation.getCurrentPosition(
   pos=>finish({lat:pos.coords.latitude,lng:pos.coords.longitude}),
   error=>finish(null,error?.code===1?'permission':error?.code===3?'timeout':'no_fix'),
   {timeout:19000,enableHighAccuracy:false,maximumAge:60000}
  );
 });
}
async function ensureApproxLocation(prefix='pin'){
 if(inFlightApproxLocation)return inFlightApproxLocation;
 const note=$(prefix+'-helper-note');
 if(note)note.textContent='Checking for a private approximate area… This may take a few seconds.';
 const run=(async()=>{
  const loc=setPendingApproxLocation(await locationPrompt());
  if(loc){
   clearPinFailure(prefix);
   if(note)note.textContent='Private map area ready ✓. Your exact GPS position is never stored.';
   toast('Private map area ready.');
   return loc;
  }
  showPinFailure(prefix);return null;
 })();
 inFlightApproxLocation=run;
 try{return await run}finally{if(inFlightApproxLocation===run)inFlightApproxLocation=null}
}
let locationDiagnosticRequest=0;
function checkAndroidLocationStatus(prefix='pin'){
 const box=$(prefix+'-diagnostics');
 if(!box)return;
 box.classList.remove('hidden');
 box.textContent='Checking device permission and Location switch…';
 const token=String(++locationDiagnosticRequest);
 const checkTimeout=setTimeout(()=>{
  if(box.isConnected && box.dataset.pendingLocationCheck===token){
   box.textContent='Android did not answer this request. Please close and reopen Whisker Hunt, then try again.';
   delete box.dataset.pendingLocationCheck;
  }
 },6500);
 box.dataset.pendingLocationCheck=token;
 window.whiskerNativeLocationDiagnostic=(returnedToken,details)=>{
  if(String(returnedToken)!==token)return;
  clearTimeout(checkTimeout);
  delete box.dataset.pendingLocationCheck;
  if(!details){box.textContent='Android diagnostics are unavailable here.';return}
  const yesNo=value=>value===true?'allowed':value===false?'not granted':'unknown';
  const onOff=value=>value===true?'on':value===false?'off':'unknown';
  box.textContent=`App version ${details.build||'unknown'} · Approximate: ${yesNo(details.coarse)} · Precise: ${yesNo(details.fine)} · Phone Location: ${onOff(details.deviceEnabled)}. No coordinates are shown.`;
 };
 if(hasAndroidActionBridge()){
  try{location.href='whiskerhunt://location-check?request='+encodeURIComponent(token)}
  catch{box.textContent='Could not contact Android location diagnostics.'}
 }else{box.textContent='Location status check is available in the Android app only.'}
}
function wireLocationOptIn(prefix,checkboxId){
 const check=$(checkboxId);if(!check)return;
 const sync=()=>{if(check.checked)showLocationHelper(prefix);else{hideLocationHelper(prefix);clearPinFailure(prefix)}};
 check.addEventListener('change',sync);sync();
 $(prefix+'-allow')?.addEventListener('click',()=>ensureApproxLocation(prefix));
 $(prefix+'-settings')?.addEventListener('click',openLocationSettings);
 $(prefix+'-device-location')?.addEventListener('click',openDeviceLocationSettings);
 $(prefix+'-retry')?.addEventListener('click',()=>ensureApproxLocation(prefix));
 $(prefix+'-status-check')?.addEventListener('click',()=>checkAndroidLocationStatus(prefix));
 const actions=$(prefix+'-helper')?.querySelector('.location-helper-actions');
 if(actions&&!$(prefix+'-skip')){
  const skip=document.createElement('button');skip.type='button';skip.id=prefix+'-skip';
  skip.className='text-btn';skip.textContent='Save cat without a pin';
  skip.addEventListener('click',()=>{
   check.checked=false;check.dispatchEvent(new Event('change'));
   setPendingApproxLocation(null);
   $(prefix==='virtual-pin'?'virtual-save-final':'save-catch')?.click();
  });
  actions.append(skip);
 }
}
async function saveCatch(){
 if(s.busy)return;if(!$('real-cat')?.checked)return toast('Please confirm this is a respectful real-cat encounter.');
 if(!s.db)return toast('Device storage is not ready.');
 const mode=s.catchMode,sig=photoSignature(s.image);let cat;
 if(s.cats.some(c=>c.signature===sig||(c.sightings||[]).some(v=>v.signature===sig)))
  return toast('This photo is already collected. Use a fresh photo for a new sighting.');
 if(mode==='new'){
  const name=$('cat-name')?.value.trim();if(!name)return toast('Please give your cat a name.');
  cat={id:id(),visualHash:null,name:name.slice(0,36),coat:$('cat-coat').value,personality:$('cat-personality').value,note:$('cat-note').value.trim(),photo:s.image,signature:sig,createdAt:new Date().toISOString(),fav:false,sightings:[]};
 }else{
  cat=s.cats.find(c=>c.id===$('repeat-cat')?.value);if(!cat)return toast('Choose a cat from your Collection.');
 }
 const btn=$('save-catch');s.busy=true;btn.disabled=true;btn.textContent='Saving your discovery…';
 let appended=false,added=false,earned=0;
 try{
  const hash=await visualFingerprint(s.image).catch(()=>null);
  if(mode==='new')cat.visualHash=hash;
  const loc=$('pin-check').checked?await locationPrompt():null;
  const note=mode==='new'?cat.note:$('repeat-note')?.value.trim();
  // Restored/merged sightings are not necessarily chronological. Ignore future
  // dates and use the most recent *past* sighting for the 1-hour XP cooldown.
  const now=Date.now();
  const lastSeen=Math.max(0,...(cat.sightings||[]).map(v=>Date.parse(v.at)).filter(t=>Number.isFinite(t)&&t<=now));
  const cooldown=mode==='repeat'&&lastSeen>0&&(now-lastSeen<3600000);
  const firstOfCoat=mode==='new'&&(cat.species||'Cat')==='Cat'&&!s.cats.some(c=>(c.species||'Cat')==='Cat'&&c.coat===cat.coat);
  earned=(mode==='new'?100:cooldown?0:30)+(firstOfCoat?25:0);
  cat.sightings.push({id:id(),visualHash:hash,at:new Date().toISOString(),note,photo:mode==='new'?null:s.image,signature:sig,lat:loc&&Number.isFinite(loc.lat)&&Math.abs(loc.lat)<=90?loc.lat:null,lng:loc&&Number.isFinite(loc.lng)&&Math.abs(loc.lng)<=180?loc.lng:null});appended=true;
  if(mode==='new'){s.cats.push(cat);added=true}
  s.profile.xp+=earned;
  await persistCatchAtomic(cat);
  closeModal();navigate('dex');toast(`${mode==='new'?'🐱 New cat added!':'🐾 Reunited with '+cat.name+'!'} +${earned} XP${wantsPin?' · 📍 Private map pin saved':''}`);
 }catch(e){console.error(e);s.profile.xp-=earned;if(appended)cat.sightings.pop();if(added)s.cats=s.cats.filter(c=>c.id!==cat.id);if(e?.message==='PIN_NOT_SAVED')showPinFailure('pin');else toast('Save failed. Please try again.');btn.disabled=false;btn.textContent='Add to my Collection →';}
 finally{s.busy=false}
}
function openDetail(catId){
 const cat=s.cats.find(c=>c.id===catId);if(!cat)return;
 if(cat.virtual)return openVirtualCatDetail(cat);
 const journal=cat.sightings.slice().reverse().map((x,idx)=>`<div class="sighting journal-row"><div class="sighting-top"><span>🐾 ${dateDisplay(x.at)}${x.lat!=null?' · 📍 Private pin':''}</span><button class="text-btn" data-edit-sighting="${esc(x.id)}">Edit ✎</button></div>${x.photo?`<img class="sighting-thumb" src="${x.photo}" alt="Cat sighting">`:''}${x.note?`<small>${esc(x.note)}</small>`:''}${x.photo?`<div class="cover-actions"><button class="text-btn" data-cover-sighting="${esc(x.id)}" ${x.photo===cat.photo?'disabled':''}>${x.photo===cat.photo?'✓ Current cover':'🖼 Make Collection cover'}</button></div>`:''}</div>`).join('');
 openModal(`<div class="sheet-head"><span class="eyebrow">CATDEX • DISCOVERY CARD</span><button class="close-btn" data-close aria-label="Close">×</button></div><img class="detail-cover" src="${cat.photo}" alt="${esc(cat.name)}"><div class="detail-row"><div><h2>${esc(cat.name)}</h2><p class="dim no-margin" style="font-size:12px">First met ${dateDisplay(cat.createdAt)}</p></div><button id="fav-cat" class="secondary" aria-label="Toggle favourite">${cat.fav?'♥':'♡'}</button></div><div class="detail-tags"><span class="detail-tag">${esc(EMOJIS[cat.coat]||'🐱')} ${esc(cat.coat)}</span><span class="detail-tag">${rank(cat)}</span><span class="detail-tag">${PERSONALITY_EMOJI[cat.personality]||'🐱'} ${esc(cat.personality||'Unknown')}</span><span class="detail-tag">${catches(cat)} sightings</span></div><div class="friendship"><div class="flex between"><span>💜 Friendship · ${friendLabel(cat)}</span><b>${friendlyScore(cat)}%</b></div><div class="quest-bar"><span style="width:${friendlyScore(cat)}%"></span></div></div>${cat.note?`<p class="dim" style="font-size:13px">“${esc(cat.note)}”</p>`:''}<div class="actions"><button id="edit-cat" class="secondary">✎ Edit details</button><button id="save-card" class="primary">🎴 Collect card</button></div><div class="sheet-head" style="margin-top:18px"><h3>Sighting journal</h3><span class="count-label">${cat.sightings.length} memories</span></div>${journal}<div class="actions"><button id="more-sighting" class="primary">📷 Spot again</button><button id="share-cat" class="secondary">↗ Share text</button></div><button id="delete-cat" class="text-btn red" style="margin-top:15px;width:100%;text-align:center">Delete this cat & its sightings</button>`);
 $('fav-cat').onclick=async()=>{cat.fav=!cat.fav;try{await saveCat(cat);openDetail(cat.id);render()}catch(e){cat.fav=!cat.fav;toast('Could not save favourite. Please retry.')}};
 $('edit-cat').onclick=()=>editCat(cat);
 $('save-card').onclick=()=>exportCatCard(cat);
 $('more-sighting').onclick=()=>{startCatch(cat.id);toast('Take a new photo — '+cat.name+' will be preselected.')} ;
 $('share-cat').onclick=()=>shareCat(cat);
 $('delete-cat').onclick=()=>deleteCat(cat);
 document.querySelectorAll('[data-edit-sighting]').forEach(b=>b.addEventListener('click',()=>editSighting(cat,b.dataset.editSighting)));
 document.querySelectorAll('[data-cover-sighting]').forEach(b=>b.addEventListener('click',()=>setCoverFromSighting(cat,b.dataset.coverSighting)));
}
// Set the Collection cover to an existing sighting without losing the original
// discovery photograph. This changes no cat/sighting IDs, XP or backup schema.
async function setCoverFromSighting(cat,sightingId){
 if(s.busy||s.storageBlocked)return;
 const entry=cat.sightings?.find(v=>v.id===sightingId);
 if(!entry?.photo||entry.photo===cat.photo)return;
 const first=cat.sightings[0];
 const old={photo:cat.photo,signature:cat.signature,visualHash:cat.visualHash,firstPhoto:first?.photo};
 s.busy=true;
 try{
  const newHash=entry.visualHash||await visualFingerprint(entry.photo).catch(()=>null);
  // The original first encounter previously used cat.photo. Retain it as an
  // explicit journal image before replacing the cover.
  if(first&&!first.photo)first.photo=cat.photo;
  cat.photo=entry.photo;
  cat.signature=entry.signature||photoSignature(entry.photo);
  cat.visualHash=newHash;
  await saveCat(cat);
  similarityCache.delete(cat.id);
  openDetail(cat.id);render();toast('Collection cover updated. Original discovery photo preserved!');
 }catch(e){
  console.error(e);cat.photo=old.photo;cat.signature=old.signature;cat.visualHash=old.visualHash;
  if(first)first.photo=old.firstPhoto;
  toast('Could not update the cover. Your original photo was kept.');
 }finally{s.busy=false}
}
async function editCat(cat){
 openModal(`<div class="sheet-head"><h2>Edit cat details ✎</h2><button class="close-btn" data-close>×</button></div><div class="field-group"><label for="edit-name">Name</label><input id="edit-name" maxlength="36" class="field" value="${esc(cat.name)}"></div><div class="field-group"><label for="edit-coat">Coat / appearance</label><select id="edit-coat" class="select">${COATS.map(c=>`<option ${cat.coat===c?'selected':''}>${c}</option>`).join('')}</select></div><div class="field-group"><label for="edit-personality">Personality (your impression)</label><select id="edit-personality" class="select">${PERSONALITIES.map(t=>`<option ${cat.personality===t?'selected':''}>${t}</option>`).join('')}</select></div><div class="field-group"><label for="edit-note">Your memory</label><textarea id="edit-note" class="field" maxlength="140" rows="3">${esc(cat.note||'')}</textarea></div><p class="footnote">These details are your descriptions. Friendship is based on sightings, not AI identification.</p><div class="actions"><button class="primary" id="edit-save">Save changes</button></div>`);
 $('edit-save').onclick=async()=>{const name=$('edit-name').value.trim();if(!name)return toast('Please enter a name.');const next={name:name.slice(0,36),coat:$('edit-coat').value,personality:$('edit-personality').value,note:$('edit-note').value.trim().slice(0,140)};const prior={name:cat.name,coat:cat.coat,personality:cat.personality,note:cat.note};Object.assign(cat,next);try{await saveCat(cat);openDetail(cat.id);render();toast('Cat updated!')}catch(e){Object.assign(cat,prior);toast('Could not update cat.')}}
}
async function editSighting(cat,sightingId){
 const entry=cat.sightings.find(x=>x.id===sightingId);if(!entry)return;
 const isFirst=cat.sightings[0]===entry;
 openModal(`<div class="sheet-head"><h2>Edit sighting 🐾</h2><button class="close-btn" data-close>×</button></div><p class="dim">${dateDisplay(entry.at)}${isFirst?' · First discovery':''}</p><div class="field-group"><label for="sighting-note">What happened?</label><textarea id="sighting-note" maxlength="140" rows="4" class="field">${esc(entry.note||'')}</textarea></div>${entry.lat!=null?'<label class="check-row"><input type="checkbox" id="forget-pin"><span>Remove the precise location pin for this sighting</span></label>':'<label class="check-row"><input type="checkbox" id="add-current-pin"><span>Save my current location (only if I am still at the place where I saw this cat).</span></label><p id="pin-failure" class="pin-failure hidden" role="alert"></p>'}<div class="actions"><button id="save-sighting" class="primary">Save entry</button></div>${!isFirst?'<button id="delete-sighting" class="text-btn red" style="margin-top:18px">Delete this return sighting</button>':'<p class="footnote">The first sighting cannot be deleted separately. You can delete the complete cat entry in the Collection.</p>'}`);
 $('save-sighting').onclick=async()=>{const before={note:entry.note,lat:entry.lat,lng:entry.lng};entry.note=$('sighting-note').value.trim().slice(0,140);if($('forget-pin')?.checked){entry.lat=null;entry.lng=null}
 if($('add-current-pin')?.checked){const loc=await locationPrompt();if(!isUsableLocation(loc)){Object.assign(entry,before);showPinFailure();return;}entry.lat=loc.lat;entry.lng=loc.lng}
 try{await saveCat(cat);openDetail(cat.id);render();toast('Sighting updated!')}catch(e){Object.assign(entry,before);toast('Could not save sighting.')}};
 if(!isFirst)$('delete-sighting').onclick=()=>{if(!confirm('Delete this return sighting and its photo? XP already earned will stay.'))return;const old=cat.sightings;cat.sightings=old.filter(x=>x.id!==sightingId);saveCat(cat).then(()=>{openDetail(cat.id);render();toast('Sighting removed.')}).catch(()=>{cat.sightings=old;toast('Could not remove sighting.')})};
}
function canvasRoundRect(ctx,x,y,w,h,r){ctx.beginPath();ctx.roundRect(x,y,w,h,r);ctx.closePath()}
async function createCatCard(cat){
 const canvas=document.createElement('canvas');canvas.width=750;canvas.height=1050;const ctx=canvas.getContext('2d');
 const background=ctx.createLinearGradient(0,0,750,1050);background.addColorStop(0,'#442d75');background.addColorStop(.58,'#18182f');background.addColorStop(1,'#10243f');ctx.fillStyle=background;ctx.fillRect(0,0,750,1050);
 for(let n=0;n<24;n++){ctx.fillStyle=n%3?'#ffffff12':'#e0c4ff26';ctx.beginPath();ctx.arc((n*173+29)%750,(n*277+51)%1050,2+(n%4),0,Math.PI*2);ctx.fill()}
 ctx.fillStyle='#ff83ad';canvasRoundRect(ctx,32,32,686,985,37);ctx.fill();ctx.fillStyle='#232340';canvasRoundRect(ctx,43,43,664,963,30);ctx.fill();
 const img=new Image();await new Promise((resolve,reject)=>{img.onload=resolve;img.onerror=reject;img.src=cat.photo});
 ctx.save();canvasRoundRect(ctx,68,170,614,530,24);ctx.clip();const scale=Math.max(614/img.width,530/img.height);const iw=img.width*scale,ih=img.height*scale;ctx.drawImage(img,68+(614-iw)/2,170+(530-ih)/2,iw,ih);ctx.restore();
 ctx.fillStyle='#bdece3';ctx.font='bold 24px system-ui, sans-serif';ctx.fillText('WHISKER HUNT · CATDEX',74,111);ctx.textAlign='right';ctx.fillStyle='#ffd08e';ctx.fillText('✦ CAT #'+String(s.cats.indexOf(cat)+1).padStart(3,'0'),674,111);ctx.textAlign='left';
 ctx.fillStyle='#fff';ctx.font='bold 54px system-ui, sans-serif';ctx.fillText(cat.name.slice(0,19),74,782);
 ctx.fillStyle='#cdb8e7';ctx.font='26px system-ui, sans-serif';ctx.fillText(cat.coat+' · '+(cat.personality&&cat.personality!=='Unknown'?cat.personality+' · ':'')+friendLabel(cat),76,836);
 ctx.fillStyle='#f9c7dc';ctx.font='bold 24px system-ui, sans-serif';ctx.fillText('🐾 '+catches(cat)+' SIGHTING'+(catches(cat)!==1?'S':''),76,908);
 ctx.textAlign='right';ctx.fillText('♥ '+friendlyScore(cat)+'% FRIENDSHIP',670,908);ctx.textAlign='left';
 ctx.fillStyle='#aeb2c8';ctx.font='20px system-ui, sans-serif';ctx.fillText('FIRST SPOTTED · '+dateDisplay(cat.createdAt).toUpperCase(),76,963);
 return canvas.toDataURL('image/png');
}
window.whiskerCardBase64=function(){return s.cardBase64||''};
async function exportCatCard(cat){
 try{toast('Creating your collectible card…');const png=await createCatCard(cat);s.cardBase64=png.slice(png.indexOf(',')+1);
 if(window.whiskerNativeReady){location.href='whiskerhunt://sticker'}else{const link=document.createElement('a');link.href=png;link.download='whisker-hunt-'+cat.name.toLowerCase().replace(/[^a-z0-9-]+/g,'-')+'-card.png';document.body.appendChild(link);link.click();link.remove();toast('Cat card downloaded!')}}catch(e){console.error(e);toast('Could not generate cat card.')}}
async function editName(cat){openModal(`<div class="sheet-head"><h2>Rename your cat</h2><button class="close-btn" data-close>×</button></div><input id="new-name" maxlength="36" class="field" value="${esc(cat.name)}"><div class="actions"><button id="name-save" class="primary">Save name</button></div>`);$('name-save').onclick=async()=>{const name=$('new-name').value.trim();if(!name)return toast('Enter a name.');const previous=cat.name;cat.name=name;try{await saveCat(cat);closeModal();render();toast('Cat renamed!')}catch(e){cat.name=previous;toast('Could not save name. Please retry.')}}}
async function deleteCat(cat){openModal(`<div class="sheet-head"><h2>Delete ${esc(cat.name)}?</h2><button class="close-btn" data-close>×</button></div><p class="dim">This permanently removes the cat, its photos and sighting journal from this device. XP already earned will remain.</p><div class="actions"><button class="secondary" id="cancel-delete">Cancel</button><button class="primary" id="confirm-delete">Delete forever</button></div>`);$('cancel-delete').onclick=closeModal;$('confirm-delete').onclick=async()=>{if(s.busy)return;s.busy=true;const previous=s.cats;s.cats=s.cats.filter(c=>c.id!==cat.id);try{await removeCat(cat);closeModal();render();toast('Cat removed from your Collection.')}catch(e){s.cats=previous;toast('Could not delete cat. Your collection was kept.')}finally{s.busy=false}}}
async function shareCat(cat){const message=`🐾 Meet ${cat.name}, a ${cat.coat.toLowerCase()} cat in my Whisker Hunt Collection! ${catches(cat)} sighting${catches(cat)!==1?'s':''}. #HushHunt`;if(window.whiskerNativeReady){location.href='whiskerhunt://share?text='+encodeURIComponent(message);return}try{if(navigator.share)await navigator.share({title:'Hush Hunt',text:message});else if(navigator.clipboard){await navigator.clipboard.writeText(message);toast('Caption copied!')}}catch(e){if(e.name!=='AbortError')toast('Could not share on this browser.')}}
function action(kind){if(kind.startsWith('osm:')){const [lat,lng]=kind.slice(4).split(',').map(Number);askOpenStreetMap(lat,lng);return}if(kind==='privacy-tools')return openPrivacyTools();if(kind==='health-check')return openCollectionHealth();if(kind==='rename-profile')return editProfile();if(kind==='export')return exportBackup();if(kind==='import'){if(window.whiskerNativeReady){location.href='whiskerhunt://restore';return}return $('backup-input').click()}if(kind==='about')return openModal(`<div class="sheet-head"><h2>Privacy & cat safety 🐾</h2><button class="close-btn" data-close>×</button></div><p class="dim">Whisker Hunt v1.1 saves your photos, cat names, sightings and optional coordinates <strong>on this device only</strong>. We don't have a server, accounts, adverts or analytics.</p><p class="dim">Choose whether to attach a location to each encounter. Locations do not appear in shared text. You decide before opening an external map.</p><p class="dim">Keep a respectful distance. Do not trespass, lure cats into dangerous places, follow them into roads, or reveal somebody's home or garden.</p><p class="dim">Export backups before uninstalling or resetting app/browser storage. Photo resemblance hints run on-device, can be wrong, and never automatically identify or merge cats. The app cannot verify whether an image contains a cat.</p>`) }
function editProfile(){openModal(`<div class="sheet-head"><h2>Your explorer name</h2><button class="close-btn" data-close>×</button></div><input id="new-profile-name" class="field" maxlength="30" value="${esc(s.profile.name)}"><div class="actions"><button id="profile-save" class="primary">Save</button></div>`);$('profile-save').onclick=async()=>{const name=$('new-profile-name').value.trim();if(!name)return toast('Enter a name');const previous=s.profile.name;s.profile.name=name;try{await saveProfile();closeModal();render();toast('Profile updated!')}catch(e){s.profile.name=previous;toast('Could not save your name. Please retry.')}}}
// Restore is additive: a backup cannot erase local edits or sightings for an existing ID.
function mergeCatRecord(local,imported){
 if(!local)return imported;
 const seen=new Set((local.sightings||[]).map(v=>v.id));
 const additions=imported.sightings.filter(v=>!seen.has(v.id));
 return {...local,sightings:[...(local.sightings||[]),...additions]};
}
function persistRestoreAtomic(cats,profile){return new Promise((resolve,reject)=>{const tx=s.db.transaction(['cats','meta'],'readwrite');tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error||new Error('Storage transaction failed'));tx.onabort=()=>reject(tx.error||new Error('Storage transaction aborted'));const store=tx.objectStore('cats');for(const cat of cats)store.put(cat);tx.objectStore('meta').put({key:'profile',value:profile})})}
// The GPS-free export is a separate, in-memory copy: the actual collection is untouched.
// Keep backup schema v1 for compatibility with every previous Whisker Hunt release.
function backupPayload(stripLocations=false){return {app:'Whisker Hunt',version:1,exportedAt:new Date().toISOString(),cats:stripLocations?s.cats.map(c=>({...c,sightings:(c.sightings||[]).map(v=>{const {lat,lng,...rest}=v;return rest})})):s.cats,profile:s.profile}}
window.whiskerBackupBase64=function(stripLocations=false){return btoa(unescape(encodeURIComponent(JSON.stringify(backupPayload(stripLocations))))) };
function downloadBackup(stripLocations){const payload=backupPayload(stripLocations);const blob=new Blob([JSON.stringify(payload)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`whisker-hunt-${stripLocations?'gps-free-':''}backup-${today()}.json`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);toast(stripLocations?'GPS-free backup saved. Your private pins remain on this device.':'Full backup downloaded — it may contain precise locations.');}
function exportBackup(){if(window.whiskerNativeReady){location.href='whiskerhunt://export';return}downloadBackup(false)}
function exportSafeBackup(){if(window.whiskerNativeReady){location.href='whiskerhunt://export-safe';return}downloadBackup(true)}
function pinnedSightings(){return s.cats.reduce((n,c)=>n+(c.sightings||[]).filter(v=>v.lat!=null||v.lng!=null).length,0)}
function estimatedBackupSize(){return new Blob([JSON.stringify(backupPayload())]).size}
function openPrivacyTools(){const count=pinnedSightings();const bytes=estimatedBackupSize();const size=bytes>=1024*1024?(bytes/1024/1024).toFixed(1)+' MB':Math.max(1,Math.round(bytes/1024))+' KB';openModal(`<div class="sheet-head"><h2>Privacy & storage 🔒</h2><button class="close-btn" data-close aria-label="Close">×</button></div><div class="soft-card"><div class="eyebrow">STORED ON THIS DEVICE</div><p class="dim" style="margin-bottom:0">${s.cats.length} cats · ${allSightings().length} sightings · <strong>${count} location pins</strong><br>Estimated backup size: ${size}</p></div><p class="dim">A full backup includes your photos and any exact location pins. Use the GPS-free backup when sending your collection to someone else.</p><div class="actions"><button id="export-safe" class="primary">↧ Export GPS-free backup</button></div><p class="footnote">The GPS-free copy keeps your cats, photos, notes, XP and quests. Your original saved locations are not changed.</p><div class="actions"><button id="forget-all-pins" class="secondary" ${count?'':'disabled'}>🗑 Forget all ${count} location pin${count===1?'':'s'}</button></div><p class="footnote">Removing pins is permanent in this collection. Previously exported full backups may still contain coordinates.</p><div class="actions"><button id="check-health" class="secondary">🩺 Review collection health</button></div><p class="footnote">Read-only check: no cats, photos, pins or XP will be changed.</p>`);$('export-safe').onclick=exportSafeBackup;$('forget-all-pins').onclick=forgetAllPins;$('check-health').onclick=openCollectionHealth}
// Non-destructive local audit. This is not a substitute for restoring a backup.
function collectionHealth(){
 const problems=[],catIds=new Set(),sightingIds=new Set();let sightings=0,photos=0,pins=0;
 for(const cat of s.cats){
  if(!cat||typeof cat!=='object'){problems.push('Invalid cat record');continue}
  if(!cat.id||catIds.has(cat.id))problems.push('Duplicate or missing cat identifier');
  catIds.add(cat.id);
  if(typeof cat.photo!=='string'||!/^data:image\/(jpeg|png|webp);base64,/.test(cat.photo))problems.push('Missing or unsupported cover photo for '+String(cat.name||'unnamed cat'));
  else photos++;
  if(!Array.isArray(cat.sightings)||!cat.sightings.length){problems.push('Missing sighting history for '+String(cat.name||'unnamed cat'));continue}
  for(const entry of cat.sightings){
   if(!entry||typeof entry!=='object'){problems.push('Invalid sighting entry');continue}
   sightings++;
   if(!entry.id||sightingIds.has(entry.id))problems.push('Duplicate or missing sighting identifier');
   sightingIds.add(entry.id);
   if(typeof entry.at!=='string'||!Number.isFinite(Date.parse(entry.at)))problems.push('Invalid sighting date');
   if(entry.photo){if(!/^data:image\/(jpeg|png|webp);base64,/.test(entry.photo))problems.push('Unsupported sighting photo');else photos++}
   if(entry.lat!=null||entry.lng!=null){
    pins++;
    if(entry.lat==null||entry.lng==null||!Number.isFinite(Number(entry.lat))||!Number.isFinite(Number(entry.lng))||Math.abs(Number(entry.lat))>90||Math.abs(Number(entry.lng))>180)problems.push('Incomplete or invalid location pin');
   }
  }
 }
 if(!Number.isFinite(s.profile.xp)||s.profile.xp<0)problems.push('Invalid XP value');
 if(!Array.isArray(s.profile.claimed))problems.push('Quest claims are not in the expected format');
 return {cats:s.cats.length,sightings,photos,pins,problems};
}
function openCollectionHealth(){
 const h=collectionHealth();const ok=!h.problems.length;
 openModal(`<div class="sheet-head"><h2>Collection health 🩺</h2><button class="close-btn" data-close aria-label="Close">×</button></div><div class="soft-card"><strong>${ok?'✓ No structural problems found':'⚠ '+h.problems.length+' potential issue(s)'}</strong><p class="dim" style="margin-bottom:0">${h.cats} cats · ${h.sightings} sightings · ${h.photos} stored photo references · ${h.pins} private pins</p></div>${ok?'<p class="dim">Your collection passed these local structure checks. This does not verify that photos show cats or guarantee that device storage is healthy.</p>':`<p class="dim">Nothing was changed. Export a full backup before making further edits.</p><div class="soft-card">${h.problems.slice(0,12).map(p=>`<p class="dim" style="margin:6px 0">• ${esc(p)}</p>`).join('')}${h.problems.length>12?'<p class="dim">Additional issues omitted.</p>':''}</div>`}<div class="actions"><button id="health-back" class="secondary">← Back to privacy tools</button></div>`);
 $('health-back').onclick=openPrivacyTools;
}
function persistCatsAtomic(cats){return new Promise((resolve,reject)=>{const tx=s.db.transaction('cats','readwrite');const store=tx.objectStore('cats');for(const c of cats)store.put(c);tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error||new Error('Location removal failed'));tx.onabort=()=>reject(tx.error||new Error('Location removal aborted'))})}
async function forgetAllPins(){if(s.busy)return;const count=pinnedSightings();if(!count)return toast('No saved locations to remove.');if(!confirm(`Permanently remove ${count} saved location pin${count===1?'':'s'} from this device? Photos, cats and XP will stay. Old backups are not changed.`))return;const updated=s.cats.map(c=>({...c,sightings:(c.sightings||[]).map(v=>{const {lat,lng,...rest}=v;return rest})}));s.busy=true;const button=$('forget-all-pins');if(button){button.disabled=true;button.textContent='Removing location pins…'}try{if(!s.native)await persistCatsAtomic(updated);const previous=s.cats;s.cats=updated;try{if(s.native)await nativeSync()}catch(e){s.cats=previous;throw e}closeModal();render();toast(`Removed ${count} private location pin${count===1?'':'s'}. Cats and XP preserved.`)}catch(e){console.error(e);toast('Could not remove locations. Your original pins were kept.');if(button){button.disabled=false;button.textContent='Try removing pins again'}}finally{s.busy=false}}

async function importBackup(e){const f=e.target.files?.[0];e.target.value='';if(!f)return;if(f.size>35*1024*1024)return toast('Backup is too large.');await loadBackupText(await f.text())}
window.whiskerLoadBackup=loadBackupText;
async function loadBackupText(jsonText){
 let data;try{data=JSON.parse(jsonText)}catch{toast('This is not a valid JSON backup.');return}
 if(data.app!=='Whisker Hunt'||data.version!==1||!Array.isArray(data.cats)||data.cats.length>2000||!data.profile||!Number.isFinite(data.profile.xp)||data.profile.xp<0)return toast('Unsupported or invalid Whisker Hunt backup.');
 const validId=v=>typeof v==='string'&&/^[a-zA-Z0-9_-]{1,100}$/.test(v);
 const validPhoto=p=>typeof p==='string'&&p.length<=12*1024*1024&&/^data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(p);
 const accepted=[];let skipped=0;const seenCatIds=new Set();
 for(const c of data.cats){
  if(!c||!validId(c.id)||seenCatIds.has(c.id)||typeof c.name!=='string'||!validPhoto(c.photo)||!Array.isArray(c.sightings)||c.sightings.length>2000){skipped++;continue}seenCatIds.add(c.id);
  const seenSightingIds=new Set();const sightings=c.sightings.filter(v=>{if(!v||!validId(v.id)||seenSightingIds.has(v.id))return false;seenSightingIds.add(v.id);return typeof v.at==='string'&&Number.isFinite(Date.parse(v.at))&&(v.photo==null||validPhoto(v.photo))}).map(v=>({id:v.id.slice(0,100),at:v.at,note:String(v.note||'').slice(0,140),photo:v.photo||null,signature:String(v.signature||''),visualHash:/^[a-f0-9]{16}$/i.test(v.visualHash||'')?v.visualHash:null,lat:safePin(v.lat)&&v.lat!=null&&Number(v.lat)>=-90&&Number(v.lat)<=90?Number(v.lat):null,lng:safePin(v.lng)&&v.lng!=null?Number(v.lng):null,captureMode:['ar-virtual','ar-live','live','photo'].includes(v.captureMode)?v.captureMode:null,arModel:typeof v.arModel==='string'&&/^[a-z0-9-]{1,50}$/.test(v.arModel)?v.arModel:null,habitat:typeof v.habitat==='string'&&/^[a-z0-9-]{1,50}$/.test(v.habitat)?v.habitat:null}));
  if(!sightings.length){skipped++;continue}
  accepted.push({id:c.id,name:c.name.slice(0,36),species:SPECIES.includes(c.species)?c.species:'Cat',speciesDetail:typeof c.speciesDetail==='string'?c.speciesDetail.slice(0,50):'',coat:COATS.includes(c.coat)?c.coat:'Other',personality:PERSONALITIES.includes(c.personality)?c.personality:'Unknown',note:String(c.note||'').slice(0,140),photo:c.photo,signature:String(c.signature||photoSignature(c.photo)),visualHash:/^[a-f0-9]{16}$/i.test(c.visualHash||'')?c.visualHash:null,createdAt:Number.isFinite(Date.parse(c.createdAt))?c.createdAt:sightings[0].at,fav:!!c.fav,virtual:c.virtual===true,arModelHint:typeof c.arModelHint==='string'&&/^[a-z0-9-]{1,50}$/.test(c.arModelHint)?c.arModelHint:null,arHabitatHint:typeof c.arHabitatHint==='string'&&/^[a-z0-9-]{1,50}$/.test(c.arHabitatHint)?c.arHabitatHint:null,sightings});
 }
 if(data.cats.length&&!accepted.length)return toast('No valid cats were found in this backup.');
 if(!confirm('Merge '+accepted.length+' cats into your Collection? Matching IDs will be updated, other cats stay, and XP will never decrease.'))return;
 const oldCats=s.cats.slice(),oldProfile={...s.profile};
 try{
  const merged=new Map(s.cats.map(c=>[c.id,c]));let newSightings=0;for(const c of accepted){const local=merged.get(c.id);const combined=mergeCatRecord(local,c);newSightings+=combined.sightings.length-(local?.sightings?.length||0);merged.set(c.id,combined)}
  const nextProfile={name:String(s.profile.name||data.profile.name||'Hush Explorer').slice(0,30),xp:Math.max(s.profile.xp,data.profile.xp),claimed:[...new Set([...(s.profile.claimed||[]),...(Array.isArray(data.profile.claimed)?data.profile.claimed.filter(x=>typeof x==='string'&&x.length<120):[])])].slice(-1200),viewSettings:hushViewSettings(s.profile.viewSettings||data.profile.viewSettings)};
  if(!s.native)await persistRestoreAtomic([...merged.values()],nextProfile);
  s.cats=[...merged.values()];s.profile=nextProfile;
  if(s.native){
   // Explicitly confirmed restore is the only write allowed after corrupted snapshots.
   s.recoveryApproved=true;
   try{await nativeSync();s.storageBlocked=false}
   finally{s.recoveryApproved=false}
  }
  render();toast('Merged '+accepted.length+' cat records · '+newSightings+' new sightings'+(skipped?' ('+skipped+' skipped)':'')+'!');
 }catch(e){console.error(e);s.cats=oldCats;s.profile=oldProfile;toast('Restore failed. Check free storage space.')}}
// Dynamic buttons are attached after each view render; home-only capture buttons.
const originalWire=wireScreen;wireScreen=function(){originalWire();for(const name of ['hero-catch','empty-catch','dex-catch']){const b=$(name);if(b)b.addEventListener('click',startCatch)}};
window.whiskerNativeStorageError=function(message){
 window.whiskerNativeReady=true;s.native=true;s.db={native:true};s.storageBlocked=true;
 s.cats=[];s.profile={name:'Hush Explorer',xp:0,claimed:[]};render();
 openModal('<div class="sheet-head"><h2>Collection needs recovery ⚠️</h2></div><p class="dim">Your local save and recovery snapshot could not be read. Whisker Hunt will not overwrite them with an empty collection.</p><p class="dim">Retry reading the device storage, or explicitly restore an exported JSON backup. Do not uninstall the app.</p><div class="actions"><button class="secondary" id="retry-native">Retry reading</button><button class="primary" id="restore-native">Restore JSON backup</button></div>');
 $('retry-native').onclick=()=>{closeModal();if(window.whiskerRequestNativeReady)window.whiskerRequestNativeReady();else location.href='whiskerhunt://ready'};
 $('restore-native').onclick=()=>{closeModal();location.href='whiskerhunt://restore'};
 console.warn('Native storage recovery required:',String(message||''));
};
window.whiskerUseNativeStorage=function(json){s.native=true;s.db={native:true};s.storageBlocked=false;s.recoveryApproved=false;window.whiskerNativeReady=true;s.cats=[];s.profile={name:'Hush Explorer',xp:0,claimed:[]};if(json){try{const data=JSON.parse(json);if(data.app==='Whisker Hunt'&&Array.isArray(data.cats)){s.cats=data.cats;s.profile={name:String(data.profile?.name||'Hush Explorer').slice(0,30),xp:Math.max(0,Number(data.profile?.xp)||0),claimed:Array.isArray(data.profile?.claimed)?data.profile.claimed:[],viewSettings:hushViewSettings(data.profile?.viewSettings)}}}catch(e){console.error(e);toast('Could not load your saved local collection.')}}render()};
document.addEventListener('DOMContentLoaded',boot);


/* v2.8 additions: AR safari prototype, stylised cat models, smarter capture metadata. */
s.encounterAr=false;
s.arModelKey='ginger-tabby';
s.arModelManual=false;
s.arModelSuggested='';
const AR_CAT_MODELS=[
 {key:'ginger-tabby',name:'Ginger Tabby',coat:'Ginger',base:'#d8873f',belly:'#f7d2a8',accent:'#8f4e24',ear:'#f5bea3',eye:'#4dcc7d',shadow:'#6a3515',pattern:'tabby'},
 {key:'tuxedo-mischief',name:'Tuxedo',coat:'Tuxedo',base:'#21242f',belly:'#f4f5f8',accent:'#4a4f61',ear:'#f5b6c3',eye:'#7ef0b6',shadow:'#0e1017',pattern:'tuxedo'},
 {key:'siamese-star',name:'Siamese',coat:'Other',base:'#f4dfc2',belly:'#fff5e8',accent:'#654335',ear:'#7f5a48',eye:'#7dd8ff',shadow:'#9a8469',pattern:'siamese'},
 {key:'midnight-panther',name:'Black Cat',coat:'Black',base:'#20242d',belly:'#2e3440',accent:'#555c6e',ear:'#8e5b62',eye:'#91ff68',shadow:'#0d1015',pattern:'solid'},
 {key:'calico-scout',name:'Calico',coat:'Calico',base:'#f5efe8',belly:'#fff9f2',accent:'#e2873d',accent2:'#3b3232',ear:'#efb8b0',eye:'#70d8b7',shadow:'#8f6649',pattern:'calico'},
 {key:'british-cloud',name:'British Shorthair',coat:'Grey',base:'#97a6c8',belly:'#cfd8ea',accent:'#7081ab',ear:'#d0b3c2',eye:'#f0d36b',shadow:'#58667d',pattern:'cloud'}
];
function getArModel(key){return AR_CAT_MODELS.find(m=>m.key===key)||AR_CAT_MODELS[0]}
function rarityWeight(rarity){return ({common:1,uncommon:.72,rare:.44,epic:.22,legendary:.1}[rarity]||1)}
function randomArModel(except=''){const caught=new Set(s.cats.filter(c=>c.virtual).map(c=>c.arModelHint));const missing=AR_CAT_MODELS.filter(m=>!caught.has(m.key)&&m.key!==except);const pool=(missing.length?missing:AR_CAT_MODELS.filter(m=>m.key!==except)).map(m=>({model:m,w:rarityWeight(m.rarity)}));const total=pool.reduce((sum,x)=>sum+x.w,0);let pick=Math.random()*total;for(const item of pool){pick-=item.w;if(pick<=0)return item.model}return pool[0]?.model||AR_CAT_MODELS[0]}
function arModelPattern(model){
 switch(model.pattern){
  case 'tabby': return `<g fill="none" stroke="${model.accent}" stroke-width="4" stroke-linecap="round" opacity=".9"><path d="M84 64c8-9 24-9 32 0"/><path d="M72 93c11-8 57-8 69 0"/><path d="M70 108c12-7 61-7 74 0"/><path d="M90 31c6 6 14 6 20 0"/></g>`;
  case 'tuxedo': return `<path d="M83 76c11 10 24 17 36 25 12-9 19-17 24-26-8-4-17-7-30-7-13 0-22 3-30 8Z" fill="#ffffff" opacity=".97"/><path d="M108 81 118 101 127 81" fill="#1d1f28" opacity=".85"/>`;
  case 'siamese': return `<g fill="${model.accent}" opacity=".95"><ellipse cx="101" cy="90" rx="18" ry="12"/><ellipse cx="77" cy="57" rx="11" ry="8"/><ellipse cx="123" cy="57" rx="11" ry="8"/></g>`;
  case 'calico': return `<g opacity=".97"><path d="M71 85c11-11 27-8 34 0-8 8-20 14-30 12-6-2-7-8-4-12Z" fill="${model.accent}"/><path d="M106 67c12-6 28-6 38 4-5 8-15 17-26 18-12 0-19-12-12-22Z" fill="${model.accent2}"/><path d="M117 101c10 2 19 6 24 15-10 6-26 6-35-3-6-6-1-14 11-12Z" fill="${model.accent}"/></g>`;
  case 'cloud': return `<g fill="none" stroke="${model.accent}" stroke-width="4" stroke-linecap="round" opacity=".75"><path d="M73 91c12-6 58-6 70 0"/><path d="M84 108c8-4 41-4 49 0"/></g>`;
  default: return `<g fill="none" stroke="${model.accent}" stroke-width="4" stroke-linecap="round" opacity=".6"><path d="M82 92c11-7 48-7 59 0"/></g>`;
 }
}
function renderArCatSvg(model,compact=false){
 const label=esc(model.name),uid='ar'+String(model.key||'cat').replace(/[^a-z0-9]+/gi,'')+(compact?'c':'f');
 const fluff=model.fur==='long',hairless=model.fur==='hairless',sleek=model.fur==='sleek';
 const earY=fluff?'16':'19',headRy=fluff?'31':'29';
 const bodyRx=fluff?'53':'49',bodyRy=fluff?'40':'36';
 const tailWidth=fluff?'16':'12';
 const furStroke=hairless?'':`<g stroke="${model.accent}" stroke-width="1.8" stroke-linecap="round" opacity="${fluff?'.42':'.22'}"><path d="M69 120 63 128"/><path d="M82 128 77 138"/><path d="M118 128 123 139"/><path d="M132 120 138 128"/></g>`;
 return `<svg class="ar-cat-svg ar-cat-realish" viewBox="0 0 200 160" role="img" aria-label="${label}">
 <defs>
  <linearGradient id="${uid}-base" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${hairless?model.belly:model.base}"/><stop offset=".55" stop-color="${model.base}"/><stop offset="1" stop-color="${model.shadow||shiftHex(model.accent,-18)}"/></linearGradient>
  <radialGradient id="${uid}-belly" cx=".5" cy=".28" r=".82"><stop offset="0" stop-color="${model.belly}"/><stop offset="1" stop-color="${hairless?model.base:model.belly}"/></radialGradient>
  <radialGradient id="${uid}-eye" cx=".5" cy=".42" r=".6"><stop offset="0" stop-color="#ffffff"/><stop offset=".38" stop-color="${model.eye}"/><stop offset="1" stop-color="#15202b"/></radialGradient>
  <linearGradient id="${uid}-tail" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${model.accent}"/><stop offset="1" stop-color="${model.shadow||shiftHex(model.accent,-20)}"/></linearGradient>
 </defs>
 <ellipse cx="100" cy="146" rx="50" ry="10" fill="#00000022"/>
 <path d="M154 112c19-12 24-36 6-49-5-4-12-7-21-7" fill="none" stroke="url(#${uid}-tail)" stroke-width="${tailWidth}" stroke-linecap="round" opacity=".97"/>
 <path d="M63 114 C62 82 74 61 103 61 C132 61 146 82 145 114 C136 129 119 138 101 138 C83 138 69 129 63 114 Z" fill="url(#${uid}-base)"/>
 <ellipse cx="103" cy="112" rx="30" ry="20" fill="url(#${uid}-belly)" opacity=".97"/>
 <path d="M77 92 C90 84 116 84 130 92" fill="none" stroke="#ffffff20" stroke-width="3" stroke-linecap="round"/>
 ${arModelPattern(model)}
 <path d="M95 88 C83 88 71 79 69 64 C67 49 78 31 98 29 C117 27 131 38 133 57 C135 75 123 88 111 88 Z" fill="url(#${uid}-base)"/>
 ${fluff?`<path d="M66 58 C61 64 61 75 68 81 C74 83 82 82 86 78" fill="${model.base}" opacity=".85"/><path d="M135 58 C141 64 141 75 134 81 C128 83 120 82 116 78" fill="${model.base}" opacity=".85"/>`:''}
 <path d="M69 42 80 ${earY} 90 43Z" fill="url(#${uid}-base)"/><path d="M106 43 118 ${earY} 128 41Z" fill="url(#${uid}-base)"/>
 <path d="M74 40 80 27 86 41Z" fill="${model.ear}" opacity=".92"/><path d="M111 41 118 27 124 40Z" fill="${model.ear}" opacity=".92"/>
 <ellipse cx="87" cy="57" rx="6.6" ry="7.6" fill="url(#${uid}-eye)"/><ellipse cx="109" cy="57" rx="6.6" ry="7.6" fill="url(#${uid}-eye)"/>
 <ellipse cx="87" cy="57" rx="1.8" ry="4.5" fill="#11161c"/><ellipse cx="109" cy="57" rx="1.8" ry="4.5" fill="#11161c"/>
 <ellipse cx="85.5" cy="55.2" rx="1.2" ry="1.2" fill="#fff" opacity=".88"/><ellipse cx="107.5" cy="55.2" rx="1.2" ry="1.2" fill="#fff" opacity=".88"/>
 <path d="M94 65 98 69 102 65" fill="#e899a5"/><path d="M98 69v5" fill="none" stroke="#6f4752" stroke-width="1.7" stroke-linecap="round"/><path d="M92 76c3 3 9 3 12 0" fill="none" stroke="#6f4752" stroke-width="1.9" stroke-linecap="round"/>
 <path d="M84 68c7 3 18 3 26 0" fill="none" stroke="#ffffff26" stroke-width="1.7" stroke-linecap="round"/>
 <g stroke="#eff6ff" stroke-width="1.7" stroke-linecap="round" opacity=".9"><path d="M89 69 67 64"/><path d="M89 74 65 75"/><path d="M107 69 129 64"/><path d="M107 74 131 75"/></g>
 <g fill="url(#${uid}-base)"><ellipse cx="79" cy="126" rx="8" ry="12"/><ellipse cx="95" cy="129" rx="8" ry="12.5"/><ellipse cx="117" cy="129" rx="8" ry="12.5"/><ellipse cx="133" cy="126" rx="8" ry="12"/></g>
 <g fill="#ffffff1f"><ellipse cx="96" cy="104" rx="13" ry="8"/><ellipse cx="118" cy="104" rx="10" ry="7"/></g>
 ${furStroke}
 ${sleek?'<path d="M72 96c12-10 48-10 61 0" fill="none" stroke="#ffffff2a" stroke-width="2"/>':''}
 </svg>`
}

function renderArModelButtons(){
 return AR_CAT_MODELS.map(model=>`<button type="button" class="ar-model-btn ${s.arModelKey===model.key?'selected':''}" data-ar-model="${esc(model.key)}" aria-pressed="${s.arModelKey===model.key?'true':'false'}"><span class="ar-thumb">${renderArCatSvg(model,true)}</span><small>${esc(model.name)}</small></button>`).join('')
}
function guessArModelFromPalette(data){
 const {r,g,b}=data; const spread=Math.max(r,g,b)-Math.min(r,g,b);
 if(r<60&&g<60&&b<60)return 'midnight-panther';
 if(r>170&&g>150&&b<130)return 'ginger-tabby';
 if(r>185&&g>170&&b>145&&Math.abs(r-b)>25)return 'siamese-star';
 if(spread<22&&r>110&&r<190&&b>100)return 'british-cloud';
 if(r>180&&g>175&&b>175)return 'tuxedo-mischief';
 if(r>145&&g>120&&b>95&&spread>45)return 'calico-scout';
 return 'tuxedo-mischief';
}
async function suggestArModelFromImage(image){
 return new Promise(resolve=>{
  const input=new Image();
  input.onload=()=>{
   try{
    const canvas=document.createElement('canvas');canvas.width=24;canvas.height=24;
    const ctx=canvas.getContext('2d',{willReadFrequently:true});
    ctx.drawImage(input,0,0,24,24);
    const pixels=ctx.getImageData(6,6,12,12).data;
    let r=0,g=0,b=0,count=0;
    for(let i=0;i<pixels.length;i+=4){const a=pixels[i+3]; if(a<40)continue; r+=pixels[i]; g+=pixels[i+1]; b+=pixels[i+2]; count++;}
    if(!count)return resolve(randomArModel().key);
    resolve(guessArModelFromPalette({r:r/count,g:g/count,b:b/count}));
   }catch{resolve(randomArModel().key)}
  };
  input.onerror=()=>resolve(randomArModel().key);
  input.src=image;
 })
}
function refreshArEncounterUi(){
 const model=getArModel(s.arModelKey);
 const mount=$('encounter-ar-cat'); if(mount)mount.innerHTML=renderArCatSvg(model);
 const label=$('encounter-ar-label'); if(label)label.textContent=model.name;
 const badge=$('ar-model-badge'); if(badge)badge.textContent=`Virtual cat: ${model.name}`;
 document.querySelectorAll('[data-ar-model]').forEach(btn=>{
  const active=btn.dataset.arModel===s.arModelKey; btn.classList.toggle('selected',active); btn.setAttribute('aria-pressed',String(active));
 });
 if($('encounter-status')&&s.encounterAr&&!s.encounterCaptured){const habitat=getArHabitat(s.arHabitatKey);$('encounter-status').textContent=`A ${model.name} appeared in ${habitat.name}! Drag the paw to catch it.`}
}
const originalOpenModal=openModal;
openModal=function(content,keepLive=false,modalClass=''){
 if(!keepLive)stopLiveCamera();
 encounterResizeObserver?.disconnect();encounterResizeObserver=null;
 const layer=$('modal-layer');layer.classList.remove('hidden');layer.setAttribute('aria-hidden','false');
 layer.innerHTML=`<div class="sheet ${modalClass||''}" role="dialog" aria-modal="true"><div class="sheet-handle"></div><div class="whisker-build-stamp">Hush Hunt v${WHISKER_BUILD} · build ${WHISKER_BUILD_NUMBER}</div>${content}</div>`;
 layer.onclick=modalBackdrop;const b=layer.querySelector('[data-close]');if(b)b.addEventListener('click',closeModal)
};
startCatch=function(catId=null){
 captureShots=[];nativePhotoRequestToken=null;photoSelectionEpoch++;
 if(s.busy)return toast('Please wait for the current save to finish.');
 if(s.storageBlocked)return toast('Restore your Collection backup before adding cats.');
 s.image='';setPendingApproxLocation(null);s.encounterLive=false;s.encounterAr=false;s.arModelManual=false;s.arModelSuggested='';
 s.revisitId=typeof catId==='string'&&s.cats.some(c=>c.id===catId)?catId:'';s.catchMode=s.revisitId?'repeat':'new';s.selectedId='';s.captureSummary=null;
 openModal(`<div class="sheet-head"><h2>Catch a cat! 📸</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim" style="font-size:13px">Start with a respectful real-cat photo, then pick the encounter style that feels best.</p><div class="capture-choice capture-choice-v28"><button id="ar-photo" class="choice choice-ar"><span>✨</span><strong>AR safari</strong><small>Full-screen live camera + stylised cat model prototype</small></button><button id="live-photo" class="choice"><span>🎥</span><strong>Live encounter</strong><small>Drag tools over the live camera</small></button><button id="take-photo" class="choice"><span>📸</span><strong>Take a photo</strong><small>Reliable camera fallback</small></button><button id="pick-photo" class="choice"><span>🖼️</span><strong>Choose a photo</strong><small>From your gallery</small></button></div><p class="footnote center">AR safari keeps only recent still frames locally and overlays a virtual cat on the live view. It is a prototype, not full object-recognition AR.</p>`);
 $('ar-photo').onclick=startArEncounter;
 $('live-photo').onclick=startLiveEncounter;
 $('take-photo').onclick=()=>requestEncounterPhoto(true);
 $('pick-photo').onclick=()=>requestEncounterPhoto(false)
};
async function startCameraEncounter(mode='live'){
 captureShots=[];
 if(s.busy||s.storageBlocked)return toast('Please wait until storage is ready.');
 nativePhotoRequestToken=null;photoSelectionEpoch++;
 s.encounterLive=true; s.encounterAr=mode==='ar'; s.arModelManual=false; s.arModelSuggested='';
 const request=++liveRequestEpoch;stopLiveCamera();
 const title=mode==='ar'?'Starting AR safari…':'Starting live camera…';
 const hint=mode==='ar'?'Preparing a full-screen live view for your virtual cat.':'Requesting camera access. No video is saved or uploaded.';
 openModal(`<div class="sheet-head"><h2>${title}</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim">${hint}</p><div class="live-loading" aria-live="polite">🎥 Preparing preview…</div><div class="actions"><button id="live-fallback" class="secondary">Cancel live camera</button></div>`,false,mode==='ar'?'ar-sheet live-start-sheet':'');
 $('live-fallback').onclick=useNormalCameraFromLiveStartup;
 let stream=null;
 try{
  if(!navigator.mediaDevices?.getUserMedia||!globalThis.isSecureContext)throw Error('Live camera is not available in this WebView or browser context.');
  if(!await requestNativeLivePermission())throw Error('Camera permission was not granted.');
  if(request!==liveRequestEpoch||$('modal-layer')?.classList.contains('hidden'))return;
  const baseConstraints=mode==='ar'?{facingMode:{ideal:'environment'},width:{ideal:640},height:{ideal:360},frameRate:{ideal:16,max:20}}:{facingMode:{ideal:'environment'},width:{ideal:960},height:{ideal:540},frameRate:{ideal:24,max:30}};
  let rearDevices=[], preferredLens=null;
  if(mode==='live'&&navigator.mediaDevices.enumerateDevices){
   try{
    const devices=await navigator.mediaDevices.enumerateDevices();
    rearDevices=devices.filter(device=>device.kind==='videoinput'&&device.deviceId);
    preferredLens=rearDevices.find(device=>/ultra[ -]?wide|0[.,][56]\s?x|wide.?angle|super.?wide/i.test(device.label));
   }catch(error){console.debug('Lens discovery unavailable',error)}
  }
  if(request!==liveRequestEpoch||$('modal-layer')?.classList.contains('hidden'))return;
  if(preferredLens){
   try{stream=await navigator.mediaDevices.getUserMedia({audio:false,video:{...baseConstraints,facingMode:undefined,deviceId:{exact:preferredLens.deviceId}}})}
   catch(error){console.debug('Ultrawide not accessible; using rear camera',error)}
  }
  if(!stream)stream=await navigator.mediaDevices.getUserMedia({audio:false,video:baseConstraints});
  if(request!==liveRequestEpoch||$('modal-layer')?.classList.contains('hidden'))return;
  const video=document.createElement('video');video.autoplay=true;video.muted=true;video.playsInline=true;video.srcObject=stream;
  await Promise.race([video.play(),new Promise((_,reject)=>setTimeout(()=>reject(Error('Camera preview timed out.')),6000))]);
  if(!video.videoWidth||!video.videoHeight)await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('No camera frames received.')),4500);video.addEventListener('loadedmetadata',()=>{clearTimeout(timer);resolve()},{once:true})});
  if(request!==liveRequestEpoch||$('modal-layer')?.classList.contains('hidden'))return;
  const first=frameFromVideo(video,mode==='ar'?360:LIVE_SAMPLE_SIZE,mode==='ar'?.58:.72); if(!first)throw Error('Camera did not provide a usable frame.');
  liveCamera={stream,video,frames:[],timer:null,active:true,sampling:false,dragging:false,rearDevices,lens:preferredLens&&stream.getVideoTracks()[0]?.getSettings?.().deviceId===preferredLens.deviceId?'ultra':'standard',zoomLabel:'1×'}; stream=null;
  if(request!==liveRequestEpoch||!liveCamera?.active)return;
  beginEncounter(first,{live:true,ar:mode==='ar'});
 }catch(error){
  if(request!==liveRequestEpoch)return;
  console.debug('Live camera unavailable',error);
  openModal(`<div class="sheet-head"><h2>${mode==='ar'?'AR Safari unavailable':'Live camera unavailable'}</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim">${esc(error?.message||'Your camera could not be opened.')} Your existing discoveries are safe. A live camera is required for new wildlife catches.</p><div class="actions"><button type="button" id="live-retry" class="primary">🎥 Try live camera again</button></div><p class="footnote">If your camera is unavailable, you can still browse Collection or restore backups. Imported pictures cannot become new catches.</p>`);
  $('live-retry').onclick=()=>startCameraEncounter(mode);
 }finally{ if(stream)for(const track of stream.getTracks())track.stop(); }
}
startLiveEncounter=function(){return startCameraEncounter('live')};
function startArEncounter(){return startCameraEncounter('ar')}
beginEncounter=function(image,options={}){
 captureShots=[]; if(!options.live)stopLiveCamera();
 s.image=image; s.encounterLive=Boolean(options.live); s.encounterAr=Boolean(options.ar); s.encounterTool='ball'; s.encounterLured=false; s.encounterCaptured=false; s.captureSummary=null; s.arModelManual=false;
 if(s.encounterAr){const spawn=randomArModel();const habitat=randomArHabitat();s.arModelKey=spawn.key;s.arHabitatKey=habitat.key;showEncounter(image,{score:0,label:'Live preview',note:'Optimised AR preview.'},options);return;}
 if(options.live){showEncounter(image,{score:0,label:'Live preview',note:'Camera ready'},options);return;}
 assessPhotoQuality(image).then(quality=>{ if(s.image!==image)return; showEncounter(image,quality,options); }).catch(()=>toast('Could not prepare encounter image. Please try another photo.'));
};
showEncounter=function(image,quality,options={}){
 const liveMode=Boolean(options.live||s.encounterLive), arMode=Boolean(options.ar||s.encounterAr);
 s.encounterLive=liveMode; s.encounterAr=arMode; s.encounterFocus={x:.52,y:(arMode ? .69 : .40)}; s.captureSummary={quality,throwRating:null};
 const model=getArModel(s.arModelKey),habitat=getArHabitat(s.arHabitatKey); if(arMode&&habitat)s.encounterFocus={x:habitat.focus.x,y:habitat.focus.y};
 const help=arMode?'✨ Cat found! Drag the claw to catch it.':'① Aim at wildlife · ② Drag the paw · ③ Capture!';
 const summary=arMode?`<div class="encounter-ar-tools"><div class="ar-model-badge" id="ar-model-badge">Wild encounter: ${esc(model.name)}</div><span class="rarity-label">${(model.rarity||'common').replace(/^./,m=>m.toUpperCase())} · ${s.cats.some(c=>c.virtual&&c.arModelHint===model.key)?'Seen before':'New discovery'}</span></div><p class="ar-smart-note">Collect over ${AR_CAT_MODELS.length} cat types across ${AR_HABITATS.length} habitats. Today's visitor is in <strong>${esc(habitat.name)}</strong> · ${esc(habitat.badge)}. Rarer cats appear less often.</p>`:'';
 openModal(`<div class="sheet-head"><h2>${arMode?'AR safari ✨':liveMode?'Live encounter 🎥':'Encounter! 🐾'}</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="encounter-quick-help">${help}</p><details class="encounter-help"><summary>${arMode?'How does AR safari work?':'How do the tools work?'}</summary><p>${arMode?'A virtual creature appears automatically. Drag the paw to catch it. The camera overlay does not yet detect floors or tables; true ARCore surface tracking is planned. No video is saved.':'Tap your subject to place the target. Drag the Whisker Paw onto the target to catch it, or use the Dangle Lure first to make catching easier. Stay at a safe distance from real cats.'}</p></details><div id="encounter-aim-guide" class="encounter-aim-guide hidden" aria-hidden="true"></div><div id="encounter-stage" class="encounter-stage ${arMode?'encounter-stage-ar':''}"><img id="encounter-photo" class="encounter-backdrop" src="${image}" alt="${arMode?'Live encounter backdrop':'Your selected wildlife photo'}"><div class="encounter-vignette"></div><div id="encounter-cat" class="encounter-cat ${arMode?'ar-model-target':''}"><div class="encounter-cat-ring"></div>${arMode?`<div id="encounter-ar-cat" class="encounter-ar-cat">${renderArCatSvg(model)}</div><span id="encounter-ar-label">${esc(model.name)}</span>`:`<img id="encounter-cat-crop" src="${image}" alt="Selected wildlife photo crop"><span>Your wildlife target</span>`}</div><div class="encounter-capture-tag">${arMode?'● VIRTUAL CREATURE · BETA':'Capture preview'}</div><div class="encounter-tool-dock" aria-label="Capture tools"><button type="button" id="tool-ball" class="dock-tool selected" aria-pressed="true" title="Whisker Paw"><span>🐾</span><small>Paw</small></button><button type="button" id="tool-lure" class="dock-tool" aria-label="Switch to Lure" aria-pressed="false" title="Switch to Lure"><span>🪶</span><small>Lure</small></button><div id="throw-item" class="throw-item throw-ball" role="button" aria-label="Drag ${encounterToolLabel('ball')} to the cat" tabindex="0"><svg class="whisker-paw-svg" viewBox="0 0 100 110" aria-hidden="true" focusable="false"><defs><linearGradient id="whisker-paw-shine" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffe5f3"/><stop offset=".4" stop-color="#fb80b7"/><stop offset="1" stop-color="#8553d8"/></linearGradient></defs><g class="paw-digits"><ellipse cx="19" cy="34" rx="11" ry="15" transform="rotate(-23 19 34)"/><ellipse cx="40" cy="20" rx="11" ry="16" transform="rotate(-9 40 20)"/><ellipse cx="62" cy="19" rx="11" ry="16" transform="rotate(9 62 19)"/><ellipse cx="82" cy="32" rx="10" ry="15" transform="rotate(24 82 32)"/></g><path class="paw-center" d="M51 47 C65 45 71 55 80 65 C90 78 84 94 71 98 C62 101 57 95 51 95 C43 95 37 102 27 98 C12 95 10 79 20 66 C29 53 35 46 51 47Z"/><path class="paw-detail" d="M33 77 Q42 69 50 75 Q58 69 68 77"/></svg><span class="throw-stick">🎣</span><span class="throw-lure-body">🧶</span><span class="drag-prompt">DRAG</span></div></div><div id="encounter-orb" class="encounter-orb hidden"><svg class="whisker-paw-svg capture-paw" viewBox="0 0 100 110" aria-hidden="true" focusable="false"><defs><linearGradient id="whisker-paw-shine-captured" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffe5f3"/><stop offset=".4" stop-color="#fb80b7"/><stop offset="1" stop-color="#8553d8"/></linearGradient></defs><g class="paw-digits"><ellipse cx="19" cy="34" rx="11" ry="15" transform="rotate(-23 19 34)"/><ellipse cx="40" cy="20" rx="11" ry="16" transform="rotate(-9 40 20)"/><ellipse cx="62" cy="19" rx="11" ry="16" transform="rotate(9 62 19)"/><ellipse cx="82" cy="32" rx="10" ry="15" transform="rotate(24 82 32)"/></g><path class="paw-center" d="M51 47 C65 45 71 55 80 65 C90 78 84 94 71 98 C62 101 57 95 51 95 C43 95 37 102 27 98 C12 95 10 79 20 66 C29 53 35 46 51 47Z"/><path class="paw-detail" d="M33 77 Q42 69 50 75 Q58 69 68 77"/></svg></div><div id="encounter-status" class="encounter-status" role="status" aria-live="polite">${arMode?`A ${esc(model.name)} appeared in ${esc(habitat.name)}! Drag the paw onto it to catch it.`:'Tap the animal to move the target. Then drag an item from the tool dock on the right.'}</div><div id="encounter-meow" class="encounter-meow hidden" aria-hidden="true">${arMode?'Meow!':'Nice shot!'}</div></div><div id="encounter-quality" class="encounter-quality">${arMode?'⚡ Smooth AR mode · Lower-latency camera preview · No video saved or uploaded.':liveMode?'🎥 Live preview · <span id="live-frame-count">1 recent frame</span> · Live burst samples recent frames during your throw and picks the clearest one near your target when you capture.':'Photo clarity estimate: <strong>'+esc(quality.label)+'</strong> · '+esc(quality.note)} <small>${arMode?'Auto habitat placement on screen. Native world-tracked AR is a future upgrade.':'No video recording or upload.'}</small></div>${summary}<div id="encounter-shots" class="encounter-shots hidden" aria-label="Choose best frame"></div>${arMode?'':`<div class="encounter-photo-actions"><button type="button" id="encounter-retake" class="secondary">${liveMode?'🎥 Retake live capture':'📸 Retake photo'}</button><button type="button" id="encounter-replace" class="secondary">🖼️ Choose another</button></div>`}<div class="encounter-launch"><div class="encounter-instructions">${arMode?`Look around gently. ${esc(model.name)} has appeared in ${esc(habitat.name)} — no tapping needed.`:'Drag the paw from the right. A green ring means your throw is on target.'}</div></div><div class="actions">${arMode?'':'<button id="encounter-skip" class="secondary">Save photo without game</button>'}<button id="encounter-continue" class="primary hidden">${arMode?'Keep this creature ✨':'Continue to Collection →'}</button></div><p class="footnote">${arMode?'Virtual creature preview: automatic placement in a themed habitat with lighter camera settings for smoother play. Full world tracking needs native ARCore.':'Live camera is local to your device; only the selected still is saved. No automatic species recognition.'} Stay a safe distance from real cats.</p>`,liveMode,arMode?'ar-sheet':'');
 if(liveMode&&liveCamera?.active){
  const stage=$('encounter-stage'),video=liveCamera.video;
  video.id='encounter-video';video.className='encounter-backdrop encounter-live-video'; stage.prepend(video);stage.classList.add('live-encounter');
  const tag=stage.querySelector('.encounter-capture-tag');if(tag)tag.textContent=arMode?'● 2D · VIRTUAL PREVIEW':'● LIVE · private';
  const crop=$('encounter-cat-crop');if(crop)crop.style.display='none';
  const status=$('encounter-status');if(status&& !arMode)status.textContent='Tap your subject to place the target, then drag a tool from the right.';
  if(!arMode)scheduleLiveSampling(liveCamera);
 }
 const selectTool=kind=>{if(s.encounterCaptured)return; s.encounterTool=kind; $('tool-ball').classList.toggle('selected',kind==='ball');$('tool-lure').classList.toggle('selected',kind==='lure'); $('tool-ball').setAttribute('aria-pressed',String(kind==='ball'));$('tool-lure').setAttribute('aria-pressed',String(kind==='lure')); const item=$('throw-item'); item.classList.toggle('throw-ball',kind==='ball');item.classList.toggle('throw-lure',kind==='lure'); item.setAttribute('aria-label','Drag '+encounterToolLabel(kind)+' to the cat'); $('encounter-status').textContent=kind==='lure'?'Aim the Dangle Lure at the cat to enlarge the target.':'Drag the Whisker Paw onto the target for a capture!';};
 $('tool-ball').onclick=()=>selectTool('ball');$('tool-lure').onclick=()=>selectTool('lure');
 if(!arMode)$('encounter-skip').onclick=async()=>{if(liveCamera)await freezeLiveEncounter();s.captureSummary=null;showCatForm(s.image)};
 $('encounter-continue').onclick=()=>arMode?showVirtualNamingForm():showCatForm(s.image);
 if(!arMode){$('encounter-retake').onclick=()=>s.encounterLive?(s.encounterAr?startArEncounter():startLiveEncounter()):requestEncounterPhoto(true);
 $('encounter-replace').onclick=()=>{s.encounterLive=false;s.encounterAr=false;requestEncounterPhoto(false)};}
 const stage=$('encounter-stage'),backdrop=$('encounter-photo'); [stage,$('encounter-status'),$('encounter-quality'),$('encounter-meow'),$('tool-ball'),$('tool-lure'),$('throw-item')].filter(Boolean).forEach(el=>{el.oncontextmenu=e=>e.preventDefault();el.onselectstart=e=>e.preventDefault();el.ondragstart=()=>false;});
 if(!arMode)stage.addEventListener('click',event=>{ const visual=$('encounter-video')||backdrop; if(s.encounterCaptured||!(event.target===stage||event.target===backdrop||event.target===visual))return; const point=encounterImagePoint(event.clientX,event.clientY,visual,visual.getBoundingClientRect()); if(point)setEncounterFocus(point.x,point.y); });
 backdrop.addEventListener('load',()=>positionEncounterFocus()); encounterResizeObserver?.disconnect(); encounterResizeObserver=typeof ResizeObserver==='function'?new ResizeObserver(()=>positionEncounterFocus()):null; encounterResizeObserver?.observe(stage); setEncounterFocus(s.encounterFocus.x,s.encounterFocus.y,false); setupEncounterDrag(); if(arMode)requestAnimationFrame(()=>$('encounter-cat')?.classList.add('ar-autospawn'));
 if(arMode){
  document.querySelectorAll('[data-ar-model]').forEach(btn=>btn.addEventListener('click',()=>{s.arModelManual=true;s.arModelKey=btn.dataset.arModel;refreshArEncounterUi()}));
  $('ar-reroll')?.addEventListener('click',()=>{s.arModelManual=true;s.arModelKey=randomArModel(s.arModelKey).key;refreshArEncounterUi()});
  refreshArEncounterUi();
  // No scene colour matching: a room's wall/furniture is not evidence of a cat or surface.
 }
};
const originalShowCatForm=showCatForm;
showCatForm=function(image){ originalShowCatForm(image); if(!s.encounterAr)return; const model=getArModel(s.arModelKey); const note=document.createElement('div'); note.className='info-note'; note.innerHTML=`<strong>AR safari prototype:</strong> Saved frame captured with the virtual <strong>${esc(model.name)}</strong> model. You can still describe the <em>real</em> cat you actually saw below.`; const extra=$('possible-matches'); extra?.parentNode?.insertBefore(note,extra); const coat=$('cat-coat'); if(coat && [...coat.options].some(o=>o.value===model.coat)) coat.value=model.coat; };
saveCatch=function(){return (async()=>{
 if(s.busy)return;if(!$('real-cat')?.checked)return toast('Please confirm this is a respectful real-cat encounter.');
 if(!s.db)return toast('Device storage is not ready.');
 const mode=s.catchMode,sig=photoSignature(s.image);let cat;
 if(s.cats.some(c=>c.signature===sig||(c.sightings||[]).some(v=>v.signature===sig)))
  return toast('This photo is already collected. Use a fresh photo for a new sighting.');
 if(mode==='new'){
  const name=$('cat-name')?.value.trim();if(!name)return toast('Please give your cat a name.');
  cat={id:id(),visualHash:null,name:name.slice(0,36),coat:$('cat-coat').value,personality:$('cat-personality').value,note:$('cat-note').value.trim(),photo:s.image,signature:sig,createdAt:new Date().toISOString(),fav:false,arModelHint:s.encounterAr?s.arModelKey:null,sightings:[]};
 }else{ cat=s.cats.find(c=>c.id===$('repeat-cat')?.value);if(!cat)return toast('Choose a cat from your Collection.'); }
 const btn=$('save-catch');s.busy=true;btn.disabled=true;btn.textContent='Saving your discovery…';
 let appended=false,added=false,earned=0;
 try{
  const hash=await visualFingerprint(s.image).catch(()=>null); if(mode==='new')cat.visualHash=hash;
  const wantsPin=$('pin-check').checked;
  const loc=wantsPin?(hasFreshApproxLocation()?s.pendingApproxLocation:await ensureApproxLocation('pin')):null;
  if(wantsPin&&!isUsableLocation(loc))throw new Error('PIN_NOT_SAVED');
  const note=mode==='new'?cat.note:$('repeat-note')?.value.trim();
  const now=Date.now(); const lastSeen=Math.max(0,...(cat.sightings||[]).map(v=>Date.parse(v.at)).filter(t=>Number.isFinite(t)&&t<=now));
  const cooldown=mode==='repeat'&&lastSeen>0&&(now-lastSeen<3600000); const firstOfCoat=mode==='new'&&(cat.species||'Cat')==='Cat'&&!s.cats.some(c=>(c.species||'Cat')==='Cat'&&c.coat===cat.coat); earned=(mode==='new'?100:cooldown?0:30)+(firstOfCoat?25:0);
  cat.sightings.push({id:id(),visualHash:hash,at:new Date().toISOString(),note,photo:mode==='new'?null:s.image,signature:sig,lat:loc&&Number.isFinite(loc.lat)&&Math.abs(loc.lat)<=90?loc.lat:null,lng:loc&&Number.isFinite(loc.lng)&&Math.abs(loc.lng)<=180?loc.lng:null,captureMode:s.encounterAr?'ar-live':s.encounterLive?'live':'photo',arModel:s.encounterAr?s.arModelKey:null}); appended=true;
  if(mode==='new'){s.cats.push(cat);added=true}
  s.profile.xp+=earned; await persistCatchAtomic(cat);
  closeModal();navigate('dex');toast(`${mode==='new'?'🐱 New cat added!':'🐾 Reunited with '+cat.name+'!'} +${earned} XP${wantsPin?' · 📍 Private map pin saved':''}`);
 }catch(e){ console.error(e);s.profile.xp-=earned;if(appended)cat.sightings.pop();if(added)s.cats=s.cats.filter(c=>c.id!==cat.id);if(e?.message==='PIN_NOT_SAVED')showPinFailure('pin');else toast('Save failed. Please try again.');btn.disabled=false;btn.textContent='Add to my Collection →'; }
 finally{s.busy=false}
 })()};


/* v3.1: 120 collectible virtual cats across many breeds, coat mixes and habitats. */
const AR_BREED_ARCHETYPES=[
 {slug:'american-shorthair',name:'American Shorthair',coat:'Tabby',base:'#ae8b6d',belly:'#ead5bc',accent:'#7d5a45',ear:'#e1b3a4',eye:'#95e486',pattern:'tabby',fur:'short'},
 {slug:'british-shorthair',name:'British Shorthair',coat:'Grey',base:'#8f9eb6',belly:'#d3dbea',accent:'#657896',ear:'#d6b9c4',eye:'#f4da76',pattern:'cloud',fur:'short'},
 {slug:'maine-coon',name:'Maine Coon',coat:'Tabby',base:'#967050',belly:'#dfc1a7',accent:'#6b452d',ear:'#d3a18f',eye:'#dfc66a',pattern:'tabby',fur:'long'},
 {slug:'ragdoll',name:'Ragdoll',coat:'White',base:'#ece5da',belly:'#fffdf8',accent:'#7d6b62',ear:'#ddbac0',eye:'#79c8ff',pattern:'siamese',fur:'long'},
 {slug:'bengal',name:'Bengal',coat:'Ginger',base:'#c68543',belly:'#efc48f',accent:'#724424',ear:'#d59d84',eye:'#97e46c',pattern:'tabby',fur:'short'},
 {slug:'persian',name:'Persian',coat:'White',base:'#f2ece5',belly:'#fffefa',accent:'#bfb0a4',ear:'#ecbcc7',eye:'#89d6b5',pattern:'cloud',fur:'long'},
 {slug:'scottish-fold',name:'Scottish Fold',coat:'Grey',base:'#9d9aa0',belly:'#d0c9cf',accent:'#6d6873',ear:'#ccaab2',eye:'#a8ef79',pattern:'cloud',fur:'short'},
 {slug:'russian-blue',name:'Russian Blue',coat:'Grey',base:'#6f88a1',belly:'#aec0d0',accent:'#516983',ear:'#c6a0aa',eye:'#79d0c2',pattern:'solid',fur:'sleek'},
 {slug:'norwegian-forest',name:'Norwegian Forest',coat:'Tabby',base:'#a48a71',belly:'#dbc7b3',accent:'#735b47',ear:'#d4a199',eye:'#a8d987',pattern:'tabby',fur:'long'},
 {slug:'siberian',name:'Siberian',coat:'Tabby',base:'#8f715e',belly:'#d7bfaf',accent:'#6f5346',ear:'#d5a49f',eye:'#93dda1',pattern:'tabby',fur:'long'},
 {slug:'sphynx',name:'Sphynx',coat:'Other',base:'#d5ac99',belly:'#edc5b5',accent:'#a57a69',ear:'#cb8f90',eye:'#7ac8f8',pattern:'solid',fur:'hairless'},
 {slug:'oriental-shorthair',name:'Oriental Shorthair',coat:'Other',base:'#a89f93',belly:'#dfd7cd',accent:'#746c62',ear:'#c5a4ad',eye:'#8ae1ad',pattern:'solid',fur:'sleek'},
 {slug:'bombay',name:'Bombay',coat:'Black',base:'#171a22',belly:'#40414b',accent:'#62626e',ear:'#a67f89',eye:'#f1cc6e',pattern:'solid',fur:'sleek'},
 {slug:'abyssinian',name:'Abyssinian',coat:'Ginger',base:'#b6774b',belly:'#ddab7b',accent:'#8b4d31',ear:'#d9a284',eye:'#abd878',pattern:'solid',fur:'short'},
 {slug:'birman',name:'Birman',coat:'White',base:'#f1e3d0',belly:'#fff8ee',accent:'#776559',ear:'#caa099',eye:'#74c9fb',pattern:'siamese',fur:'long'}
];
const AR_COAT_VARIANTS=[
 {slug:'ginger-tabby',label:'Ginger Tabby',coat:'Ginger',base:'#da8a41',belly:'#f7d1a9',accent:'#8f4d23',ear:'#f0bba1',eye:'#7ee17d',pattern:'tabby'},
 {slug:'silver-tabby',label:'Silver Tabby',coat:'Grey',base:'#b8bbc2',belly:'#eef0f4',accent:'#737885',ear:'#d6bbc4',eye:'#8ad4ff',pattern:'tabby'},
 {slug:'tuxedo',label:'Tuxedo',coat:'Tuxedo',base:'#20242d',belly:'#f6f7fa',accent:'#4a5160',ear:'#f2bcc7',eye:'#80efb7',pattern:'tuxedo'},
 {slug:'calico',label:'Calico',coat:'Calico',base:'#f5efe8',belly:'#fff9f2',accent:'#e2873d',accent2:'#3b3232',ear:'#efb8b0',eye:'#70d8b7',pattern:'calico'},
 {slug:'cream-point',label:'Cream Point',coat:'White',base:'#f4dfc2',belly:'#fff5e8',accent:'#7b5a46',ear:'#e0b6af',eye:'#7dd8ff',pattern:'siamese'},
 {slug:'blue-smoke',label:'Blue Smoke',coat:'Grey',base:'#8894aa',belly:'#c7d0de',accent:'#5c6780',ear:'#cfafba',eye:'#f0d36b',pattern:'cloud'},
 {slug:'chocolate',label:'Chocolate',coat:'Other',base:'#8d5f49',belly:'#d6b69b',accent:'#633d2f',ear:'#c99d93',eye:'#8ee3a3',pattern:'solid'},
 {slug:'golden-white',label:'Golden White',coat:'White',base:'#ead6b2',belly:'#fff7ea',accent:'#a7804d',ear:'#e1b9b0',eye:'#9cde8d',pattern:'cloud'}
];
const AR_HABITATS=[
 {key:'window-perch',name:'Window perch',focus:{x:.72,y:.40},badge:'Sunbeams'},
 {key:'bookshelf-nook',name:'Bookshelf nook',focus:{x:.68,y:.36},badge:'Quiet nook'},
 {key:'sofa-arm',name:'Sofa arm',focus:{x:.62,y:.58},badge:'Living room'},
 {key:'kitchen-chair',name:'Kitchen chair',focus:{x:.58,y:.64},badge:'Kitchen'},
 {key:'desk-corner',name:'Desk corner',focus:{x:.68,y:.61},badge:'Home office'},
 {key:'hallway-run',name:'Hallway run',focus:{x:.50,y:.70},badge:'Hallway'},
 {key:'stair-landing',name:'Stair landing',focus:{x:.56,y:.52},badge:'Stairs'},
 {key:'balcony-rail',name:'Balcony rail',focus:{x:.70,y:.49},badge:'Balcony'},
 {key:'garden-path',name:'Garden path',focus:{x:.50,y:.74},badge:'Garden'},
 {key:'bedroom-rug',name:'Bedroom rug',focus:{x:.54,y:.70},badge:'Bedroom'},
 {key:'laundry-basket',name:'Laundry basket',focus:{x:.44,y:.68},badge:'Laundry'},
 {key:'patio-pot',name:'Patio flower pot',focus:{x:.66,y:.66},badge:'Patio'}
];
function hexMix(a,b,t=.5){const pa=parseInt(a.slice(1),16),pb=parseInt(b.slice(1),16);const ar=(pa>>16)&255,ag=(pa>>8)&255,ab=pa&255,br=(pb>>16)&255,bg=(pb>>8)&255,bb=pb&255;const mix=v=>Math.max(0,Math.min(255,Math.round(v)));return '#'+[mix(ar+(br-ar)*t),mix(ag+(bg-ag)*t),mix(ab+(bb-ab)*t)].map(v=>v.toString(16).padStart(2,'0')).join('')}
function shiftHex(hex,delta=0){const p=parseInt(hex.slice(1),16),r=((p>>16)&255)+delta,g=((p>>8)&255)+delta,b=(p&255)+delta;return '#'+[r,g,b].map(v=>Math.max(0,Math.min(255,Math.round(v))).toString(16).padStart(2,'0')).join('')}
function slugifyText(text){return String(text||'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/(^-|-$)/g,'')}
function buildArCatalog(){const rarityCycle=['common','common','common','uncommon','uncommon','rare','rare','epic','legendary'];const out=[];for(const breed of AR_BREED_ARCHETYPES){for(const coat of AR_COAT_VARIANTS){const key=`${breed.slug}-${coat.slug}`;out.push({key,name:`${coat.label} ${breed.name}`,breed:breed.name,coat:coat.coat,base:hexMix(breed.base,coat.base,.55),belly:hexMix(breed.belly,coat.belly,.5),accent:hexMix(breed.accent,coat.accent,.55),accent2:coat.accent2||shiftHex(coat.accent,-26),ear:hexMix(breed.ear,coat.ear,.5),eye:coat.eye||breed.eye,pattern:coat.pattern||breed.pattern,fur:breed.fur,rarity:rarityCycle[out.length%rarityCycle.length]})}}return out.slice(0,128)}
AR_CAT_MODELS.splice(0,AR_CAT_MODELS.length,...buildArCatalog())
s.arHabitatKey='window-perch';
function getArHabitat(key){return AR_HABITATS.find(h=>h.key===key)||AR_HABITATS[0]}
function discoveredHabitatKeys(){return new Set(s.cats.filter(c=>c.virtual).flatMap(c=>(c.sightings||[]).map(x=>x.habitat).filter(Boolean)))}
function randomArHabitat(except=''){const discovered=discoveredHabitatKeys();const missing=AR_HABITATS.filter(h=>!discovered.has(h.key)&&h.key!==except);const pool=missing.length?missing:AR_HABITATS.filter(h=>h.key!==except);return pool[Math.floor(Math.random()*pool.length)]||AR_HABITATS[0]}
function renderVirtualGallery(){
 const virtual=s.cats.filter(c=>c.virtual);
 const habitatCount=discoveredHabitatKeys().size;
 return `<section class="virtual-gallery"><div class="section-title"><div><div class="eyebrow">VIRTUAL FRIENDS</div><h3>My AR cats 🐾</h3></div><span class="pill purple">${virtual.length} / ${AR_CAT_MODELS.length} cats</span></div><div class="info-note" style="margin-bottom:12px"><strong>Safari progress:</strong> ${virtual.length} cats discovered · ${habitatCount} / ${AR_HABITATS.length} habitats visited. Over ${AR_CAT_MODELS.length} cats are available, and rarer cats appear less often.</div>${virtual.length?`<div class="ar-collected-list">${virtual.map(c=>{const last=(c.sightings||[]).at(-1)||{};const habitat=last.habitat?getArHabitat(last.habitat).name:'Mystery habitat';return `<button type="button" class="ar-collected" data-cat="${esc(c.id)}"><img src="${c.photo}" alt="${esc(c.name)}"><span>${esc(c.name)}</span><small>${c.sightings.length} catches · ${esc(habitat)} · ${(getArModel(c.arModelHint).rarity||'common').replace(/^./,m=>m.toUpperCase())}</small></button>`}).join('')}</div>`:`<p class="dim">Your virtual friends will appear here. Open AR Safari to meet a new cat in a new habitat!</p>`}</section>`;
}
// Browser/MAUI asset path: the generated image is a PNG data URI, compatible
// with Whisker Hunt's v1 JSON validation and old backup readers.
function makeVirtualCover(model){
 return new Promise((resolve,reject)=>{
  const canvas=document.createElement('canvas');canvas.width=480;canvas.height=480;
  const ctx=canvas.getContext('2d');
  const gradient=ctx.createLinearGradient(0,0,480,480);gradient.addColorStop(0,'#2f3c66');gradient.addColorStop(1,'#191f36');ctx.fillStyle=gradient;ctx.fillRect(0,0,480,480);
  const svg=renderArCatSvg(model).replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ');
  const img=new Image();const svgUrl='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);
  img.onload=()=>{
   try{ctx.drawImage(img,45,36,390,330);ctx.fillStyle='#ffffff';ctx.font='bold 23px sans-serif';ctx.textAlign='center';ctx.fillText(model.name,240,408);ctx.font='16px sans-serif';ctx.fillStyle='#b4ffeb';ctx.fillText('VIRTUAL • HUSH HUNT',240,442);resolve(canvas.toDataURL('image/png'));}
   catch(e){reject(e)}
  };
  img.onerror=()=>reject(new Error('Unable to create virtual cat card'));
  img.src=svgUrl;
 });
}
async function saveVirtualArCatch(){
 if(s.busy||s.storageBlocked||!s.db||!s.encounterCaptured)return;
 const key=s.arModelKey,model=getArModel(key),habitat=getArHabitat(s.arHabitatKey);
 const existing=s.cats.find(c=>c.virtual===true&&c.arModelHint===key);
 const btn=$('encounter-continue')||$('virtual-save-final');if(btn){btn.disabled=true;btn.textContent=`Keeping your ${(model.species||'cat').toLowerCase()}…`}
 s.busy=true;let cat,added=false,appended=false;
 try{
  if(existing){cat=existing;}else{
   const photo=await makeVirtualScenePhoto(model,s.image,s.encounterFocus,habitat);
   cat={id:id(),name:($('virtual-name')?.value.trim()||model.name).slice(0,36),species:model.species||'Cat',speciesDetail:model.speciesDetail||'',coat:model.coat,personality:'Playful',note:($('virtual-memory')?.value.trim()||'A magical encounter!').slice(0,140),photo,signature:photoSignature(photo),createdAt:new Date().toISOString(),fav:false,virtual:true,arModelHint:key,arHabitatHint:habitat.key,visualHash:null,sightings:[]};
   s.cats.push(cat);added=true;
  }
  const memory=($('virtual-memory')?.value.trim()||'A magical encounter!').slice(0,140);
  const wantsPin=$('virtual-pin')?.checked;
  const pin=wantsPin?(hasFreshApproxLocation()?s.pendingApproxLocation:await ensureApproxLocation('virtual-pin')):null;
  if(wantsPin&&!isUsableLocation(pin))throw new Error('PIN_NOT_SAVED');
  const lat=pin&&Number.isFinite(pin.lat)?Math.round(pin.lat*100)/100:null;
  const lng=pin&&Number.isFinite(pin.lng)?Math.round(pin.lng*100)/100:null;
  const sightingPhoto=existing?await makeVirtualScenePhoto(model,s.image,s.encounterFocus,habitat):null;
  cat.arHabitatHint=habitat.key;
  cat.sightings.push({id:id(),at:new Date().toISOString(),note:memory,photo:sightingPhoto,lat,lng,captureMode:'ar-virtual',arModel:key,habitat:habitat.key});appended=true;
  await persistCatchAtomic(cat);setPendingApproxLocation(null);
  closeModal();navigate('dex');toast(`${speciesIcon(model.species||'Cat')} ${model.name} explored your ${habitat.name.toLowerCase()}!${wantsPin?' 📍 Private map pin saved':''}`);
 }catch(e){console.error(e);if(appended)cat?.sightings.pop();if(added)s.cats=s.cats.filter(c=>c.id!==cat.id);if(e?.message==='PIN_NOT_SAVED')showPinFailure('virtual-pin');else toast('Could not save this virtual discovery. Try again.');if(btn){btn.disabled=false;btn.textContent='Try saving again'}}
 finally{s.busy=false}
}


function openVirtualCatDetail(cat){
 const model=getArModel(cat.arModelHint);
 openModal(`<div class="sheet-head"><h2>${esc(cat.name)} 🐾</h2><button class="close-btn" data-close aria-label="Close">×</button></div><img class="detail-cover" src="${cat.photo}" alt="${esc(cat.name)}"><div class="info-note"><strong>Virtual friend</strong> · Collected ${cat.sightings.length} time${cat.sightings.length===1?'':'s'}. This is a game character, not a photograph of a real animal.</div><div class="actions"><button type="button" class="primary" id="virtual-find-more">✨ Find another virtual cat</button><button type="button" class="secondary" id="virtual-close">Back to Collection</button></div><button type="button" class="text-btn red" id="virtual-delete" style="margin:15px auto;display:block">Delete virtual cat</button>`);
 $('virtual-find-more').onclick=startArEncounter;
 $('virtual-close').onclick=()=>navigate('dex');
 $('virtual-delete').onclick=()=>deleteCat(cat);
}
// Count real cats in the real-world home and profile statistics. Virtual cats
// remain visible in their own separate Collection gallery.
const originalRenderHome=renderHome;
renderHome=function(){const all=s.cats;try{s.cats=all.filter(c=>!c.virtual);return originalRenderHome()}finally{s.cats=all}};
const originalRenderProfile=renderProfile;
renderProfile=function(){const all=s.cats;try{s.cats=all.filter(c=>!c.virtual);return originalRenderProfile()}finally{s.cats=all}};



/* v3.0 quality-of-life: generated names/memories, batch camera, AR photo, backup access */
const WHISKER_NAMES=['Mochi','Biscuit','Pebbles','Pumpkin','Miso','Clover','Pickles','Noodle','Pudding','Maple','Mittens','Waffles','Tango','Sprout','Cinnamon','Poppy','Nimbus','Coco','Beans','Pixel','Socks','Toffee','Muffin','Fudge','Luna','Nova','Pip','Snowball','Marbles','Jellybean'];
const WHISKER_MEMORIES=[
 'A little whiskered explorer made today feel magical.',
 'A curious face appeared at just the right moment!',
 'Found a fluffy new friend on our adventure.',
 'Tiny paws, big personality — what a lovely discovery!',
 'Our surprise visitor brightened the whole day.',
 'The cat looked around as if it owned the whole world.',
 'A sweet little moment I want to remember forever.',
 'A playful encounter full of whiskers and wonder.',
 'This curious kitty made our walk much more fun.',
 'Found a new friend with the most expressive eyes.'
];
const randomFrom=list=>list[Math.floor(Math.random()*list.length)];
const rollWhiskerName=()=>randomFrom(WHISKER_NAMES);
const rollWhiskerMemory=()=>randomFrom(WHISKER_MEMORIES);
function addDiceButton(id,buttonId,label){
 const el=$(id);if(!el||$(buttonId))return;
 const wrapper=document.createElement('div');wrapper.className='dice-field';el.parentNode.insertBefore(wrapper,el);wrapper.append(el);
 const button=document.createElement('button');button.type='button';button.id=buttonId;button.className='dice-button';button.textContent='🎲';button.title='Suggest a '+label;button.setAttribute('aria-label','Generate random '+label);button.onclick=()=>{el.value=label==='name'?rollWhiskerName():rollWhiskerMemory();el.dispatchEvent(new Event('input',{bubbles:true}))};wrapper.append(button);
}
const originalRealFormV30=showCatForm;
showCatForm=function(photo){originalRealFormV30(photo);addDiceButton('cat-name','dice-name','name');addDiceButton('cat-note','dice-memory','memory');const checkbox=$('pin-check');if(checkbox){checkbox.checked=false;const description=checkbox.closest('label')?.querySelector('span');if(description)description.textContent='📍 Add a private map pin for this sighting? (optional; safe and private)';}wireLocationOptIn('pin','pin-check')}
let multiPhotos=[],multiPhotoActive=false,multiSelected=0;
function startMultiPhotoCapture(){multiPhotos=[];multiSelected=0;multiPhotoActive=true;requestEncounterPhoto(true)}
function deliverPhoto(image){
 if(!multiPhotoActive){beginEncounter(image);return}
 if(multiPhotos.length>=6){toast('Six photos is the limit. Delete one or tap Done.');showMultiPhotoReview();return}
 multiPhotos.push(image);multiSelected=multiPhotos.length-1;showMultiPhotoReview();
}
function showMultiPhotoReview(){
 if(!multiPhotos.length){openModal(`<div class="sheet-head"><h2>Take cat photos 📸</h2><button class="close-btn" data-close>×</button></div><p class="dim">Take several photos, then choose the clearest one.</p><button type="button" class="primary" id="batch-first">Take photo</button>`);$('batch-first').onclick=()=>requestEncounterPhoto(true);return}
 openModal(`<div class="sheet-head"><h2>Choose your best shot 📸</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim">${multiPhotos.length} of 6 photos · Tap a thumbnail to preview. Delete any blurry ones.</p><img id="batch-cover" class="photo-preview batch-main" src="${multiPhotos[multiSelected]}" alt="Selected photo"><div class="batch-thumbs">${multiPhotos.map((photo,i)=>`<button type="button" class="batch-thumb ${multiSelected===i?'selected':''}" data-batch="${i}" aria-label="View photo ${i+1}"><img src="${photo}" alt="Photo ${i+1}"><span>${i+1}</span></button>`).join('')}</div><div class="actions"><button type="button" class="secondary" id="batch-delete">🗑 Delete selected</button><button type="button" class="secondary" id="batch-add" ${multiPhotos.length>=6?'disabled':''}>📸 Take another</button></div><div class="actions"><button type="button" class="primary" id="batch-done">Done · Use this photo →</button></div><p class="footnote">Only the selected photo is sent to the catch screen. Unused photos are discarded.</p>`);
 document.querySelectorAll('[data-batch]').forEach(b=>b.onclick=()=>{multiSelected=Number(b.dataset.batch);showMultiPhotoReview()});
 $('batch-delete').onclick=()=>{multiPhotos.splice(multiSelected,1);multiSelected=Math.max(0,Math.min(multiSelected,multiPhotos.length-1));showMultiPhotoReview()};
 $('batch-add').onclick=()=>requestEncounterPhoto(true);
 $('batch-done').onclick=()=>{const image=multiPhotos[multiSelected];if(!image)return;multiPhotoActive=false;multiPhotos=[];beginEncounter(image)};
}
const originalCloseModalV30=closeModal;
closeModal=function(){multiPhotoActive=false;multiPhotos=[];originalCloseModalV30()};
function showVirtualNamingForm(){
 if(!s.encounterCaptured)return;
 const model=getArModel(s.arModelKey),habitat=getArHabitat(s.arHabitatKey),existing=s.cats.find(c=>c.virtual&&c.arModelHint===model.key);
 const proposed=existing?.name||rollWhiskerName();const memo=rollWhiskerMemory();
 openModal(`<div class="sheet-head"><h2>${existing?'You met again!':'A new virtual friend!'} 🐾</h2><button class="close-btn" data-close aria-label="Close">×</button></div><div class="virtual-photo-preview" id="virtual-photo-preview">Preparing your AR photo…</div><p class="dim" style="font-size:12px">${esc(model.name)} · ${esc(habitat.name)} · ${existing?'Already in your collection':'New discovery'} · Rename it or use the dice.</p><div class="field-group"><label for="virtual-name">Cat name</label><input id="virtual-name" class="field" maxlength="36" value="${esc(proposed)}" ${existing?'readonly':''}></div><div class="field-group"><label for="virtual-memory">Little memory</label><textarea id="virtual-memory" class="field" maxlength="140" rows="3">${esc(memo)}</textarea></div><label class="check-row"><input type="checkbox" id="virtual-pin"><span>📍 Save an approximate private area on my map (optional)</span></label><p id="virtual-pin-failure" class="pin-failure hidden" role="alert"></p><div id="virtual-pin-helper" class="location-helper hidden" aria-hidden="true"><p id="virtual-pin-helper-note">Your app permission and the phone Location switch must both allow location. Only an approximate area is kept on this device.</p><div class="location-helper-actions"><button type="button" id="virtual-pin-allow" class="secondary">Allow location</button><button type="button" id="virtual-pin-settings" class="secondary">Open app settings</button><button type="button" id="virtual-pin-device-location" class="text-btn">Phone Location switch</button><button type="button" id="virtual-pin-retry" class="text-btn">Retry</button><button type="button" id="virtual-pin-status-check" class="text-btn">Check location status</button></div><p id="virtual-pin-diagnostics" class="location-diagnostics hidden" role="status"></p></div><p class="footnote">Location is off by default. If enabled, we ask permission and round the coordinates to roughly 1 km. Photos and location stay on your device. Habitat tags stay private too.</p><div class="actions"><button id="virtual-save-final" type="button" class="primary">Keep this creature ✨</button></div>`);
 if(!existing)addDiceButton('virtual-name','virtual-dice-name','name');addDiceButton('virtual-memory','virtual-dice-memory','memory');
 $('virtual-save-final').onclick=saveVirtualArCatch;wireLocationOptIn('virtual-pin','virtual-pin');
 const key=s.arModelKey,frame=s.image,focus={...s.encounterFocus};
 makeVirtualScenePhoto(model,frame,focus,habitat).then(data=>{if($('virtual-photo-preview')&&s.arModelKey===key){$('virtual-photo-preview').innerHTML=`<img class="photo-preview" alt="Virtual creature in your captured camera scene" src="${data}">`}}).catch(()=>{if($('virtual-photo-preview'))$('virtual-photo-preview').textContent='Photo preview unavailable; this creature can still be saved.'});
}
function loadImageForComposition(data){return new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>resolve(img);img.onerror=()=>reject(new Error('AR image could not be loaded'));img.src=data})}
async function makeVirtualScenePhoto(model,frame,focus={x:.5,y:.69},habitat=getArHabitat(s.arHabitatKey)){
 const canvas=document.createElement('canvas');canvas.width=720;canvas.height=960;const ctx=canvas.getContext('2d');
 ctx.fillStyle='#182235';ctx.fillRect(0,0,720,960);
 if(typeof frame==='string'&&frame.startsWith('data:image/')){
  const photo=await loadImageForComposition(frame);const scale=Math.max(720/photo.width,960/photo.height),dw=photo.width*scale,dh=photo.height*scale;
  ctx.drawImage(photo,(720-dw)/2,(960-dh)/2,dw,dh);
 }
 ctx.fillStyle='rgba(8,13,23,.18)';ctx.fillRect(0,0,720,960);
 const floorY=Math.max(280,Math.min(820,960*(focus?.y??.69)+120));
 ctx.fillStyle='rgba(0,0,0,.20)';ctx.beginPath();ctx.ellipse(720*(focus?.x??.5),floorY,128,28,0,0,Math.PI*2);ctx.fill();
 const kind=model.species||'Cat';
 const cat=kind==='Cat'
  ?await loadImageForComposition('data:image/svg+xml;charset=utf-8,'+encodeURIComponent(renderArCatSvg(model).replace('<svg ','<svg xmlns="http://www.w3.org/2000/svg" ')))
  :await loadImageForComposition(safariCreatureArt(kind,model.speciesDetail));
 const x=Math.max(120,Math.min(600,720*(focus?.x??.5))),y=Math.max(180,Math.min(760,960*(focus?.y??.69)));
 ctx.shadowColor='rgba(4,8,18,.38)';ctx.shadowBlur=22;
 if(kind==='Cat')ctx.drawImage(cat,x-210,y-180,420,340);
 else ctx.drawImage(cat,x-185,y-185,370,370);
 ctx.shadowBlur=0;
 ctx.fillStyle='rgba(11,19,35,.74)';ctx.fillRect(18,18,304,50);ctx.fillStyle='#ecf6ff';ctx.font='bold 24px sans-serif';ctx.fillText('AR Safari · '+habitat.name,34,50);
 ctx.fillStyle='rgba(11,19,35,.76)';ctx.fillRect(0,886,720,74);ctx.textAlign='center';ctx.fillStyle='#f8f7ff';ctx.font='bold 26px sans-serif';ctx.fillText(model.name,360,924);ctx.font='16px sans-serif';ctx.fillStyle='#cdd8ea';ctx.fillText((model.species||model.breed||'Virtual cat')+' · '+habitat.badge,360,946);
 return canvas.toDataURL('image/jpeg',.88);
}
const existingRealForm=showCatForm;
// The first form render and the New/Seen Before toggle both receive dice controls.
const previousProfileV30=renderProfile;
renderProfile=function(){return previousProfileV30()+`<section class="soft-card backup-help"><h3>💾 Keep your Collection safe</h3><p class="dim">Tap <strong>Save full backup</strong>, then save or share the JSON file to a safe folder. It includes cats, photos, memories and any private pins. Use <strong>GPS-free backup</strong> to exclude location data. To restore, select Restore a backup in Your data.</p><div class="actions"><button type="button" class="primary" data-action="export">💾 Save full backup</button><button type="button" class="secondary" data-action="export-safe">🔒 GPS-free backup</button></div></section>`};
// Existing screen wiring handles data-action through action().
const originalActionV30=action;
action=function(kind){if(kind==='export-safe')return exportSafeBackup();return originalActionV30(kind)};


/* v3.2.0 — cleaner live tool switcher and cat-claw paw polish */
encounterToolLabel = kind => kind==='lure' ? 'Dangle Lure' : 'Whisker Paw';
function whiskerPawSvgMarkup(extraClass=''){
 return `<svg class="whisker-paw-svg ${extraClass}" viewBox="0 0 100 118" aria-hidden="true" focusable="false"><defs><linearGradient id="paw-fill" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffd9ea"/><stop offset=".58" stop-color="#fb86bd"/><stop offset="1" stop-color="#8d58dc"/></linearGradient></defs><g class="paw-claws"><path class="paw-claw claw-1" d="M17 26 C17 18 20 11 23 6 C26 12 27 20 26 27 Z"/><path class="paw-claw claw-2" d="M37 15 C37 9 39 3 42 0 C45 5 46 11 45 16 Z"/><path class="paw-claw claw-3" d="M55 15 C55 9 58 3 60 0 C63 5 64 11 63 16 Z"/><path class="paw-claw claw-4" d="M74 26 C74 18 77 11 80 6 C83 12 84 20 83 27 Z"/></g><g class="paw-digits"><ellipse class="paw-toe toe-1" cx="20" cy="36" rx="11" ry="14" transform="rotate(-18 20 36)" fill="url(#paw-fill)"/><ellipse class="paw-toe toe-2" cx="40" cy="23" rx="10.5" ry="14.5" transform="rotate(-7 40 23)" fill="url(#paw-fill)"/><ellipse class="paw-toe toe-3" cx="60" cy="23" rx="10.5" ry="14.5" transform="rotate(7 60 23)" fill="url(#paw-fill)"/><ellipse class="paw-toe toe-4" cx="80" cy="36" rx="11" ry="14" transform="rotate(18 80 36)" fill="url(#paw-fill)"/></g><path class="paw-center" d="M50 52 C64 49 74 58 81 70 C88 82 83 99 69 104 C61 108 56 102 50 102 C44 102 39 108 31 104 C17 99 12 82 19 70 C26 58 36 49 50 52 Z" fill="url(#paw-fill)"/><path class="paw-pad-split" d="M35 81 C40 75 46 74 50 79 C54 74 60 75 65 81"/><path class="paw-sheen" d="M26 63 C39 54 60 52 74 63"/></svg>`;
}
function syncEncounterToolDock(kind){
 const tools=[['ball',$('tool-ball')],['lure',$('tool-lure')]];
 for(const [toolKind,btn] of tools){
  if(!btn)continue;
  const active=toolKind===kind;
  btn.hidden=active;
  btn.classList.toggle('selected',active);
  btn.setAttribute('aria-hidden',String(active));
  btn.setAttribute('aria-pressed',String(active));
  btn.tabIndex=active?-1:0;
  btn.setAttribute('aria-label',toolKind==='lure'?'Switch to Lure':'Switch to Paw');
  btn.title=toolKind==='lure'?'Switch to Lure':'Switch to Paw';
  const label=btn.querySelector('small');if(label)label.textContent=toolKind==='lure'?'Switch to Lure':'Switch to Paw';
 }
 const item=$('throw-item');
 if(item){
  item.classList.toggle('throw-ball',kind==='ball');
  item.classList.toggle('throw-lure',kind==='lure');
  item.setAttribute('aria-label','Drag '+encounterToolLabel(kind)+' to the cat');
 }
 const status=$('encounter-status');
 if(status && !s.encounterCaptured){
  status.textContent=kind==='lure' ? 'Aim the Dangle Lure at the cat to enlarge the target.' : 'Drag the Whisker Paw onto the target for a capture!';
 }
}
showEncounter=function(image,quality,options={}){
 const liveMode=Boolean(options.live||s.encounterLive), arMode=Boolean(options.ar||s.encounterAr);
 s.encounterLive=liveMode; s.encounterAr=arMode; s.encounterFocus={x:.52,y:(arMode ? .69 : .40)}; s.captureSummary={quality,throwRating:null}; s.encounterTool='ball';
 const model=getArModel(s.arModelKey),habitat=getArHabitat(s.arHabitatKey); if(arMode&&habitat)s.encounterFocus={x:habitat.focus.x,y:habitat.focus.y};
 const help=arMode?'✨ Cat found! Drag the claw to catch it.':'① Aim at wildlife · ② Drag the paw · ③ Capture!';
 const summary=arMode?`<div class="encounter-ar-tools"><div class="ar-model-badge" id="ar-model-badge">Wild encounter: ${esc(model.name)}</div><span class="rarity-label">${(model.rarity||'common').replace(/^./,m=>m.toUpperCase())} · ${s.cats.some(c=>c.virtual&&c.arModelHint===model.key)?'Seen before':'New discovery'}</span></div><p class="ar-smart-note">Collect over ${AR_CAT_MODELS.length} cat types across ${AR_HABITATS.length} habitats. Today's visitor is in <strong>${esc(habitat.name)}</strong> · ${esc(habitat.badge)}. Rarer cats appear less often.</p>`:'';
 openModal(`<div class="sheet-head"><h2>${arMode?'AR safari ✨':liveMode?'Live encounter 🎥':'Encounter! 🐾'}</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="encounter-quick-help">${help}</p><details class="encounter-help"><summary>${arMode?'How does AR safari work?':'How do the tools work?'}</summary><p>${arMode?'A virtual creature appears automatically. Drag the paw to catch it. The camera overlay does not yet detect floors or tables; true ARCore surface tracking is planned. No video is saved.':'Tap your subject to place the target. Drag the Whisker Paw onto the target to catch it, or use the Dangle Lure first to make catching easier. Stay at a safe distance from real cats.'}</p></details><div id="encounter-aim-guide" class="encounter-aim-guide hidden" aria-hidden="true"></div><div id="encounter-stage" class="encounter-stage ${arMode?'encounter-stage-ar':''}"><img id="encounter-photo" class="encounter-backdrop" src="${image}" alt="${arMode?'Live encounter backdrop':'Your selected wildlife photo'}"><div class="encounter-vignette"></div><div id="encounter-cat" class="encounter-cat ${arMode?'ar-model-target':''}"><div class="encounter-cat-ring"></div>${arMode?`<div id="encounter-ar-cat" class="encounter-ar-cat">${renderArCatSvg(model)}</div><span id="encounter-ar-label">${esc(model.name)}</span>`:`<img id="encounter-cat-crop" src="${image}" alt="Selected wildlife photo crop"><span>Your wildlife target</span>`}</div><div class="encounter-capture-tag">${arMode?'● VIRTUAL CREATURE · BETA':'Capture preview'}</div><div class="encounter-tool-dock" aria-label="Capture tools"><button type="button" id="tool-ball" class="dock-tool" aria-label="Switch to Paw" aria-pressed="true" title="Switch to Paw" hidden aria-hidden="true" tabindex="-1"><span>🐾</span><small>Paw</small></button><button type="button" id="tool-lure" class="dock-tool" aria-label="Switch to Lure" aria-pressed="false" title="Switch to Lure"><span>🪶</span><small>Lure</small></button><div id="throw-item" class="throw-item throw-ball" role="button" aria-label="Drag ${encounterToolLabel('ball')} to the cat" tabindex="0">${whiskerPawSvgMarkup()}<span class="throw-stick">🎣</span><span class="throw-lure-body">🧶</span><span class="drag-prompt">DRAG</span></div></div><div id="encounter-orb" class="encounter-orb hidden">${whiskerPawSvgMarkup('capture-paw')}</div><div id="encounter-status" class="encounter-status" role="status" aria-live="polite">${arMode?`A ${esc(model.name)} appeared in ${esc(habitat.name)}! Drag the paw onto it to catch it.`:'Tap the animal to move the target. Then drag the paw from the right.'}</div><div id="encounter-meow" class="encounter-meow hidden" aria-hidden="true">${arMode?'Meow!':'Nice shot!'}</div></div><div id="encounter-quality" class="encounter-quality">${arMode?'⚡ Smooth AR mode · Lower-latency camera preview · No video saved or uploaded.':liveMode?'🎥 Live preview · <span id="live-frame-count">1 recent frame</span> · Live burst samples recent frames during your throw and picks the clearest one near your target when you capture.':'Photo clarity estimate: <strong>'+esc(quality.label)+'</strong> · '+esc(quality.note)} <small>${arMode?'Auto habitat placement on screen. Native world-tracked AR is a future upgrade.':'No video recording or upload.'}</small></div>${summary}<div id="encounter-shots" class="encounter-shots hidden" aria-label="Choose best frame"></div>${arMode?'':`<div class="encounter-photo-actions"><button type="button" id="encounter-retake" class="secondary">${liveMode?'🎥 Retake live capture':'📸 Retake photo'}</button><button type="button" id="encounter-replace" class="secondary">🖼️ Choose another</button></div>`}<div class="encounter-launch"><div class="encounter-instructions">${arMode?`Look around gently. ${esc(model.name)} has appeared in ${esc(habitat.name)} — no tapping needed.`:'Drag the paw from the right. Only the other tool is shown, so the view stays clean.'}</div></div><div class="actions">${arMode?'':'<button id="encounter-skip" class="secondary">Save photo without game</button>'}<button id="encounter-continue" class="primary hidden">${arMode?'Keep this creature ✨':'Continue to Collection →'}</button></div><p class="footnote">${arMode?'Virtual creature preview: automatic placement in a themed habitat with lighter camera settings for smoother play. Full world tracking needs native ARCore.':'Live camera is local to your device; only the selected still is saved. No automatic species recognition.'} Stay a safe distance from real cats.</p>`,liveMode,arMode?'ar-sheet':'');
 if(liveMode&&liveCamera?.active){
  const stage=$('encounter-stage'),video=liveCamera.video;
  video.id='encounter-video';video.className='encounter-backdrop encounter-live-video'; stage.prepend(video);stage.classList.add('live-encounter');
  const tag=stage.querySelector('.encounter-capture-tag');if(tag)tag.textContent=arMode?'● 2D · VIRTUAL PREVIEW':'● LIVE · private';
  const crop=$('encounter-cat-crop');if(crop)crop.style.display='none';
  const status=$('encounter-status');if(status&& !arMode)status.textContent='Tap your subject to place the target, then drag the paw from the right.';
  if(!arMode)scheduleLiveSampling(liveCamera);
 }
 const selectTool=kind=>{if(s.encounterCaptured)return; s.encounterTool=kind; syncEncounterToolDock(kind);
  const item=$('throw-item');if(item){item.classList.remove('tool-switch-pop');void item.offsetWidth;item.classList.add('tool-switch-pop');}
 };
 $('tool-ball').onclick=()=>selectTool('ball'); $('tool-lure').onclick=()=>selectTool('lure');
 syncEncounterToolDock(s.encounterTool||'ball');
 if(!arMode)$('encounter-skip').onclick=async()=>{if(liveCamera)await freezeLiveEncounter();s.captureSummary=null;showCatForm(s.image)};
 $('encounter-continue').onclick=()=>arMode?showVirtualNamingForm():showCatForm(s.image);
 if(!arMode){$('encounter-retake').onclick=()=>s.encounterLive?(s.encounterAr?startArEncounter():startLiveEncounter()):requestEncounterPhoto(true);
 $('encounter-replace').onclick=()=>{s.encounterLive=false;s.encounterAr=false;requestEncounterPhoto(false)};}
 const stage=$('encounter-stage'),backdrop=$('encounter-photo'); [stage,$('encounter-status'),$('encounter-quality'),$('encounter-meow'),$('tool-ball'),$('tool-lure'),$('throw-item')].filter(Boolean).forEach(el=>{el.oncontextmenu=e=>e.preventDefault();el.onselectstart=e=>e.preventDefault();el.ondragstart=()=>false;});
 if(!arMode)stage.addEventListener('click',event=>{ const visual=$('encounter-video')||backdrop; if(s.encounterCaptured||!(event.target===stage||event.target===backdrop||event.target===visual))return; const point=encounterImagePoint(event.clientX,event.clientY,visual,visual.getBoundingClientRect()); if(point)setEncounterFocus(point.x,point.y); });
 backdrop.addEventListener('load',()=>positionEncounterFocus()); encounterResizeObserver?.disconnect(); encounterResizeObserver=typeof ResizeObserver==='function'?new ResizeObserver(()=>positionEncounterFocus()):null; encounterResizeObserver?.observe(stage); setEncounterFocus(s.encounterFocus.x,s.encounterFocus.y,false); setupEncounterDrag(); if(arMode)requestAnimationFrame(()=>$('encounter-cat')?.classList.add('ar-autospawn'));
 if(arMode){
  document.querySelectorAll('[data-ar-model]').forEach(btn=>btn.addEventListener('click',()=>{s.arModelManual=true;s.arModelKey=btn.dataset.arModel;refreshArEncounterUi()}));
  $('ar-reroll')?.addEventListener('click',()=>{s.arModelManual=true;s.arModelKey=randomArModel(s.arModelKey).key;refreshArEncounterUi()});
  refreshArEncounterUi();
 }
};
handleEncounterHit=function(kind,accuracy=.45){
 if(s.encounterCaptured||!$('encounter-status'))return;
 if(kind==='lure'){
  if(s.encounterLured){$('encounter-status').textContent='The cat is focused on the lure. Try your Whisker Paw.';return}
  s.encounterLured=true;$('encounter-cat')?.classList.add('curious');
  $('encounter-status').textContent='The toy caught the cat’s attention! Its target is now larger.';
  s.encounterTool='ball';syncEncounterToolDock('ball');const item=$('throw-item');if(item){item.classList.remove('tool-switch-pop');void item.offsetWidth;item.classList.add('tool-switch-pop')}return;
 }
 const rating=accuracy<=.23?'Purrfect!':accuracy<=.55?'Great!':'Nice!';
 s.captureSummary.throwRating=rating;
 runEncounterCapture();
};


/* v3.3 — Friendly, non-destructive recovery wizard */
const previousRenderProfileV33=renderProfile;
renderProfile=function(){return previousRenderProfileV33()+`<section class="soft-card recovery-help"><h3>🐱 Missing a cat?</h3><p class="dim">Find missing cats from a saved recovery copy. We will show what we find before you decide.</p><button type="button" class="primary" data-action="recovery-wizard">🔎 Find missing cats</button></section>`};
const previousActionV33=action;
action=function(kind){if(kind==='recovery-wizard')return openRecoveryWizard();return previousActionV33(kind)};
function openRecoveryWizard(){
 if(s.busy)return toast('Please wait for the current save to finish.');
 openModal(`<div class="sheet-head"><h2>Find missing cats 🐱</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim">We'll check the recovery copy on this phone. This won't change any cat or photo.</p><div id="recovery-result" class="soft-card"><p class="dim">Checking your saved recovery copy…</p></div><div class="actions"><button type="button" id="recovery-file" class="secondary">📁 Choose a backup file instead</button></div><p class="footnote">Only cats in a saved copy can be recovered. If neither copy has your missing cats, keep the app installed and seek help with older backups.</p>`);
 $('recovery-file').onclick=()=>action('import');
 if(window.whiskerNativeReady)location.href='whiskerhunt://recovery-preview';
 else renderRecoveryPreview({available:false,browser:true});
}
function renderRecoveryPreview(info){
 const target=$('recovery-result');if(!target)return;
 if(!info||!info.available){
  target.innerHTML='<strong>No phone recovery copy found</strong><p class="dim">You can still try a JSON backup saved on your phone or in cloud storage.</p>';
  return;
 }
 const records=Array.isArray(info.cats)?info.cats:[];
 const ids=new Map(s.cats.map(c=>[c.id,c]));
 const missing=records.filter(c=>!ids.has(c.id));
 const sightings=records.filter(c=>ids.has(c.id)&&(ids.get(c.id).sightings||[]).length<(c.sightings||0));
 const names=missing.slice(0,8).map(c=>`<li>${esc(c.name)}</li>`).join('');
 target.innerHTML=`<strong>${records.length} cats in recovery copy</strong><p class="dim">${missing.length} missing cat${missing.length===1?'':'s'} · ${sightings.length} cat${sightings.length===1?'':'s'} may have extra memories</p>${missing.length?`<ul class="recovery-names">${names}</ul>`:'<p class="dim">No missing cat IDs detected in this copy.</p>'}<p class="footnote">Restoring merges cats and sightings. Existing cats and photos stay. Your recovery copy is kept.</p><div class="actions"><button type="button" class="primary" id="recovery-merge" ${missing.length||sightings.length?'':'disabled'}>🐾 Restore found cats</button><button type="button" class="secondary" id="recovery-export">💾 Save my current Collection first</button></div>`;
 $('recovery-merge').onclick=()=>{if(s.busy)return;location.href='whiskerhunt://recovery-merge'};
 $('recovery-export').onclick=()=>{if(window.whiskerNativeReady)location.href='whiskerhunt://recovery-export';else downloadBackup(false)};
}
window.whiskerRecoveryPreview=renderRecoveryPreview;
window.whiskerRecoveryMissing=function(){const target=$('recovery-result');if(target)target.innerHTML='<p class="dim">The recovery copy is not readable. Nothing was changed. Try a saved JSON backup instead.</p>'};
window.whiskerRecoveryImport=function(json){
 if(s.busy)return toast('Please wait for the current save to finish.');
 if(typeof json!=='string'||json.length>36*1024*1024)return toast('Recovery copy is too large to restore. Nothing was changed.');
 // Existing loadBackupText asks for confirmation and merges by ID rather than replacing.
 return loadBackupText(json);
};


/* v3.8: real-world Collection (species added without migrating existing Collection records). */
const SPECIES=['Cat','Dog','Snail','Butterfly','Moth','Bee','Ladybird','Beetle','Dragonfly','Ant','Spider','Bird','Squirrel','Rabbit','Hedgehog','Frog','Other'];
const SPECIES_EMOJI={Cat:'🐈',Dog:'🐕',Snail:'🐌',Butterfly:'🦋',Moth:'🦋',Bee:'🐝',Ladybird:'🐞',Beetle:'🪲',Dragonfly:'🪰',Ant:'🐜',Spider:'🕷️',Bird:'🐦',Squirrel:'🐿️',Rabbit:'🐇',Hedgehog:'🦔',Frog:'🐸',Other:'🔎'};
function speciesOf(entry){return SPECIES.includes(entry?.species)?entry.species:'Cat'}
function speciesIcon(value){return SPECIES_EMOJI[value]||'🐾'}
function visibleWildlife(){return s.cats.filter(c=>!c.virtual)}
function speciesOptions(active){return SPECIES.map(key=>`<option value="${esc(key)}" ${active===key?'selected':''}>${speciesIcon(key)} ${esc(key)}</option>`).join('')}
const previousStartCatchWildlife=startCatch;
startCatch=function(catId=null){
 const actual=typeof catId==='string'&&s.cats.some(c=>c.id===catId)?catId:null;
 s.spottedSpecies=actual?speciesOf(s.cats.find(c=>c.id===actual)):'Cat';
 previousStartCatchWildlife(actual);
 const title=document.querySelector('.sheet-head h2');if(title&&title.textContent.includes('Catch a cat'))title.textContent='Spot wildlife! 📸';
 const intro=document.querySelector('.capture-choice-v28')?.previousElementSibling;
 if(intro)intro.textContent='Snails, insects, dogs, birds or cats — photograph wildlife kindly, then choose the species before saving.';
};
const previousShowCatFormWildlife=showCatForm;
showCatForm=function(photo){
 previousShowCatFormWildlife(photo);
 const prior=s.revisitId?s.cats.find(c=>c.id===s.revisitId):null;
 s.spottedSpecies=prior?speciesOf(prior):(SPECIES.includes(s.spottedSpecies)?s.spottedSpecies:'Cat');
 s.spottedDetail=''; s.fieldGroupExpanded=!prior&&s.wildTarget==='Unknown';
 const region=$('catch-extra');if(!region)return;
 const chooser=document.createElement('div');chooser.className='field-group species-picker';
 chooser.innerHTML=`<div class="visual-field-heading"><div><span class="visual-step">STEP 1 · WHO DID YOU FIND?</span><h3>Pick an animal</h3></div><button type="button" class="visual-change" id="change-species">Change animal ↗</button></div><select id="wildlife-species" class="select field-guide-native-select" aria-label="Choose the animal or insect">${speciesOptions(s.spottedSpecies)}</select><div id="field-guide-species" class="field-guide-species" aria-label="Animal groups"></div><div id="field-guide-selected" class="field-guide-selected"></div><small class="field-help">Pictures are little guides, not automatic identification. If you're unsure, that's okay!</small>`;
 region.parentElement.insertBefore(chooser,region);
 const advice=document.createElement('p');advice.className='field-help wildlife-safety';
 advice.textContent='Observe without touching, feeding or disturbing wildlife; never trespass. Take a photo from a safe distance.';
 chooser.after(advice);
 const update=()=>{
  const species=s.spottedSpecies,isCat=species==='Cat';
  const newMode=$('mode-new');if(newMode)newMode.textContent=isCat?'✨ New cat':'✨ New discovery';
  const modeIntro=$('mode-new')?.closest('.chips')?.previousElementSibling;if(modeIntro&&modeIntro.tagName==='P')modeIntro.textContent='Is this a new discovery or one you have spotted before?';
  const confirmation=$('real-cat')?.closest('label')?.querySelector('span');if(confirmation)confirmation.textContent=`I photographed this ${species.toLowerCase()==='other'?'animal':species.toLowerCase()} without disturbing it or approaching unsafely.`;
  const newLabel=$('cat-name')?.closest('.field-group')?.querySelector('label');if(newLabel)newLabel.textContent=`Name your ${isCat?'cat':'discovery'}`;
  const coat=$('cat-coat');if(coat){if(!isCat)coat.value='Other';coat.closest('.field-group').classList.add('hidden')}
  const personality=$('cat-personality');if(personality){if(!isCat)personality.value='Unknown';personality.closest('.field-group').classList.toggle('hidden',!isCat)}
  const extra=$('species-details');if(extra)extra.remove();
  if(s.catchMode==='new'){
    const details=document.createElement('div');details.className='field-group visual-field-types';details.id='species-details';
    details.innerHTML=`<div class="visual-field-heading"><div><span class="visual-step">STEP 2 · WHAT KIND?</span><h3>${esc(species)} varieties</h3></div><span class="visual-tap-hint">Tap a picture<small class="artwork-release">REALISTIC FIELD GUIDE 66</small></span></div><div id="field-guide-types" class="field-guide-types" role="group" aria-label="${esc(species)} appearance or variety"></div><input class="field hidden" id="wildlife-detail" maxlength="50" autocomplete="off" placeholder="Write the type you saw (optional)"><small class="field-help">Not sure? Choose "Not sure" and keep going. One simple fallback option keeps the guide clearer for children.</small>`;
    region.prepend(details);
    renderFieldGuideVarieties();
  }
  renderFieldGuideSpecies();
  const repeat=$('repeat-cat');if(repeat){
   const previous=repeat.value;
   const matches=visibleWildlife().filter(c=>speciesOf(c)===species);
   repeat.innerHTML=matches.length?matches.map(c=>`<option value="${esc(c.id)}">${esc(c.name)}${c.speciesDetail?' · '+esc(c.speciesDetail):''}</option>`).join(''):'<option value="">No saved sightings of this species yet</option>';
   if(matches.some(c=>c.id===previous))repeat.value=previous;
   else if(s.revisitId&&matches.some(c=>c.id===s.revisitId))repeat.value=s.revisitId;
  }
  const matches=$('possible-matches');if(matches&&!isCat){matches.classList.add('hidden');matches.innerHTML=''}else if(matches)matches.classList.remove('hidden');
  const save=$('save-catch');if(save)save.textContent=s.catchMode==='repeat'?'Save another sighting →':'Add to Collection →';
 };
 $('wildlife-species').addEventListener('change',e=>{s.spottedSpecies=e.target.value;s.spottedDetail='';s.coatChoice='';update()});
 for(const mode of ['mode-new','mode-repeat'])$(mode)?.addEventListener('click',update);
 update();
};
// Species-safe save path. Old Collection records keep their IDs, photos, locations, XP and quests.
saveCatch=function(){return (async()=>{
 if(s.busy)return;
 if(!$('real-cat')?.checked)return toast('Please confirm that the animal was photographed safely.');
 if(!s.db)return toast('Device storage is not ready.');
 const mode=s.catchMode,species=SPECIES.includes(s.spottedSpecies)?s.spottedSpecies:'Cat',sig=photoSignature(s.image);
 if(s.cats.some(c=>c.signature===sig||(c.sightings||[]).some(v=>v.signature===sig)))return toast('This photo is already collected. Choose a different image for a new sighting.');
 let animal;
 if(mode==='new'){
  const name=$('cat-name')?.value.trim();if(!name)return toast('Give your discovery a name.');
  animal={id:id(),name:name.slice(0,36),species,speciesDetail:species==='Cat'?'':($('wildlife-detail')?.value.trim()||'').slice(0,50),coat:species==='Cat'?$('cat-coat').value:'Other',personality:species==='Cat'?$('cat-personality').value:'Unknown',note:$('cat-note')?.value.trim()||'',photo:s.image,signature:sig,visualHash:null,createdAt:new Date().toISOString(),fav:false,arModelHint:null,sightings:[]};
 }else{
  animal=s.cats.find(c=>!c.virtual&&c.id===$('repeat-cat')?.value&&speciesOf(c)===species);
  if(!animal)return toast(`Choose an existing ${species.toLowerCase()} or select New discovery.`);
 }
 const btn=$('save-catch');s.busy=true;btn.disabled=true;btn.textContent='Saving your discovery…';
 let appended=false,added=false,earned=0;
 try{
  const hash=await visualFingerprint(s.image).catch(()=>null);if(mode==='new')animal.visualHash=hash;
  const wantsPin=!!$('pin-check')?.checked;
  const loc=wantsPin?(hasFreshApproxLocation()?s.pendingApproxLocation:await ensureApproxLocation('pin')):null;
  if(wantsPin&&!isUsableLocation(loc))throw new Error('PIN_NOT_SAVED');
  const note=mode==='new'?animal.note:($('repeat-note')?.value.trim()||'');
  const now=Date.now(),lastSeen=Math.max(0,...animal.sightings.map(v=>Date.parse(v.at)).filter(t=>Number.isFinite(t)&&t<=now));
  const cooldown=mode==='repeat'&&lastSeen>0&&(now-lastSeen<3600000);
  const firstCatCoat=mode==='new'&&species==='Cat'&&!s.cats.some(c=>!c.virtual&&speciesOf(c)==='Cat'&&c.coat===animal.coat);
  earned=(mode==='new'?100:cooldown?0:30)+(firstCatCoat?25:0);
  animal.sightings.push({id:id(),visualHash:hash,at:new Date().toISOString(),note,photo:mode==='new'?null:s.image,signature:sig,lat:isUsableLocation(loc)?loc.lat:null,lng:isUsableLocation(loc)?loc.lng:null,captureMode:s.encounterLive?'live':'photo',arModel:null});appended=true;
  if(mode==='new'){s.cats.push(animal);added=true}
  s.profile.xp+=earned;
  await persistCatchAtomic(animal);
  setPendingApproxLocation(null);closeModal();navigate('dex');
  toast(`${speciesIcon(species)} ${mode==='new'?'New discovery saved!':'Another sighting saved!'} +${earned} XP${wantsPin?' · 📍 Private pin saved':''}`);
 }catch(error){
  console.error(error);s.profile.xp-=earned;if(appended)animal.sightings.pop();if(added)s.cats=s.cats.filter(c=>c.id!==animal.id);
  if(error?.message==='PIN_NOT_SAVED')showPinFailure('pin');else toast('Save failed. Your photo is still here — please retry.');
  btn.disabled=false;btn.textContent='Try saving again';
 }finally{s.busy=false}
})()};
// Collection UI, with Cat Bingo retained for existing cat players.
const previousRenderDexWildlife=renderDex;
renderDex=function(){
 const real=visibleWildlife(),counts=SPECIES.map(type=>({type,n:real.filter(c=>speciesOf(c)===type).length})).filter(v=>v.n);
 let html=previousRenderDexWildlife();
 html=html.replace('<h1>The Collection 🐈</h1>', '<h1>Collection 🌿</h1>');
 html=html.replace(/<p class="subtitle">[^<]*real cats · [^<]*virtual friends<\/p>/,`<p class="subtitle">${real.length} real-world discoveries · ${s.cats.filter(c=>c.virtual).length} virtual cats</p>`);
 const panel=`<section class="wildlife-collection"><div class="eyebrow">WILDLIFE COLLECTION</div><h3>Explore your discoveries</h3><p class="dim">Snails, butterflies, birds, dogs and other discoveries all belong here.</p><div class="wildlife-stat-grid">${counts.length?counts.map(v=>`<span class="wildlife-stat">${speciesIcon(v.type)} ${esc(v.type)} <strong>${v.n}</strong></span>`).join(''):'<span class="dim">Your first discovery is waiting.</span>'}</div><div class="chips wildlife-filter">${SPECIES.map(v=>`<button class="chip ${s.filter==='Species:'+v?'selected':''}" data-filter="Species:${v}">${speciesIcon(v)} ${v}</button>`).join('')}</div></section>`;
 html=html.replace('<section class="virtual-gallery">',panel+'<section class="virtual-gallery">');
 html=html.replace('Search your feline friends...', 'Search wildlife, snails, dogs and memories...');
 // Cat Bingo remains visible but is explicitly cat-only; remove its duplicate coat filter row from other species.
 return html;
};
dexGrid=function(){
 const q=s.search.toLowerCase();const records=visibleWildlife().filter(c=>{
  const species=speciesOf(c),filter=s.filter;
  const matching=filter==='All'||(filter==='Favourites'&&c.fav)||(filter.startsWith('Species:')&&species===filter.slice(8))||(species==='Cat'&&c.coat===filter);
  return matching&&[c.name,species,c.speciesDetail||'',c.coat,c.note||''].some(v=>String(v).toLowerCase().includes(q));
 }).sort((a,b)=>{const last=c=>Math.max(0,...(c.sightings||[]).map(v=>Date.parse(v.at)||0));switch(s.dexSort){case 'name':return a.name.localeCompare(b.name);case 'last':return last(b)-last(a);case 'visits':return catches(b)-catches(a)||a.name.localeCompare(b.name);case 'favourites':return Number(b.fav)-Number(a.fav)||last(b)-last(a);default:return b.createdAt.localeCompare(a.createdAt)}});
 return records.length?`<div class="cat-grid">${records.map(c=>`<button class="cat-tile" data-cat="${esc(c.id)}"><img class="cat-img" src="${c.photo}" alt="${esc(c.name)}"><div class="cat-info"><strong>${esc(c.name)}</strong><small>${speciesIcon(speciesOf(c))} ${esc(speciesOf(c))}${c.speciesDetail?' · '+esc(c.speciesDetail):speciesOf(c)==='Cat'?' · '+esc(c.coat):''} · ${catches(c)} sighting${catches(c)!==1?'s':''}</small><div class="tagline"><span class="tag">${rank(c)}</span><span class="badge-heart">${c.fav?'♥':'♡'}</span></div></div></button>`).join('')}</div>`:`<div class="feature-empty empty-dex"><div class="big">🔎</div><h3>No matching wildlife found</h3><p>Try another species filter, or add a new discovery.</p><button class="primary" id="dex-catch">📸 Spot wildlife</button></div>`;
};
const previousOpenDetailWildlife=openDetail;
openDetail=function(animalId){
 previousOpenDetailWildlife(animalId);
 const animal=s.cats.find(c=>c.id===animalId);if(!animal||animal.virtual)return;
 const species=speciesOf(animal);if(species==='Cat')return;
 const eyebrow=document.querySelector('.sheet .eyebrow');if(eyebrow)eyebrow.textContent=`COLLECTION · ${species.toUpperCase()} DISCOVERY`;
 const tags=document.querySelector('.detail-tags');if(tags){const first=tags.querySelector('.detail-tag');if(first)first.textContent=`${speciesIcon(species)} ${species}${animal.speciesDetail?' · '+animal.speciesDetail:''}`;}
 const spot=$('more-sighting');if(spot)spot.textContent='📷 Spot again';
 const del=$('delete-cat');if(del)del.textContent='Delete this discovery & sightings';
};
editCat=async function(animal){
 const species=speciesOf(animal);
 openModal(`<div class="sheet-head"><h2>Edit discovery ✎</h2><button class="close-btn" data-close aria-label="Close">×</button></div><div class="field-group"><label for="edit-name">Name</label><input id="edit-name" maxlength="36" class="field" value="${esc(animal.name)}"></div><div class="field-group"><label for="edit-species">Species</label><select id="edit-species" class="select">${speciesOptions(species)}</select></div><div class="field-group"><label for="edit-species-detail">Type / breed (optional)</label><input id="edit-species-detail" class="field" maxlength="50" value="${esc(animal.speciesDetail||'')}" placeholder="e.g. Garden snail"></div><div class="field-group" id="edit-coat-group"><label for="edit-coat">Coat / appearance</label><select id="edit-coat" class="select">${COATS.map(c=>`<option ${animal.coat===c?'selected':''}>${c}</option>`).join('')}</select></div><div class="field-group" id="edit-personality-group"><label for="edit-personality">Personality</label><select id="edit-personality" class="select">${PERSONALITIES.map(c=>`<option ${animal.personality===c?'selected':''}>${c}</option>`).join('')}</select></div><div class="field-group"><label for="edit-note">Your memory</label><textarea id="edit-note" class="field" maxlength="140" rows="3">${esc(animal.note||'')}</textarea></div><p class="footnote">Descriptions are yours, not automatic AI identifications. Changes won't erase photographs or sightings.</p><div class="actions"><button class="primary" id="edit-save">Save changes</button></div>`);
 initEditFieldGuide(animal);
 const sync=()=>{const show=$('edit-species').value==='Cat';$('edit-coat-group').classList.toggle('hidden',!show);$('edit-personality-group').classList.toggle('hidden',!show);renderEditFieldGuide()};
 $('edit-species').onchange=()=>{s.editVisualDetail='';sync()};sync();
 $('edit-save').onclick=async()=>{
  if(s.busy)return;const name=$('edit-name').value.trim();if(!name)return toast('Please enter a name.');
  const prior={name:animal.name,species:animal.species,speciesDetail:animal.speciesDetail,coat:animal.coat,personality:animal.personality,note:animal.note};
  const nextSpecies=$('edit-species').value;
  const next={name:name.slice(0,36),species:nextSpecies,speciesDetail:$('edit-species-detail').value.trim().slice(0,50),coat:nextSpecies==='Cat'?$('edit-coat').value:animal.coat,personality:nextSpecies==='Cat'?$('edit-personality').value:animal.personality,note:$('edit-note').value.trim().slice(0,140)};
  Object.assign(animal,next);s.busy=true;
  try{await saveCat(animal);closeModal();openDetail(animal.id);render();toast('Discovery updated!')}
  catch(error){console.error(error);Object.assign(animal,prior);toast('Could not update discovery; original data kept.')}
  finally{s.busy=false}
 };
};
const previousShareWildlife=shareCat;
shareCat=function(animal){if(speciesOf(animal)==='Cat')return previousShareWildlife(animal);
 const message=`${speciesIcon(speciesOf(animal))} I discovered ${animal.name}, a ${animal.speciesDetail||speciesOf(animal)} in Hush Hunt! #HushHunt`;
 if(window.whiskerNativeReady){location.href='whiskerhunt://share?text='+encodeURIComponent(message);return}
 if(navigator.share)navigator.share({title:'Hush Hunt',text:message}).catch(()=>{});
 else if(navigator.clipboard)navigator.clipboard.writeText(message).then(()=>toast('Caption copied!')).catch(()=>{});
};
const previousJournalWildlife=renderJournal;
renderJournal=function(){return previousJournalWildlife().replace('YOUR REAL-WORLD CAT ADVENTURES','YOUR REAL-WORLD WILDLIFE ADVENTURES').replace('Search cats and memories','Search wildlife and memories')};
const previousJournalCardsWildlife=journalCards;
journalCards=function(){return previousJournalCardsWildlife().replace(/ · (Tabby|Ginger|Black|White|Tuxedo|Calico|Grey|Other)<\/small>/g,' · Discovery</small>')};
const previousRenderHomeWildlife=renderHome;
renderHome=function(){return previousRenderHomeWildlife().replace('YOUR CAT-CHASING ADVENTURE','YOUR WILDLIFE ADVENTURE').replace('See a cat?<br>Catch the moment.','Spot wildlife?<br>Capture the moment.').replace('Meet real cats, level up and build your own legendary collection.','Discover real animals, snails and insects — safely and at your own pace.').replace('📸 Catch a cat →','📸 Spot wildlife →').replace('Unique cats','Discoveries').replace('Your cat collection','Your Collection').replace('Found a friendly-looking feline? Snap your first cat and bring your Collection to life.','Found a snail, butterfly or a friendly-looking animal? Photograph it safely to begin your Collection.');};
const previousRenderProfileWildlife=renderProfile;
renderProfile=function(){return previousRenderProfileWildlife().replace('<span>Cats</span>','<span>Discoveries</span>').replace('Keep your Collection safe','Keep your Collection safe');};

/* New optional wildlife quests; older cat-only quests keep their existing meaning. */
const priorDailyWildlife=dailyQuests;
dailyQuests=function(){const real=visibleWildlife(),todayEntries=real.flatMap(c=>c.sightings||[]).filter(v=>dateKey(v.at)===today());return [{id:'wildlife-first',icon:'🌿',title:'Wildlife explorer',description:'Photograph one animal or insect today',progress:todayEntries.length,target:1,xp:35},...priorDailyWildlife()]};
const priorWeeklyWildlife=weeklyQuests;
weeklyQuests=function(){const species=new Set(visibleWildlife().filter(c=>dateKey(c.createdAt)>=weekKey()).map(speciesOf));return [{id:'wildlife-variety',weekly:true,icon:'🦋',title:'Species explorer',description:'Find two different species this week',progress:species.size,target:2,xp:150},...priorWeeklyWildlife()]};

/* v3.8.1 — Live-only wildlife discoveries.
 * Local UX provenance check, not cryptographic authentication or species AI.
 * Stored photos, old imports, and JSON restore remain read-only/compatible.
 */
s.realLiveProof=null;
function realLivePhotoReady(image=s.image){
 const proof=s.realLiveProof;
 return !!proof?.ready && proof.images instanceof Set && typeof image==='string' && proof.images.has(image);
}
function showLiveOnlyCameraChoice(message='Only animals spotted through the live camera count as new Collection discoveries.'){
 s.encounterLive=false;s.encounterAr=false;s.realLiveProof=null;
 openModal(`<div class="sheet-head"><h2>Live wildlife camera 🎥</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim">${esc(message)}</p><div class="capture-choice"><button type="button" class="choice" id="live-only-retry"><span>🎥</span><strong>Open live camera</strong><small>Spot wildlife now and save your best live frame</small></button><button type="button" id="live-only-collection" class="choice"><span>📚</span><strong>My Collection</strong><small>View older discoveries and photos</small></button></div><p class="footnote center">No gallery upload or normal-camera import for new discoveries. Your existing photos and Collection backups are unaffected.</p>`);
 $('live-only-retry').onclick=startLiveEncounter;
 $('live-only-collection').onclick=()=>navigate('dex');
}
const v44StartCatch=startCatch;
startCatch=function(animalId=null){
 s.realLiveProof=null;
 v44StartCatch(animalId);
 const picker=document.querySelector('.capture-choice-v28');
 if(!picker)return;
 picker.innerHTML=`<button id="live-photo" type="button" class="choice choice-live-only"><span>🎥</span><strong>Spot real wildlife</strong><small>Live camera only · cats, snails, dogs, insects and more</small></button><button id="ar-photo" type="button" class="choice"><span>✨</span><strong>AR Safari</strong><small>Find virtual creatures · separate collection</small></button>`;
 $('live-photo').onclick=startLiveEncounter;
 $('ar-photo').onclick=startArEncounter;
 const intro=picker.previousElementSibling;
 if(intro)intro.textContent='Every new real-world discovery starts in the live camera. Point at a safely observed animal, catch the moment, then choose its species.';
 const foot=picker.nextElementSibling;
 if(foot)foot.textContent='No imported photos for new catches. You can still view old photos and restore backups. Never disturb or chase wildlife.';
};
// Old native-photo, phone-camera and gallery callbacks cannot introduce a new
// record: they no longer open a collectible encounter.
requestEncounterPhoto=async function(){toast('New wildlife catches must use the live camera.');showLiveOnlyCameraChoice()};
startMultiPhotoCapture=function(){showLiveOnlyCameraChoice()};
showSafeCameraChooser=function(){showLiveOnlyCameraChoice('Live camera stopped. Try again when you are ready. No photo was imported.')};
useNormalCameraFromLiveStartup=function(){liveRequestEpoch++;stopLiveCamera();showLiveOnlyCameraChoice()};
const v44BeginEncounter=beginEncounter;
beginEncounter=function(image,options={}){
 if(options.ar===true)return v44BeginEncounter(image,options); // AR virtual cats remain their own game.
 if(options.live!==true||!liveCamera?.active){
  s.realLiveProof=null;
  toast('Use the live camera to collect a new real animal.');
  return showLiveOnlyCameraChoice();
 }
 s.realLiveProof={source:'camera-stream',images:new Set([image]),ready:false};
 return v44BeginEncounter(image,options);
};
const v44FinishLiveEncounter=finishLiveEncounter;
finishLiveEncounter=async function(session){
 const proof=!s.encounterAr&&liveCamera===session?s.realLiveProof:null;
 await v44FinishLiveEncounter(session);
 if(!proof||proof!==s.realLiveProof)return;
 // Source images are exclusively frames collected from this camera session.
 if(liveCamera!==null||session?.active||!captureShots.length)return;
 for(const f of captureShots){if(typeof f?.image==='string')proof.images.add(f.image)}
 proof.ready=proof.images.has(s.image) && !!$('encounter-stage')?.isConnected;
};
const v44ShowCatForm=showCatForm;
showCatForm=function(image){
 if(!realLivePhotoReady(image)){
  toast('Take a live wildlife capture before saving.');
  return showLiveOnlyCameraChoice('Your camera has not captured a live wildlife frame yet. Open the live camera to try again.');
 }
 v44ShowCatForm(image);
 const info=document.createElement('p');info.className='live-only-verified';info.textContent='✓ Live camera discovery · Pick the species you actually observed.';
 const species=$('wildlife-species')?.closest('.field-group');if(species)species.before(info);
};
const v44SaveCatch=saveCatch;
saveCatch=function(){
 if(!realLivePhotoReady()){
  toast('Cannot save an imported photo as a new wildlife discovery.');
  return;
 }
 return v44SaveCatch();
};
const v44ShowEncounter=showEncounter;
showEncounter=function(image,quality,options={}){
 const virtual=Boolean(options.ar||s.encounterAr);
 if(!virtual && (!options.live||!s.realLiveProof))return showLiveOnlyCameraChoice();
 v44ShowEncounter(image,quality,options);
 if(virtual)return;
 // Keep the ephemeral frame-choice tray, which contains only recent live video frames.
 $('encounter-replace')?.remove();
 const retake=$('encounter-retake');if(retake){retake.textContent='🎥 Retake live';retake.onclick=startLiveEncounter}
 const qualityLabel=$('encounter-quality');if(qualityLabel)qualityLabel.dataset.captureSource='live';
};
const v44CloseModal=closeModal;
closeModal=function(){s.realLiveProof=null;return v44CloseModal()};

const v44RenderHomeLiveOnly=renderHome;
renderHome=function(){return v44RenderHomeLiveOnly().replace('Photograph it safely to begin your Collection.','Capture it with the live camera to begin your Collection.').replace('Photograph one animal or insect today','Spot one animal or insect live today').replace('Catch your first cat','Spot your first animal').replace('View Collection','View Collection')};



/* v3.8.2: Earlier provisional identity and gentle species-specific discovery tools.
   These tools are virtual camera overlays, never instructions to touch wildlife.
   Existing state/backup identifiers are intentionally unchanged. */
const HUSH_HUNT_BRAND='Hush Hunt';
const FIELD_TOOLS={
 Cat:{icon:'🐈',primary:'Whisker Claw',altIcon:'🪶',secondary:'Dangle Lure',status:'Catch the cat with your virtual claw.'},
 Dog:{icon:'🐕',primary:'Paw Tag',altIcon:'🔎',secondary:'Focus Lens'},
 Snail:{icon:'🍃',primary:'Leaf Stamp',altIcon:'🔎',secondary:'Macro Lens'},
 Butterfly:{icon:'🥅',primary:'Photo Net',altIcon:'🔎',secondary:'Macro Lens'},
 Moth:{icon:'🥅',primary:'Photo Net',altIcon:'🔎',secondary:'Macro Lens'},
 Bee:{icon:'🌼',primary:'Flower Token',altIcon:'🔎',secondary:'Macro Lens'},
 Ladybird:{icon:'🐞',primary:'Spot Token',altIcon:'🔎',secondary:'Macro Lens'},
 Beetle:{icon:'🪲',primary:'Beetle Badge',altIcon:'🔎',secondary:'Macro Lens'},
 Ant:{icon:'🐜',primary:'Trail Token',altIcon:'🔎',secondary:'Macro Lens'},
 Spider:{icon:'🕸️',primary:'Web Emblem',altIcon:'🔎',secondary:'Macro Lens'},
 Dragonfly:{icon:'🪷',primary:'Pond Token',altIcon:'🔎',secondary:'Macro Lens'},
 Bird:{icon:'🪶',primary:'Feather Badge',altIcon:'🔭',secondary:'Binoculars'},
 Squirrel:{icon:'🌰',primary:'Acorn Stamp',altIcon:'🔭',secondary:'Binoculars'},
 Rabbit:{icon:'🥕',primary:'Carrot Token',altIcon:'🔭',secondary:'Binoculars'},
 Hedgehog:{icon:'🍂',primary:'Leaf Badge',altIcon:'🔭',secondary:'Binoculars'},
 Frog:{icon:'🍀',primary:'Pond Badge',altIcon:'🔎',secondary:'Focus Lens'},
 Other:{icon:'🧭',primary:'Explorer Token',altIcon:'🔎',secondary:'Focus Lens'},
 Unknown:{icon:'🧭',primary:'Discovery Token',altIcon:'🔎',secondary:'Focus Lens'}
};
s.wildTarget='Unknown';
function discoveryTool(){return FIELD_TOOLS[s.encounterAr?'Cat':s.wildTarget]||FIELD_TOOLS.Unknown}
function renderWildlifeTargetPicker(){
 return `<div class="wildlife-preselect"><label for="wild-target">What are you spotting?</label><select class="select" id="wild-target" aria-label="Animal you want to observe"><option value="Unknown">🧭 Surprise me / not sure</option>${SPECIES.map(v=>`<option value="${esc(v)}">${speciesIcon(v)} ${esc(v)}</option>`).join('')}</select><small>Choose an animal for its discovery tool. You can correct the species after the photo.</small></div>`;
}
function wireWildlifeTarget(){
 const field=$('wild-target');if(!field)return;
 field.value=s.wildTarget;
 field.onchange=()=>{s.wildTarget=FIELD_TOOLS[field.value]?field.value:'Unknown';if(s.wildTarget!=='Unknown')s.spottedSpecies=s.wildTarget;};
}
const zOldStartCatch=startCatch;
startCatch=function(animalId=null){
 s.wildTarget='Unknown';zOldStartCatch(animalId);
 const picker=document.querySelector('.capture-choice-v28');
 if(picker){picker.insertAdjacentHTML('beforebegin',renderWildlifeTargetPicker());wireWildlifeTarget();}
 const title=document.querySelector('.sheet-head h2');if(title)title.textContent='Spot wildlife 🎥';
};
const zOldLiveChoice=showLiveOnlyCameraChoice;
showLiveOnlyCameraChoice=function(message){
 zOldLiveChoice(message);
 const picker=$('live-only-retry');
 if(picker){picker.insertAdjacentHTML('beforebegin',renderWildlifeTargetPicker());wireWildlifeTarget();}
};
const zOldSyncDock=syncEncounterToolDock;
syncEncounterToolDock=function(kind){
 zOldSyncDock(kind);
 if(!s.encounterAr){
   const t=discoveryTool();
   const btnA=$('tool-ball'),btnB=$('tool-lure');
   if(btnA){btnA.querySelector('span').textContent=t.icon;btnA.setAttribute('aria-label','Switch to '+t.primary);btnA.title='Switch to '+t.primary;btnA.querySelector('small').textContent=t.primary==='Whisker Claw'?'Paw':'Token';}
   if(btnB){btnB.querySelector('span').textContent=t.altIcon;btnB.setAttribute('aria-label','Switch to '+t.secondary);btnB.title='Switch to '+t.secondary;btnB.querySelector('small').textContent=t.secondary==='Dangle Lure'?'Lure':t.secondary==='Binoculars'?'Binoculars':'Lens';}
   const item=$('throw-item');
   if(item){
     const prompt='<span class="drag-prompt">DRAG</span>';
     item.innerHTML=kind==='ball'&&s.wildTarget==='Cat'?whiskerPawSvgMarkup():`<span class="wild-tool-art" aria-hidden="true">${kind==='ball'?t.icon:t.altIcon}</span>`;
     item.insertAdjacentHTML('beforeend',prompt);
     item.classList.toggle('wild-token',s.wildTarget!=='Cat'||kind==='lure');
     item.setAttribute('aria-label',`Drag ${kind==='ball'?t.primary:t.secondary} to the animal`);
   }
   const status=$('encounter-status');
   if(status&&!s.encounterCaptured)status.textContent=kind==='ball'?`Drag the ${t.primary} onto the glowing ring.`:`Use the ${t.secondary} to focus the encounter first.`;
 }
};
const zOldShowEncounter=showEncounter;
showEncounter=function(image,quality,options={}){
 zOldShowEncounter(image,quality,options);
 if(options.ar||s.encounterAr||!$('encounter-stage'))return;
 const t=discoveryTool();
 const help=document.querySelector('.encounter-quick-help');if(help)help.textContent=`① Aim at the animal · ② Drag the ${t.primary} · ③ Discover!`;
 const guidance=document.querySelector('.encounter-instructions');if(guidance)guidance.textContent=`Drag the ${t.primary} onto the ring. The other tool is on the right.`;
 const h=document.querySelector('.encounter-help p');if(h)h.textContent=`These tools are virtual stamps and camera focus aids only. Never touch, bait, chase, collect or disturb wild animals.`;
 const orb=$('encounter-orb');if(orb){orb.innerHTML=s.wildTarget==='Cat'?whiskerPawSvgMarkup('capture-paw'):`<span class="wild-orb-art" aria-hidden="true">${t.icon}</span>`;orb.classList.toggle('wild-token',s.wildTarget!=='Cat');}
 syncEncounterToolDock(s.encounterTool||'ball');
};
const zOldHandleHit=handleEncounterHit;
handleEncounterHit=function(kind,accuracy=.45){
 if(s.encounterAr||s.wildTarget==='Cat')return zOldHandleHit(kind,accuracy);
 if(s.encounterCaptured||!$('encounter-status'))return;
 if(kind==='lure'){
   s.encounterLured=true;
   $('encounter-cat')?.classList.add('curious');
   s.encounterTool='ball';syncEncounterToolDock('ball');
   const status=$('encounter-status');if(status)status.textContent='Focused! Now use your '+discoveryTool().primary+'.';
   return;
 }
 if(s.captureSummary)s.captureSummary.throwRating=accuracy<=.23?'Wonderful!':accuracy<=.55?'Great!':'Nice!';
 runEncounterCapture();
};
const zOldShowCatForm=showCatForm;
showCatForm=function(image){
 zOldShowCatForm(image);
 if(!s.encounterAr&&$('wildlife-species')&&s.wildTarget!=='Unknown'){
   const select=$('wildlife-species');select.value=s.wildTarget;
   select.dispatchEvent(new Event('change',{bubbles:true}));
 }
};
const zOldRenderHome=renderHome;
renderHome=function(){
 return zOldRenderHome().replace(/YOUR CAT-CHASING ADVENTURE/g,'YOUR WILDLIFE ADVENTURE').replace(/Every whisker has a story\. Find yours\./g,'Every species has a story. Find yours.').replace(/THE WORLD IS YOUR CATDEX/g,'THE WORLD IS YOUR COLLECTION').replace(/See a cat\?/g,'Spot wildlife?').replace(/Meet real cats, level up and build your own legendary collection\./g,'Find real animals, discover new species and grow your Collection.').replace(/📸 Catch a cat →/g,'🎥 Spot wildlife →').replace(/Unique cats/g,'Discoveries').replace(/Your cat collection/g,'Your wildlife collection');
};



/* v3.8.3 — Hush Hunt visual Field Guide: all 17 species groups have illustrations
 * and tappable varieties. Offline bundled image assets; no model/remote calls.
 * Data keys, existing cat 'coat', and speciesDetail remain unchanged. */
const FIELD_GUIDE_VARIETIES={"Cat":["Tabby","Ginger","Brown","Black","White","Cream","Tuxedo","Calico","Tortoiseshell","Grey","Colourpoint","Other"],"Dog":["Labrador","Golden Retriever","Poodle","Terrier","Spaniel","Bulldog","Dachshund","Husky","Mixed Breed"],"Snail":["Garden Snail","Grove Snail","Roman Snail","Glass Snail","Amber Snail","Pond Snail","Other Snail"],"Butterfly":["Peacock","Red Admiral","Small Tortoiseshell","Painted Lady","Comma","Large White","Common Blue","Brimstone","Swallowtail","Blue Morpho"],"Moth":["Emperor Moth","Elephant Hawk-moth","Hummingbird Hawk-moth","Garden Tiger","Jersey Tiger","Six-spot Burnet","Silver Y"],"Bee":["Honeybee","Buff-tailed Bumblebee","Red-tailed Bumblebee","White-tailed Bumblebee","Common Carder Bee","Leafcutter Bee","Mining Bee","Wasp"],"Ladybird":["Seven-spot","Two-spot","Harlequin","Fourteen-spot","Pine Ladybird","Twenty-two-spot"],"Beetle":["Stag Beetle","Rose Chafer","Ground Beetle","Weevil","Soldier Beetle","Click Beetle","Longhorn Beetle","Dung Beetle"],"Dragonfly":["Emperor Dragonfly","Broad-bodied Chaser","Southern Hawker","Common Darter","Four-spotted Chaser","Golden-ringed Dragonfly"],"Ant":["Black Garden Ant","Red Ant","Wood Ant","Yellow Meadow Ant","Pavement Ant","Other Ant"],"Spider":["Garden Spider","House Spider","Jumping Spider","Zebra Spider","Wolf Spider","Crab Spider","Cellar Spider"],"Bird":["Robin","Blackbird","House Sparrow","Blue Tit","Great Tit","Magpie","Wood Pigeon","Starling","Crow","Seagull","Parakeet","Duck","Swan","Owl"],"Squirrel":["Grey Squirrel","Red Squirrel","Flying Squirrel","Ground Squirrel","Other Squirrel"],"Rabbit":["Wild Rabbit","Lop-eared","Dutch Rabbit","Lionhead","Netherland Dwarf","Flemish Giant"],"Hedgehog":["European Hedgehog","African Pygmy Hedgehog","Long-eared Hedgehog","Other Hedgehog"],"Frog":["Common Frog","Pool Frog","Marsh Frog","Tree Frog","Bullfrog","Other Frog"],"Other":["Fox","Deer","Mouse","Bat","Lizard","Worm","Slug","Fish","Tortoise","Other Animal"]};
const FIELD_GUIDE_EMOJI={"Cat": "🐱", "Dog": "🐶", "Snail": "🐌", "Butterfly": "🦋", "Moth": "🦋", "Bee": "🐝", "Ladybird": "🐞", "Beetle": "🪲", "Dragonfly": "🪰", "Ant": "🐜", "Spider": "🕷️", "Bird": "🐦", "Squirrel": "🐿️", "Rabbit": "🐰", "Hedgehog": "🦔", "Frog": "🐸", "Other": "🦊"};
s.spottedDetail=''; s.coatChoice=''; s.fieldGroupExpanded=false;
function fieldGuideArt(group,type=null){
 const name=v=>String(v).toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
 return 'field_art_v80/'+name(group)+'-'+(type?name(type):'group')+'.webp';
}
function safariCreatureArt(group,type=null){
 const name=v=>String(v).toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
 return 'safari_cutouts_v85/'+name(group)+'-'+(type?name(type):'group')+'.png';
}
function fieldGuideHash(text){let h=0;for(const ch of String(text)){h=(h*31+ch.charCodeAt(0))>>>0}return h>>>0}
function fieldGuideBadgeCode(group,name){
 const stop=new Set(['dragonfly','snail','spider','bird','beetle','moth','butterfly','bee','ladybird','ant','dog','cat','frog','rabbit','hedgehog','squirrel','animal','other','group']);
 const parts=String(name).split(/[^A-Za-z0-9]+/).filter(Boolean).filter(p=>!stop.has(p.toLowerCase()));
 if(!parts.length)return '?';
 return parts.slice(0,2).map(p=>p[0].toUpperCase()).join('');
}
function fieldGuideAccent(group,name){
 const palette=[['#5fc6ff','rgba(95,198,255,0.22)'],['#ffb36b','rgba(255,179,107,0.22)'],['#8fe388','rgba(143,227,136,0.22)'],['#ff8ab0','rgba(255,138,176,0.22)'],['#b197ff','rgba(177,151,255,0.22)'],['#ffd45f','rgba(255,212,95,0.22)'],['#6fe3d4','rgba(111,227,212,0.22)'],['#9ad1ff','rgba(154,209,255,0.22)']];
 const [badge,tint]=palette[fieldGuideHash(group+'|'+name)%palette.length];
 return {badge,tint,code:fieldGuideBadgeCode(group,name)};
}
function fieldGuideTile(name, group, opts={}){
 const isSelected=opts.selected===true,kind=opts.kind||'type';
 const img=opts.image||fieldGuideArt(group,name),action=kind==='group'?'data-guide-group':'data-guide-type';
 return `<button type="button" class="field-guide-tile ${kind==='group'?'field-guide-tile-group':''} ${isSelected?'chosen':''}" ${action}="${esc(name)}" aria-pressed="${isSelected?'true':'false'}" aria-label="${esc(name)}"><span class="field-guide-figure"><img src="${esc(img)}" loading="lazy" alt="" width="136" height="136"></span><span>${esc(name)}</span>${isSelected?'<span class="visual-tile-check" aria-hidden="true">✓</span>':''}</button>`;
}
function renderFieldGuideSpecies(){
 const grid=$('field-guide-species'),chosen=$('field-guide-selected');if(!grid||!chosen)return;
 const group=SPECIES.includes(s.spottedSpecies)?s.spottedSpecies:'Cat';
 grid.classList.toggle('hidden',!s.fieldGroupExpanded);
 chosen.innerHTML=`<img src="${fieldGuideArt(group)}" alt="" width="64" height="64"><span><strong>${esc(group)}</strong><small>Tap Change animal to choose another</small></span><span class="field-guide-check">✓</span>`;
 grid.innerHTML=SPECIES.map(x=>fieldGuideTile(x,x,{selected:x===group,kind:'group',image:fieldGuideArt(x)})).join('');
 grid.querySelectorAll('[data-guide-group]').forEach(btn=>btn.onclick=()=>{
  s.fieldGroupExpanded=false;const selected=$('wildlife-species');selected.value=btn.dataset.guideGroup;
  selected.dispatchEvent(new Event('change',{bubbles:true}));
 });
 $('change-species').onclick=()=>{s.fieldGroupExpanded=!s.fieldGroupExpanded;renderFieldGuideSpecies()};
}
function renderFieldGuideVarieties(){
 const grid=$('field-guide-types');if(!grid)return;
 const group=s.spottedSpecies,options=FIELD_GUIDE_VARIETIES[group]||FIELD_GUIDE_VARIETIES.Other;
 const selected=group==='Cat'?($('cat-coat')?.value||'Other'):s.spottedDetail;
 grid.innerHTML=options.map(x=>fieldGuideTile(x,group,{selected:selected===x})).join('')+
 (group==='Cat'?'':fieldGuideTile('Not sure',group,{selected:!selected, image:fieldGuideArt('Other','Not sure')}));
 grid.querySelectorAll('[data-guide-type]').forEach(btn=>btn.onclick=()=>{
  const value=btn.dataset.guideType;
  if(group==='Cat'){$('cat-coat').value=value;s.coatChoice=value;}
  else{s.spottedDetail=value==='Not sure'?'':value;$('wildlife-detail').value=s.spottedDetail;}
  grid.querySelectorAll('[data-guide-type]').forEach(x=>{const on=x===btn;x.classList.toggle('chosen',on);x.setAttribute('aria-pressed',String(on));});
  const custom=$('wildlife-detail');if(custom)custom.classList.add('hidden');
  const tip=grid.parentElement?.querySelector('#hush-inline-tip');
  if(tip){
   const selection=group==='Cat'?($('cat-coat')?.value||'Other'):(s.spottedDetail||'Not sure');
   tip.textContent='Look for: '+(HUSH_FIELD_EDUCATION.types[group]?.[selection]||HUSH_FIELD_EDUCATION.groups[group]||HUSH_FIELD_EDUCATION.groups.Other);
  }
 });
 if(group!=='Cat'&&selected===''){
  const unsure=[...grid.querySelectorAll('[data-guide-type]')].find(x=>x.dataset.guideType==='Not sure');
  unsure?.classList.add('chosen');unsure?.setAttribute('aria-pressed','true');
 }
}
function initEditFieldGuide(animal){
 s.editVisualDetail=speciesOf(animal)==='Cat'?animal.coat||'Other':animal.speciesDetail||'';
 const anchor=$('edit-species-detail');if(!anchor)return;
 const wrap=document.createElement('div');wrap.id='edit-field-guide';wrap.className='edit-field-guide';
 wrap.innerHTML='<div class="visual-field-heading"><div><span class="visual-step">EASY IDENTIFICATION</span><h3>Tap a picture to change the type</h3></div></div><div id="edit-visual-types" class="field-guide-types"></div>';
 anchor.closest('.field-group').before(wrap);
}
function renderEditFieldGuide(){
 const grid=$('edit-visual-types');if(!grid)return;
 const group=$('edit-species')?.value||'Cat';const types=FIELD_GUIDE_VARIETIES[group]||FIELD_GUIDE_VARIETIES.Other;
 const detail=$('edit-species-detail');const coat=$('edit-coat');
 const active=group==='Cat'?coat?.value:detail?.value;
 grid.innerHTML=types.map(t=>fieldGuideTile(t,group,{selected:active===t})).join('')+
 (group==='Cat'?'':fieldGuideTile('Not sure',group,{selected:!active,image:fieldGuideArt('Other','Not sure')}));
 grid.querySelectorAll('[data-guide-type]').forEach(btn=>btn.onclick=()=>{
  const v=btn.dataset.guideType;
  if(group==='Cat'){if(coat)coat.value=v;}
  else if(detail)detail.value=v==='Not sure'?'':v;
  renderEditFieldGuide();
 });
}

// Little album of wildlife varieties; old cat coat Bingo remains unchanged.
const hushOldDex=renderDex;
renderDex=function(){
 let html=hushOldDex();
 const kind=s.filter.startsWith('Species:')?s.filter.slice(8):null;
 if(!kind||!FIELD_GUIDE_VARIETIES[kind]||kind==='Cat')return html;
 const items=FIELD_GUIDE_VARIETIES[kind];
 const spotted=new Set(visibleWildlife().filter(c=>speciesOf(c)===kind).map(c=>String(c.speciesDetail||'').trim().toLowerCase()).filter(Boolean));
 const num=items.filter(x=>spotted.has(x.toLowerCase())).length;
 const tiles=items.map(x=>`<div class="variant-album-tile ${spotted.has(x.toLowerCase())?'unlocked':''}"><img src="${fieldGuideArt(kind,x)}" alt="" loading="lazy" width="80" height="80"><span>${esc(x)}</span><small>${spotted.has(x.toLowerCase())?'✓ DISCOVERED':'○ TO DISCOVER'}</small></div>`).join('');
 const album=`<section class="variant-album"><div class="visual-field-heading"><div><span class="visual-step">YOUR WILDLIFE ALBUM</span><h3>${esc(kind)} varieties</h3></div><strong class="variant-progress">${num} / ${items.length}</strong></div><div class="variant-album-grid">${tiles}</div><p class="field-help">Discover types through live sightings. Not sure of the exact type? You can still save the animal.</p></section>`;
 return html.replace('<div id="dex-grid">',album+'<div id="dex-grid">');
};
// Reuse the established home layout, with wildlife rather than one cat as its hero.
const hushOldHome=renderHome;
renderHome=function(){return hushOldHome().replace('<span class="hero-cat" aria-hidden="true">🐈</span>','<span class="hero-cat hush-hero-animal" aria-hidden="true">🦋<span>🐌</span></span>')};
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
  const mount=$('encounter-ar-cat');if(mount)mount.innerHTML=`<img class="ar-wildlife-art" src="${safariCreatureArt(group,m.speciesDetail)}" alt="Illustrated ${esc(m.name)}">`;
 }
 const badge=$('ar-model-badge');if(badge)badge.textContent=`${speciesIcon(group)} Virtual ${group.toLowerCase()}: ${m.name}`;
 const tag=document.querySelector('.encounter-capture-tag');if(tag&&s.encounterAr)tag.textContent=`● 2D · VIRTUAL ${group.toUpperCase()}`;
 const help=document.querySelector('.encounter-quick-help');if(help&&s.encounterAr)help.textContent=`✨ ${group} found! Drag the discovery token to collect it.`;
 const title=document.querySelector('.encounter-help p');if(title&&s.encounterAr)title.textContent='This is a stylised 2D creature overlay, not true world-tracked AR. Animals are fictional game encounters; no real wildlife is handled or disturbed.';
 const primary=$('throw-item');if(primary&&s.encounterAr&&!s.encounterCaptured){primary.innerHTML=group==='Cat'?whiskerPawSvgMarkup():['Butterfly','Moth'].includes(group)?hushNetSvg():`<span class="wild-tool-art" aria-hidden="true">${FIELD_TOOLS[group]?.icon||'🧭'}</span>`;primary.insertAdjacentHTML('beforeend','<span class="drag-prompt">DRAG</span>');primary.classList.toggle('wild-token',group!=='Cat');}
 const alt=$('tool-lure');if(alt&&s.encounterAr){const tool=FIELD_TOOLS[group]||FIELD_TOOLS.Cat;alt.querySelector('span').textContent=tool.altIcon;alt.querySelector('small').textContent=tool.secondary;alt.setAttribute('aria-label',`Switch to ${tool.secondary}`);}
};
const hushOldSafariName=showVirtualNamingForm;
showVirtualNamingForm=function(){hushOldSafariName();const m=getArModel(s.arModelKey);const group=m.species||'Cat';const label=document.querySelector('label[for="virtual-name"]');if(label)label.textContent=`${group} name`;const btn=$('virtual-save-final');if(btn)btn.textContent=`Keep this ${group.toLowerCase()} ${speciesIcon(group)}`;};
const hushOldVirtualGallery=renderVirtualGallery;
renderVirtualGallery=function(){return hushOldVirtualGallery().replace('My AR cats 🐾','My AR wildlife ✨').replace(/(\d+) cats<\/span>/,'$1 creatures</span>').replace('cats discovered','virtual creatures discovered').replace('cats are available','creatures are available').replace('a new cat in a new habitat','new wildlife friends in different habitats').replace('rarer cats appear less often','rarer creatures appear less often');};
const hushOldVirtualDetail=openVirtualCatDetail;
openVirtualCatDetail=function(cat){hushOldVirtualDetail(cat);const g=speciesOf(cat);const btn=$('virtual-find-more');if(btn)btn.textContent='✨ Find more virtual wildlife';const del=$('virtual-delete');if(del)del.textContent='Delete virtual discovery';};
// All 17 species get an illustrated, collectible challenge. The original Cat Bingo
// remains as a bonus challenge for existing users instead of losing old progress.
const hushPrevDex384=renderDex;
renderDex=function(){
 let html=hushPrevDex384();
 const real=s.cats.filter(c=>!c.virtual);
 const discoveredGroups=new Set(real.map(c=>speciesOf(c)));
 const tiles=SPECIES.map(group=>{
  const found=real.filter(c=>speciesOf(c)===group);
  const varieties=new Set(found.map(c=>group==='Cat'?(c.coat||'Other'):(c.speciesDetail||''))).size;
  const total=FIELD_GUIDE_VARIETIES[group]?.length||1;
  return `<button type="button" class="hush-challenge-tile ${found.length?'found':''}" data-hush-filter="Species:${esc(group)}" aria-label="See ${esc(group)} discoveries"><img src="${fieldGuideArt(group)}" alt=""><strong>${esc(group)}</strong><small>${found.length?`${varieties} / ${total} kinds`:'Not found yet'}</small><span class="hush-tick">${found.length?'✓':'?'}</span></button>`;
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
 const tag=$('encounter-species-hint');if(tag)tag.textContent='';
}
function hushNetSvg(){return `<svg class="hush-photo-net-svg" viewBox="0 0 94 110" role="img" aria-label="Virtual photo net"><defs><linearGradient id="hush-net-rim" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#c0eaff"/><stop offset="1" stop-color="#71abdd"/></linearGradient></defs><path d="M47 62 L17 108" stroke="#bd8056" stroke-linecap="round" stroke-width="9"/><path d="M47 63 L17 108" stroke="#f9c394" stroke-linecap="round" stroke-width="4"/><ellipse cx="55" cy="36" rx="33" ry="29" transform="rotate(-18 55 36)" fill="#e2f9ff42" stroke="url(#hush-net-rim)" stroke-width="7"/><g stroke="#9cd5ec" stroke-width="1.4" opacity=".78"><path d="M24 34L78 15M22 44L88 26M29 55L87 37M39 62L84 49M31 18L64 64M45 10L77 54M60 7L87 40M25 35L52 64"/></g></svg>`;}
const hushPriorSyncTool=syncEncounterToolDock;
syncEncounterToolDock=function(kind){hushPriorSyncTool(kind);if(!s.encounterAr&&['Butterfly','Moth'].includes(s.wildTarget)&&kind==='ball'){const item=$('throw-item');if(item)item.innerHTML=hushNetSvg()+'<span class="drag-prompt">DRAG</span>';}};
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
function hushDistanceText(km){
 if(!Number.isFinite(km)||km<0)return 'Distance unavailable';
 if(km<.1)return 'Same approximate area';
 if(hushViewSettings(s.profile.viewSettings).units==='imperial'){
  // Rounded ~1km pins have significant uncertainty; never show falsely precise yards.
  if(km<.4)return `≈ ${Math.max(100,Math.round(km*1093.6133/100)*100)} yd straight-line`;
  const mi=km*.6213711922;return `≈ ${mi<10?mi.toFixed(1):Math.round(mi)} mi straight-line`;
 }
 if(km<1)return `≈ ${Math.max(100,Math.round(km*1000/100)*100)} m straight-line`;
 return `≈ ${km<10?km.toFixed(1):Math.round(km)} km straight-line`;
}
function hushProject(lat,lng,z){const n=256*2**z,clamped=Math.max(-85.05,Math.min(85.05,lat));const sin=Math.sin(clamped*Math.PI/180);return {x:(lng+180)/360*n,y:(.5-Math.log((1+sin)/(1-sin))/(4*Math.PI))*n}}
function hushUnproject(x,y,z){const n=256*2**z;return {lng:x/n*360-180,lat:Math.atan(Math.sinh(Math.PI*(1-2*y/n)))*180/Math.PI}}
const hushOldRenderExplore=renderExplore;
renderExplore=function(){
 s.hushStreetEnabled=hushViewSettings(s.profile.viewSettings).streetMapEnabled;
 let html=hushOldRenderExplore().replace('<h1>Cat map 🗺️</h1>','<h1>Wildlife map 🗺️</h1>');
 if(s.hushStreetEnabled)html=html.replace('This is a private location plot, not a street map.','The private plot above is offline; the optional street map below loads online tiles.');
 const geo=savedMapPoints();
 const map=`<section class="hush-street-section"><div class="flex between"><div><div class="eyebrow">OPTIONAL ONLINE MAP</div><h3>Explore the real streets 🗺️</h3></div><button id="hush-street-toggle" type="button" class="${s.hushStreetEnabled?'secondary':'primary'}">${s.hushStreetEnabled?'🔒 Private plot':'🌍 Street map'}</button></div><p class="dim">${s.hushStreetEnabled?'Street tiles load from OpenStreetMap when this page is open. Your choice is remembered in Profile; turn it off at any time.':'The private plot above stays completely offline. Enable street tiles to view streets and remember that choice for next time. OpenStreetMap can see the map area you browse.'}</p>${s.hushStreetEnabled&&geo.length?`<div id="hush-street-map" class="hush-street-map" aria-label="Interactive map with saved wildlife sightings"><div id="hush-tile-canvas" class="hush-tile-canvas"></div><div id="hush-street-pins"></div><div class="hush-map-controls"><button type="button" id="hush-zoom-in" aria-label="Zoom in">+</button><button type="button" id="hush-zoom-out" aria-label="Zoom out">−</button><button type="button" id="hush-map-reset" aria-label="Show all saved locations">⌖</button></div><span class="hush-osm-credit">© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a></span></div><div id="hush-map-distances" class="hush-map-distances" aria-live="polite"></div><small class="footnote">Distances use your Profile units and are rough straight-line estimates between ~1 km-rounded pins—not walking distances or precise wildlife locations. Drag to pan, use +/− to zoom.</small>`:''}</section>`;
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
 const existing=new Map([...tiles.querySelectorAll('.hush-map-tile')].map(el=>[el.dataset.tileKey,el]));
 const needed=new Set();
 for(let tx=tx0;tx<=tx1;tx++)for(let ty=ty0;ty<=ty1;ty++){
  if(ty<0||ty>=limit)continue;
  const x=((tx%limit)+limit)%limit,key=`${z}/${x}/${ty}`;needed.add(key);
  let el=existing.get(key);
  if(!el){el=document.createElement('img');el.className='hush-map-tile';el.alt='';el.draggable=false;el.dataset.tileKey=key;el.src=`https://tile.openstreetmap.org/${key}.png`;tiles.appendChild(el)}
  el.style.left=`${Math.round(tx*256-left)}px`;el.style.top=`${Math.round(ty*256-top)}px`;
 }
 for(const [key,el] of existing){if(!needed.has(key))el.remove()}
 pins.innerHTML=geo.map((g,i)=>{const p=hushProject(g.lat,g.lng,z);const near=geo.slice(0,i).filter(o=>o.lat===g.lat&&o.lng===g.lng).length;let x=p.x-left+near*13,y=p.y-top+near*13;return `<button type="button" class="hush-street-pin ${i===s.hushSelectedIndex?'chosen':''}" data-street-index="${i}" style="left:${x}px;top:${y}px" aria-label="Show ${esc(g.name)} on map"><span>${speciesIcon(g.species)}</span><small>${esc(g.name)}</small></button>`}).join('');
 pins.querySelectorAll('[data-street-index]').forEach(btn=>btn.onclick=()=>hushStreetSelection(Number(btn.dataset.streetIndex)));
 hushStreetSelection(Math.min(s.hushSelectedIndex,geo.length-1));
}
function hushOpenStreetConsent(){openModal(`<div class="sheet-head"><h2>See street tiles? 🗺️</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p>To show an interactive map inside Hush Hunt, your phone will download map tiles from <strong>OpenStreetMap</strong>.</p><p class="dim">OpenStreetMap may see your IP address and which approximate map areas you browse. We do not upload your photos, collection or complete list of pins. Zooming and panning may request more tiles. Ask a trusted adult if you're unsure.</p><div class="actions"><button type="button" class="secondary" id="hush-map-cancel">Stay private</button><button type="button" class="primary" id="hush-map-accept">Show street map</button></div>`);$('hush-map-cancel').onclick=closeModal;$('hush-map-accept').onclick=async()=>{const btn=$('hush-map-accept');btn.disabled=true;try{await hushSaveViewSettings({streetMapEnabled:true});s.hushStreetCenter=null;closeModal();render()}catch(e){btn.disabled=false;toast('Could not remember the street map setting. Try again.')}};}
function hushWireStreet(){
 const toggle=$('hush-street-toggle');if(!toggle)return;
 toggle.onclick=async()=>{if(s.hushStreetEnabled){toggle.disabled=true;try{await hushSaveViewSettings({streetMapEnabled:false});render()}catch(e){toggle.disabled=false;toast('Could not save your map choice.')}}else hushOpenStreetConsent()};
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
wireScreen=function(){hushOldWireScreen();document.querySelectorAll('[data-hush-filter]').forEach(b=>b.onclick=()=>{s.filter=b.dataset.hushFilter;render()});if(s.screen==='explore')hushWireStreet();};
const hushOldSelectPin=selectPrivateMapPin;
selectPrivateMapPin=function(i){hushOldSelectPin(i);hushStreetSelection(i)};

/* v3.8.5 — native ARCore optional world-tracked Safari.
   Native ARCore uses camera tracking, a plane hit-test and a world anchor.
   Native ARCore uses true low-poly OpenGL animal meshes. 2D Safari uses illustrated sprites.
   Browser and unsupported Android devices use the previous 2D Safari unchanged. */
s.hushNativeArPhoto=null;
s.hushNativeArPendingModel=null;
const hushOriginalVirtualPhoto=makeVirtualScenePhoto;
makeVirtualScenePhoto=async function(model,frame,focus,habitat){
 if(s.hushNativeArPhoto && frame===s.hushNativeArPhoto) return frame;
 return hushOriginalVirtualPhoto(model,frame,focus,habitat);
};
function hushChooseArSafari(){
 const supported=hasAndroidActionBridge();
 openModal(`<div class="sheet-head"><h2>AR Safari ✨</h2><button class="close-btn" data-close aria-label="Close">×</button></div>
 <p class="dim">Find playful wildlife friends around you. Which mode would you like?</p>
 <div class="hush-ar-choice"><button id="hush-arcore-start" class="choice" type="button" ><span>🌍</span><strong>ARCore • Real surfaces</strong><small>Place a low-poly 3D creature on a tracked surface. Walk around it to see different angles.</small></button>
 <button id="hush-ar-2d" class="choice" type="button"><span>✨</span><strong>2D Safari • Quick play</strong><small>All devices · illustrated camera overlays · no surface tracking.</small></button></div>
 <p class="footnote">${supported?'ARCore needs a supported phone, Google Play Services for AR and camera permission.':'Tap to try ARCore on your device; the Android app will tell you if AR services need installing.'} Google Play Services for AR is provided by Google LLC and governed by the Google Privacy Policy. The ARCore models are stylised low-poly prototypes, not photorealistic animals. Only tap Collect to save a photo.</p>`);
 $('hush-ar-2d').onclick=()=>hushOriginalStartArEncounter();
 $('hush-arcore-start').onclick=hushLaunchArCore;
}
const hushOriginalStartArEncounter=startArEncounter;
startArEncounter=function(){return hushChooseArSafari()};
function hushLaunchArCore(){
 if(!hasAndroidActionBridge()){
  openModal('<div class="sheet-head"><h2>ARCore needs the Android app</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim">Real-world surface tracking only works in the installed Android version of Hush Hunt. The browser demo supports 2D Safari instead.</p><div class="actions"><button type="button" class="primary" id="hush-ar-use-2d">✨ Try 2D Safari</button></div>');
  $('hush-ar-use-2d').onclick=hushOriginalStartArEncounter;return;
 }
 const model=randomArModel(),group=model.species||'Cat';
 s.hushNativeArPendingModel=model.key;
 // Native ARCore constructs genuine low-poly 3D geometry, without
 // relying on the separately versioned 2D Safari PNG cutouts.
 closeModal();
 toast('Opening ARCore Safari… Move your phone slowly to find a surface.');
 const pairs=[['model',model.key],['name',model.name],['species',group]];
 location.href='whiskerhunt://arcore?'+pairs.map(([k,v])=>k+'='+encodeURIComponent(v)).join('&');
}
window.hushNativeArCoreResult=function(result){
 if(!result||typeof result!=='object')return;
 if(result.status==='captured' && typeof result.photo==='string' && result.photo.startsWith('data:image/jpeg;base64,') && result.photo.length<8000000){
  // Never attach the photo to a real wildlife sighting. This is an AR virtual collection entry.
  const model=getArModel(result.model||s.hushNativeArPendingModel);
  s.arModelKey=model.key;
  s.arHabitatKey=randomArHabitat().key;
  s.image=result.photo;
  s.hushNativeArPhoto=result.photo;
  s.encounterCaptured=true;
  s.encounterAr=true;
  s.encounterLive=false;
  s.encounterFocus={x:.5,y:.58};
  s.hushNativeArPendingModel=null;
  showVirtualNamingForm();
  const note=$('virtual-photo-preview')?.nextElementSibling;
  if(note){const msg=result.message||'Native AR encounter';note.insertAdjacentHTML('beforebegin',`<p class="info-note">🌍 ${esc(msg)} This is a low-poly 3D animal at a world-tracked ARCore anchor.</p>`);}
  return;
 }
 s.hushNativeArPendingModel=null;
 if(result.status==='fallback')return hushOriginalStartArEncounter();
 if(result.status==='cancelled')return;
 openModal(`<div class="sheet-head"><h2>ARCore not ready</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim">${esc(result.message||'Native ARCore cannot run right now.')}</p><button id="hush-ar-fallback" class="primary" type="button">✨ Use 2D Safari instead</button>`);
 $('hush-ar-fallback').onclick=()=>hushOriginalStartArEncounter();
};
const hushOldCloseArModal=closeModal;
closeModal=function(){
 const result=hushOldCloseArModal();
 // Retain native photo until the naming/save action has used it. A new Safari
 // encounter explicitly resets it, so stale captures cannot be reused.
 return result;
};


/* v3.8.6 — persisted explorer preferences and species-correct virtual Safari.
   Storage IDs, backup version and native app identifier must not change. */
function hushViewSettings(value){
 const v=value&&typeof value==='object'&&!Array.isArray(value)?value:{};
 return {units:v.units==='metric'?'metric':'imperial',streetMapEnabled:v.streetMapEnabled===true};
}
async function hushSaveViewSettings(next){
 if(s.storageBlocked)throw new Error('Storage recovery is required');
 const previous=hushViewSettings(s.profile.viewSettings);
 const proposed=hushViewSettings({...previous,...next});
 s.profile.viewSettings=proposed;
 s.hushStreetEnabled=proposed.streetMapEnabled;
 try{await saveProfile()}catch(error){s.profile.viewSettings=previous;s.hushStreetEnabled=previous.streetMapEnabled;throw error}
 return proposed;
}
const hushPreviousRenderProfile386=renderProfile;
renderProfile=function(){
 const pref=hushViewSettings(s.profile.viewSettings);
 const panel=`<section class="soft-card hush-view-prefs" aria-label="Map and distance preferences">
 <div class="eyebrow">EXPLORER SETTINGS</div><h3>🧭 My map preferences</h3>
 <p class="dim">Choose how your discovery distances appear. Both options use approximate saved pins.</p>
 <label for="hush-unit-setting"><strong>Distance units</strong></label>
 <select id="hush-unit-setting" class="select" aria-label="Distance units">
 <option value="imperial" ${pref.units==='imperial'?'selected':''}>Miles & yards (UK)</option>
 <option value="metric" ${pref.units==='metric'?'selected':''}>Kilometres & metres</option></select>
 <label class="check-row hush-street-preference"><input id="hush-street-setting" type="checkbox" ${pref.streetMapEnabled?'checked':''}><span><strong>Remember street map</strong><small>When enabled, opening Map downloads online OpenStreetMap tiles. Turn this off for private, offline-only viewing.</small></span></label>
 <p class="footnote">Online street tiles can reveal your approximate viewed area and IP address to the map service. Your saved collection and photos are not uploaded.</p>
 </section>`;
 const main=hushPreviousRenderProfile386().replace('<div class="profile-avatar">🐱</div>','<div class="profile-avatar">🧭</div>').replace('🐱 Missing a cat?','🧭 Missing discoveries?').replace('Find missing cats from a saved recovery copy.','Find missing wildlife discoveries from a saved recovery copy.').replace('🔎 Find missing cats','🔎 Find missing discoveries');
 return main.replace('<div class="section-title"><h2>Your discovery insights',panel+'<div class="section-title"><h2>Your discovery insights');
};
const hushPreviousWireScreen386=wireScreen;
wireScreen=function(){
 hushPreviousWireScreen386();
 if(s.screen!=='profile')return;
 const units=$('hush-unit-setting'),street=$('hush-street-setting');
 if(units)units.onchange=async()=>{
  units.disabled=true;
  try{await hushSaveViewSettings({units:units.value});toast('Distance units saved.');}
  catch(error){toast('Could not save your units.');}
  finally{units.disabled=false;units.value=hushViewSettings(s.profile.viewSettings).units;}
 };
 if(street)street.onchange=async()=>{
  const wanted=street.checked,previous=hushViewSettings(s.profile.viewSettings);
  if(wanted&&!previous.streetMapEnabled){
   street.checked=false;
   hushOpenStreetConsent();
   return;
  }
  street.disabled=true;
  try{await hushSaveViewSettings({streetMapEnabled:wanted});toast(wanted?'Street map preference saved.':'Offline private map preferred.');}
  catch(error){toast('Could not save your map preference.');}
  finally{street.disabled=false;street.checked=hushViewSettings(s.profile.viewSettings).streetMapEnabled;}
 };
};
function hushSafariSpecies(){return getArModel(s.arModelKey).species||'Cat'}
function hushSafariTool(){return FIELD_TOOLS[hushSafariSpecies()]||FIELD_TOOLS.Unknown}
function hushSafariSymbol(group,kind){
 const tool=FIELD_TOOLS[group]||FIELD_TOOLS.Unknown;
 if(kind==='lure')return `<span class="wild-tool-art" aria-hidden="true">${tool.altIcon}</span>`;
 if(group==='Cat')return whiskerPawSvgMarkup();
 if(group==='Butterfly'||group==='Moth')return hushNetSvg();
 return `<span class="wild-tool-art" aria-hidden="true">${tool.icon}</span>`;
}
function hushUpdateSafariInterface(){
 if(!s.encounterAr||!$('encounter-stage'))return;
 const model=getArModel(s.arModelKey),group=model.species||'Cat',tool=hushSafariTool();
 const habitat=getArHabitat(s.arHabitatKey);
 const current=s.encounterTool||'ball';
 const item=$('throw-item');
 if(item&&!s.encounterCaptured){item.innerHTML=hushSafariSymbol(group,current)+'<span class="drag-prompt">DRAG</span>';item.classList.toggle('wild-token',group!=='Cat'||current==='lure');item.setAttribute('aria-label',`Drag ${current==='ball'?tool.primary:tool.secondary} to collect the virtual ${group.toLowerCase()}`)}
 const orb=$('encounter-orb');
 if(orb){orb.innerHTML=hushSafariSymbol(group,'ball');orb.classList.toggle('wild-token',group!=='Cat');}
 const alt=$('tool-lure'),primary=$('tool-ball');
 if(alt){const span=alt.querySelector('span'),small=alt.querySelector('small');if(span)span.textContent=tool.altIcon;if(small)small.textContent=`Switch to ${tool.secondary}`;alt.title=`Switch to ${tool.secondary}`;alt.setAttribute('aria-label',`Switch to ${tool.secondary}`)}
 if(primary){const span=primary.querySelector('span'),small=primary.querySelector('small');if(span)span.textContent=tool.icon;if(small)small.textContent=`Switch to ${tool.primary}`;primary.title=`Switch to ${tool.primary}`;primary.setAttribute('aria-label',`Switch to ${tool.primary}`)}
 const help=document.querySelector('.encounter-quick-help');
 if(help)help.textContent=`✨ ${group} found! Drag the ${tool.primary} to collect it.`;
 const note=document.querySelector('.ar-smart-note');
 if(note)note.innerHTML=`Discover ${AR_CAT_MODELS.length} virtual varieties from ${SPECIES.length} wildlife groups. Today's ${esc(group.toLowerCase())} appeared in <strong>${esc(habitat.name)}</strong> · ${esc(habitat.badge)}. Rare creatures appear less often.`;
 const status=$('encounter-status');
 if(status&&!s.encounterCaptured)status.textContent=current==='ball'?`A ${model.name} appeared! Drag the ${tool.primary} onto the ring.`:`Use the ${tool.secondary} to focus this virtual ${group.toLowerCase()}.`;
 const caption=document.querySelector('.encounter-instructions');
 if(caption)caption.textContent=`${tool.primary} for ${group.toLowerCase()} · ${tool.secondary} is the alternate tool.`;
 const quality=$('encounter-quality');if(quality&&s.encounterAr)quality.innerHTML=`✨ Virtual ${esc(group.toLowerCase())} · illustrative camera overlay · no video uploaded. <small>For world-tracked surfaces, choose ARCore mode.</small>`;
 const tag=document.querySelector('.encounter-capture-tag');if(tag)tag.textContent=`● 2D · VIRTUAL ${group.toUpperCase()}`;
 const meow=$('encounter-meow');if(meow)meow.textContent=group==='Cat'?'Meow!':'✨';
 const action=$('encounter-continue');if(action)action.textContent=`Keep this ${group.toLowerCase()} ${speciesIcon(group)}`;
 const foot=document.querySelector('.ar-sheet .footnote');if(foot)foot.textContent='Virtual 2D wildlife preview. Species artwork is illustrative; choose ARCore for tracked surfaces. Keep a safe distance from real animals.';
}
const hushPreviousSyncDock386=syncEncounterToolDock;
syncEncounterToolDock=function(kind){hushPreviousSyncDock386(kind);if(s.encounterAr)hushUpdateSafariInterface()};
const hushPreviousRefresh386=refreshArEncounterUi;
refreshArEncounterUi=function(){hushPreviousRefresh386();hushUpdateSafariInterface()};
const hushPreviousShowVirtualNaming386=showVirtualNamingForm;
showVirtualNamingForm=function(){hushPreviousShowVirtualNaming386();const group=hushSafariSpecies(),btn=$('virtual-save-final');if(btn)btn.textContent=`Keep this ${group.toLowerCase()} ${speciesIcon(group)}`;const title=document.querySelector('.sheet-head h2');if(title)title.textContent=`${speciesIcon(group)} ${group==='Cat'?'A virtual cat':'A virtual '+group.toLowerCase()} discovery!`;};
const hushPreviousRenderVirtualGallery386=renderVirtualGallery;
renderVirtualGallery=function(){return hushPreviousRenderVirtualGallery386().replaceAll('My AR cats 🐾','My AR wildlife ✨').replace(/\b(\d+) cats\b/g,'$1 creatures').replace('cats discovered','virtual creatures discovered').replace('cats are available','creatures are available').replace('new cat in a new habitat','new creature in a new habitat').replace('rarer cats appear less often','rarer creatures appear less often')};
const hushPreviousRenderHome386=renderHome;
renderHome=function(){
 return hushPreviousRenderHome386().replace('YOUR CAT-CHASING ADVENTURE','YOUR WILDLIFE ADVENTURE').replace('Every whisker has a story. Find yours.','Every little life has a story. Find yours.').replace('✦ THE WORLD IS YOUR CATDEX','✦ THE WORLD IS YOUR COLLECTION').replace('See a cat?<br>Catch the moment.','See wildlife?<br>Catch the moment.').replace('Meet real cats, level up and build your own legendary collection.','Spot real wildlife, earn XP and build a collection of discoveries.').replace('📸 Catch a cat →','📸 Spot wildlife →').replace('Unique cats','Discoveries').replace('Your cat collection','Your wildlife collection').replace('Found a friendly-looking feline? Snap your first cat and bring your Collection to life.','Find a creature, spot it live, and start your Collection.');
};
const hushPreviousRenderQuests386=renderQuests;
renderQuests=function(){return hushPreviousRenderQuests386().replace('No need to disturb cats or visit private property.','Never disturb wildlife or enter private property.');};
const hushPreviousOpenHealth386=openCollectionHealth;
openCollectionHealth=function(){hushPreviousOpenHealth386();const modal=$('modal-layer');if(!modal)return;const num=s.cats.length;modal.querySelectorAll('p').forEach(p=>{if(p.textContent.includes(' cats ·'))p.innerHTML=p.innerHTML.replace(`${num} cats ·`,`${num} discoveries ·`);if(p.textContent.includes('photos show cats'))p.textContent='The scan checks record structure, not species identification or device storage health.'});};

const hushPreviousDexConsistency386=renderDex;
renderDex=function(){return hushPreviousDexConsistency386().replace(/(\d+) virtual cats/g,'$1 virtual wildlife').replace(/virtual cats discovered/g,'virtual wildlife discovered')};

const hushPreviousInsights386=collectionInsights;
collectionInsights=function(){
 const real=s.cats.filter(c=>!c.virtual);
 const kinds=new Set(real.map(c=>`${speciesOf(c)}:${speciesOf(c)==='Cat'?(c.coat||'Other'):(c.speciesDetail||'Not sure')}`));
 const total=Object.values(FIELD_GUIDE_VARIETIES).reduce((n,v)=>n+(Array.isArray(v)?v.length:0),0);
 return hushPreviousInsights386().replace(/<small>🌈 Coat varieties<\/small><strong>[^<]*<\/strong><span>Different appearances<\/span>/,`<small>🌎 Wildlife varieties</small><strong>${kinds.size} / ${total}</strong><span>Different animal types spotted</span>`);
};
const hushPreviousRenderJournal386=renderJournal;
renderJournal=function(){return hushPreviousRenderJournal386().replace('>New cats</button>','>New finds</button>')};
const hushPreviousJournalCards386=journalCards;
journalCards=function(){return hushPreviousJournalCards386().replace('capture a cat to start your journal','spot wildlife live to start your journal').replace('📸 Catch a cat','🎥 Spot wildlife')};



/* v3.8.9 — collection wording, clearer variety tiles, and ARCore gate fix.
   These are optional, editable creative prompts, NOT statements of what a camera identified.
   All legacy data/schema/backup identifiers remain unchanged. */
const HUSH_DICE_NAMES={
 Cat:['Mochi','Purrcy','Mittens','Whisk','Nimbus','Tabbykins','Velvet','Biscuit'],
 Dog:['Barkley','Scout','Waffles','Rover','Biscuit','Teddy','Pippin','Tango'],
 Snail:['Shellbert','Swirly','Scoot','Pebble','Snailor','Puddles','Slowmo','Cinnamon'],
 Butterfly:['Flutter','Mariposa','Prism','Sunny','Petal','Twirl','Papillon','Dazzle'],
 Moth:['Luna','Moonbeam','Dusty','Lantern','Velvet','Misty','Twilight','Ember'],
 Bee:['Bumble','Buzzby','Honeydrop','Pollen','Zippy','Goldie','Daisy','Nectar'],
 Ladybird:['Dotty','Speckles','Ruby','Lucky','Button','Polka','Poppy','Pip'],
 Beetle:['Shiny','Armor','Bumper','Copper','Roly','Jewel','Click','Ziggy'],
 Dragonfly:['Dart','Skimmer','Glitter','Flash','Azure','Dash','Ripple','Sky'],
 Ant:['Crumb','Scout','Tiny','March','Pepper','Pip','Dot','Pebble'],
 Spider:['Spinner','Silky','Webby','Tangle','Eightbit','Clover','Wisp','Dotty'],
 Bird:['Chirpy','Pip','Feather','Skye','Robinette','Echo','Tweedle','Whistle'],
 Squirrel:['Acorn','Nutmeg','Dash','Hazel','Nibbles','Chestnut','Pip','Twitch'],
 Rabbit:['Hopper','Clover','Binky','Thistle','Cotton','Carrot','Pippin','Dewdrop'],
 Hedgehog:['Prickle','Hedgie','Chestnut','Pincushion','Moss','Button','Spike','Tumble'],
 Frog:['Ribbit','Puddle','Hopper','Lily','Splash','Croak','Emerald','Pebble'],
 Other:['Pip','Pixel','Moss','Pebbles','Sprout','Noodle','Clover','Echo']
};
const HUSH_DICE_COMMON_NAMES=['Pickles','Mochi','Bubbles','Sprout','Pebbles','Noodle','Maple','Jellybean','Pudding','Miso','Doodle','Nova','Beanie','Sunny','Tinker','Cocoa','Nimbus','Roo','Poppy','Twix','Littlebit','Bramble','Crumble','Fidget'];
const HUSH_DICE_GENERIC_MEMORIES=[
 'A tiny surprise made an ordinary day a little brighter.',
 'We nearly walked past this little wonder!',
 'A lovely reminder to look more closely at the world.',
 'One of those small moments worth keeping forever.',
 'A quiet discovery on an unexpectedly exciting adventure.',
 'We stopped for a moment and noticed something wonderful.',
 'The best discoveries sometimes come when you slow down.',
 'A little life with a story of its own.',
 'It felt like finding a secret hiding in plain sight.',
 'Today’s adventure had a delightful surprise.',
 'A special moment from the great outdoors.',
 'We spotted a tiny neighbour sharing our world.',
 'Nature has a way of making a normal day extraordinary.',
 'A moment of curiosity turned into a new discovery.',
 'We found something lovely where we least expected it.',
 'Our little explorer moment was worth remembering.',
 'Sometimes the smallest find makes the biggest memory.',
 'A new page for our collection of everyday wonders.'
];
const HUSH_DICE_SPECIES_MEMORIES={
 Cat:['A curious cat stopped to watch the world go by.','We spotted a mysterious feline in its favourite hiding place.','A quiet whiskered visitor made the day special.','A cat appeared, looked around, and stole the show.'],
 Dog:['A friendly-looking dog crossed our path today.','We spotted a dog busy exploring the neighbourhood.','A wagging tail would make this day hard to forget.','A four-legged adventurer made a surprise appearance.'],
 Snail:['A tiny shell carried a whole world of wonder.','We noticed a snail making its very own slow journey.','A spiral shell caught our eye after the rain.','Slow and steady turned out to be the best discovery of the day.','A tiny traveller reminded us to take our time.'],
 Butterfly:['A flash of colour made us stop and look.','A butterfly brought a little magic to the garden.','Delicate wings made this moment worth saving.','One fluttering visitor made the world feel brighter.'],
 Moth:['A quiet winged visitor appeared when we least expected it.','The moth’s patterned wings were a tiny work of art.','A little night-time explorer joined our adventure.','We discovered beauty hiding in the smallest wing patterns.'],
 Bee:['A busy pollinator was hard at work among the flowers.','A tiny buzz led us to a lovely discovery.','We watched a bee visit the blossoms from a safe distance.','A small visitor with a very important job.'],
 Ladybird:['Those little spots were impossible to miss.','We found a colourful beetle taking a tiny stroll.','A spotty visitor brightened our day.','A little ladybird made a very big impression.'],
 Beetle:['A shiny little explorer wandered into view.','We discovered a beetle with an amazing shell.','Small armour, big adventure!','This tiny crawler deserved its own moment of fame.'],
 Dragonfly:['A shimmering dragonfly flashed past our eyes.','We spotted an aerial acrobat near the water.','Those sparkling wings were worth a second look.','A darting visitor made this a memorable find.'],
 Ant:['A little ant was on a very important mission.','We watched a tiny explorer follow its trail.','A small discovery with a surprisingly busy life.','A whole adventure in just a few footsteps.'],
 Spider:['An intricate web revealed a hidden neighbour.','A quiet eight-legged visitor made us look twice.','There was a tiny architect at work nearby.','A fascinating creature showed up in an unexpected corner.'],
 Bird:['A little bird brought a burst of colour to the day.','A cheerful song made us look up.','We spotted a feathered neighbour on our adventure.','A quick glimpse of wings was all it took.'],
 Squirrel:['A bushy tail vanished around the next corner.','A squirrel was busy on its daily adventures.','We noticed a nimble little explorer among the trees.','A quick dash turned into a memorable encounter.'],
 Rabbit:['A rabbit made a surprise appearance in the grass.','We spotted a pair of curious ears peeking out.','A little hop made this moment special.','A quiet visitor reminded us to tread softly.'],
 Hedgehog:['A spiky little neighbour made our day.','We discovered a tiny adventurer in the undergrowth.','A hedgehog reminded us that nature has hidden surprises.','Those little spines made a memorable silhouette.'],
 Frog:['A small splash hinted that someone was nearby.','We spotted a frog enjoying its watery world.','A little leap made us look twice.','An unexpected visitor near the pond brightened our walk.'],
 Other:['A creature we had never noticed before appeared today.','A surprise visitor added a new chapter to our adventure.','Another reminder of how much life is all around us.','A lovely mystery for our growing wildlife collection.']
};
function hushDiceSpecies(virtual=false){
 const kind=virtual?(getArModel(s.arModelKey).species||'Cat'):(s.spottedSpecies||s.wildTarget||'Other');
 return Object.prototype.hasOwnProperty.call(HUSH_DICE_NAMES,kind)?kind:'Other';
}
function hushRollName(kind){
 const names=HUSH_DICE_NAMES[kind]||HUSH_DICE_NAMES.Other;
 return randomFrom(Math.random()<.75?names:HUSH_DICE_COMMON_NAMES);
}
function hushRollMemory(kind,detail=''){
 const species=HUSH_DICE_SPECIES_MEMORIES[kind]||HUSH_DICE_SPECIES_MEMORIES.Other;
 const variety=(detail||'').trim().slice(0,45);
 const varied=variety&&variety!=='Not sure'&&variety!=='Other'&&Math.random()<.15
   ?`Our ${variety.toLowerCase()} discovery reminded us to notice the little things.`:null;
 return varied||randomFrom(Math.random()<.75?species:HUSH_DICE_GENERIC_MEMORIES);
}
// Capture on the way in: legacy dice handlers never run for new captures.
document.addEventListener('click',event=>{
 const control=event.target?.closest?.('button');
 if(!control||!['dice-name','dice-memory','virtual-dice-name','virtual-dice-memory'].includes(control.id))return;
 const virtual=control.id.startsWith('virtual-');
 const kind=hushDiceSpecies(virtual);
 const inputId=(virtual?'virtual-':'cat-')+(control.id.endsWith('name')?'name':'note');
 const input=control.id==='virtual-dice-memory'?$('virtual-memory'):$(inputId);
 if(!input)return;
 event.preventDefault();event.stopImmediatePropagation();
 const detail=virtual?getArModel(s.arModelKey).speciesDetail||'':($('wildlife-detail')?.value||s.spottedDetail||'');
 input.value=control.id.endsWith('name')?hushRollName(kind):hushRollMemory(kind,detail);
 input.dispatchEvent(new Event('input',{bubbles:true}));
},{capture:true});

const hushPreviousVirtualNaming388=showVirtualNamingForm;
showVirtualNamingForm=function(){
 hushPreviousVirtualNaming388();
 const kind=hushDiceSpecies(true),model=getArModel(s.arModelKey);
 const note=$('virtual-memory'),name=$('virtual-name');
 // Old virtual friends retain their own names. Only fresh suggestions change.
 const existing=s.cats.find(c=>c.virtual&&c.arModelHint===model.key);
 if(!existing&&name)name.value=hushRollName(kind);
 if(note)note.value=hushRollMemory(kind,model.speciesDetail||'');
};

const hushPreviousShowEncounter388=showEncounter;
showEncounter=function(image,quality,options={}){
 const result=hushPreviousShowEncounter388(image,quality,options);
 if(!s.encounterAr){
  const action=$('encounter-continue');if(action)action.textContent='Continue to Collection →';
  const note=$('encounter-quality');if(note&&s.encounterLive&&!s.encounterCaptured){
   note.innerHTML='🎥 Live burst · <span id="live-frame-count">1 recent frame</span> · We keep recent stills during your throw and suggest the clearest five. <small>No video recording or uploading.</small>';
  }
  const info=document.querySelector('.encounter-help p');if(info)info.textContent='Aim at the wildlife without touching or disturbing it. Drag the themed capture item onto the target. Hush Hunt saves only your chosen live-camera photo.';
 }
 return result;
};
const hushPreviousRenderDex388=renderDex;
renderDex=function(){return hushPreviousRenderDex388().replace(/Collection/g,'Collection').replace(/The Collection 🐈/g,'Your Collection 🌿')};
const hushPreviousRenderHome388=renderHome;
renderHome=function(){return hushPreviousRenderHome388().replace(/Collection/g,'Collection').replace(/Collection/g,'Collection')};
const hushPreviousRenderProfile388=renderProfile;
renderProfile=function(){return hushPreviousRenderProfile388().replace(/Collection/g,'Collection')};

// Shared copy in the real discovery form; the Collection database name itself is kept.
const hushPreviousRealFormCopy388=showCatForm;
showCatForm=function(photo){
 const result=hushPreviousRealFormCopy388(photo);
 const button=$('save-catch');if(button&&s.catchMode==='new')button.textContent='Add to Collection →';
 const preview=$('modal-layer')?.querySelector('.photo-preview');if(preview)preview.alt='Your chosen wildlife photo';
 const modal=$('modal-layer');if(modal){
  modal.querySelectorAll('.footnote').forEach(p=>{
   if(p.textContent.includes('selected still image is saved to your Collection'))
    p.textContent='Only your chosen live-camera photo is saved in Collection. Extra burst frames stay temporary and no video is recorded.';
  });
 }
 return result;
};
const hushPreviousLiveChooserCopy388=showLiveOnlyCameraChoice;
showLiveOnlyCameraChoice=function(message){
 const result=hushPreviousLiveChooserCopy388(message);
 const modal=$('modal-layer');if(modal){modal.querySelectorAll('small,strong,p').forEach(el=>{
  if(el.children.length===0&&el.textContent.includes('Collection'))el.textContent=el.textContent.replaceAll('Collection','Collection');
 });}
 return result;
};


/* v3.10.1 — fast entry, actual lens-aware zoom, immediate shutter. No data migration. */
const hushFastPreviousHome=renderHome;
renderHome=function(){
 const html=hushFastPreviousHome();
 const buttons=`<div class="hush-direct-capture" role="group" aria-label="Start a wildlife camera mode">
   <button type="button" id="hush-direct-live" class="hush-direct-btn hush-direct-live"><span class="hush-direct-icon">📷</span><strong>Live Capture</strong><small>Open camera now</small></button>
   <button type="button" id="hush-direct-ar" class="hush-direct-btn hush-direct-ar"><span class="hush-direct-icon">✨</span><strong>AR Safari</strong><small>Find virtual friends</small></button>
  </div>`;
 // Keep the existing home hero and stats; put the action choices above the fold.
 return html.replace(/<button id="hero-catch" class="primary">[^<]*<\/button>/,
  '<div class="hush-hero-direct-label">Choose a camera mode below ↓</div>').replace('</section><div class="stats">','</section>'+buttons+'<div class="stats">');
};
const hushFastPreviousWire=wireScreen;
wireScreen=function(){
 hushFastPreviousWire();
 const live=$('hush-direct-live');if(live)live.onclick=()=>hushFastLiveCapture();
 const ar=$('hush-direct-ar');if(ar)ar.onclick=()=>startArEncounter();
};
function hushFastLiveCapture(){
 if(s.busy)return toast('Please wait for the current save.');
 if(s.storageBlocked)return toast('Restore your Collection backup before adding sightings.');
 captureShots=[]; nativePhotoRequestToken=null; photoSelectionEpoch++;
 s.realLiveProof=null; s.image='';s.encounterLive=false;s.encounterAr=false;
 s.revisitId='';s.catchMode='new';s.selectedId='';s.captureSummary=null;
 setPendingApproxLocation(null);
 return startLiveEncounter();
}
function hushLensName(device){return /ultra[ -]?wide|0[.,][56]\s?x|wide.?angle|super.?wide/i.test(device?.label||'');}
function hushTrackZoom(session){
 try{return session?.stream?.getVideoTracks?.()[0]?.getCapabilities?.()?.zoom||null}catch{return null}
}
function hushLensList(session){
 const cams=session?.rearDevices||[];
 const ultra=cams.find(hushLensName);
 const primaryId=session?.stream?.getVideoTracks?.()[0]?.getSettings?.().deviceId;
 const normal=cams.find(d=>d.deviceId!==ultra?.deviceId&&/back|rear|environment|camera/i.test(d.label)) ||
  cams.find(d=>d.deviceId!==ultra?.deviceId&&d.deviceId===primaryId) ||
  cams.find(d=>d.deviceId!==ultra?.deviceId&&(!/front|selfie|user/i.test(d.label)));
 return {ultra,normal};
}
function hushSyncZoomUi(session){
 if(!session?.active||session!==liveCamera)return;
 const dock=$('hush-live-zoom');if(!dock)return;
 const caps=hushTrackZoom(session);
 const {ultra,normal}=hushLensList(session);
 const half=!!(caps&&caps.min<=.5)||(!!ultra && (!!normal||session.lens==='ultra'));
 const double=!!(caps&&caps.max>=2);
 const options=[...(half?[.5]:[]),1,...(double?[2]:[])];
 dock.innerHTML=options.map(v=>`<button type="button" class="hush-zoom-option ${session.zoomLabel===v+'×'?'selected':''}" data-hush-zoom="${v}" aria-pressed="${session.zoomLabel===v+'×'}">${v}×</button>`).join('');
 if(!half&&!double)dock.innerHTML='<span class="hush-zoom-info">Full view · 1×</span>';
 dock.querySelectorAll('[data-hush-zoom]').forEach(b=>b.onclick=()=>hushSetLiveZoom(session,Number(b.dataset.hushZoom)));
}
async function hushSetLiveZoom(session,value){
 if(!session?.active||session!==liveCamera||session.switching||s.encounterCaptured)return;
 const {ultra,normal}=hushLensList(session);
 const lens=value===.5&&ultra?'ultra':'standard';
 const target=lens==='ultra'?ultra:normal;
 const track=session.stream?.getVideoTracks?.()[0];
 const current=track?.getSettings?.().deviceId;
 let nextStream=null;
 session.switching=true;
 try{
  if(target?.deviceId&&current!==target.deviceId){
   // Keep old preview visible until replacement is ready, never stop capture first.
   nextStream=await navigator.mediaDevices.getUserMedia({audio:false,video:{deviceId:{exact:target.deviceId},width:{ideal:960},height:{ideal:540},frameRate:{ideal:24,max:30}}});
   if(!session.active||session!==liveCamera){nextStream.getTracks().forEach(t=>t.stop());return;}
   const old=session.stream;session.video.srcObject=nextStream;
   try{await session.video.play()}
   catch(error){session.video.srcObject=old;await session.video.play().catch(()=>{});throw error}
   if(!session.active||session!==liveCamera){session.video.srcObject=old;return;}
   session.stream=nextStream;old?.getTracks?.().forEach(t=>t.stop());
   nextStream=null;session.lens=lens;
  }
  const newTrack=session.stream?.getVideoTracks?.()[0],caps=hushTrackZoom(session);
  // 0.5x is exposed only when the camera itself supports zoom-out, or when an
  // actual ultrawide device was selected. CSS digital zoom never masquerades as 0.5x.
  const zoom=caps?Math.max(caps.min,Math.min(caps.max,session.lens==='ultra'&&value===.5?caps.min:value)):null;
  if(zoom!=null&&newTrack?.applyConstraints)await newTrack.applyConstraints({advanced:[{zoom}]});
  session.zoomLabel=value+'×';
 }catch(error){console.debug('Lens zoom unavailable',error);toast('That camera zoom is unavailable on this phone.');}
 finally{if(nextStream)nextStream.getTracks().forEach(t=>t.stop());session.switching=false;hushSyncZoomUi(session)}
}
function hushAddLiveControls(){
 const session=liveCamera;
 if(!session?.active||s.encounterAr||!$('encounter-stage'))return;
 const stage=$('encounter-stage');
 stage.classList.add('hush-quick-stage');
 const dock=document.createElement('div');dock.id='hush-live-zoom';dock.className='hush-live-zoom';dock.setAttribute('aria-label','Camera zoom');stage.appendChild(dock);
 session.zoomLabel=session.lens==='ultra'?'0.5×':'1×';
 hushSyncZoomUi(session);
 const action=document.createElement('button');action.id='hush-quick-shutter';action.type='button';action.className='hush-quick-shutter';
 action.setAttribute('aria-label','Take wildlife photo immediately');action.innerHTML='<span aria-hidden="true">●</span><small>Quick photo</small>';
 stage.appendChild(action);
 action.onclick=async()=>{
  if(!session.active||session!==liveCamera||session.freezePromise||s.encounterCaptured)return;
  action.disabled=true;const label=$('encounter-status');if(label)label.textContent='Photo captured! Preparing your best frame…';
  try{
   await freezeLiveEncounter();
   if(s.realLiveProof?.ready&&realLivePhotoReady(s.image)){
    s.captureSummary=null;
    showCatForm(s.image);
   }else if($('encounter-stage')){
    toast('No usable frame yet. Please try capturing again.');action.disabled=false;
   }
  }catch(error){console.warn('Quick capture failed',error);if($('encounter-stage')){action.disabled=false;toast('Photo could not be captured. Try again.')}}
 };
 // If camera labels were hidden until permission, discover extra physical lenses
 // once the preview is already on screen. Never hold up the first preview.
 if(navigator.mediaDevices?.enumerateDevices)navigator.mediaDevices.enumerateDevices().then(devices=>{
  if(session!==liveCamera||!session.active)return;
  session.rearDevices=devices.filter(device=>device.kind==='videoinput'&&device.deviceId);
  hushSyncZoomUi(session);
 }).catch(()=>{});
 // Native zoom min 0.5 is applied only after camera is already working.
 const zoom=hushTrackZoom(session);
 // Keep the current physical lens at initial open; user controls optical zoom and lens choice.
 // Pinch handling lives in hushInstallLivePinch and works even when WebView omits native zoom capabilities.
}
const hushFastPreviousShowEncounter=showEncounter;
showEncounter=function(image,quality,options={}){
 const result=hushFastPreviousShowEncounter(image,quality,options);
 const sheet=document.querySelector('#modal-layer .sheet');
 if(sheet){
  if(options.live===true&&options.ar!==true)sheet.classList.add('live-sheet');
  if(options.ar===true)sheet.classList.add('ar-sheet');
 }
 if(options.live===true&&options.ar!==true&&!s.encounterAr)hushAddLiveControls();
 return result;
};


/* v3.10.3 • educational Field Guide: browser/native offline, no changes to saved data. */
const HUSH_FIELD_EDUCATION={"groups":{"Cat":"Look at fur colour, markings, ear shape and tail. Coat patterns are not the same as breeds.","Dog":"Look at size, ear shape, coat and muzzle. Many dogs are mixes and cannot be identified by looks alone.","Snail":"Check the shell shape, colour, bands and habitat. Never pull a snail off a surface.","Butterfly":"Notice wing colour and patterns on both sides. Photograph butterflies without catching them.","Moth":"Moths vary widely in shape and colour. Some fly by day; look at wing patterns and antennae.","Bee":"Notice body shape, hairiness and markings. Watch bees from a distance and leave flowers undisturbed.","Ladybird":"Count spots only as one clue. Pattern, size and head markings can matter more.","Beetle":"Beetles have hard wing cases. Look at body shape, antennae and colours.","Dragonfly":"Dragonflies have four long wings and large eyes. Check abdomen shape, colour and habitat.","Ant":"Ants have elbowed antennae and narrow waists. Colours vary; many look alike.","Spider":"Spiders have eight legs and no antennae. Look at their web, markings and body shape.","Bird":"Look at beak, size, wing bars and tail as well as colour. Listen for calls without approaching nests.","Squirrel":"Look at ears, tail, size and coat colour. Coat colours can vary within a species.","Rabbit":"Wild rabbits and pet rabbit breeds can look different. Look at ear shape, size and setting.","Hedgehog":"Look for a rounded body, pointed snout and spines. Observe without touching or disturbing it.","Frog":"Look at skin, colour, leg length and habitat. Patterns vary and some species are hard to distinguish.","Other":"For an unfamiliar animal, photograph it safely and record where you saw it. It is fine to say “Not sure”."},"types":{"Cat":{"Tabby":"Often has stripes, swirls or spots; look for the M-shaped mark on the forehead.","Ginger":"Orange or reddish coat; many ginger cats also show faint or bold tabby stripes.","Brown":"A brown coat can be solid or patterned; check whether stripes are visible.","Black":"Looks mostly black, though sunlight may reveal faint markings.","White":"Mostly white fur; eye colour can be blue, green, amber or mixed.","Cream":"Pale warm beige colouring; compare with the deeper orange of ginger.","Tuxedo":"Usually black with white on the chest, paws or face, like a little suit.","Calico":"Distinct areas of white, orange and dark fur; a coat pattern, not a breed.","Tortoiseshell":"Mottled black and orange or brown patches, usually with very little white.","Grey":"Cool grey or blue-looking coat; may be solid or tabby-patterned.","Colourpoint":"Paler body with darker ears, face, paws and tail.","Other":"If the markings do not fit, describe the colours and pattern in your notes."},"Dog":{"Labrador":"Sturdy body, short dense coat and broad head; black, yellow or chocolate are common.","Golden Retriever":"Medium-large dog with a feathered golden coat and hanging ears.","Poodle":"Curly coat, narrow muzzle and long legs; sizes vary widely.","Terrier":"Often lively-looking with a wiry or smooth coat; many different terrier breeds exist.","Spaniel":"Usually has soft floppy ears and a silky or wavy coat.","Bulldog":"Stocky build, broad head, short muzzle and skin folds.","Dachshund":"Long body, short legs and drooping ears.","Husky":"Thick double coat, upright ears and bushy tail; eyes may be blue or brown.","Mixed Breed":"A mixed-breed dog may combine features of several breeds; looks alone cannot confirm ancestry."},"Snail":{"Garden Snail":"Rounded brown shell often with flecks or mottling; typically found in damp gardens.","Grove Snail":"Smooth shell may be yellow, pinkish or brown, sometimes with dark spiral bands.","Roman Snail":"A relatively large, rounded, pale shell with many visible growth lines.","Glass Snail":"Thin, glossy, often translucent shell; the body may be visible through it.","Amber Snail":"Small amber-coloured shell with a large opening, often near damp plants.","Pond Snail":"Aquatic snail with a taller pointed shell, typically in fresh water.","Other Snail":"Check shell shape and location; different species can look very similar."},"Butterfly":{"Peacock":"A large eye-shaped spot on each reddish-brown wing is the key clue.","Red Admiral":"Dark wings with bright red-orange bands and white markings near the tips.","Small Tortoiseshell":"Orange wings with black and yellow patches and blue crescents at the edges.","Painted Lady":"Orange and brown wings with black tips and small white spots.","Comma":"Orange-brown wings with deeply scalloped edges; the underside has a tiny white C mark.","Large White":"Mainly white wings with dark tips and sometimes black spots.","Common Blue":"Males often look bright blue above; females are usually brown with orange edge spots.","Brimstone":"Leaf-shaped, pale yellow-green wings; females are often paler.","Swallowtail":"Large cream-yellow wings with black veins, blue edging and long hindwing tails. Rare in Britain, mainly in the Norfolk Broads wetlands.","Blue Morpho":"Large tropical butterfly with striking iridescent blue upperwings edged in black, often with white spots. The brown undersides bear eye-spots; native to Central and South American rainforest, not wild Britain."},"Moth":{"Emperor Moth":"Large furry moth with bold round eye-spots on each wing.","Elephant Hawk-moth":"Often pink and olive green, with a streamlined body.","Hummingbird Hawk-moth":"Hovers in front of flowers and has orange hindwings.","Garden Tiger":"Bold cream-and-brown forewings, often with bright orange hindwings.","Jersey Tiger":"Dark forewings with creamy stripes and bright orange or red hindwings.","Six-spot Burnet":"Dark iridescent wings with pairs of red spots; often found on flowers.","Silver Y":"Mottled grey-brown forewings with a small silver Y-shaped marking."},"Bee":{"Honeybee":"Brown-and-gold banded abdomen and slimmer shape than many bumblebees.","Buff-tailed Bumblebee":"Rounded, furry bee with yellow bands and a pale buff or off-white tail.","Red-tailed Bumblebee":"Black fuzzy body with a rusty red or orange tail.","White-tailed Bumblebee":"Black-and-yellow bands with a clean-looking white tail.","Common Carder Bee":"Ginger or brown furry thorax; banding can be subtle.","Leafcutter Bee":"Often carries pollen on hairs under the abdomen and cuts neat circles from leaves.","Mining Bee":"Many species nest in soil; often furry, small to medium, and hard to distinguish."},"Ladybird":{"Seven-spot":"Typically red with seven black spots; three on each wing case and one by the centre.","Two-spot":"Often red with two black spots, but darker forms also exist.","Harlequin":"Highly variable colours; often a pale W-shaped marking behind the head.","Fourteen-spot":"Usually yellow with rectangular black markings that can merge into a checkerboard.","Pine Ladybird":"Mostly dark with red spots shaped a little like commas.","Twenty-two-spot":"Bright yellow with many small black spots; usually found near mildew."},"Beetle":{"Stag Beetle":"Large beetle; males have antler-like jaws, while females have smaller jaws.","Rose Chafer":"Shiny metallic green beetle, often seen feeding on flowers.","Ground Beetle":"Often dark, fast-running and found beneath stones or logs.","Weevil":"Many have a long snout with antennae set partway along it.","Soldier Beetle":"Soft-looking, elongated body; often red or orange on summer flowers.","Click Beetle":"Long narrow body; can make a click to spring itself upright.","Longhorn Beetle":"Often has antennae as long as, or longer than, its body.","Dung Beetle":"Often rounded, sturdy and found around animal dung."},"Dragonfly":{"Emperor Dragonfly":"Large dragonfly with vivid blue abdomen and green thorax, especially in males.","Broad-bodied Chaser":"A broad, flattened abdomen; mature males often look powdery blue.","Southern Hawker":"Large patterned dragonfly; males show blue and green markings.","Common Darter":"Small dragonfly that often perches; mature males are frequently reddish.","Four-spotted Chaser":"Look for four distinct dark spots near the middle of the wings.","Golden-ringed Dragonfly":"Very long black-and-yellow ringed body and green eyes."},"Ant":{"Black Garden Ant":"Small, dark brown or black ant commonly seen on paths and in gardens.","Red Ant":"Often reddish with a darker abdomen; several different species share this name.","Wood Ant":"Usually reddish-brown and dark, often near large mound nests in woodland.","Yellow Meadow Ant":"Small yellowish ant that spends much of its life underground.","Pavement Ant":"Tiny dark ants often nesting in cracks between stones.","Other Ant":"Look at size, colour and nesting place; close-up details may be needed."},"Spider":{"Garden Spider":"Rounded abdomen with a pale cross-shaped pattern; often in circular webs.","House Spider":"Long-legged brown spider; many species occur inside buildings.","Jumping Spider":"Compact body and very large front-facing eyes; moves in short jumps.","Zebra Spider":"Tiny jumping spider with clear black-and-white stripes.","Wolf Spider":"Fast ground hunter with a robust body, often seen without a web.","Crab Spider":"Front legs held sideways like a crab; often waits on flowers.","Cellar Spider":"Very long thin legs and a small body; often hangs upside down indoors."},"Bird":{"Robin":"Orange-red face and chest, with a brown back; often hops near gardens.","Blackbird":"Adult males are black with a yellow-orange bill; females are browner.","House Sparrow":"Small, chunky brown bird; adult males have a grey crown and black throat.","Blue Tit":"Blue cap, yellow underside and white cheeks with a dark eye stripe.","Great Tit":"Black head with white cheeks and a central black stripe on a yellow belly.","Magpie":"Long tail and bold black-and-white body with an iridescent sheen.","Wood Pigeon":"Large plump grey pigeon with white neck patches.","Starling":"Dark, glossy bird that can sparkle green-purple and show pale speckles.","Crow":"Large black bird with a strong dark bill; several crow species look similar.","Seagull":"Gulls vary with age; look at size, beak and wing markings.","Parakeet":"Bright green body, long pointed tail and red beak in a ring-necked parakeet.","Duck":"Broad flat bill and webbed feet; plumage depends on species and sex.","Swan":"Very large waterbird with a long neck; British mute swans usually have orange bills.","Owl":"Rounded or heart-shaped face, forward-facing eyes and often silent flight."},"Squirrel":{"Grey Squirrel":"Usually grey-brown with a white belly and broad bushy tail.","Red Squirrel":"Often russet red with a paler belly; some have ear tufts, especially in winter.","Flying Squirrel":"Has a skin membrane between front and back legs for gliding; not native to Britain.","Ground Squirrel":"Typically lives in burrows and spends more time on the ground.","Other Squirrel":"Squirrels can be black, grey or reddish; colour alone does not prove species."},"Rabbit":{"Wild Rabbit":"Brown-grey coat, short fluffy tail and upright ears; lives in warrens.","Lop-eared":"Domestic rabbit with ears that hang beside its face.","Dutch Rabbit":"Domestic breed with clear patches of contrasting coat colour.","Lionhead":"Domestic rabbit with a distinctive mane of longer fur around the head.","Netherland Dwarf":"Small, compact pet rabbit with short ears.","Flemish Giant":"Very large domestic rabbit with a long, sturdy body."},"Hedgehog":{"European Hedgehog":"Brown-and-cream spines, pointed face and small ears; native to Britain.","African Pygmy Hedgehog":"Smaller, often pale-faced pet hedgehog; not native to Britain.","Long-eared Hedgehog":"Has noticeably larger ears; native to parts of Asia and the Middle East.","Other Hedgehog":"Check face, ears and where it was seen before choosing a type."},"Frog":{"Common Frog":"Variable brown or olive skin with a dark patch behind the eye; found near ponds.","Pool Frog":"Usually greenish-brown with spots; close identification can be difficult.","Marsh Frog":"Large greenish frog with dark spots, often near water.","Tree Frog":"Many have toe pads for climbing and bright green skin.","Bullfrog":"Large frog with a broad head; not native to Britain.","Other Frog":"Patterns vary a lot; a photo and the habitat are useful clues."},"Other":{"Fox":"Pointed muzzle, triangular ears and a long bushy tail.","Deer":"Hoofed mammal; size, antlers and rump pattern vary among deer species.","Mouse":"Small rodent with a pointed muzzle, whiskers and long thin tail.","Bat":"The only mammals capable of sustained powered flight; wings are skin membranes.","Lizard":"Scaly skin, long tail and usually four legs; some look snake-like.","Worm":"Long, soft segmented body; earthworms help mix and aerate soil.","Slug":"Soft shell-less-looking mollusc; often active in damp conditions.","Fish":"Fins and gills are key clues; look at body shape and fin placement.","Tortoise":"Land-dwelling reptile with a protective shell and stout legs.","Other Animal":"If it does not fit the groups, take a clear photo and add a description."}}};
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
/* v3.10.9: six wildlife categories, preserving all legacy species and subtype values. */
const HUSH_CATEGORIES=[{name:'Mammals',icon:'🦊'},{name:'Birds',icon:'🐦'},{name:'Reptiles',icon:'🦎'},{name:'Amphibians',icon:'🐸'},{name:'Insects',icon:'🦋'},{name:'Other wildlife',icon:'🐌'}];
const HUSH_CATEGORY_GROUPS={
 'Mammals':['Cat','Dog','Squirrel','Rabbit','Hedgehog','Other'],
 'Birds':['Bird'],
 'Reptiles':['Other'],
 'Amphibians':['Frog'],
 'Insects':['Butterfly','Moth','Bee','Ladybird','Beetle','Dragonfly','Ant'],
 'Other wildlife':['Snail','Spider','Other']};
const HUSH_OTHER_KIND_CATEGORY={Fox:'Mammals',Deer:'Mammals',Mouse:'Mammals',Bat:'Mammals',Lizard:'Reptiles',Tortoise:'Reptiles',Fish:'Other wildlife',Slug:'Other wildlife',Worm:'Other wildlife','Other Animal':'Other wildlife'};
function hushCategory(group,kind){
 if(group==='Other')return HUSH_OTHER_KIND_CATEGORY[kind]||'Other wildlife';
 for(const [name,groups] of Object.entries(HUSH_CATEGORY_GROUPS))if(groups.includes(group))return name;
 return 'Other wildlife';
}
function hushAnimalCategory(animal){return hushCategory(speciesOf(animal),animal.speciesDetail||'');}
let hushGuideContext=null;
function hushGuideHasForm(){return !!($('wildlife-species')||$('edit-species'))}
function hushGuideOpen(group,type){
 if(document.querySelector('#hush-fullscreen-guide'))return;
 const fromEdit=!!$('edit-species'),fromCapture=!!$('wildlife-species');
 hushGuideContext={fromEdit,fromCapture,focus:document.activeElement,overflow:document.body.style.overflow,group:FIELD_GUIDE_VARIETIES[group]?group:'Cat',type:type||null,category:hushCategory(group,type)};
 const screen=document.createElement('section');screen.id='hush-fullscreen-guide';screen.className='hush-fullscreen-guide';screen.setAttribute('role','dialog');screen.setAttribute('aria-modal','true');screen.setAttribute('aria-label','Wildlife Field Guide');
 document.body.appendChild(screen);document.body.style.overflow='hidden';hushGuideRender();
 screen.querySelector('#hush-guide-close')?.focus();
}
function hushGuideClose(){const screen=$('hush-fullscreen-guide');if(!screen)return;screen.remove();if(hushGuideContext){document.body.style.overflow=hushGuideContext.overflow;hushGuideContext.focus?.focus?.()}hushGuideContext=null;}
function hushGuideRender(){
 const screen=$('hush-fullscreen-guide'),ctx=hushGuideContext;if(!screen||!ctx)return;
 const group=ctx.group,types=FIELD_GUIDE_VARIETIES[group]||[],type=types.includes(ctx.type)?ctx.type:null;
 const category=ctx.category||hushCategory(group,type);ctx.category=category;
 const detail=type?HUSH_FIELD_EDUCATION.types[group]?.[type]:HUSH_FIELD_EDUCATION.groups[group];
 const categoryBar=HUSH_CATEGORIES.map(c=>`<button class="hush-category-tab ${category===c.name?'active':''}" data-hush-guide-category="${esc(c.name)}" aria-pressed="${category===c.name}">${c.icon} ${esc(c.name)}</button>`).join('');
 const available=HUSH_CATEGORY_GROUPS[category]||['Other'];
 const chips=available.map(g=>`<button type="button" data-hush-guide-group="${esc(g)}" class="hush-guide-chip ${g===group?'active':''}" aria-pressed="${g===group}">${FIELD_GUIDE_EMOJI[g]||'🐾'} ${esc(g==='Other'?'Other kinds':g)}</button>`).join('');
 const visibleTypes=group==='Other'?types.filter(name=>hushCategory('Other',name)===category):types;
 const cards=visibleTypes.map(name=>`<button type="button" class="hush-guide-reference ${name===type?'active':''}" data-hush-guide-type="${esc(name)}" aria-pressed="${name===type}"><img src="${fieldGuideArt(group,name)}" alt="Illustrative ${esc(name)} reference" loading="lazy"><strong>${esc(name)}</strong><small>${esc(HUSH_FIELD_EDUCATION.types[group]?.[name]||'Observe carefully and compare several features.')}</small></button>`).join('');
 const image=type?fieldGuideArt(group,type):group==='Other'?fieldGuideArt('Other',category==='Reptiles'?'Lizard':category==='Mammals'?'Fox':'Slug'):fieldGuideArt(group);
 const chosenAction=hushGuideHasForm()&&(ctx.fromCapture||ctx.fromEdit);
 screen.innerHTML=`<header class="hush-guide-top"><div><div class="hush-guide-kicker">HUSH HUNT • LITTLE EXPLORERS</div><h2>Wildlife Field Guide</h2><p>Study the clues, then decide what you really saw.</p></div><button type="button" id="hush-guide-close" class="hush-guide-close" aria-label="Close field guide">✕</button></header>
 <div class="hush-guide-scroll"><div class="hush-category-tabs" role="group" aria-label="Animal categories">${categoryBar}</div><div class="hush-guide-chips" role="group" aria-label="Animal groups">${chips}</div>
 <article class="hush-guide-feature"><img src="${image}" alt="Illustrated reference for ${esc(type||group)}"><div><div class="hush-guide-kicker">${esc(category)} • ${type?'KIND':'GROUP'}</div><h3>${esc(type||group)}</h3><p>${esc(detail||'Look carefully at several features before choosing a type.')}</p>${type?`<p class="hush-guide-small">Also check: ${esc(HUSH_FIELD_EDUCATION.groups[group]||'Compare shape and surroundings.')}</p>`:''}${chosenAction?`<button type="button" id="hush-guide-use" class="hush-guide-use">Use this ${type?'identification':'group'} ✓</button>`:''}</div></article>
 <h3 class="hush-guide-subtitle">Compare ${esc(category.toLowerCase())} kinds <span>${visibleTypes.length} examples</span></h3>
 <div class="hush-guide-references">${cards}</div><p class="hush-guide-disclaimer">Reference illustrations are not verified diagnostic photographs. There is no automatic species identification. If unsure, save your observation as “Not sure”. Never disturb wildlife.</p></div>`;
 screen.querySelector('#hush-guide-close').onclick=hushGuideClose;
 screen.querySelectorAll('[data-hush-guide-category]').forEach(b=>b.onclick=()=>{ctx.category=b.dataset.hushGuideCategory;ctx.group=(HUSH_CATEGORY_GROUPS[ctx.category]||['Other'])[0];ctx.type=null;hushGuideRender()});
 screen.querySelectorAll('[data-hush-guide-group]').forEach(b=>b.onclick=()=>{ctx.group=b.dataset.hushGuideGroup;ctx.type=null;hushGuideRender()});
 screen.querySelectorAll('[data-hush-guide-type]').forEach(b=>b.onclick=()=>{ctx.type=b.dataset.hushGuideType;hushGuideRender();screen.querySelector('.hush-guide-feature')?.scrollIntoView({block:'nearest',behavior:'smooth'})});
 const use=screen.querySelector('#hush-guide-use');if(use)use.onclick=hushGuideUse;
}
function hushGuideUse(){
 const ctx=hushGuideContext;if(!ctx)return;
 const group=ctx.group,type=ctx.type;
 if(group==='Other')hushCaptureCategory=ctx.category||hushCategory(group,type);
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



/* v3.10.5 — storyboard-inspired Home, Live Capture, and Identified UI pass. */
function hushStoryCategory(group){
 const map={Cat:'Mammal',Dog:'Mammal',Bird:'Bird',Butterfly:'Insect',Moth:'Insect',Bee:'Insect',Ladybird:'Insect',Beetle:'Insect',Dragonfly:'Insect',Ant:'Insect',Spider:'Arachnid',Snail:'Mollusc',Squirrel:'Mammal',Rabbit:'Mammal',Hedgehog:'Mammal',Frog:'Amphibian',Other:'Wildlife'};
 return map[group]||'Wildlife';
}
function hushStoryGroupTags(group,detail){
 const tags=[group==='Other'?hushCategory(group,detail):hushStoryCategory(group)];
 if(group==='Cat'||group==='Dog'||group==='Bird'||group==='Squirrel'||group==='Rabbit'||group==='Hedgehog')tags.push('Common');
 if(group==='Butterfly'||group==='Bee'||group==='Dragonfly'||group==='Moth'||group==='Ladybird'||group==='Beetle'||group==='Ant'||group==='Spider')tags.push('Mini beast');
 if(group==='Snail'||group==='Frog')tags.push('Garden');
 if(detail&&detail!=='Not sure')tags.push(detail);
 return tags.slice(0,3);
}
function hushStoryFeatures(group,detail){
 const typeText=(HUSH_FIELD_EDUCATION.types[group]||{})[detail||'']||'';
 const groupText=HUSH_FIELD_EDUCATION.groups[group]||HUSH_FIELD_EDUCATION.groups.Other||'';
 const parts=(typeText+' '+groupText).split(/(?<=[.!?])\s+/).map(s=>s.trim()).filter(Boolean);
 const clean=parts.map(s=>s.replace(/[“”"]/g,'')).slice(0,4);
 return clean.length?clean:['Use the guide pictures to compare colour, shape and body features.','Observe from a safe distance and avoid touching wildlife.'];
}
function hushRefreshIdentifiedPanel(){
 const panel=$('hush-identified-panel'); if(!panel)return;
 const species=SPECIES.includes(s.spottedSpecies)?s.spottedSpecies:'Other';
 const detail=species==='Cat'?($('cat-coat')?.value||'Other'):($('wildlife-detail')?.value.trim()||s.spottedDetail||'Not sure');
 const title=(detail&&detail!=='Not sure'&&species!=='Cat')?detail:species;
 const subtitle=(detail&&detail!=='Not sure'&&species!=='Cat')?species+' · guide-based selection':'Use the field guide below to confirm the species';
 const titleEl=$('hush-id-title'); if(titleEl)titleEl.textContent=title;
 const subEl=$('hush-id-subtitle'); if(subEl)subEl.textContent=subtitle;
 const imgEl=$('hush-id-thumb'); if(imgEl)imgEl.src=fieldGuideArt(species, detail&&detail!=='Not sure'?detail:null);
 const tagsEl=$('hush-id-tags'); if(tagsEl)tagsEl.innerHTML=hushStoryGroupTags(species,detail).map(tag=>`<span>${esc(tag)}</span>`).join('');
 const featuresEl=$('hush-id-features'); if(featuresEl)featuresEl.innerHTML=hushStoryFeatures(species,detail).map(line=>`<li>${esc(line.replace(/[.!?]+$/,''))}</li>`).join('');
 const pill=$('hush-id-pill'); if(pill)pill.textContent=s.encounterLive?'Live capture':'Guide mode';
}
const hushStoryHomePrevious=renderHome;
renderHome=function(){
 const total=allSightings().length, discovered=s.cats.length, badgeCount=medals().filter(m=>m.ok).length;
 const fox=fieldGuideArt('Other','Fox');
 return `<section class="hush-story-home"><div class="hush-story-hero" style="--hero-art:url('${fox}')"><div class="hush-story-topbar"><button type="button" class="hush-story-icon" data-go="profile" aria-label="Open profile">⚙️</button><button type="button" class="hush-story-icon" data-go="quests" aria-label="Open achievements">🏆</button></div><div class="hush-story-brand"><div class="hush-story-paw">🐾</div><h1>Hush Hunt</h1><p>EXPLORE • DISCOVER • LEARN</p></div><div class="hush-story-copy"><h2>Spot wildlife around you</h2><p>Use Live Capture for real discoveries, or open AR Safari for playful virtual exploring.</p></div><div class="hush-story-main-actions"><button type="button" id="hush-direct-live" class="hush-story-main hush-story-main-live"><span class="emoji">📷</span><strong>Live Capture</strong><small>Find real animals in the wild</small></button><button type="button" id="hush-direct-ar" class="hush-story-main hush-story-main-ar"><span class="emoji">✨</span><strong>AR Safari</strong><small>Discover virtual animals</small></button></div><div class="hush-story-mini-actions"><button type="button" class="hush-story-mini" data-go="dex"><span>🖼️</span><strong>Collection</strong></button><button type="button" class="hush-story-mini" data-go="explore"><span>📍</span><strong>Animal Map</strong></button><button type="button" class="hush-story-mini" data-go="quests"><span>🏆</span><strong>Achievements</strong></button></div></div><div class="hush-story-stats"><div><strong>${discovered}</strong><span>Discoveries</span></div><div><strong>${total}</strong><span>Sightings</span></div><div><strong>${badgeCount}</strong><span>Badges</span></div></div><p class="hush-release-caption">v${WHISKER_BUILD} · build ${WHISKER_BUILD_NUMBER}</p></section>`;
};
const hushStoryWirePrevious=wireScreen;
wireScreen=function(){
 hushStoryWirePrevious();
 const live=$('hush-direct-live'); if(live)live.onclick=()=>hushFastLiveCapture();
 const ar=$('hush-direct-ar'); if(ar)ar.onclick=()=>startArEncounter();
};
const hushStoryEncounterPrevious=showEncounter;
showEncounter=function(image,quality,options={}){
 const result=hushStoryEncounterPrevious(image,quality,options);
 if(options.live===true&&options.ar!==true){
   const title=document.querySelector('#modal-layer .sheet-head h2'); if(title)title.textContent='Live Capture';
   const status=$('encounter-status'); if(status&&!s.encounterCaptured)status.textContent='Frame your subject, use the zoom buttons if needed, and tap Quick photo when ready.';
 }
 return result;
};
const hushStoryFormPrevious=showCatForm;
showCatForm=function(photo){
 const result=hushStoryFormPrevious(photo);
 const sheet=document.querySelector('#modal-layer .sheet');
 if(sheet)sheet.classList.add('identified-sheet');
 const title=document.querySelector('#modal-layer .sheet-head h2'); if(title)title.textContent='Identified!';
 const preview=document.querySelector('#modal-layer .photo-preview');
 const extra=$('catch-extra');
 if(extra && !document.querySelector('#hush-identified-panel')){
   const panel=document.createElement('section');
   panel.id='hush-identified-panel';
   panel.className='hush-identified-panel';
   panel.innerHTML=`<div class="hush-photo-only"><img id="hush-id-photo" src="${esc(photo)}" alt="Your captured wildlife photo"><span id="hush-id-pill" class="hush-photo-label">Your photo</span></div><div class="hush-discovery-summary" aria-live="polite"><span class="hush-discovery-check">✓</span><div><h3 id="hush-id-title">Choose an animal below</h3><p id="hush-id-subtitle">Species and variety not confirmed yet</p></div></div><div id="hush-id-tags" class="hidden"></div><ul id="hush-id-features" class="hidden"></ul>`;
   // The preview MUST follow the header, never precede it (old layout caused an enormous cropped panel above the heading).
   const formHeader=extra.parentElement.querySelector('.sheet-head');
   if(formHeader) formHeader.insertAdjacentElement('afterend',panel);
   else extra.parentElement.prepend(panel);
 }
 if(preview)preview.style.display='none';
 ['wildlife-species','cat-coat','wildlife-detail'].forEach(id=>$(id)?.addEventListener('change',hushRefreshIdentifiedPanel));
 $('wildlife-detail')?.addEventListener('input',hushRefreshIdentifiedPanel);
 document.querySelectorAll('#field-guide-types [data-guide-type]').forEach(btn=>btn.addEventListener('click',()=>setTimeout(hushRefreshIdentifiedPanel,0)));
 document.querySelectorAll('#mode-new,#mode-repeat').forEach(btn=>btn?.addEventListener('click',()=>setTimeout(hushRefreshIdentifiedPanel,0)));
 hushRefreshIdentifiedPanel();
 return result;
};


/* v3.10.9 — group browser, cross-wildlife bingo and reliable camera zoom. */
let hushCaptureCategory='Mammals';
const hushUpdatedGuideSpecies=renderFieldGuideSpecies;
renderFieldGuideSpecies=function(){
 hushUpdatedGuideSpecies();
 const grid=$('field-guide-species');if(!grid)return;
 const chooser=grid.parentElement;
 let tabs=chooser.querySelector('#hush-capture-categories');
 if(!tabs){tabs=document.createElement('div');tabs.id='hush-capture-categories';tabs.className='hush-category-tabs';grid.before(tabs);}
 // Keep the category independent of the stored species, so "Other" can represent lizards, foxes etc.
 if(s.spottedSpecies!=='Other')hushCaptureCategory=hushCategory(s.spottedSpecies);
 tabs.innerHTML=HUSH_CATEGORIES.map(c=>`<button type="button" data-hush-capture-category="${esc(c.name)}" class="hush-category-tab ${c.name===hushCaptureCategory?'active':''}" aria-pressed="${c.name===hushCaptureCategory}">${c.icon} ${esc(c.name)}</button>`).join('');
 grid.querySelectorAll('[data-guide-group]').forEach(tile=>{
  const type=tile.dataset.guideGroup;
  tile.classList.toggle('hidden',!(HUSH_CATEGORY_GROUPS[hushCaptureCategory]||[]).includes(type));
 });
 if(s.spottedSpecies==='Other'){
   const picture=grid.querySelector('[data-guide-group="Other"] img');
   const chosen=chooser.querySelector('#field-guide-selected img');
   const representative=fieldGuideArt('Other',hushCaptureCategory==='Reptiles'?'Lizard':hushCaptureCategory==='Mammals'?'Fox':'Slug');
   if(picture)picture.src=representative;
   if(chosen)chosen.src=representative;
 }
 tabs.querySelectorAll('[data-hush-capture-category]').forEach(btn=>btn.onclick=()=>{
  hushCaptureCategory=btn.dataset.hushCaptureCategory;
  const groups=HUSH_CATEGORY_GROUPS[hushCaptureCategory]||[];
  // On tab change, select a group in the category so varieties match immediately.
  const selected=$('wildlife-species');if(selected&&!groups.includes(selected.value)){
   selected.value=groups[0]||'Other';selected.dispatchEvent(new Event('change',{bubbles:true}));
  }else renderFieldGuideSpecies();
  if(selected?.value==='Other')renderFieldGuideVarieties();
 });
};
const hushUpdatedVarieties=renderFieldGuideVarieties;
renderFieldGuideVarieties=function(){
 hushUpdatedVarieties();
 if(s.spottedSpecies!=='Other')return;
 $('field-guide-types')?.querySelectorAll('[data-guide-type]').forEach(tile=>{
  const type=tile.dataset.guideType;
  if(type!=='Not sure')tile.classList.toggle('hidden',hushCategory('Other',type)!==hushCaptureCategory);
 });
};
const hushExpandedDex=renderDex;
renderDex=function(){
 let html=hushExpandedDex();
 const real=visibleWildlife();
 const categoryCards=HUSH_CATEGORIES.map(cat=>{
  const count=real.filter(a=>hushAnimalCategory(a)===cat.name).length;
  return `<button type="button" class="hush-collection-category ${s.filter==='Category:'+cat.name?'active':''}" data-hush-category-filter="${esc(cat.name)}"><span>${cat.icon}</span><strong>${esc(cat.name)}</strong><small>${count} discoveries</small></button>`;
 }).join('');
 const intro=`<section class="hush-collection-categories"><h3>Explore by animal family</h3><div class="hush-category-card-grid">${categoryCards}</div></section>`;
 html=html.replace('<section class="wildlife-collection">',intro+'<section class="wildlife-collection">');
 // Keep original Cat Coats intact as an optional challenge; add one for every other major kind.
 const missions=[
  ['Bird plumage','Bird','🐦'],['Butterfly wings','Butterfly','🦋'],['Bee varieties','Bee','🐝'],
  ['Dragonflies','Dragonfly','🪰'],['Beetle patterns','Beetle','🪲'],['Snail shells','Snail','🐌'],
  ['Frog friends','Frog','🐸'],['Dog types','Dog','🐕'],['Spiders','Spider','🕷️'],
  ['Moth markings','Moth','🌙'],['Ladybird patterns','Ladybird','🐞'],['Squirrels','Squirrel','🐿️']];
 const missionHtml=missions.map(([label,group,icon])=>{
  const all=FIELD_GUIDE_VARIETIES[group]||[];
  const found=new Set(real.filter(a=>speciesOf(a)===group).map(a=>String(a.speciesDetail||'').toLowerCase()));
  const seen=all.filter(x=>found.has(x.toLowerCase())).length;
  const pct=all.length?Math.round(100*seen/all.length):0;
  return `<button type="button" class="hush-bonus-challenge" data-hush-filter="Species:${esc(group)}"><span>${icon}</span><div><strong>${esc(label)}</strong><small>${seen} / ${all.length} varieties found</small><b class="hush-bonus-progress"><i style="width:${pct}%"></i></b></div><span class="arrow">›</span></button>`;
 }).join('');
 html=html.replace('BONUS · CAT COATS','BONUS · CAT COATS (CLASSIC)');
 html=html.replace('<div class="bingo">',`<section class="hush-bonus-section"><h3>More wildlife challenges</h3><p>Explore all kinds — cats are just one part of the adventure.</p><div class="hush-bonus-list">${missionHtml}</div></section><div class="bingo">`);
 return html;
};
const hushCategoryDexGrid=dexGrid;
dexGrid=function(){
 if(!s.filter.startsWith('Category:'))return hushCategoryDexGrid();
 const category=s.filter.slice(9),q=s.search.toLowerCase();
 const records=visibleWildlife().filter(c=>hushAnimalCategory(c)===category&&[c.name,speciesOf(c),c.speciesDetail||'',c.coat,c.note||''].some(v=>String(v).toLowerCase().includes(q)));
 if(!records.length)return '<div class="feature-empty"><h3>No discoveries in this family yet</h3><p>Spot your first animal to start filling this category.</p></div>';
 return `<div class="cat-grid">${records.map(c=>`<button class="cat-tile" data-cat="${esc(c.id)}"><img class="cat-img" src="${c.photo}" alt="${esc(c.name)}"><div class="cat-info"><strong>${esc(c.name)}</strong><small>${esc(speciesOf(c))}${c.speciesDetail?' · '+esc(c.speciesDetail):''}</small></div></button>`).join('')}</div>`;
};
const hushCategoryWiring=wireScreen;
wireScreen=function(){
 hushCategoryWiring();
 document.querySelectorAll('[data-hush-category-filter]').forEach(b=>b.onclick=()=>{s.filter='Category:'+b.dataset.hushCategoryFilter;render()});
};
/* v3.10.10 — unified live zoom and two-finger gestures.
 * Inward pinch zooms out, outward spread zooms in, and button presses share
 * the same optical/digital pipeline. Never fake a physical wide-angle lens.
 */
function hushWideAvailable(session){
 const caps=hushTrackZoom(session);
 if(caps && Number.isFinite(caps.min) && caps.min<=.60001)return true;
 return !!hushLensList(session).ultra;
}
function hushZoomFloor(session){return hushWideAvailable(session)?.6:1;}
function hushClampZoom(session,value){
 const n=Number(value);
 return Math.min(3,Math.max(hushZoomFloor(session),Number.isFinite(n)?n:1));
}
function hushZoomText(value){return `${Number(value).toFixed(1).replace(/\.0$/,'')}×`;}
function hushRefreshZoomControls(session){
 if(!session?.active||session!==liveCamera)return;
 const dock=$('hush-live-zoom');if(!dock)return;
 const wide=hushWideAvailable(session),current=hushClampZoom(session,session.logicalZoom??(session.lens==='ultra'?.6:1));
 const values=[...(wide?[.6]:[]),1,2,3];
 dock.innerHTML=`<span class="hush-zoom-current" aria-live="off">${hushZoomText(current)}</span>`+
 values.map(v=>`<button type="button" data-hush-zoom="${v}" class="hush-zoom-option ${Math.abs(current-v)<.045?'selected':''}" aria-label="Zoom ${hushZoomText(v)}" aria-pressed="${Math.abs(current-v)<.045}">${hushZoomText(v)}</button>`).join('');
 dock.querySelectorAll('button[data-hush-zoom]').forEach(button=>button.onclick=()=>hushSetLiveZoom(session,Number(button.dataset.hushZoom)));
 dock.setAttribute('aria-label','Zoom controls, two-finger pinch inward to zoom out or spread outward to zoom in');
}
hushSyncZoomUi=hushRefreshZoomControls;
async function hushSwitchLensForZoom(session,wantUltra){
 const {ultra,normal}=hushLensList(session);
 const target=wantUltra?ultra:normal;
 const current=session.stream?.getVideoTracks?.()[0]?.getSettings?.().deviceId;
 if(!target?.deviceId||target.deviceId===current)return !wantUltra || session.lens==='ultra';
 let replacement=null;
 try{
  replacement=await navigator.mediaDevices.getUserMedia({audio:false,video:{deviceId:{exact:target.deviceId},width:{ideal:960},height:{ideal:540},frameRate:{ideal:24,max:30}}});
  if(!session.active||session!==liveCamera)return false;
  const oldStream=session.stream;
  session.video.srcObject=replacement;
  try{await session.video.play();}catch(error){session.video.srcObject=oldStream;await session.video.play().catch(()=>{});throw error;}
  session.stream=replacement;session.lens=wantUltra?'ultra':'standard';replacement=null;
  oldStream?.getTracks?.().forEach(t=>t.stop());
  session.frames=[];
  return true;
 }catch(error){console.debug('Changing wide lens not supported',error);return false;}
 finally{replacement?.getTracks?.().forEach(t=>t.stop());}
}
async function hushApplyRequestedZoom(session,desired){
 if(!session.active||session!==liveCamera||s.encounterCaptured)return;
 const value=hushClampZoom(session,desired);
 const {ultra}=hushLensList(session);
 const needUltra=value<1&&!!ultra;
 const nativeIsWide=hushTrackZoom(session)?.min<=.60001;
 // A multi-camera native track can zoom out directly without switching physical devices.
 if(!nativeIsWide && session.lens!==(needUltra?'ultra':'standard')){
  const switched=await hushSwitchLensForZoom(session,needUltra);
  if(!switched&&needUltra){toast('0.6× wide lens is not exposed by this camera.');session.requestedZoom=1;return;}
 }
 if(!session.active||session!==liveCamera)return;
 const track=session.stream.getVideoTracks()[0];
 const caps=hushTrackZoom(session);
 const opticalBaseline=session.lens==='ultra'?.6:1;
 // Hardware API zoom represents 1× at the current physical lens, except a
 // multi-camera track with native zoom min below 1 (which uses device-wide values).
 const nativeTarget=nativeIsWide?value:value/opticalBaseline;
 let appliedNative=1, nativeUsed=false;
 if(caps && caps.min<=nativeTarget && caps.max>=nativeTarget && track?.applyConstraints){
  try{
   await track.applyConstraints({advanced:[{zoom:nativeTarget}]});
   appliedNative=nativeTarget;nativeUsed=true;
  }catch(error){console.debug('Native camera zoom unavailable',error);}
 }
 if(!nativeUsed&&caps?.min<=1&&track?.applyConstraints){
  try{await track.applyConstraints({advanced:[{zoom:1}]});}catch{}
 }
 // A software crop can zoom IN only, never reveal pixels outside the sensor.
 let digital=1;
 if(!nativeUsed)digital=Math.max(1,value/opticalBaseline);
 session.digitalZoom=digital;
 session.logicalZoom=value;
 session.zoomLabel=hushZoomText(value);
 session.frames=[]; // Previous frames must not mix different visual zoom levels.
 session.video.style.transform=digital>1.005?`scale(${digital.toFixed(3)})`:'none';
 session.video.style.transformOrigin='center center';
 hushRefreshZoomControls(session);
}
hushSetLiveZoom=function(session,requested){
 if(!session?.active||session!==liveCamera||s.encounterCaptured)return Promise.resolve();
 session.requestedZoom=hushClampZoom(session,requested);
 // Coalesce rapid pinch events while asynchronous native lens constraints run.
 if(session.zoomPromise)return session.zoomPromise;
 session.zoomPromise=(async()=>{
  while(session.active&&session===liveCamera && session.requestedZoom!=null){
   const goal=session.requestedZoom;session.requestedZoom=null;
   await hushApplyRequestedZoom(session,goal);
  }
 })().finally(()=>{session.zoomPromise=null;});
 return session.zoomPromise;
};
function hushInstallLivePinch(session){
 const stage=$('encounter-stage');if(!stage)return;
 stage.classList.add('hush-pinch-camera');
 let startDistance=0,startZoom=1,active=false,lastSent=0;
 const distance=touches=>Math.hypot(touches[0].clientX-touches[1].clientX,touches[0].clientY-touches[1].clientY);
 stage.addEventListener('touchstart',event=>{
  if(event.touches.length!==2||!session.active||session!==liveCamera){active=false;return;}
  active=true;startDistance=Math.max(1,distance(event.touches));startZoom=session.logicalZoom??(session.lens==='ultra'?.6:1);
  event.preventDefault();
 },{passive:false,capture:true});
 stage.addEventListener('touchmove',event=>{
  if(!active||event.touches.length!==2||session!==liveCamera||!session.active)return;
  event.preventDefault();
  const now=Date.now();if(now-lastSent<65)return;lastSent=now;
  // pinching inward decreases finger spacing; spreading outward increases it.
  const desired=hushClampZoom(session,startZoom*distance(event.touches)/startDistance);
  hushSetLiveZoom(session,Math.round(desired*100)/100);
 },{passive:false,capture:true});
 stage.addEventListener('touchend',event=>{
  if(event.touches.length<2)active=false;
 },{passive:true,capture:true});
 stage.addEventListener('touchcancel',()=>{active=false;},{passive:true,capture:true});
}
const hushPre31010AddControls=hushAddLiveControls;
hushAddLiveControls=function(){
 hushPre31010AddControls();
 const session=liveCamera;
 if(!session?.active||s.encounterAr)return;
 session.logicalZoom=session.lens==='ultra'?.6:1;
 session.digitalZoom=1;
 session.zoomLabel=hushZoomText(session.logicalZoom);
 hushRefreshZoomControls(session);
 hushInstallLivePinch(session);
 const dock=$('hush-live-zoom');if(dock){
  const hint=document.createElement('span');hint.className='hush-pinch-hint';hint.textContent='Pinch in: zoom out · Spread: zoom in';
  dock.insertAdjacentElement('afterend',hint);
 }
};


/* v3.10.11 / 74 — immersive rotating themes, neutral mystery capture and compact controls.
 * Theme settings live separately from the animal database; no migration or reset.
 */
const HUSH_THEMES_74=[
 {id:'twilight-fox',liveArt:'button_scenes_v75/twilight-fox-live.webp',arArt:'button_scenes_v75/twilight-fox-ar.webp',name:'Purple fox twilight',accent:'#d37ce7',live:'#159d87',ar:'#7064ec'},
 {id:'blue-morpho-garden',liveArt:'button_scenes_v75/blue-morpho-garden-live.webp',arArt:'button_scenes_v75/blue-morpho-garden-ar.webp',name:'Blue Morpho garden',accent:'#59ddd7',live:'#158e80',ar:'#367be7'},
 {id:'mountain-deer',liveArt:'button_scenes_v75/mountain-deer-live.webp',arArt:'button_scenes_v75/mountain-deer-ar.webp',name:'Mountain deer',accent:'#e8c58f',live:'#3e9052',ar:'#4388bb'},
 {id:'robin-woodland',liveArt:'button_scenes_v75/robin-woodland-live.webp',arArt:'button_scenes_v75/robin-woodland-ar.webp',name:'Robin woodland',accent:'#b2d980',live:'#219b67',ar:'#4988ce'},
 {id:'moonlit-owl',liveArt:'button_scenes_v75/moonlit-owl-live.webp',arArt:'button_scenes_v75/moonlit-owl-ar.webp',name:'Moonlit owl',accent:'#bcb1fa',live:'#317f85',ar:'#7266e7'},
 {id:'butterfly-meadow',liveArt:'button_scenes_v75/butterfly-meadow-live.webp',arArt:'button_scenes_v75/butterfly-meadow-ar.webp',name:'Butterfly meadow',accent:'#efbf75',live:'#3a9b6b',ar:'#487ee1'}
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
 if(!hero || ['v79','v80'].includes(hero.dataset.hushThemeSystem))return; // Legacy themes must never overwrite the v79 dynamic/static selection.
 hero.style.setProperty('--hush-wallpaper',`url("themes_v74/${theme.id}.webp")`);
 hero.style.setProperty('--hush-theme-accent',theme.accent);
 hero.style.setProperty('--hush-live',theme.live);
 hero.style.setProperty('--hush-ar',theme.ar);
 hero.style.setProperty('--hush-live-photo',`url("${theme.liveArt}")`);
 hero.style.setProperty('--hush-ar-photo',`url("${theme.arArt}")`);
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
  const currentlyShown=hushCurrentTheme74().id;
  if(kind==='static')hushThemePrefs74.theme=currentlyShown;
  hushThemePrefs74.mode=kind;
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
 return `<section class="hush-story-home"><div class="hush-story-hero hush-immersive-home" style="--hush-wallpaper:url('themes_v74/${current.id}.webp');--hush-theme-accent:${current.accent};--hush-live:${current.live};--hush-ar:${current.ar};--hush-live-photo:url('${current.liveArt}');--hush-ar-photo:url('${current.arArt}')">
 <div class="hush-story-topbar"><button id="hush-theme-open-home" type="button" class="hush-story-icon" aria-label="Change home theme">⚙️</button><span class="hush-home-eyebrow" aria-hidden="true">WILDLIFE EXPLORER</span></div>
 <div class="hush-story-brand"><span class="hush-story-paw" aria-hidden="true">🐾</span><h1>Hush <em>Hunt</em></h1><p>EXPLORE · DISCOVER · LEARN</p></div>
 <div class="hush-home-hero-spacer" aria-hidden="true"></div>
 <div class="hush-home-action-zone"><p class="hush-theme-tag">${esc(current.name)}</p><div class="hush-story-main-actions"><button type="button" id="hush-direct-live" class="hush-story-main hush-story-main-live"><span class="emoji">📷</span><strong>Live Capture</strong><small>Find real wildlife</small></button><button type="button" id="hush-direct-ar" class="hush-story-main hush-story-main-ar"><span class="emoji">✨</span><strong>AR Safari</strong><small>Explore virtual wildlife</small></button></div>
 </div></div>
 <div class="hush-story-stats"><div><strong>${discovered}</strong><span>Discoveries</span></div><div><strong>${total}</strong><span>Sightings</span></div><div><strong>${badges}</strong><span>Badges</span></div></div><p class="hush-release-caption">v${WHISKER_BUILD} · build ${WHISKER_BUILD_NUMBER}</p></section>`;
};
const hushProfileBefore74=renderProfile;
renderProfile=function(){return hushProfileBefore74().replace('<div class="profile-actions">','<div class="profile-actions"><button id="hush-theme-open-profile" class="secondary" type="button">🎨 &nbsp; Home screen theme <span>›</span></button>')};
const hushWireBefore74=wireScreen;
wireScreen=function(){
 hushWireBefore74();
 $('hush-theme-open-home')?.addEventListener('click',hushThemeSettings74);
 $('hush-theme-open-profile')?.addEventListener('click',hushThemeSettings74);
 if($('hush-direct-live'))$('hush-direct-live').onclick=hushFastLiveCapture;
 if($('hush-direct-ar'))$('hush-direct-ar').onclick=()=>startArEncounter();
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
 tile.innerHTML=`<span class="field-guide-figure"><img src="field_art_v80/other-other.webp" loading="lazy" alt="" width="136" height="136"></span><span>Other</span>`;
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
 const other=document.createElement('button');other.type='button';other.className='field-guide-tile';other.dataset.guideType='Other';other.innerHTML='<span class="field-guide-figure"><img src="field_art_v80/other-other.webp" alt=""></span><span>Other</span>';
 other.onclick=()=>{const species=$('edit-species')?.value;const el=species==='Cat'?$('edit-coat'):$('edit-species-detail');if(el)el.value='Other';renderEditFieldGuide()};grid.appendChild(other);
};
const hushOldGuideRender74=hushGuideRender;
hushGuideRender=function(){hushOldGuideRender74();const screen=$('hush-fullscreen-guide');if(!screen)return;
 screen.querySelectorAll('.hush-guide-reference').forEach(tile=>{
  const kind=tile.dataset.hushGuideType;
  if(/^Other(?:\s|$)/.test(kind))tile.remove();
 });
 const note=screen.querySelector('.hush-guide-disclaimer');if(note)note.textContent='Illustrations are learning examples, not verified identifications. If the type is uncertain, choose Other and describe what you saw. Never disturb wildlife.';
 const grid=screen.querySelector('.hush-guide-references');
 if(grid){
  const other=document.createElement('button');other.type='button';other.className='hush-guide-reference hush-guide-other';
  other.innerHTML='<img src="field_art_v80/other-other.webp" alt="Unidentified wildlife"><strong>Other</strong><small>None of the examples match? Choose Other and add a note about what you saw.</small>';
  other.onclick=()=>{if(hushGuideHasForm()){hushGuideContext.type='Other';hushGuideUse()}else toast('Choose a type only when the features match. Other is also a valid discovery.')};
  grid.appendChild(other);
 }
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
  // The captured image must remain unobstructed; identification help lives in the guide below.
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


/* v3.10.14 / build 77 — post-capture tidy-up, restored burst chooser, cleaner species cards, and reliable theme switching. */
const HUSH_THEMES_76=[
 {id:'vivid-fox',name:'Twilight fox',accent:'#ff8fcf',live:'#1bb88c',ar:'#6f74ff',wallpaper:'themes_v79/vivid-fox.webp',liveArt:'button_scenes_v79/vivid-fox-live.webp',arArt:'button_scenes_v79/vivid-fox-ar.webp'},
 {id:'mountain-deer',name:'Mountain Deer',accent:'#ffcc7a',live:'#74c756',ar:'#65a7ff',wallpaper:'themes_v79/mountain-deer.webp',liveArt:'button_scenes_v79/mountain-deer-live.webp',arArt:'button_scenes_v79/mountain-deer-ar.webp'},
 {id:'meadow-rabbit',name:'Meadow Rabbit',accent:'#ffd968',live:'#66c84f',ar:'#4db2ff',wallpaper:'themes_v79/meadow-rabbit.webp',liveArt:'button_scenes_v79/meadow-rabbit-live.webp',arArt:'button_scenes_v79/meadow-rabbit-ar.webp'},
 {id:'waterfall-kingfisher',name:'Waterfall Blue Tit',accent:'#76d8ff',live:'#31bdb0',ar:'#477bff',wallpaper:'themes_v79/waterfall-kingfisher.webp',liveArt:'button_scenes_v79/waterfall-kingfisher-live.webp',arArt:'button_scenes_v79/waterfall-kingfisher-ar.webp'}
];
function hushLoadThemePrefs76(){
 try{const raw=JSON.parse(localStorage.getItem('hush.theme.settings.v77')||localStorage.getItem('hush.theme.settings.v76')||'{}');
  return {mode:raw.mode==='static'?'static':'dynamic',theme:HUSH_THEMES_76.some(t=>t.id===raw.theme)?raw.theme:'vivid-fox',motion:raw.motion===true};
 }catch{return {mode:'dynamic',theme:'vivid-fox',motion:false};}
}
let hushThemePrefs76=hushLoadThemePrefs76();
let hushLaunchTheme76='';
function hushPickLaunchTheme76(){
 if(hushThemePrefs76.mode==='static')return hushThemePrefs76.theme;
 let previous=-1;try{previous=Number(localStorage.getItem('hush.theme.last.v77')||localStorage.getItem('hush.theme.last.v76')||'-1');}catch{}
 const next=(previous+1)%HUSH_THEMES_76.length;
 try{localStorage.setItem('hush.theme.last.v77',String(next));}catch{}
 return HUSH_THEMES_76[next].id;
}
function hushCurrentTheme76(forceRotate=false){
 if(hushThemePrefs76.mode==='static'){
  hushLaunchTheme76=hushThemePrefs76.theme;
 }else if(forceRotate || !hushLaunchTheme76){
  hushLaunchTheme76=hushPickLaunchTheme76();
 }
 const id=hushLaunchTheme76||hushThemePrefs76.theme;
 return HUSH_THEMES_76.find(t=>t.id===id)||HUSH_THEMES_76[0];
}
function hushPersistTheme76(){
 try{localStorage.setItem('hush.theme.settings.v77',JSON.stringify(hushThemePrefs76));}catch{toast('Theme changes may not persist in private mode.');}
}
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden'&&hushThemePrefs76.mode==='dynamic')hushLaunchTheme76='';});
window.addEventListener('focus',()=>{if(hushThemePrefs76.mode==='dynamic'){hushLaunchTheme76='';if(s.screen==='home')render();}});
function hushThemeSettings76(){
 const current=hushCurrentTheme76();
 const options=HUSH_THEMES_76.map(t=>`<button type="button" data-hush-theme76="${t.id}" class="hush-theme-choice ${current.id===t.id?'active':''}" aria-pressed="${current.id===t.id}"><img src="${t.wallpaper}" alt=""><span>${esc(t.name)}</span></button>`).join('');
 openModal(`<div class="sheet-head"><h2>🎨 Home screen themes</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim">Choose a vibrant wildlife home screen. Dynamic rotates a different scene each time you reopen Hush Hunt.</p>
 <div class="hush-theme-mode" role="group" aria-label="Theme behaviour"><button id="hush-theme76-dynamic" class="secondary ${hushThemePrefs76.mode==='dynamic'?'active':''}" aria-pressed="${hushThemePrefs76.mode==='dynamic'}">🔀 Dynamic</button><button id="hush-theme76-static" class="secondary ${hushThemePrefs76.mode==='static'?'active':''}" aria-pressed="${hushThemePrefs76.mode==='static'}">📌 Static</button></div>
 <p class="footnote" id="hush-theme76-explanation">${hushThemePrefs76.mode==='dynamic'?'Dynamic rotates to a different scene whenever you reopen the app.':'Static keeps the selected scene on every launch.'}</p>
 <h3>Wildlife scenes</h3><div class="hush-theme-grid">${options}</div>
 <label class="check-row hush-motion-setting"><input id="hush-theme76-motion" type="checkbox" ${hushThemePrefs76.motion?'checked':''}><span>Subtle background motion (off by default)</span></label>
 <div class="actions"><button type="button" class="primary" id="hush-theme76-done">Save theme</button></div>`,false,'hush-theme-sheet');
 let shown=current.id;
 function setMode(kind){
  hushThemePrefs76.mode=kind;
  if(kind==='static')hushThemePrefs76.theme=shown;
  $('hush-theme76-dynamic').setAttribute('aria-pressed',String(kind==='dynamic'));
  $('hush-theme76-static').setAttribute('aria-pressed',String(kind==='static'));
  $('hush-theme76-dynamic').classList.toggle('active',kind==='dynamic');
  $('hush-theme76-static').classList.toggle('active',kind==='static');
  $('hush-theme76-explanation').textContent=kind==='dynamic'?'Dynamic rotates to a different scene whenever you reopen the app.':'Static keeps the selected scene on every launch.';
 }
 $('hush-theme76-dynamic').onclick=()=>setMode('dynamic');
 $('hush-theme76-static').onclick=()=>setMode('static');
 document.querySelectorAll('[data-hush-theme76]').forEach(btn=>btn.onclick=()=>{
  shown=btn.dataset.hushTheme76;
  hushThemePrefs76.theme=shown;
  // Choosing a specific scene is an explicit request to lock it in.
  setMode('static');
  hushLaunchTheme76=shown;
  document.querySelectorAll('[data-hush-theme76]').forEach(b=>{const on=b===btn;b.classList.toggle('active',on);b.setAttribute('aria-pressed',String(on));});
 });
 $('hush-theme76-motion').onchange=e=>{hushThemePrefs76.motion=e.target.checked;hushPersistTheme76();};
 $('hush-theme76-done').onclick=()=>{if(hushThemePrefs76.mode==='static'){hushThemePrefs76.theme=shown;hushLaunchTheme76=shown;}else hushLaunchTheme76='';hushPersistTheme76();closeModal();render();};
}
renderHome=function(){
 const current=hushCurrentTheme76(), total=allSightings().length, discovered=s.cats.length, badges=medals().filter(m=>m.ok).length;
 return `<section class="hush-story-home"><div class="hush-story-hero hush-immersive-home ${hushThemePrefs76.motion?'hush-motion':''}" data-hush-theme-system="v79" style="--hush-wallpaper:url('${current.wallpaper}');--hush-theme-accent:${current.accent};--hush-live:${current.live};--hush-ar:${current.ar};--hush-live-photo:url('${current.liveArt}');--hush-ar-photo:url('${current.arArt}')"><div class="hush-story-topbar"><button id="hush-theme-open-home" type="button" class="hush-story-icon" aria-label="Change home theme">⚙️</button><span class="hush-home-eyebrow" aria-hidden="true">WILDLIFE EXPLORER</span></div><div class="hush-story-brand"><div class="hush-story-paw">🐾</div><h1>Hush <em>Hunt</em></h1><p>EXPLORE · DISCOVER · LEARN</p></div><div class="hush-home-hero-spacer"></div><div class="hush-home-action-zone"><p class="hush-theme-tag">${esc(current.name)}</p><div class="hush-story-main-actions"><button type="button" id="hush-direct-live" class="hush-story-main hush-story-main-live"><span class="emoji">📷</span><strong>Live Capture</strong><small>Spot real wildlife around you</small></button><button type="button" id="hush-direct-ar" class="hush-story-main hush-story-main-ar"><span class="emoji">✨</span><strong>AR Safari</strong><small>Bring wildlife to life in AR</small></button></div></div></div><div class="hush-story-stats"><div><strong>${discovered}</strong><span>Discoveries</span></div><div><strong>${total}</strong><span>Sightings</span></div><div><strong>${badges}</strong><span>Badges</span></div></div><p class="hush-release-caption">v${WHISKER_BUILD} · build ${WHISKER_BUILD_NUMBER}</p></section>`;
};
const hushProfileBefore76=renderProfile;
renderProfile=function(){const html=hushProfileBefore76();return html.includes('id="hush-theme-open-profile"')?html:html.replace('<div class="profile-actions">','<div class="profile-actions"><button id="hush-theme-open-profile" class="secondary" type="button">🎨 &nbsp; Home screen theme <span>›</span></button>');};
const hushWireBefore76=wireScreen;
wireScreen=function(){
 hushWireBefore76();
 $('hush-direct-live')?.addEventListener('click',()=>hushFastLiveCapture());
 $('hush-direct-ar')?.addEventListener('click',()=>startArEncounter());
 $('hush-theme-open-home')?.addEventListener('click',hushThemeSettings76);
 $('hush-theme-open-profile')?.addEventListener('click',hushThemeSettings76);
};
function hushRearCandidates76(session){return (session?.rearDevices||[]).filter(d=>d?.deviceId&&!/front|selfie|user/i.test(d.label||''));}
hushLensName=function(device){const label=(device?.label||'').toLowerCase();return /ultra|super.?wide|wide.?angle|0[\.,]?(5|6)x|macro/.test(label)&&!/front|selfie|user/.test(label)};
hushLensList=function(session){
 const rear=hushRearCandidates76(session),primaryId=session?.stream?.getVideoTracks?.()[0]?.getSettings?.().deviceId;
 let ultra=rear.find(hushLensName);
 if(!ultra&&rear.length>1)ultra=rear.find(d=>d.deviceId!==primaryId)||rear[0]||null;
 const normal=rear.find(d=>d.deviceId===primaryId)||rear.find(d=>d.deviceId!==ultra?.deviceId)||rear[0]||null;
 return {ultra,normal};
};
hushWideAvailable=function(session){
 const caps=hushTrackZoom(session);
 if(caps && Number.isFinite(caps.min) && caps.min<=.61001)return true;
 return hushRearCandidates76(session).length>1 || !!hushLensList(session).ultra || /OnePlus|CPH/i.test(navigator.userAgent||'');
};
hushZoomFloor=function(session){return hushWideAvailable(session)?.6:1;};
function hushCompactLiveLayout76(){
 const sheet=document.querySelector('#modal-layer .sheet.live-sheet'),stage=$('encounter-stage');
 if(!sheet||!stage||s.encounterAr)return;
 sheet.classList.add('hush-camera-clean');
 const title=document.querySelector('#modal-layer .sheet-head h2'); if(title)title.textContent='Live Capture';
 const tag=stage.querySelector('.encounter-capture-tag'); if(tag)tag.textContent='● LIVE';
 const species=document.querySelector('.hush-live-species');
 if(species){
  if(species.parentElement!==stage)stage.appendChild(species);
  species.classList.add('hush-live-species-compact');
  species.querySelector('label')?.setAttribute('aria-hidden','true');
  const hint=species.querySelector('small'); if(hint){hint.textContent=''; hint.setAttribute('aria-hidden','true');}
 }
 const status=$('encounter-status'); if(status&&!s.encounterCaptured)status.textContent='Use 0.6× / 1× / 2× / 3× or pinch to frame your subject, then tap the shutter.';
 let toggle=$('hush-game-toggle');
 if(!toggle){
  toggle=document.createElement('button');toggle.type='button';toggle.id='hush-game-toggle';toggle.className='hush-game-toggle';toggle.textContent='🐾 Game';toggle.setAttribute('aria-pressed','false');
  toggle.onclick=()=>{const on=sheet.classList.toggle('hush-game-open');toggle.setAttribute('aria-pressed',String(on));toggle.textContent=on?'✕ Close game':'🐾 Game';};
  stage.appendChild(toggle);
 }
 const zoom=$('hush-live-zoom');
 if(zoom&&liveCamera?.active){
  hushRefreshZoomControls(liveCamera);
  if(!zoom.querySelector('[data-hush-zoom="0.6"]') && hushWideAvailable(liveCamera)){
   const button=document.createElement('button');button.type='button';button.className='hush-zoom-option';button.dataset.hushZoom='0.6';button.textContent='0.6×';button.setAttribute('aria-label','Zoom 0.6×');button.onclick=()=>hushSetLiveZoom(liveCamera,.6);
   const first=zoom.querySelector('button[data-hush-zoom]');if(first)zoom.insertBefore(button,first);else zoom.appendChild(button);
  }
 }
}
const hushAddLiveControlsBefore76=hushAddLiveControls;
hushAddLiveControls=function(){hushAddLiveControlsBefore76();if(liveCamera?.active&&!s.encounterAr)hushCompactLiveLayout76();};
const hushShowEncounterBefore76=showEncounter;
showEncounter=function(image,quality,options={}){const result=hushShowEncounterBefore76(image,quality,options);if(options.live===true&&options.ar!==true)hushCompactLiveLayout76();return result;};


/* v3.10.16: responsive, species-specific discovery flow with explicit repeat behavior. */
const hushPreviousShowCatForm78=showCatForm;
function hushDiscoverySpeciesLabel79(){
 const group=$('wildlife-species')?.value||s.spottedSpecies||'Other';
 return (SPECIES.includes(group)&&group!=='Other')?group:'wildlife';
}
function hushUpdateDiscovery79(){
 const sheet=document.querySelector('#modal-layer .sheet.identified-sheet');
 if(!sheet)return;
 const group=hushDiscoverySpeciesLabel79();
 const newBtn=$('mode-new'), repeatBtn=$('mode-repeat');
 if(!newBtn||!repeatBtn)return;
 const label=group==='wildlife'?'New wildlife':`New ${group}`;
 newBtn.textContent=`✨ ${label}`;
 newBtn.setAttribute('aria-label',`Add a new ${group.toLowerCase()} to your collection`);
 const already=visibleWildlife().filter(c=>speciesOf(c)===(group==='wildlife'?'Other':group));
 repeatBtn.textContent='↻ Seen before';
 repeatBtn.disabled=already.length===0;
 repeatBtn.setAttribute('aria-label',already.length?`Add another sighting of a ${group.toLowerCase()} already in your collection`:`No ${group.toLowerCase()} discoveries in your collection yet`);
 if(!already.length && s.catchMode==='repeat'){
  newBtn.click();
  return;
 }
 let help=$('hush-repeat-explainer');
 if(!help){
  help=document.createElement('p');help.id='hush-repeat-explainer';help.className='hush-repeat-explainer';help.setAttribute('role','status');
  newBtn.closest('.chips')?.insertAdjacentElement('afterend',help);
 }
 if(help){
  help.textContent=s.catchMode==='repeat'
   ?`Choose which ${group.toLowerCase()} you have already collected. This photo will be saved as another sighting, not a new animal.`
   :already.length?`New creates a separate ${group.toLowerCase()} entry. “Seen before” adds this photo to one of your ${already.length} existing ${already.length===1?'entry':'entries'}.`
   :`This will be your first saved ${group.toLowerCase()} discovery. “Seen before” becomes available after you collect one.`;
 }
 const title=$('hush-id-title'), subtitle=$('hush-id-subtitle');
 const specific=(group==='wildlife'?'Wildlife':group);
 const kind=group==='Cat'?($('cat-coat')?.value||''):
  ($('wildlife-detail')?.value?.trim()||s.spottedDetail||'');
 if(title)title.textContent=group==='wildlife'?'Species not chosen':specific;
 if(subtitle)subtitle.textContent=kind&&kind!=='Other'&&kind!=='Not sure'?`Kind: ${kind}`:group==='wildlife'?'Choose an animal below to identify this photo':'Choose the kind below, if known';
 const intro=newBtn.closest('.chips')?.previousElementSibling;
 if(intro&&intro.tagName==='P')intro.textContent='Are you adding a new animal or another sighting of one you already know?';
}
showCatForm=function(photo){
 const output=hushPreviousShowCatForm78(photo);
 const sheet=document.querySelector('#modal-layer .sheet.identified-sheet');
 if(!sheet)return output;
 const oldSummary=[...sheet.children].find(el=>el.classList?.contains('info-note')&&el.textContent.includes('Encounter complete'));
 if(oldSummary)oldSummary.classList.add('hush-legacy-summary');
 // Layout order: heading → unobstructed photo → simple identification → choose new or seen before.
 const image=$('hush-id-photo'); if(image)image.src=photo;
 const summary=sheet.querySelector('.hush-identified-panel');
 const header=sheet.querySelector('.sheet-head');
 if(summary&&header&&summary.previousElementSibling!==header)header.insertAdjacentElement('afterend',summary);
 sheet.classList.add('hush-discovery-v79');
 const newBtn=$('mode-new'), repeatBtn=$('mode-repeat');
 for(const button of [newBtn,repeatBtn])button?.addEventListener('click',()=>queueMicrotask(hushUpdateDiscovery79));
 $('wildlife-species')?.addEventListener('change',()=>queueMicrotask(hushUpdateDiscovery79));
 $('cat-coat')?.addEventListener('change',()=>queueMicrotask(hushUpdateDiscovery79));
 $('wildlife-detail')?.addEventListener('input',()=>queueMicrotask(hushUpdateDiscovery79));
 // Species tiles are dynamic; delegated click listener survives guide re-renders.
 sheet.addEventListener('click',event=>{
  if(event.target.closest('[data-guide-type],[data-guide-group],[data-hush-capture-category],#change-species'))
   queueMicrotask(hushUpdateDiscovery79);
 });
 hushUpdateDiscovery79();
 sheet.scrollTop=0;
 return output;
};


// v3.10.15: Earlier release wrappers registered duplicate bubble listeners.
// Capture-phase launch dispatch gives the requested mode exactly one launch per tap.
const hushWireBefore78=wireScreen;
wireScreen=function(){
  hushWireBefore78();
  const live=document.getElementById('hush-direct-live');
  const ar=document.getElementById('hush-direct-ar');
  if(live)live.addEventListener('click',event=>{
    event.preventDefault();event.stopImmediatePropagation();
    hushFastLiveCapture();
  },{capture:true});
  if(ar)ar.addEventListener('click',event=>{
    event.preventDefault();event.stopImmediatePropagation();
    hushChooseArSafari();
  },{capture:true});
  for(const id of ['hush-theme-open-home','hush-theme-open-profile']){
    const button=document.getElementById(id);
    if(button)button.addEventListener('click',event=>{
      event.preventDefault();event.stopImmediatePropagation();
      hushThemeSettings80();
    },{capture:true});
  }
};


/* v3.10.17 build 80: canonical wildlife themes, reptiles heading and cleaned art */
if(typeof HUSH_FIELD_EDUCATION!=='undefined'){
 if(HUSH_FIELD_EDUCATION.types?.Bee)HUSH_FIELD_EDUCATION.types.Bee.Wasp='Wasps are not bees: most have a smoother body and narrow waist. View from a distance and never disturb a nest. This tile is a general illustration, not a species-level identification.';
}
// Preserve the database identifier "Other" so earlier reptile discoveries remain readable;
// show a precise category name instead of "Other" when identifying a lizard or tortoise.
const hushSpeciesRenderBefore80=renderFieldGuideSpecies;
renderFieldGuideSpecies=function(){
 hushSpeciesRenderBefore80();
 const chosen=$('field-guide-selected');
 const reptile=s.spottedSpecies==='Other'&&hushCaptureCategory==='Reptiles';
 if(reptile){
  const label=chosen?.querySelector('strong');if(label)label.textContent='Reptiles';
  const small=chosen?.querySelector('small');if(small)small.textContent='Choose Lizard or Tortoise below';
  const candidate=$('field-guide-species')?.querySelector('[data-guide-group="Other"]>span:not(.field-guide-figure)');
  if(candidate)candidate.textContent='Reptiles';
 }
};
const hushVarietiesBefore80=renderFieldGuideVarieties;
renderFieldGuideVarieties=function(){
 hushVarietiesBefore80();
 const section=$('field-guide-types')?.closest('.visual-field-types');
 if(s.spottedSpecies==='Other'&&hushCaptureCategory==='Reptiles'){
  const heading=section?.querySelector('h3');if(heading)heading.textContent='Reptile varieties';
 }
 if(s.spottedSpecies==='Bee'){
  const heading=section?.querySelector('h3');if(heading)heading.textContent='Bees and wasps';
 }
};
const HUSH_THEMES_80=[
 {id:'twilight-fox',name:'Twilight Fox',wallpaper:'themes_v80/twilight-fox.webp',liveArt:'button_scenes_v80/twilight-fox-live.webp',arArt:'button_scenes_v80/twilight-fox-ar.webp'},
 {id:'mountain-deer',name:'Mountain Deer',wallpaper:'themes_v80/mountain-deer.webp',liveArt:'button_scenes_v80/mountain-deer-live.webp',arArt:'button_scenes_v80/mountain-deer-ar.webp'},
 {id:'meadow-rabbit',name:'Meadow Rabbit',wallpaper:'themes_v80/meadow-rabbit.webp',liveArt:'button_scenes_v80/meadow-rabbit-live.webp',arArt:'button_scenes_v80/meadow-rabbit-ar.webp'},
 {id:'waterfall-kingfisher',name:'Waterfall Blue Tit',wallpaper:'themes_v80/waterfall-kingfisher.webp',liveArt:'button_scenes_v80/waterfall-kingfisher-live.webp',arArt:'button_scenes_v80/waterfall-kingfisher-ar.webp'},
 {id:'forest-owl',name:'Forest Owl',wallpaper:'themes_v80/forest-owl.webp',liveArt:'button_scenes_v80/forest-owl-live.webp',arArt:'button_scenes_v80/forest-owl-ar.webp'},
 {id:'highland-stag',name:'Highland Stag',wallpaper:'themes_v80/highland-stag.webp',liveArt:'button_scenes_v80/highland-stag-live.webp',arArt:'button_scenes_v80/highland-stag-ar.webp'},
 {id:'butterfly-garden',name:'Butterfly Garden',wallpaper:'themes_v80/butterfly-garden.webp',liveArt:'button_scenes_v80/butterfly-garden-live.webp',arArt:'button_scenes_v80/butterfly-garden-ar.webp'},
 {id:'lakeside-swan',name:'Lakeside Swan',wallpaper:'themes_v80/lakeside-swan.webp',liveArt:'button_scenes_v80/lakeside-swan-live.webp',arArt:'button_scenes_v80/lakeside-swan-ar.webp'},
 {id:'woodland-hedgehog',name:'Woodland Hedgehog',wallpaper:'themes_v80/woodland-hedgehog.webp',liveArt:'button_scenes_v80/woodland-hedgehog-live.webp',arArt:'button_scenes_v80/woodland-hedgehog-ar.webp'},
 {id:'autumn-squirrel',name:'Autumn Squirrel',wallpaper:'themes_v80/autumn-squirrel.webp',liveArt:'button_scenes_v80/autumn-squirrel-live.webp',arArt:'button_scenes_v80/autumn-squirrel-ar.webp'},
 {id:'moonlit-badger',name:'Moonlit Bat',wallpaper:'themes_v80/moonlit-badger.webp',liveArt:'button_scenes_v80/moonlit-badger-live.webp',arArt:'button_scenes_v80/moonlit-badger-ar.webp'},
 {id:'sunrise-robin',name:'Sunrise Robin',wallpaper:'themes_v80/sunrise-robin.webp',liveArt:'button_scenes_v80/sunrise-robin-live.webp',arArt:'button_scenes_v80/sunrise-robin-ar.webp'},
 {id:'bluebell-hare',name:'Bluebell Rabbit',wallpaper:'themes_v80/bluebell-hare.webp',liveArt:'button_scenes_v80/bluebell-hare-live.webp',arArt:'button_scenes_v80/bluebell-hare-ar.webp'},
 {id:'bumblebee-meadow',name:'Bumblebee Meadow',wallpaper:'themes_v80/bumblebee-meadow.webp',liveArt:'button_scenes_v80/bumblebee-meadow-live.webp',arArt:'button_scenes_v80/bumblebee-meadow-ar.webp'},
 {id:'dragonfly-pond',name:'Dragonfly Pond',wallpaper:'themes_v80/dragonfly-pond.webp',liveArt:'button_scenes_v80/dragonfly-pond-live.webp',arArt:'button_scenes_v80/dragonfly-pond-ar.webp'},
 {id:'misty-wolf',name:'Misty Husky',wallpaper:'themes_v80/misty-wolf.webp',liveArt:'button_scenes_v80/misty-wolf-live.webp',arArt:'button_scenes_v80/misty-wolf-ar.webp'},
 {id:'coastal-seagull',name:'Coastal Seagull',wallpaper:'themes_v80/coastal-seagull.webp',liveArt:'button_scenes_v80/coastal-seagull-live.webp',arArt:'button_scenes_v80/coastal-seagull-ar.webp'},
 {id:'rainforest-frog',name:'Rainforest Frog',wallpaper:'themes_v80/rainforest-frog.webp',liveArt:'button_scenes_v80/rainforest-frog-live.webp',arArt:'button_scenes_v80/rainforest-frog-ar.webp'},
 {id:'riverside-otter',name:'Riverside Fish',wallpaper:'themes_v80/riverside-otter.webp',liveArt:'button_scenes_v80/riverside-otter-live.webp',arArt:'button_scenes_v80/riverside-otter-ar.webp'},
 {id:'alpine-eagle',name:'Alpine Parakeet',wallpaper:'themes_v80/alpine-eagle.webp',liveArt:'button_scenes_v80/alpine-eagle-live.webp',arArt:'button_scenes_v80/alpine-eagle-ar.webp'}
];
const HUSH_THEME_PREF_KEY_80='hush.theme.preferences.v80';
function hushThemeLoad80(){
 let old={};
 try{old=JSON.parse(localStorage.getItem(HUSH_THEME_PREF_KEY_80)||localStorage.getItem('hush.theme.settings.v77')||localStorage.getItem('hush.theme.settings.v76')||'{}')}catch{}
 let theme=old.theme||'twilight-fox';
 if(theme==='vivid-fox')theme='twilight-fox';
 if(!HUSH_THEMES_80.some(t=>t.id===theme))theme='twilight-fox';
 return {mode:old.mode==='static'?'static':'dynamic',theme,motion:old.motion===true};
}
let hushThemePref80=hushThemeLoad80();
let hushThemeSession80=null;
let hushThemeWasHidden80=false;
function hushPersist80(){try{localStorage.setItem(HUSH_THEME_PREF_KEY_80,JSON.stringify(hushThemePref80))}catch{}}
function hushPickTheme80(){
 if(hushThemePref80.mode==='static')return hushThemePref80.theme;
 let previous='';try{previous=localStorage.getItem('hush.theme.last.v80')||''}catch{}
 const idx=HUSH_THEMES_80.findIndex(x=>x.id===previous);
 const chosen=HUSH_THEMES_80[(idx+1)%HUSH_THEMES_80.length];
 try{localStorage.setItem('hush.theme.last.v80',chosen.id)}catch{}
 return chosen.id;
}
function hushCurrentTheme80(){
 if(hushThemePref80.mode==='static')hushThemeSession80=hushThemePref80.theme;
 else if(!hushThemeSession80)hushThemeSession80=hushPickTheme80();
 return HUSH_THEMES_80.find(x=>x.id===hushThemeSession80)||HUSH_THEMES_80[0];
}
document.addEventListener('visibilitychange',()=>{
 if(document.hidden){hushThemeWasHidden80=true;return;}
 if(hushThemeWasHidden80){hushThemeWasHidden80=false;if(hushThemePref80.mode==='dynamic'){hushThemeSession80=null;if(s.screen==='home')render();}}
});
function hushThemeSettings80(){
 const active=hushCurrentTheme80();
 const cards=HUSH_THEMES_80.map(x=>`<button type="button" class="hush-theme-choice ${x.id===active.id?'active':''}" data-v80-theme="${x.id}" aria-pressed="${x.id===active.id}"><img src="${x.wallpaper}" loading="lazy" alt=""/><span>${esc(x.name)}</span></button>`).join('');
 openModal(`<div class="sheet-head"><h2>🎨 Home screen themes</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim">Choose a scene to keep it fixed, or select Dynamic to rotate through all 20 wildlife designs each time you reopen the app.</p><div class="hush-theme-mode"><button id="hush-v80-dynamic" type="button" class="secondary ${hushThemePref80.mode==='dynamic'?'active':''}">🔀 Dynamic</button><button id="hush-v80-static" type="button" class="secondary ${hushThemePref80.mode==='static'?'active':''}">📌 Static</button></div><p class="footnote" id="hush-v80-mode-help">${hushThemePref80.mode==='static'?'Your selected scene stays fixed.':'Automatically changes when you return to the app.'}</p><div class="hush-theme-grid">${cards}</div><p class="footnote">These colourful scenes are bundled for offline use.</p><div class="actions"><button type="button" class="primary" id="hush-v80-save">Apply theme</button></div>`,false,'hush-theme-sheet');
 function setMode(mode){hushThemePref80.mode=mode;for(const id of ['dynamic','static'])$('hush-v80-'+id)?.classList.toggle('active',mode===id);$('hush-v80-mode-help').textContent=mode==='dynamic'?'A new scene is selected when you return to the app.':'The selected wildlife scene stays fixed.';}
 $('hush-v80-dynamic').onclick=()=>setMode('dynamic');
 $('hush-v80-static').onclick=()=>setMode('static');
 document.querySelectorAll('[data-v80-theme]').forEach(b=>b.onclick=()=>{
  hushThemePref80.theme=b.dataset.v80Theme;setMode('static');
  document.querySelectorAll('[data-v80-theme]').forEach(n=>{const on=n===b;n.classList.toggle('active',on);n.setAttribute('aria-pressed',String(on))});
 });
 $('hush-v80-save').onclick=()=>{
  if(hushThemePref80.mode==='static')hushThemeSession80=hushThemePref80.theme;
  else hushThemeSession80=null;
  hushPersist80();closeModal();render();
 };
}
renderHome=function(){
 const theme=hushCurrentTheme80(),total=allSightings().length,discovered=visibleWildlife().length,badges=medals().filter(m=>m.ok).length;
 return `<section class="hush-story-home"><div class="hush-story-hero hush-immersive-home hush-v80-home hush-v81-home" data-hush-theme-system="v80" data-active-theme="${theme.id}" style="--hush-wallpaper:url('${theme.wallpaper}');--hush-live-photo:url('${theme.liveArt}');--hush-ar-photo:url('${theme.arArt}')"><img class="hush-theme-photo" src="${esc(theme.wallpaper)}" alt="" aria-hidden="true" decoding="async" fetchpriority="high"><div class="hush-story-topbar"><button type="button" id="hush-theme-open-home" class="hush-story-icon" aria-label="Choose a home theme">⚙️</button><span class="hush-home-eyebrow">WILDLIFE EXPLORER</span></div><div class="hush-story-brand"><span class="hush-story-paw">🐾</span><h1>Hush <em>Hunt</em></h1><p>EXPLORE · DISCOVER · LEARN</p></div><div class="hush-home-hero-spacer"></div><div class="hush-home-action-zone"><p class="hush-theme-tag">${esc(theme.name)}</p><div class="hush-story-main-actions"><button id="hush-direct-live" type="button" class="hush-story-main hush-story-main-live"><span class="emoji">📷</span><strong>Live Capture</strong><small>Spot real wildlife</small></button><button id="hush-direct-ar" type="button" class="hush-story-main hush-story-main-ar"><span class="emoji">✨</span><strong>AR Safari</strong><small>Explore virtual wildlife</small></button></div></div></div><div class="hush-story-stats"><div><strong>${discovered}</strong><span>Discoveries</span></div><div><strong>${total}</strong><span>Sightings</span></div><div><strong>${badges}</strong><span>Badges</span></div></div><p class="hush-release-caption">v${WHISKER_BUILD} · build ${WHISKER_BUILD_NUMBER}</p></section>`;
};
// Install single capture-phase handler which overrides legacy theme listeners.
const hushWireBefore80=wireScreen;
wireScreen=function(){
 hushWireBefore80();
 for(const id of ['hush-theme-open-home','hush-theme-open-profile']){
  const button=$(id);if(button)button.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();hushThemeSettings80()},{capture:true});
 }
};


/* v3.10.18 / Build 81: Reliable photographic theme background + genuine wide lens handling. */
// A dedicated full-bleed image sits behind the UI. It is independent of earlier
// !important CSS background shorthands which accidentally hid the selected theme.
function hushRepairHomeScene81(){
 const hero=document.querySelector('.hush-v81-home');if(!hero)return;
 const img=hero.querySelector('.hush-theme-photo');if(!img)return;
 const theme=hushCurrentTheme80();
 if(img.getAttribute('src')!==theme.wallpaper)img.setAttribute('src',theme.wallpaper);
 hero.dataset.activeTheme=theme.id;
 img.onerror=()=>{
  // If the newest packaged asset is missing, keep a nature-themed fallback,
  // not a blank green/purple expanse.
  hero.classList.add('hush-theme-asset-error');
  const fallback='themes_v74/'+theme.id+'.webp';
  if(!img.dataset.fallbackTried&&theme.id!=='twilight-fox'){
   img.dataset.fallbackTried='true';img.src='themes_v74/twilight-fox.webp';
  }
 };
 img.onload=()=>hero.classList.remove('hush-theme-asset-error');
}
const hushWireBefore81=wireScreen;
wireScreen=function(){
 hushWireBefore81();
 hushRepairHomeScene81();
};
// Browser device lists may contain macro/telephoto/selfie cameras. Multiple
// video inputs are not proof of an ultrawide camera. Match only explicit labels.
hushLensName=function(device){
 const label=(device?.label||'').toLowerCase();
 return !/front|selfie|user|macro|telephoto/.test(label)&&
  /ultra[ -]?wide|super[ -]?wide|wide[ -]?angle|0[.,]?[56]\s*x/.test(label);
};
hushLensList=function(session){
 const devices=(session?.rearDevices||[]).filter(d=>d?.deviceId&&!/front|selfie|user/i.test(d.label||''));
 const current=session?.stream?.getVideoTracks?.()[0]?.getSettings?.().deviceId;
 const ultra=devices.find(hushLensName)||null;
 const normal=devices.find(d=>d.deviceId===current&&d.deviceId!==ultra?.deviceId)||
  devices.find(d=>d.deviceId!==ultra?.deviceId)||null;
 return {ultra,normal};
};
hushWideAvailable=function(session){
 const z=hushTrackZoom(session);
 return !!(z&&Number.isFinite(Number(z.min))&&Number(z.min)<=.61001)||!!hushLensList(session).ultra;
};
hushZoomFloor=function(session){return hushWideAvailable(session)?.6:1;};
function hushShowPhoneWide81(){
 const stage=$('encounter-stage');if(!stage)return;
 const prev=stage.querySelector('#hush-wide81');if(prev){prev.remove();return;}
 const panel=document.createElement('section');
 panel.id='hush-wide81';panel.className='hush-wide81';panel.setAttribute('role','dialog');
 panel.setAttribute('aria-label','Use the ultrawide camera');
 panel.innerHTML='<strong>0.6× ultrawide</strong><p>Your phone has an ultrawide camera, but Android WebView hasn\'t exposed it to Hush Hunt. Shrinking the 1× picture would not make the view wider. Open your phone camera, select <b>0.6×</b>, then take the photo. You can still add it to your collection.</p><div class="hush-wide81-actions"><button type="button" class="primary" id="hush-wide81-native">📷 Open phone camera</button><button type="button" class="secondary" id="hush-wide81-cancel">Keep 1× live view</button></div>';
 stage.appendChild(panel);
 $('hush-wide81-native').onclick=()=>{panel.remove();void requestEncounterPhoto(true);};
 $('hush-wide81-cancel').onclick=()=>panel.remove();
}
const hushSetZoomBefore81=hushSetLiveZoom;
hushSetLiveZoom=async function(session,value){
 if(!session?.active||session!==liveCamera||s.encounterCaptured)return;
 if(Number(value)<1&&!hushWideAvailable(session)){
  hushShowPhoneWide81();return;
 }
 await hushSetZoomBefore81(session,value);
 // Do not display 0.6× as applied if the native track stayed at 1×.
 if(Number(value)<1&&session===liveCamera&&session.lens!=='ultra'){
  const z=Number(session.stream?.getVideoTracks?.()[0]?.getSettings?.().zoom);
  if(Number.isFinite(z)&&z>.68){
   session.logicalZoom=1;session.zoomLabel='1×';
   session.video.style.transform='none';session.digitalZoom=1;
   hushRefreshZoomControls(session);
   toast('Wide lens was not applied. Use your phone camera for a true 0.6× photo.');
   hushShowPhoneWide81();
  }
 }
};
// 0.6× is always discoverable, but switches to a documented native-camera route
// when WebView doesn't provide actual ultrawide frames. No fake CSS zoom-out.
hushRefreshZoomControls=function(session){
 if(!session?.active||session!==liveCamera)return;
 const dock=$('hush-live-zoom');if(!dock)return;
 const canWide=hushWideAvailable(session);
 const current=Number(session.logicalZoom||(session.lens==='ultra'?.6:1));
 const values=[.6,1,2,3];
 dock.innerHTML=values.map(v=>`<button type="button" data-hush-zoom="${v}" class="hush-zoom-option ${Math.abs(current-v)<.055?'selected':''}" aria-pressed="${Math.abs(current-v)<.055}" aria-label="${v===.6&&!canWide?'Open phone ultrawide 0.6× camera':'Zoom '+v+'×'}" title="${v===.6&&!canWide?'Use phone camera for a true ultrawide photo':'Camera zoom'}">${v===.6&&!canWide?'0.6× ↗':v+'×'}</button>`).join('');
 dock.querySelectorAll('button').forEach(b=>b.onclick=()=>hushSetLiveZoom(session,Number(b.dataset.hushZoom)));
 dock.setAttribute('aria-label',canWide?'Zoom controls including ultrawide':'Zoom controls; 0.6× opens phone ultrawide camera');
};
hushSyncZoomUi=hushRefreshZoomControls;


/* v3.10.19 — single authoritative majestic gallery theme implementation. */
const HUSH_THEMES_83=[{id:"twilight-fox",name:"Twilight Fox",wallpaper:"themes_v87/twilight-fox.webp",preview:"theme_previews_v87/twilight-fox.webp",liveArt:"button_scenes_v87/twilight-fox-live.webp",arArt:"button_scenes_v87/twilight-fox-ar.webp"},{id:"mountain-deer",name:"Mountain Deer",wallpaper:"themes_v87/mountain-deer.webp",preview:"theme_previews_v87/mountain-deer.webp",liveArt:"button_scenes_v87/mountain-deer-live.webp",arArt:"button_scenes_v87/mountain-deer-ar.webp"},{id:"meadow-rabbit",name:"Meadow Rabbit",wallpaper:"themes_v87/meadow-rabbit.webp",preview:"theme_previews_v87/meadow-rabbit.webp",liveArt:"button_scenes_v87/meadow-rabbit-live.webp",arArt:"button_scenes_v87/meadow-rabbit-ar.webp"},{id:"waterfall-kingfisher",name:"Waterfall Kingfisher",wallpaper:"themes_v87/waterfall-kingfisher.webp",preview:"theme_previews_v87/waterfall-kingfisher.webp",liveArt:"button_scenes_v87/waterfall-kingfisher-live.webp",arArt:"button_scenes_v87/waterfall-kingfisher-ar.webp"},{id:"forest-owl",name:"Forest Owl",wallpaper:"themes_v87/forest-owl.webp",preview:"theme_previews_v87/forest-owl.webp",liveArt:"button_scenes_v87/forest-owl-live.webp",arArt:"button_scenes_v87/forest-owl-ar.webp"},{id:"lakeside-swan",name:"Lakeside Swan",wallpaper:"themes_v87/lakeside-swan.webp",preview:"theme_previews_v87/lakeside-swan.webp",liveArt:"button_scenes_v87/lakeside-swan-live.webp",arArt:"button_scenes_v87/lakeside-swan-ar.webp"},{id:"woodland-hedgehog",name:"Woodland Hedgehog",wallpaper:"themes_v87/woodland-hedgehog.webp",preview:"theme_previews_v87/woodland-hedgehog.webp",liveArt:"button_scenes_v87/woodland-hedgehog-live.webp",arArt:"button_scenes_v87/woodland-hedgehog-ar.webp"},{id:"red-squirrel-glade",name:"Red Squirrel Glade",wallpaper:"themes_v87/red-squirrel-glade.webp",preview:"theme_previews_v87/red-squirrel-glade.webp",liveArt:"button_scenes_v87/red-squirrel-glade-live.webp",arArt:"button_scenes_v87/red-squirrel-glade-ar.webp"},{id:"robin-dawn",name:"Robin Dawn",wallpaper:"themes_v87/robin-dawn.webp",preview:"theme_previews_v87/robin-dawn.webp",liveArt:"button_scenes_v87/robin-dawn-live.webp",arArt:"button_scenes_v87/robin-dawn-ar.webp"},{id:"butterfly-garden",name:"Butterfly Garden",wallpaper:"themes_v87/butterfly-garden.webp",preview:"theme_previews_v87/butterfly-garden.webp",liveArt:"button_scenes_v87/butterfly-garden-live.webp",arArt:"button_scenes_v87/butterfly-garden-ar.webp"},{id:"highland-stag",name:"Highland Stag",wallpaper:"themes_v87/highland-stag.webp",preview:"theme_previews_v87/highland-stag.webp",liveArt:"button_scenes_v87/highland-stag-live.webp",arArt:"button_scenes_v87/highland-stag-ar.webp"},{id:"river-otter",name:"River Otter",wallpaper:"themes_v87/river-otter.webp",preview:"theme_previews_v87/river-otter.webp",liveArt:"button_scenes_v87/river-otter-live.webp",arArt:"button_scenes_v87/river-otter-ar.webp"},{id:"puffin-cliffs",name:"Puffin Cliffs",wallpaper:"themes_v87/puffin-cliffs.webp",preview:"theme_previews_v87/puffin-cliffs.webp",liveArt:"button_scenes_v87/puffin-cliffs-live.webp",arArt:"button_scenes_v87/puffin-cliffs-ar.webp"},{id:"moonlit-badger",name:"Moonlit Badger",wallpaper:"themes_v87/moonlit-badger.webp",preview:"theme_previews_v87/moonlit-badger.webp",liveArt:"button_scenes_v87/moonlit-badger-live.webp",arArt:"button_scenes_v87/moonlit-badger-ar.webp"},{id:"autumn-hare",name:"Autumn Hare",wallpaper:"themes_v87/autumn-hare.webp",preview:"theme_previews_v87/autumn-hare.webp",liveArt:"button_scenes_v87/autumn-hare-live.webp",arArt:"button_scenes_v87/autumn-hare-ar.webp"},{id:"golden-eagle-peaks",name:"Golden Eagle Peaks",wallpaper:"themes_v87/golden-eagle-peaks.webp",preview:"theme_previews_v87/golden-eagle-peaks.webp",liveArt:"button_scenes_v87/golden-eagle-peaks-live.webp",arArt:"button_scenes_v87/golden-eagle-peaks-ar.webp"},{id:"woodland-frog",name:"Woodland Frog",wallpaper:"themes_v87/woodland-frog.webp",preview:"theme_previews_v87/woodland-frog.webp",liveArt:"button_scenes_v87/woodland-frog-live.webp",arArt:"button_scenes_v87/woodland-frog-ar.webp"},{id:"wildflower-bee-meadow",name:"Wildflower Bee Meadow",wallpaper:"themes_v87/wildflower-bee-meadow.webp",preview:"theme_previews_v87/wildflower-bee-meadow.webp",liveArt:"button_scenes_v87/wildflower-bee-meadow-live.webp",arArt:"button_scenes_v87/wildflower-bee-meadow-ar.webp"},{id:"arctic-fox-snowfall",name:"Arctic Fox Snowfall",wallpaper:"themes_v87/arctic-fox-snowfall.webp",preview:"theme_previews_v87/arctic-fox-snowfall.webp",liveArt:"button_scenes_v87/arctic-fox-snowfall-live.webp",arArt:"button_scenes_v87/arctic-fox-snowfall-ar.webp"},{id:"red-panda-bamboo",name:"Red Panda Bamboo",wallpaper:"themes_v87/red-panda-bamboo.webp",preview:"theme_previews_v87/red-panda-bamboo.webp",liveArt:"button_scenes_v87/red-panda-bamboo-live.webp",arArt:"button_scenes_v87/red-panda-bamboo-ar.webp"}];
const HUSH_THEME_STORE_82='hush.theme.settings.v87';
function hushLoadTheme82(){
 let obj={};
 try { obj=JSON.parse(localStorage.getItem(HUSH_THEME_STORE_82)||localStorage.getItem('hush.theme.settings.v82')||localStorage.getItem('hush.theme.preferences.v80')||'{}'); }catch{}
 const ids=HUSH_THEMES_83.map(t=>t.id);
 let theme=obj.theme||'twilight-fox';
 if(theme==='vivid-fox')theme='twilight-fox';
 if(!ids.includes(theme))theme='twilight-fox';
 return {mode:obj.mode==='static'?'static':'dynamic',theme,motion:obj.motion===true};
}
// Earlier handlers all delegate to these functions after this assignment.
// Keep existing preference references to avoid competing v74/v76/v80 engines.
hushThemePref80=hushLoadTheme82();
hushThemeSession80=null;
hushPersist80=function(){try{localStorage.setItem(HUSH_THEME_STORE_82,JSON.stringify(hushThemePref80));}catch{}};
hushPickTheme80=function(){
 if(hushThemePref80.mode==='static')return hushThemePref80.theme;
 let last='';try{last=localStorage.getItem('hush.theme.last.v87')||'';}catch{}
 const pos=HUSH_THEMES_83.findIndex(t=>t.id===last);
 const t=HUSH_THEMES_83[(pos+1+HUSH_THEMES_83.length)%HUSH_THEMES_83.length];
 try{localStorage.setItem('hush.theme.last.v87',t.id);}catch{}
 return t.id;
};
hushCurrentTheme80=function(){
 if(hushThemePref80.mode==='static')hushThemeSession80=hushThemePref80.theme;
 else if(!hushThemeSession80)hushThemeSession80=hushPickTheme80();
 return HUSH_THEMES_83.find(t=>t.id===hushThemeSession80)||HUSH_THEMES_83[0];
};
function hushApplyTheme82(){
 const theme=hushCurrentTheme80();
 document.documentElement.style.setProperty('--hush-nav-wallpaper', `url("${theme.wallpaper}")`);
 const hero=document.querySelector('.hush-v83-home');
 if(!hero)return;
 hero.dataset.activeTheme=theme.id;
 const img=hero.querySelector('.hush-theme-photo');if(img&&img.getAttribute('src')!==theme.wallpaper)img.src=theme.wallpaper;
 const live=hero.querySelector('.hush-scene-card-live');if(live&&live.getAttribute('src')!==theme.liveArt)live.src=theme.liveArt;
 const ar=hero.querySelector('.hush-scene-card-ar');if(ar&&ar.getAttribute('src')!==theme.arArt)ar.src=theme.arArt;
 const name=hero.querySelector('.hush-theme-tag');if(name)name.textContent=theme.name;
}
hushThemeSettings80=function(){
 const active=hushCurrentTheme80();
 const cards=HUSH_THEMES_83.map(t=>`<button type="button" class="hush-theme-choice ${t.id===active.id?'active':''}" data-v82-theme="${t.id}" aria-pressed="${t.id===active.id}"><img loading="lazy" src="${t.preview}" alt="${esc(t.name)}"/><span>${esc(t.name)}</span></button>`).join('');
 openModal(`<div class="sheet-head"><h2>🎨 Home screen themes</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim">20 complete wildlife landscapes, based on the majestic gallery. Select a scene to keep it fixed, or choose Dynamic to rotate each time you reopen Hush Hunt.</p>
 <div class="hush-theme-mode" role="group" aria-label="Theme mode"><button type="button" id="hush-v82-dynamic" class="secondary ${hushThemePref80.mode==='dynamic'?'active':''}" aria-pressed="${hushThemePref80.mode==='dynamic'}">🔀 Dynamic</button><button type="button" id="hush-v82-static" class="secondary ${hushThemePref80.mode==='static'?'active':''}" aria-pressed="${hushThemePref80.mode==='static'}">📌 Static</button></div>
 <p class="footnote" id="hush-v82-mode-help">${hushThemePref80.mode==='static'?'Your chosen design will stay on Home.':'Automatically rotates through the 20 designs.'}</p><div class="hush-theme-grid">${cards}</div><div class="actions"><button type="button" id="hush-v82-save" class="primary">Done</button></div>`,false,'hush-theme-sheet');
 function selectMode(mode){
  hushThemePref80.mode=mode;
  if(mode==='dynamic')hushThemeSession80=null;
  else hushThemeSession80=hushThemePref80.theme;
  hushPersist80();
  for(const m of ['dynamic','static']){
   const b=$('hush-v82-'+m);if(b){b.classList.toggle('active',mode===m);b.setAttribute('aria-pressed',String(mode===m));}
  }
  const p=$('hush-v82-mode-help');if(p)p.textContent=mode==='static'?'Selected theme applied immediately and kept on reopen.':'Rotates to the next theme when the app is reopened.';
  hushApplyTheme82();
 }
 $('hush-v82-dynamic').onclick=()=>selectMode('dynamic');
 $('hush-v82-static').onclick=()=>selectMode('static');
 document.querySelectorAll('[data-v82-theme]').forEach(btn=>btn.onclick=()=>{
  hushThemePref80.theme=btn.dataset.v82Theme;
  hushThemeSession80=hushThemePref80.theme;
  selectMode('static');
  document.querySelectorAll('[data-v82-theme]').forEach(b=>{const on=b===btn;b.classList.toggle('active',on);b.setAttribute('aria-pressed',String(on));});
 });
 $('hush-v82-save').onclick=()=>{hushPersist80();closeModal();render();};
};
renderHome=function(){
 const theme=hushCurrentTheme80(),total=allSightings().length,discovered=visibleWildlife().length,badges=medals().filter(m=>m.ok).length;
 return `<section class="hush-story-home"><div class="hush-story-hero hush-immersive-home hush-v80-home hush-v81-home hush-v83-home" data-active-theme="${theme.id}" data-hush-theme-system="v83"><img class="hush-theme-photo" src="${theme.wallpaper}" alt="" aria-hidden="true" fetchpriority="high"><div class="hush-story-topbar"><button type="button" id="hush-theme-open-home" class="hush-story-icon" aria-label="Choose a home theme">⚙️</button><span class="hush-home-eyebrow">WILDLIFE EXPLORER</span></div><div class="hush-story-brand"><span class="hush-story-paw">🐾</span><h1>Hush <em>Hunt</em></h1><p>EXPLORE · DISCOVER · LEARN</p></div><div class="hush-home-hero-spacer"></div><div class="hush-home-action-zone"><p class="hush-theme-tag">${esc(theme.name)}</p><div class="hush-story-main-actions"><button type="button" id="hush-direct-live" class="hush-story-main hush-story-main-live"><img class="hush-scene-card-art hush-scene-card-live" src="${theme.liveArt}" alt="" aria-hidden="true"><span class="emoji">📷</span><strong>Live Capture</strong><small>Spot real wildlife</small></button><button type="button" id="hush-direct-ar" class="hush-story-main hush-story-main-ar"><img class="hush-scene-card-art hush-scene-card-ar" src="${theme.arArt}" alt="" aria-hidden="true"><span class="emoji">✨</span><strong>AR Safari</strong><small>Explore virtual wildlife</small></button></div></div></div><div class="hush-story-stats"><div><strong>${discovered}</strong><span>Discoveries</span></div><div><strong>${total}</strong><span>Sightings</span></div><div><strong>${badges}</strong><span>Badges</span></div></div><p class="hush-release-caption">v${WHISKER_BUILD} · build ${WHISKER_BUILD_NUMBER}</p></section>`;
};


/* v82 must never fall back to obsolete v74 animal cutout artwork. */
hushRepairHomeScene81=function(){
 hushApplyTheme82();
 const img=document.querySelector('.hush-v83-home>.hush-theme-photo');
 if(!img)return;
 img.onerror=()=>{
  const theme=hushCurrentTheme80();
  const hero=document.querySelector('.hush-v83-home');
  if(hero)hero.classList.add('hush-theme-asset-error');
  // Keep the correctly named gallery scene even on a slow WebView asset load.
  if(!img.dataset.v82Fallback){img.dataset.v82Fallback='true';img.src=theme.preview;}
 };
 img.onload=()=>document.querySelector('.hush-v83-home')?.classList.remove('hush-theme-asset-error');
};

/* v3.10.20: Home artwork uses full-frame, non-blurred v83 wallpapers. No legacy images are referenced by the active theme registry. */


/* v3.10.21 — One phone-height Home composition; Collection begins with real photos. */
renderHome=function(){
 const theme=hushCurrentTheme80();
 document.documentElement.style.setProperty('--hush-nav-wallpaper', `url("${theme.wallpaper}")`);
 return `<section class="hush-story-home hush-home-v84 hush-home-v85 hush-home-v87"><div class="hush-story-hero hush-immersive-home hush-v84-home hush-v85-home hush-v87-home" data-active-theme="${theme.id}"><img class="hush-theme-photo" src="${theme.wallpaper}" alt="" fetchpriority="high"><div class="hush-story-topbar"><button type="button" id="hush-theme-open-home" class="hush-story-icon" aria-label="Choose home background">⚙️</button><span class="hush-home-eyebrow">WILDLIFE EXPLORER</span></div><div class="hush-story-brand"><span class="hush-story-paw">🐾</span><h1>Hush <em>Hunt</em></h1><p>EXPLORE · DISCOVER · LEARN</p></div><div class="hush-home-hero-spacer" aria-hidden="true"></div><div class="hush-home-action-zone"><p class="hush-theme-tag">${esc(theme.name)}</p><div class="hush-story-main-actions"><button type="button" id="hush-direct-live" class="hush-story-main hush-story-main-live"><img class="hush-scene-card-art" src="${theme.liveArt}" alt=""><span class="emoji">📷</span><strong>Live Capture</strong><small>Spot real wildlife</small></button><button type="button" id="hush-direct-ar" class="hush-story-main hush-story-main-ar"><img class="hush-scene-card-art" src="${theme.arArt}" alt=""><span class="emoji">✨</span><strong>AR Safari</strong><small>Explore virtual wildlife</small></button></div></div></div></section>`;
};
// Preserve wildlife bingo, cat-coat bonuses and virtual gallery below the album,
// without forcing people past those panels to reach their saved photographs.
const hushDexBefore84=renderDex;
renderDex=function(){
 const html=hushDexBefore84();
 const source=document.createElement('div');source.innerHTML=html;
 const find=selector=>source.querySelector(selector)?.outerHTML||'';
 const real=visibleWildlife(),virtual=s.cats.filter(c=>c.virtual).length;
 const cats=real.length;
 const categoryCards=HUSH_CATEGORIES.map(cat=>{
  const count=real.filter(a=>hushAnimalCategory(a)===cat.name).length;
  return `<button type="button" class="hush-collection-category ${s.filter==='Category:'+cat.name?'active':''}" data-hush-category-filter="${esc(cat.name)}"><span>${cat.icon}</span><strong>${esc(cat.name)}</strong><small>${count} discoveries</small></button>`;
 }).join('');
 // Original discovery grid stays the only source of truth for filtered photo cards.
 // The rest of the legacy sections remain in an optional collapsed challenges area.
 const extras=['.hush-challenge','.hush-bonus-section','.bingo','.virtual-gallery','.variant-album']
  .map(find).filter(Boolean).join('');
 return `<div class="hush-dex-v84"><header class="hush-dex-header"><span class="eyebrow">YOUR COLLECTION</span><h1>Your Collection 🌿</h1><p>${cats} real-world discover${cats===1?'y':'ies'} · ${virtual} virtual wildlife</p></header><section class="hush-collection-categories"><h3>Explore by animal family</h3><div class="hush-category-card-grid">${categoryCards}</div></section><section class="hush-discovery-album"><div class="hush-album-title"><h3>Your discoveries</h3><span>${cats} saved</span></div><input class="search-input" id="dex-search" aria-label="Search your wildlife collection" placeholder="Search your wildlife…"><div class="chips"><button type="button" class="chip ${s.filter==='All'?'selected':''}" data-filter="All">✦ All</button><button type="button" class="chip ${s.filter==='Favourites'?'selected':''}" data-filter="Favourites">♥ Favourites</button></div><div class="dex-sort-row"><label for="dex-sort">Sort</label><select id="dex-sort" class="select" aria-label="Sort your collection"><option value="recent">Recently discovered</option><option value="last">Last seen</option><option value="name">Name A–Z</option><option value="visits">Most sightings</option><option value="favourites">Favourites first</option></select></div><div id="dex-grid">${dexGrid()}</div></section>${extras?`<details class="hush-collection-more"><summary>More challenges & virtual wildlife <span>⌄</span></summary>${extras}</details>`:''}</div>`;
};

/* v3.10.21 — a working Android ultrawide PHOTO hand-off.
   Android WebView does not expose the OnePlus ultrawide lens as a controllable
   media stream. Use the installed native camera so its true 0.6× setting is
   available. Only actual camera captures (never gallery imports) qualify. */
let hushWideNativeToken84=null;
const hushNativePhotoBefore84=window.whiskerNativePhoto;
window.whiskerNativePhoto=function(data,requestToken){
 if(hushWideNativeToken84!==null && String(requestToken)===hushWideNativeToken84){
  hushWideNativeToken84=null;
  nativePhotoRequestToken=null;
  if(typeof data!=='string'||!data.startsWith('data:image/'))return toast('Camera returned an invalid image.');
  const picture=new Image();
  picture.onload=()=>{
   const canvas=document.createElement('canvas'),scale=Math.min(1,1200/Math.max(picture.naturalWidth,picture.naturalHeight));
   canvas.width=Math.max(1,Math.round(picture.naturalWidth*scale));canvas.height=Math.max(1,Math.round(picture.naturalHeight*scale));
   canvas.getContext('2d').drawImage(picture,0,0,canvas.width,canvas.height);
   const photo=canvas.toDataURL('image/jpeg',.88);
   s.image=photo;s.encounterLive=true;s.encounterAr=false;s.encounterCaptured=true;
   s.realLiveProof={source:'native-camera',ready:true,images:new Set([photo])};
   s.spottedSpecies='Cat';s.wildTarget='Unknown';
   // Go directly to species confirmation, just like Quick Photo. No game overlay.
   showCatForm(photo);
  };
  picture.onerror=()=>toast('Could not read the phone-camera photo.');picture.src=data;
  return;
 }
 return hushNativePhotoBefore84?.(data,requestToken);
};
const hushOriginalPhotoCancel84=window.whiskerNativePhotoCancelled;
window.whiskerNativePhotoCancelled=function(token){
 if(hushWideNativeToken84!==null&&String(token)===hushWideNativeToken84){hushWideNativeToken84=null;nativePhotoRequestToken=null;toast('Wide photo cancelled. Open Live Capture to try again.');return;}
 hushOriginalPhotoCancel84?.(token);
};
const hushOriginalPhotoError84=window.whiskerNativePhotoError;
window.whiskerNativePhotoError=function(token,message){
 if(hushWideNativeToken84!==null&&String(token)===hushWideNativeToken84){hushWideNativeToken84=null;nativePhotoRequestToken=null;toast(message||'Phone camera could not open.');return;}
 hushOriginalPhotoError84?.(token,message);
};
const hushRealLivePhotoReadyBefore84=realLivePhotoReady;
realLivePhotoReady=function(image=s.image){
 return hushRealLivePhotoReadyBefore84(image)||
  (s.realLiveProof?.source==='native-camera'&&s.realLiveProof.ready===true&&s.realLiveProof.images.has(image));
};
function hushOpenNativeWide84(){
 if(!window.whiskerNativeReady&&!hasAndroidActionBridge()){
  toast('0.6× uses the installed Android phone camera.');return;
 }
 // Distinct token means a cancelled request cannot overwrite a later live frame.
 const token=String(++nativePhotoRequestSequence);
 nativePhotoRequestToken=token;hushWideNativeToken84=token;
 stopLiveCamera();
 const stage=$('encounter-stage');
 if(stage){const status=$('encounter-status');if(status)status.textContent='Choose 0.6× on your phone camera, take your photo, then return here.';}
 location.href='whiskerhunt://capture?request='+encodeURIComponent(token);
}
hushShowPhoneWide81=function(){
 const stage=$('encounter-stage');if(!stage)return;
 stage.querySelector('#hush-wide81')?.remove();
 const panel=document.createElement('section');panel.id='hush-wide81';panel.className='hush-wide81';panel.setAttribute('role','dialog');panel.setAttribute('aria-label','Real 0.6× ultrawide capture');
 panel.innerHTML='<strong>True 0.6× wide photo</strong><p>Android WebView cannot reliably control this phone’s ultrawide lens. Open the real phone camera, select <b>0.6×</b>, and take your photo. It will return directly to Hush Hunt for species confirmation.</p><div class="hush-wide81-actions"><button type="button" class="primary" id="hush-wide81-native">📷 Open 0.6× phone camera</button><button type="button" class="secondary" id="hush-wide81-cancel">Return to 1× view</button></div>';
 stage.appendChild(panel);
 $('hush-wide81-native').onclick=()=>{panel.remove();hushOpenNativeWide84()};
 $('hush-wide81-cancel').onclick=()=>panel.remove();
};


/* v3.10.23 · build 86: true native in-app wide-photo handoff, never external picker.
 * Browser/unsupported devices do not pretend that 1× frames are 0.6×. */
let hushWideRequest86=null;
function hushReturnToLive86(message){
 hushWideRequest86=null;
 hushWideNativeToken84=null;
 nativePhotoRequestToken=null;
 if(document.querySelector('#modal-layer .live-sheet')){
   // Restart a fresh camera stream; the old getUserMedia track was stopped while
   // native Android owned the camera. Do not leave a frozen/play-icon video frame.
   startLiveEncounter();
   if(message)toast(message);
 }else if(message)toast(message);
}
window.hushNativeWideResult=function(result){
 if(!result||String(result.request)!==String(hushWideRequest86))return;
 const token=hushWideRequest86;
 if(result.status==='captured'&&typeof result.photo==='string'&&result.photo.startsWith('data:image/jpeg;base64,')){
  hushWideRequest86=null;
  // Reuse the normal identification and existing collection persistence;
  // the native photo is not a virtual Safari capture.
  window.whiskerNativePhoto(result.photo,token);
  return;
 }
 const message=result.status==='unavailable' ?
  (result.message||'The 0.6× rear lens is not exposed to Android apps on this device.') :
  result.status==='cancelled'?'Wide photo cancelled. Live Capture is ready again.':
  (result.message||'Could not use the rear ultrawide camera.');
 hushReturnToLive86(message);
};
function hushOpenNativeWide86(){
 if(!hasAndroidActionBridge()){
  toast('True in-app ultrawide capture requires the Android version of Hush Hunt.');return;
 }
 const token=String(++nativePhotoRequestSequence);
 nativePhotoRequestToken=token;
 hushWideNativeToken84=token;
 hushWideRequest86=token;
 document.querySelector('#hush-wide81')?.remove();
 // Camera ownership is handed to a Hush Hunt native Activity, not to an
 // external front camera. Native activity selects only genuine rear ultrawide.
 stopLiveCamera();
 const status=$('encounter-status');
 if(status)status.textContent='Opening Hush Hunt rear ultrawide camera…';
 location.href='whiskerhunt://wide-camera?request='+encodeURIComponent(token);
}
hushShowPhoneWide81=function(){
 const stage=$('encounter-stage');if(!stage)return;
 stage.querySelector('#hush-wide81')?.remove();
 const panel=document.createElement('section');
 panel.id='hush-wide81';panel.className='hush-wide81';
 panel.setAttribute('role','dialog');panel.setAttribute('aria-label','Rear ultrawide photo');
 panel.innerHTML='<strong>0.6× rear ultrawide</strong><p>Take a photo inside Hush Hunt using a genuine rear ultrawide camera. It is never simulated from 1×. If Android does not expose the wider lens, Live Capture will reopen at 1×.</p><div class="hush-wide81-actions"><button type="button" class="primary" id="hush-wide81-native">📷 In-app 0.6× camera</button><button type="button" class="secondary" id="hush-wide81-cancel">Keep 1× live view</button></div>';
 stage.appendChild(panel);
 $('hush-wide81-native').onclick=hushOpenNativeWide86;
 $('hush-wide81-cancel').onclick=()=>panel.remove();
};
