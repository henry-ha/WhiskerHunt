/* Whisker Hunt 2.7 — offline-first, no accounts, no tracking, no server. */
'use strict';
const WHISKER_BUILD='2.8.0', WHISKER_BUILD_NUMBER=28;
const DATABASE='whiskerhunt_local_v1', DB_VERSION=1;
const COATS=['Tabby','Ginger','Black','White','Tuxedo','Calico','Grey','Other'];
const PERSONALITIES=['Unknown','Curious','Sleepy','Playful','Shy','Friendly','Adventurous'];
const PERSONALITY_EMOJI={Unknown:'🐱',Curious:'🔎',Sleepy:'💤',Playful:'🧶',Shy:'🌙',Friendly:'💗',Adventurous:'🧭'};
const EMOJIS={Tabby:'🐯',Ginger:'🧡',Black:'🖤',White:'🤍',Tuxedo:'🎩',Calico:'🎨',Grey:'🌫️',Other:'🐱'};
const similarityCache=new Map();
let matchRequest=0;
let encounterEpoch=0;
let encounterCropEpoch=0;
let photoSelectionEpoch=0;
let nativePhotoRequestSequence=0, nativePhotoRequestToken=null;
let encounterResizeObserver=null;
let liveCamera=null;
let liveRequestEpoch=0;
let captureShots=[]; // Ephemeral review options only; never saved to CatDex or backups.
const s={cats:[],profile:{name:'Cat Explorer',xp:0,claimed:[]},screen:'home',filter:'All',search:'',dexSort:'recent',image:'',cardBase64:'',catchMode:'new',selectedId:'',revisitId:'',journalFilter:'All',journalSearch:'',busy:false,db:null,native:false,storageBlocked:false,recoveryApproved:false,encounterLive:false};
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
const allSightings=()=>s.cats.flatMap(c=>c.sightings||[]);
const level=()=>Math.floor(s.profile.xp/200)+1;
const levelTitle=()=>['Curious Kitten','Street Spotter','Cat Whisperer','Whisker Scout','Paw Legend','Alley Explorer','Cat Chronicler','Purr Master','Legendary Spotter','Whisker Guardian'][Math.min(level()-1,9)];
// Android ships a private native JSON CatDex; only obsolete service worker caches
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
window.whiskerRequestNativeSync=function(token){location.href='whiskerhunt://sync?request='+encodeURIComponent(token)+(s.recoveryApproved?'&recover=1':'')};
function nativeSync(){
 if(s.storageBlocked&&!s.recoveryApproved)return Promise.reject(new Error('Android recovery required before saving'));
 if(!s.native)return Promise.resolve();
 if(!window.whiskerNativeReady)return Promise.reject(new Error('Android storage is not ready'));
 const run=()=>new Promise((resolve,reject)=>{
  const token=String(++nativeSyncSequence);
  const timer=setTimeout(()=>{
   nativeSyncPending.delete(token);reject(new Error('Android save timed out'));
  },15000);
  nativeSyncPending.set(token,{resolve,reject,timer});
  try{window.whiskerRequestNativeSync(token)}
  catch(e){clearTimeout(timer);nativeSyncPending.delete(token);reject(e)}
 });
 const task=nativeSyncQueue.then(run,run);
 nativeSyncQueue=task.catch(()=>{});
 return task;
}
async function saveCat(c){if(s.native)return nativeSync();await transact('cats','readwrite','put',c)}
async function removeCat(c){if(s.native)return nativeSync();await transact('cats','readwrite','delete',c.id)}
async function saveProfile(){if(s.native)return nativeSync();await transact('meta','readwrite','put',{key:'profile',value:s.profile})}
async function boot(){if(window.whiskerAndroidShell){
  // Native shell must never open IndexedDB: it can contain unrelated browser data.
  s.db=null;s.native=true;
  $('view').innerHTML='<div class="feature-empty"><div class="big">🐾</div><h3>Loading your CatDex…</h3><p>Checking your private collection on this device.</p></div>';
 }else{try{s.db=await openDb();s.cats=await transact('cats','readonly','getAll');const p=await transact('meta','readonly','get','profile');if(p?.value){s.profile={...s.profile,...p.value}}}catch(e){console.error(e);toast('Local storage unavailable. Check browser privacy settings.')}render();}$('nav-catch').addEventListener('click',startCatch);document.querySelectorAll('[data-nav]').forEach(b=>b.addEventListener('click',()=>navigate(b.dataset.nav)));$('head-profile').addEventListener('click',()=>navigate('profile'));$('image-input').addEventListener('change',inputPhoto);$('library-input').addEventListener('change',inputPhoto);$('backup-input').addEventListener('change',importBackup);if(window.whiskerAndroidShell)retireAndroidShellWorker();else if('serviceWorker'in navigator&&location.protocol.startsWith('http'))navigator.serviceWorker.register('sw.js').catch(()=>{});window.whiskerBootComplete=true;
 if(window.whiskerAndroidShell){
  const requestReady=()=>{if(window.whiskerRequestNativeReady)window.whiskerRequestNativeReady();else location.href='whiskerhunt://ready'};
  requestReady();
  setTimeout(()=>{if(!window.whiskerNativeReady&&!s.storageBlocked){$('view').innerHTML='<div class="feature-empty"><div class="big">⚠️</div><h3>Collection did not load</h3><p>Your data has not been changed. Please retry.</p><button class="primary" id="retry-native-load">Retry loading</button></div>';$('retry-native-load').onclick=requestReady}},12000);
 }else if(window.whiskerPendingNativeData!==undefined)window.whiskerUseNativeStorage(window.whiskerPendingNativeData);
}
function navigate(page){closeModal();s.screen=page;window.scrollTo(0,0);document.querySelectorAll('[data-nav]').forEach(b=>b.classList.toggle('current',b.dataset.nav===page));render()}
function render(){const views={home:renderHome,dex:renderDex,explore:renderExplore,quests:renderQuests,profile:renderProfile,journal:renderJournal};$('view').innerHTML=(views[s.screen]||renderHome)();wireScreen()}
function wireScreen(){document.querySelectorAll('[data-go]').forEach(b=>b.addEventListener('click',()=>navigate(b.dataset.go)));document.querySelectorAll('[data-cat]').forEach(b=>b.addEventListener('click',()=>openDetail(b.dataset.cat)));document.querySelectorAll('[data-claim]').forEach(b=>b.addEventListener('click',()=>claimQuest(b.dataset.claim)));document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{s.filter=b.dataset.filter;render()}));if($('dex-search')){$('dex-search').value=s.search;$('dex-search').addEventListener('input',e=>{s.search=e.target.value;updateDexGrid()})}if($('dex-sort')){$('dex-sort').value=s.dexSort;$('dex-sort').addEventListener('change',e=>{s.dexSort=e.target.value;updateDexGrid()})}document.querySelectorAll('[data-action]').forEach(b=>b.addEventListener('click',()=>action(b.dataset.action)));document.querySelectorAll('[data-journal-catch]').forEach(b=>b.addEventListener('click',startCatch));document.querySelectorAll('[data-journal-filter]').forEach(b=>b.addEventListener('click',()=>{s.journalFilter=b.dataset.journalFilter;render()}));if($('journal-search')){$('journal-search').value=s.journalSearch;$('journal-search').addEventListener('input',e=>{s.journalSearch=e.target.value;updateJournalCards()})}}
function section(label,link='',go=''){return `<div class="section-title"><h2>${label}</h2>${link?`<button class="text-btn" data-go="${go}">${link} →</button>`:''}</div>`}
function renderHome(){const total=allSightings().length;const daily=dailyQuests()[0];const latest=[...s.cats].sort((a,b)=>b.createdAt.localeCompare(a.createdAt)).slice(0,6);return `<div class="intro"><div class="eyebrow">YOUR CAT-CHASING ADVENTURE</div><h1>Hello, explorer <span>👋</span></h1><p class="dim no-margin" style="font-size:13px">Every whisker has a story. Find yours.</p></div><section class="hero"><span class="pill lime">✦ THE WORLD IS YOUR CATDEX</span><div class="hero-title">See a cat?<br>Catch the moment.</div><p class="hero-desc">Meet real cats, level up and build your own legendary collection.</p><button id="hero-catch" class="primary">📸 Catch a cat →</button><span class="hero-cat" aria-hidden="true">🐈</span></section><div class="stats"><div class="stat"><strong>${s.cats.length}</strong><span>Unique cats</span></div><div class="stat"><strong>${total}</strong><span>Sightings</span></div><div class="stat"><strong>${streak()}</strong><span>Day streak</span></div></div><div class="level-card"><div class="level-top"><span class="level-num">✦ LEVEL ${level()}</span><span class="level-name">${levelTitle()}</span></div><div class="progress"><b style="width:${s.profile.xp%200/2}%"></b></div><p class="progress-copy">${s.profile.xp%200} / 200 XP to your next level · ${s.profile.xp} total XP</p></div>${section('Today\'s challenge','All quests','quests')}<div class="quest-card"><div class="quest-top"><div class="quest-icon">${daily.icon}</div><div class="quest-details"><h3>${daily.title}</h3><p>${daily.description}</p></div><div class="quest-reward">+${daily.xp} XP</div></div><div class="quest-bar"><span style="width:${Math.min(100,100*daily.progress/daily.target)}%"></span></div><div class="flex between" style="margin-top:9px"><span class="count-label">${Math.min(daily.progress,daily.target)} / ${daily.target}</span>${questAction(daily)}</div></div>${section('Your cat collection','View CatDex','dex')}${latest.length?`<div class="cat-strip">${latest.map(c=>`<button class="mini-cat" data-cat="${esc(c.id)}"><img src="${c.photo}" alt="${esc(c.name)}"><strong>${esc(c.name)}</strong><small>${esc(c.coat)} · ${catches(c)} sighting${catches(c)!==1?'s':''}</small></button>`).join('')}</div>`:`<div class="feature-empty"><div class="big">🐈‍⬛</div><h3>Your adventure starts here</h3><p>Found a friendly-looking feline? Snap your first cat and bring your CatDex to life.</p><button id="empty-catch" class="secondary">Catch your first cat</button></div>`}`}
function renderDex(){const coats=new Set(s.cats.map(c=>c.coat));return `<div class="page-head"><div class="eyebrow">YOUR COLLECTION</div><h1>The CatDex 🐈</h1><p class="subtitle">${s.cats.length} unique cats discovered · ${allSightings().length} moments collected</p></div><div class="bingo"><div class="flex between"><div><div class="eyebrow">COAT COLLECTION CHALLENGE</div><h3>Cat Bingo</h3></div><span class="bingo-progress">${coats.size} / ${COATS.length}</span></div><div class="bingo-grid">${COATS.map(c=>`<button class="bingo-tile ${coats.has(c)?'found':''}" data-filter="${c}" aria-label="Filter ${c} cats"><span>${EMOJIS[c]}</span><small>${c}</small>${coats.has(c)?'<b>✓</b>':'<b>?</b>'}</button>`).join('')}</div><p class="bingo-sub">${coats.size===COATS.length?'🎉 Your coat collection is complete!':'Meet cats with different coats to fill your album. Tap a tile to filter.'}</p></div><input class="search-input" id="dex-search" aria-label="Search cats" placeholder="⌕   Search your feline friends..."><div class="chips">${['All','Favourites',...COATS].map(c=>`<button class="chip ${s.filter===c?'selected':''}" data-filter="${c}">${c==='All'?'✦ ':c==='Favourites'?'♥ ':''}${c}</button>`).join('')}</div><div class="dex-sort-row"><label for="dex-sort">Sort your collection</label><select id="dex-sort" class="select" aria-label="Sort cats"><option value="recent">Recently discovered</option><option value="last">Last seen</option><option value="name">Name A–Z</option><option value="visits">Most sightings</option><option value="favourites">Favourites first</option></select></div><div id="dex-grid">${dexGrid()}</div>`}
function dexGrid(){const q=s.search.toLowerCase();const cs=s.cats.filter(c=>(s.filter==='All'||(s.filter==='Favourites'&&c.fav)||c.coat===s.filter)&&(c.name.toLowerCase().includes(q)||c.coat.toLowerCase().includes(q))).sort((a,b)=>{const last=c=>Math.max(0,...(c.sightings||[]).map(v=>Date.parse(v.at)||0));switch(s.dexSort){case 'name':return a.name.localeCompare(b.name);case 'last':return last(b)-last(a);case 'visits':return catches(b)-catches(a)||a.name.localeCompare(b.name);case 'favourites':return Number(b.fav)-Number(a.fav)||last(b)-last(a);default:return b.createdAt.localeCompare(a.createdAt)}});return cs.length?`<div class="cat-grid">${cs.map(c=>`<button class="cat-tile" data-cat="${esc(c.id)}"><img class="cat-img" src="${c.photo}" alt="${esc(c.name)}"><div class="cat-info"><strong>${esc(c.name)}</strong><small>${esc(c.coat)} · ${catches(c)} sightings${c.personality&&c.personality!=='Unknown'?' · '+esc(c.personality):''}</small><div class="tagline"><span class="tag">${rank(c)}</span><span class="badge-heart">${c.fav?'♥':'♡'}</span></div></div></button>`).join('')}</div>`:`<div class="feature-empty empty-dex"><div class="big">🐱</div><h3>No cats found (yet!)</h3><p>${s.cats.length?'Try another filter or search.':'Every great collection begins with one curious cat.'}</p><button class="primary" id="dex-catch">📸 Catch a cat</button></div>`}
function updateDexGrid(){const node=$('dex-grid');if(node){node.innerHTML=dexGrid();node.querySelectorAll('[data-cat]').forEach(el=>el.addEventListener('click',()=>openDetail(el.dataset.cat)));const b=$('dex-catch');if(b)b.addEventListener('click',startCatch)}}
function rank(cat){const n=catches(cat);return n>=5?'👑 Local legend':n>=3?'★ Old friend':'✦ New friend'}
function streak(){const days=[...new Set(allSightings().map(x=>dateKey(x.at)))].sort().reverse();if(!days.length)return 0;const start=new Date();if(!days.includes(dateKey(start))){start.setDate(start.getDate()-1);if(!days.includes(dateKey(start)))return 0}let count=0;while(days.includes(dateKey(start))){count++;start.setDate(start.getDate()-1)}return count}
function weekKey(){const d=new Date();d.setHours(12,0,0,0);d.setDate(d.getDate()-((d.getDay()+6)%7));return dateKey(d)}
function weeklyQuests(){const entries=allSightings().filter(v=>dateKey(v.at)>=weekKey());const newCats=s.cats.filter(c=>dateKey(c.createdAt)>=weekKey());const repeatIds=new Set(s.cats.filter(c=>c.sightings.some((v,i)=>i>0&&dateKey(v.at)>=weekKey())).map(c=>c.id));return [{id:'weekly-new',weekly:true,icon:'🧭',title:'Neighbourhood explorer',description:'Discover 3 different cats this week',progress:newCats.length,target:3,xp:200},{id:'weekly-friends',weekly:true,icon:'💜',title:'Familiar faces',description:'Log a repeat sighting for 2 different cats',progress:repeatIds.size,target:2,xp:150},{id:'weekly-days',weekly:true,icon:'📆',title:'Adventure days',description:'Spot cats on 3 different days this week',progress:new Set(entries.map(v=>dateKey(v.at))).size,target:3,xp:150}]}
function questMarker(q){return (q.weekly?weekKey():today())+':'+q.id}
function renderQuestCard(q){return `<div class="quest-card ${s.profile.claimed.includes(questMarker(q))?'complete':''}"><div class="quest-top"><div class="quest-icon">${q.icon}</div><div class="quest-details"><h3>${q.title}</h3><p>${q.description}</p></div><div class="quest-reward">+${q.xp} XP</div></div><div class="quest-bar"><span style="width:${Math.min(100,100*q.progress/q.target)}%"></span></div><div class="flex between" style="margin-top:9px"><span class="count-label">${Math.min(q.progress,q.target)} / ${q.target}</span>${questAction(q)}</div></div>`}
function dailyQuests(){const todaySightings=allSightings().filter(a=>dateKey(a.at)===today());const todayNew=s.cats.filter(c=>dateKey(c.createdAt)===today());const coats=new Set(todayNew.map(c=>c.coat));return [{id:'first',icon:'📷',title:'First whisker of the day',description:'Record a cat sighting today',progress:todaySightings.length,target:1,xp:35},{id:'double',icon:'🐾',title:'Double pawprints',description:'Record two cat encounters today',progress:todaySightings.length,target:2,xp:60},{id:'discover',icon:'✨',title:'New face in town',description:'Meet one new cat today',progress:todayNew.length,target:1,xp:75},{id:'variety',icon:'🌈',title:'Coat collector',description:'Meet two different coat types today',progress:coats.size,target:2,xp:100}]}
function questAction(q){if(s.profile.claimed.includes(questMarker(q)))return `<span class="complete-word">✓ CLAIMED</span>`;if(q.progress>=q.target)return `<button class="text-btn" data-claim="${q.id}">Claim reward ✦</button>`;return `<span class="count-label">In progress</span>`}
function medals(){const cs=s.cats;const coats=new Set(cs.map(c=>c.coat));return [{icon:'🥇',name:'First Pawprint',desc:'Find your first cat',ok:cs.length>=1},{icon:'🐾',name:'Whisker Whisperer',desc:'Find 5 different cats',ok:cs.length>=5},{icon:'🌈',name:'Colour Collector',desc:'Discover 4 coat types',ok:coats.size>=4},{icon:'⭐',name:'Old Friends',desc:'Spot the same cat 3 times',ok:cs.some(c=>catches(c)>=3)},{icon:'👑',name:'Neighbourhood Legend',desc:'Spot one cat 5 times',ok:cs.some(c=>catches(c)>=5)},{icon:'🔥',name:'Dedicated Explorer',desc:'Reach a 3-day streak',ok:streak()>=3}]}
function renderQuests(){const qs=dailyQuests();return `<div class="page-head"><div class="eyebrow">DAILY & WEEKLY ADVENTURES</div><h1>Quests & rewards ✨</h1><p class="subtitle">Earn XP by exploring naturally. No need to disturb cats or visit private property.</p></div><div class="soft-card"><div class="flex between"><div><div class="eyebrow">TOTAL EXPERIENCE</div><h2 style="font-size:29px;margin:6px 0 0">${s.profile.xp} <small style="color:#c7abec;font-size:13px">XP</small></h2></div><div class="icon-round">🏆</div></div></div>${section('Daily quests')}<p class="quest-hint">Reset daily at local midnight.</p><div class="quest-grid">${qs.map(renderQuestCard).join('')}</div>${section('Weekly adventures')}<p class="quest-hint">Reset every Monday. Previous rewards remain yours.</p><div class="quest-grid">${weeklyQuests().map(renderQuestCard).join('')}</div>${section('Your badges')}<div class="medal-grid">${medals().map(m=>`<div class="medal ${m.ok?'unlocked':''}"><span>${m.icon}</span><strong>${m.name}</strong><small>${m.ok?'✓ Unlocked':m.desc}</small></div>`).join('')}</div>`}
function renderExplore(){const geo=s.cats.flatMap(c=>(c.sightings||[]).filter(x=>x.lat!=null&&x.lng!=null).map(x=>({...x,name:c.name,photo:c.photo,id:c.id})));let pins='';if(geo.length){const minX=Math.min(...geo.map(x=>x.lng)),maxX=Math.max(...geo.map(x=>x.lng)),minY=Math.min(...geo.map(x=>x.lat)),maxY=Math.max(...geo.map(x=>x.lat));pins=geo.map(g=>{const x=maxX===minX?50:25+50*((g.lng-minX)/(maxX-minX)),y=maxY===minY?51:28+47*(1-(g.lat-minY)/(maxY-minY));return `<button class="map-pin" style="left:${x}%;top:${y}%" title="${esc(g.name)}" data-cat="${esc(g.id)}"><span>🐾</span></button>`}).join('')}return `<div class="page-head"><div class="eyebrow">YOUR PRIVATE TRAIL</div><h1>Cat map 🗺️</h1><p class="subtitle">Remember the places you met your feline friends. Locations never leave this device.</p></div><div class="map-board">${pins||`<div style="position:absolute;top:42%;width:100%;text-align:center;z-index:1;font-size:48px">🐾<p style="color:#c4c6db;font-size:12px;margin-top:3px">No location pins yet</p></div>`}</div><div class="map-foot"><span>🔒</span><div>This is a <strong>private coordinate plot</strong>, not a street map. Pins are saved only if you opt in when catching a cat. Nearby pins are separated slightly for visibility.</div></div>${section(`Saved locations (${geo.length})`)}${geo.length?geo.slice().reverse().slice(0,20).map(g=>`<div class="map-entry"><img src="${g.photo}" alt=""><div><strong>${esc(g.name)}</strong><small>${dateDisplay(g.at)} · Private location</small></div><button class="text-btn" data-action="osm:${g.lat},${g.lng}">View map ↗</button></div>`).join(''):`<div class="feature-empty"><div class="big">📍</div><h3>Make memories, not public pins</h3><p>When you save a sighting, you can optionally add its location. Never follow cats onto private property.</p></div>`}<div class="info-note">Opening OpenStreetMap shares the selected coordinates with that external site. Your pins are not uploaded by Whisker Hunt.</div>`}
function journalEntries(){return s.cats.flatMap(cat=>(cat.sightings||[]).map((entry,index)=>({cat,entry,isFirst:index===0}))).filter(x=>x.entry&&typeof x.entry.at==='string'&&Number.isFinite(Date.parse(x.entry.at))).sort((a,b)=>Date.parse(b.entry.at)-Date.parse(a.entry.at))}
function journalCards(){const query=s.journalSearch.trim().toLowerCase();const entries=journalEntries().filter(x=>(s.journalFilter==='All'||(s.journalFilter==='New cats'&&x.isFirst)||(s.journalFilter==='Reunions'&&!x.isFirst))&&(!query||[x.cat.name,x.cat.coat,x.entry.note||''].some(v=>String(v).toLowerCase().includes(query))));if(!entries.length)return `<div class="feature-empty"><div class="big">📖</div><h3>No matching memories</h3><p>Try another filter, or capture a cat to start your journal.</p><button class="secondary" data-journal-catch>📸 Catch a cat</button></div>`;let lastDay='';return entries.slice(0,100).map(({cat,entry,isFirst})=>{const day=dateKey(entry.at);const heading=day!==lastDay?`<h3 class="journal-day">${esc(dateDisplay(entry.at))}</h3>`:'';lastDay=day;return `${heading}<button class="journal-card" data-cat="${esc(cat.id)}"><img src="${entry.photo||cat.photo}" alt=""><span class="journal-card-body"><strong>${esc(cat.name)}</strong><small>${isFirst?'✨ First discovery':'🐾 Reunion'} · ${esc(cat.coat)}</small>${entry.note?`<span class="journal-note">${esc(entry.note)}</span>`:''}</span><span class="journal-arrow">›</span></button>`}).join('')+(entries.length>100?'<p class="footnote">Showing your 100 most recent matching sightings.</p>':'')}
function updateJournalCards(){const target=$('journal-results');if(!target)return;target.innerHTML=journalCards();target.querySelectorAll('[data-cat]').forEach(b=>b.addEventListener('click',()=>openDetail(b.dataset.cat)));const catchButton=target.querySelector('[data-journal-catch]');if(catchButton)catchButton.addEventListener('click',startCatch)}
function renderJournal(){const entries=journalEntries();const uniqueDays=new Set(entries.map(x=>dateKey(x.entry.at))).size;return `<div class="page-head"><div class="eyebrow">YOUR REAL-WORLD CAT ADVENTURES</div><h1>Sighting journal 📖</h1><p class="subtitle">${entries.length} encounters across ${uniqueDays} day${uniqueDays===1?'':'s'}. Your photos and memories stay private.</p></div><button class="text-btn journal-back" data-go="profile">← Back to profile</button><input class="search-input" id="journal-search" aria-label="Search sightings" placeholder="⌕   Search cats and memories..."><div class="chips">${['All','New cats','Reunions'].map(v=>`<button class="chip ${s.journalFilter===v?'selected':''}" data-journal-filter="${v}">${v}</button>`).join('')}</div><div id="journal-results">${journalCards()}</div>`}
function collectionInsights(){
 const entries=journalEntries(),coats=new Set(s.cats.map(c=>c.coat));
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
function openModal(content,keepLive=false){if(!keepLive)stopLiveCamera();encounterResizeObserver?.disconnect();encounterResizeObserver=null;const layer=$('modal-layer');layer.classList.remove('hidden');layer.setAttribute('aria-hidden','false');layer.innerHTML=`<div class="sheet" role="dialog" aria-modal="true"><div class="sheet-handle"></div><div class="whisker-build-stamp">Whisker Hunt v${WHISKER_BUILD} · build ${WHISKER_BUILD_NUMBER}</div>${content}</div>`;layer.onclick=modalBackdrop;const b=layer.querySelector('[data-close]');if(b)b.addEventListener('click',closeModal)}
function modalBackdrop(e){if(e.target.id==='modal-layer')closeModal()}
function closeModal(){captureShots=[];nativePhotoRequestToken=null;liveRequestEpoch++;stopLiveCamera();encounterEpoch++;encounterCropEpoch++;photoSelectionEpoch++;encounterResizeObserver?.disconnect();encounterResizeObserver=null;const l=$('modal-layer');l.classList.add('hidden');l.setAttribute('aria-hidden','true');l.innerHTML=''}
function startCatch(catId=null){captureShots=[];nativePhotoRequestToken=null;photoSelectionEpoch++;if(s.busy)return toast('Please wait for the current save to finish.');if(s.storageBlocked)return toast('Restore your CatDex backup before adding cats.');s.image='';s.encounterLive=false;s.revisitId=typeof catId==='string'&&s.cats.some(c=>c.id===catId)?catId:'';s.catchMode=s.revisitId?'repeat':'new';s.selectedId='';s.captureSummary=null;openModal(`<div class="sheet-head"><h2>Catch a cat! 📸</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim" style="font-size:13px">Start with a respectful photo, then play the capture encounter with a Whisker Pod or the Dangle Lure.</p><div class="capture-choice"><button id="live-photo" class="choice"><span>🎥</span><strong>Live encounter</strong><small>Drag tools over the live camera · beta</small></button><button id="take-photo" class="choice"><span>📸</span><strong>Take a photo</strong><small>Reliable camera fallback</small></button><button id="pick-photo" class="choice"><span>🖼️</span><strong>Choose a photo</strong><small>From your gallery</small></button></div><p class="footnote center">Live mode keeps only recent still frames in memory; it does not record video. Real cats only, please.</p>`);$('live-photo').onclick=startLiveEncounter;$('take-photo').onclick=()=>requestEncounterPhoto(true);$('pick-photo').onclick=()=>requestEncounterPhoto(false)}
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
  beginEncounter(image);
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
   beginEncounter(canvas.toDataURL('image/jpeg',.84));
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
function encounterToolLabel(kind){return kind==='lure'?'Dangle Lure':'Whisker Pod'}
const LIVE_FRAME_MAX=4,LIVE_SAMPLE_INTERVAL=900,LIVE_SAMPLE_SIZE=520,LIVE_CAPTURE_SIZE=720;
// Live camera uses the standard MediaStream API when available. No video is
// recorded or stored: up to four recent JPEG stills stay in memory only.
// The Android WebView may deny camera access; the native photo picker remains
// available as an explicit fallback without changing any saved CatDex data.
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
 canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);
 return canvas.toDataURL('image/jpeg',quality);
}
async function sampleLiveFrame(session,options={}){
 const force=Boolean(options.force),maxSize=options.maxSize||LIVE_SAMPLE_SIZE,quality=options.quality??.68;
 if(!session?.active||session.sampling||session.video.readyState<2)return;
 if(!force&&(session.dragging||document.visibilityState==='hidden'))return;
 session.sampling=true;
 try{
  const image=frameFromVideo(session.video,maxSize,quality);
  if(!image||!session.active||session!==liveCamera)return;
  const now=Date.now();session.frames.push({image,quality:null,at:now});
  session.frames=session.frames.filter(frame=>now-frame.at<=3000).slice(-LIVE_FRAME_MAX);
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
// Keeping the crop in memory avoids changing the existing CatDex photo schema.
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
 const candidates=frames.slice(-8);
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
// Keep the choice private and ephemeral. Only the confirmed still enters CatDex.
function displayCaptureShotChoices(frames){
 const tray=$('encounter-shots');
 captureShots=frames.slice(0,3).filter(f=>typeof f?.image==='string'&&f.image.startsWith('data:image/'));
 if(!tray||captureShots.length<2){if(tray)tray.classList.add('hidden');return;}
 tray.classList.remove('hidden');
 tray.innerHTML=`<div class="shots-title"><strong>Choose your favourite shot</strong><small>Suggested first · tap another to compare</small></div><div class="shots-row">${captureShots.map((f,i)=>`<button type="button" class="shot-option ${i===0?'selected':''}" data-shot="${i}" aria-pressed="${i===0}" aria-label="Choose ${i===0?'suggested':'alternate'} photo ${i+1}"><img src="${f.image}" alt="Shot ${i+1}"><span>${i===0?'✦ Best':`Shot ${i+1}`}</span></button>`).join('')}</div>`;
 tray.querySelectorAll('[data-shot]').forEach(button=>button.onclick=()=>selectCaptureShot(Number(button.dataset.shot)));
}
function selectCaptureShot(index){
 const choice=captureShots[index],tray=$('encounter-shots');
 if(!choice||!tray||!tray.isConnected||s.storageBlocked)return;
 s.image=choice.image;
 if(s.captureSummary){s.captureSummary.quality=choice.quality||s.captureSummary.quality;s.captureSummary.subjectQuality=choice.subjectQuality||null;}
 const photo=$('encounter-photo');if(photo)photo.src=choice.image;
 const quality=$('encounter-quality');if(quality)quality.innerHTML=`Selected shot ${index+1} of ${captureShots.length} · Cat area: <strong>${esc(choice.subjectQuality?.label||'Not rated')}</strong> · Photo: <strong>${esc(choice.quality?.label||'Not rated')}</strong><small>Tap another thumbnail if you prefer it.</small>`;
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
 openModal(`<div class="sheet-head"><h2>Starting live camera…</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim">Requesting camera access. No video is saved or uploaded.</p><div class="live-loading" aria-live="polite">🎥 Preparing preview…</div><div class="actions"><button id="live-fallback" class="secondary">Use normal camera instead</button></div>`);
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
  openModal(`<div class="sheet-head"><h2>Live camera unavailable</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim">${esc(error?.message||'Your camera could not be opened.')} Your CatDex is safe. You can still take a normal photo or choose one from your gallery.</p><div class="actions"><button id="live-normal-camera" class="primary">📸 Take a photo</button><button id="live-normal-gallery" class="secondary">🖼️ Gallery</button></div>`);
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
 // Always include a sharper release-time still. Earlier preview frames stay
 // small for responsiveness; the final frame is captured at higher quality.
 const still=frameFromVideo(session.video,LIVE_CAPTURE_SIZE,.84);
 if(still)session.frames.push({image:still,quality:null,at:Date.now()});
 session.frames=session.frames.slice(-LIVE_FRAME_MAX);
 const frames=session.frames.slice();
 if(!frames.length)return;
 const stage=$('encounter-stage'),focus={x:s.encounterFocus?.x??.5,y:s.encounterFocus?.y??.4};
 const qualityLabel=$('encounter-quality');
 if(qualityLabel)qualityLabel.textContent='Choosing your clearest cat photo…';
 const ranked=await rankLiveFramesAtFocus(frames,focus);
 const selected=ranked[0]||null;
 // Retake, modal close or a backgrounded app must never apply a stale result.
 if(!session.active||session!==liveCamera||!stage?.isConnected||stage!==$('encounter-stage'))return;
 if(selected){
  s.image=selected.image;
  if(s.captureSummary){s.captureSummary.quality=selected.quality;s.captureSummary.subjectQuality=selected.subjectQuality||null}
  const photo=$('encounter-photo');if(photo)photo.src=selected.image;
  if(qualityLabel)qualityLabel.innerHTML=`Best of ${frames.length} recent frames · Cat target: <strong>${esc(selected.subjectQuality?.label||'Not assessed')}</strong> · Full photo: ${esc(selected.quality?.label||'Not assessed')}. <small>Offline focus-area estimate; no automatic cat recognition.</small>`;
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
 if(announce&&$('encounter-status'))$('encounter-status').textContent='Target moved. Drag the Whisker Pod onto the cat, or try the Dangle Lure first.';
}
function showEncounter(image,quality,options={}){
 const liveMode=Boolean(options.live||s.encounterLive);
 s.encounterLive=liveMode;
 s.encounterFocus={x:.5,y:.40};
 s.captureSummary={quality,throwRating:null};
 openModal(`<div class="sheet-head"><h2>${liveMode?'Live encounter 🎥':'Encounter! 🐾'}</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="encounter-quick-help">① Tap the cat · ② Drag the paw · ③ Catch!</p><details class="encounter-help"><summary>How do the tools work?</summary><p>Tap the cat to place your target. Drag the Whisker Paw onto the target to catch it, or use the Dangle Lure first to make catching easier. Stay at a safe distance from real cats.</p></details><div id="encounter-aim-guide" class="encounter-aim-guide hidden" aria-hidden="true"></div><div id="encounter-stage" class="encounter-stage"><img id="encounter-photo" class="encounter-backdrop" src="${image}" alt="Your selected cat photo"><div class="encounter-vignette"></div><div id="encounter-cat" class="encounter-cat"><div class="encounter-cat-ring"></div><img id="encounter-cat-crop" src="${image}" alt="Selected cat photo crop"><span>Your cat target</span></div><div class="encounter-capture-tag">Capture preview</div><div class="encounter-tool-dock" aria-label="Capture tools"><button type="button" id="tool-ball" class="dock-tool selected" aria-pressed="true" title="Whisker Pod"><span>🐾</span><small>Pod</small></button><button type="button" id="tool-lure" class="dock-tool" aria-pressed="false" title="Dangle Lure"><span>🪶</span><small>Lure</small></button><div id="throw-item" class="throw-item throw-ball" role="button" aria-label="Drag ${encounterToolLabel('ball')} to the cat" tabindex="0"><svg class="whisker-paw-svg" viewBox="0 0 100 110" aria-hidden="true" focusable="false"><defs><linearGradient id="whisker-paw-shine" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffe5f3"/><stop offset=".4" stop-color="#fb80b7"/><stop offset="1" stop-color="#8553d8"/></linearGradient></defs><g class="paw-digits"><ellipse cx="19" cy="34" rx="11" ry="15" transform="rotate(-23 19 34)"/><ellipse cx="40" cy="20" rx="11" ry="16" transform="rotate(-9 40 20)"/><ellipse cx="62" cy="19" rx="11" ry="16" transform="rotate(9 62 19)"/><ellipse cx="82" cy="32" rx="10" ry="15" transform="rotate(24 82 32)"/></g><path class="paw-center" d="M51 47 C65 45 71 55 80 65 C90 78 84 94 71 98 C62 101 57 95 51 95 C43 95 37 102 27 98 C12 95 10 79 20 66 C29 53 35 46 51 47Z"/><path class="paw-detail" d="M33 77 Q42 69 50 75 Q58 69 68 77"/></svg><span class="throw-stick">🎣</span><span class="throw-lure-body">🧶</span><span class="drag-prompt">DRAG</span></div></div><div id="encounter-orb" class="encounter-orb hidden"><svg class="whisker-paw-svg capture-paw" viewBox="0 0 100 110" aria-hidden="true" focusable="false"><defs><linearGradient id="whisker-paw-shine-captured" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffe5f3"/><stop offset=".4" stop-color="#fb80b7"/><stop offset="1" stop-color="#8553d8"/></linearGradient></defs><g class="paw-digits"><ellipse cx="19" cy="34" rx="11" ry="15" transform="rotate(-23 19 34)"/><ellipse cx="40" cy="20" rx="11" ry="16" transform="rotate(-9 40 20)"/><ellipse cx="62" cy="19" rx="11" ry="16" transform="rotate(9 62 19)"/><ellipse cx="82" cy="32" rx="10" ry="15" transform="rotate(24 82 32)"/></g><path class="paw-center" d="M51 47 C65 45 71 55 80 65 C90 78 84 94 71 98 C62 101 57 95 51 95 C43 95 37 102 27 98 C12 95 10 79 20 66 C29 53 35 46 51 47Z"/><path class="paw-detail" d="M33 77 Q42 69 50 75 Q58 69 68 77"/></svg></div><div id="encounter-status" class="encounter-status" role="status" aria-live="polite">Tap the cat to move the target. Then drag an item from the tool dock on the right.</div><div id="encounter-meow" class="encounter-meow hidden" aria-hidden="true">Meow!</div></div><div id="encounter-quality" class="encounter-quality">${liveMode?'🎥 Live preview · <span id="live-frame-count">1 recent frame</span> · Whisker Hunt keeps a few recent stills and picks the clearest one near your target when you capture.':'Photo clarity estimate: <strong>'+esc(quality.label)+'</strong> · '+esc(quality.note)} <small>${liveMode?'No video recording or upload.':'Single-image heuristic; no cat recognition.'}</small></div><div id="encounter-shots" class="encounter-shots hidden" aria-label="Choose best frame"></div><div class="encounter-photo-actions"><button type="button" id="encounter-retake" class="secondary">${liveMode?'🎥 Retake live capture':'📸 Retake photo'}</button><button type="button" id="encounter-replace" class="secondary">🖼️ Choose another</button></div><div class="encounter-launch"><div class="encounter-instructions">Drag the paw from the right. A green ring means your throw is on target.</div></div><div class="actions"><button id="encounter-skip" class="secondary">Save photo without game</button><button id="encounter-continue" class="primary hidden">Continue to CatDex →</button></div><p class="footnote">${liveMode?'Live camera is local to your device; only the selected still is saved. No cat recognition.':'Your target is a user-selected crop of your photo, not a live AI-generated cat.'} Stay a safe distance from real cats.</p>`,liveMode);
 if(liveMode&&liveCamera?.active){
  const stage=$('encounter-stage'),video=liveCamera.video;
  video.id='encounter-video';video.className='encounter-backdrop encounter-live-video';
  stage.prepend(video);stage.classList.add('live-encounter');
  const tag=stage.querySelector('.encounter-capture-tag');if(tag)tag.textContent='● LIVE · private';
  const crop=$('encounter-cat-crop');if(crop)crop.style.display='none';
  const status=$('encounter-status');if(status)status.textContent='Tap the cat to place the target, then drag a tool from the right.';
  scheduleLiveSampling(liveCamera);
 }
 const selectTool=kind=>{
  if(s.encounterCaptured)return;
  s.encounterTool=kind;
  $('tool-ball').classList.toggle('selected',kind==='ball');$('tool-lure').classList.toggle('selected',kind==='lure');
  $('tool-ball').setAttribute('aria-pressed',String(kind==='ball'));$('tool-lure').setAttribute('aria-pressed',String(kind==='lure'));
  const item=$('throw-item');item.classList.toggle('throw-ball',kind==='ball');item.classList.toggle('throw-lure',kind==='lure');
  item.setAttribute('aria-label','Drag '+encounterToolLabel(kind)+' to the cat');
  $('encounter-status').textContent=kind==='lure'?'Aim the Dangle Lure at the cat to enlarge the target.':'Drag the Whisker Pod onto the cat for a capture!';
 };
 $('tool-ball').onclick=()=>selectTool('ball');$('tool-lure').onclick=()=>selectTool('lure');
 $('encounter-skip').onclick=async()=>{if(liveCamera)await freezeLiveEncounter();s.captureSummary=null;showCatForm(s.image)};
 $('encounter-continue').onclick=()=>showCatForm(s.image);
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
  if(s.encounterLured){$('encounter-status').textContent='The cat is focused on the lure. Try your Whisker Pod.';return}
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
 setTimeout(()=>{if(stage?.isConnected&&status)status.textContent='Paw grab…';if(stage?.isConnected)orb?.classList.add('grab-1')},260);
 setTimeout(()=>{if(stage?.isConnected&&status)status.textContent='Holding on…';if(stage?.isConnected){orb?.classList.remove('grab-1');orb?.classList.add('grab-2');if(meow){meow.classList.remove('hidden');meow.classList.add('float')}}},650);
 setTimeout(()=>{if(!stage?.isConnected)return;orb?.classList.remove('grab-2');cat?.classList.remove('grabbed');if(meow)meow.classList.remove('float');if(status)status.textContent=`You captured this cat! ${s.captureSummary.throwRating}`;$('encounter-continue')?.classList.remove('hidden')},1180);
}
function showCatForm(image){s.image=image;const request=++matchRequest;openModal(`<div class="sheet-head"><h2>Nice spotting! 🐾</h2><button class="close-btn" data-close aria-label="Close">×</button></div><img class="photo-preview" src="${image}" alt="Your chosen cat photo">${s.captureSummary?`<div class="info-note"><strong>Encounter complete.</strong> Captured with ${esc(s.encounterLured?'the Dangle Lure + Whisker Pod combo':'a Whisker Pod')}. ${esc(s.captureSummary.throwRating||'Nice!')} Photo clarity: <strong>${esc(s.captureSummary.quality?.label||'Unrated')}</strong>.</div>`:''}<p class="dim" style="font-size:12px;margin-bottom:11px">Is this a new cat or one you've met before?</p><div class="chips" style="margin-top:0"><button id="mode-new" class="chip ${s.revisitId?'':'selected'}">✨ New cat</button><button id="mode-repeat" class="chip ${s.revisitId?'selected':''}">🐾 Seen before</button></div><div id="catch-extra"></div><div id="possible-matches" aria-live="polite"></div><label class="check-row"><input id="real-cat" type="checkbox"><span>I saw a real cat and took this picture without disturbing or approaching it unsafely.</span></label><label class="check-row"><input id="pin-check" type="checkbox"><span>Add an optional private location pin (never shared).</span></label><div class="actions"><button id="save-catch" class="primary">Add to my CatDex →</button></div><p class="footnote">Only the selected still image is saved to your CatDex. Live mode compares recent frames locally when supported; no video is stored.</p>`);s.catchMode=s.revisitId?'repeat':'new';const drawExtra=()=>{const extra=$('catch-extra');if(s.catchMode==='new'){extra.innerHTML=`<div class="field-group"><label for="cat-name">Give your cat a name</label><input class="field" id="cat-name" maxlength="36" placeholder="e.g. Sir Pounce-a-lot" autocomplete="off"></div><div class="field-group"><label for="cat-coat">Coat / appearance</label><select class="select" id="cat-coat">${COATS.map(c=>`<option>${c}</option>`).join('')}</select></div><div class="field-group"><label for="cat-personality">Personality (your impression)</label><select class="select" id="cat-personality">${PERSONALITIES.map(t=>`<option>${t}</option>`).join('')}</select></div><div class="field-group"><label for="cat-note">Little memory (optional)</label><input class="field" id="cat-note" maxlength="140" placeholder="e.g. Sleeping in the café window"></div>`}else{extra.innerHTML=s.cats.length?`<div class="field-group"><label for="repeat-cat">Which cat did you see again?</label><select id="repeat-cat" class="select">${s.cats.map(c=>`<option value="${esc(c.id)}" ${c.id===s.revisitId?'selected':''}>${esc(c.name)} (${esc(c.coat)})</option>`).join('')}</select></div><div class="field-group"><label for="repeat-note">Add a memory (optional)</label><input id="repeat-note" class="field" maxlength="140" placeholder="What was your friend up to?"></div>`:`<div class="info-note">No cats collected yet. Add your first new cat!</div>`}};drawExtra();$('mode-new').onclick=()=>{s.catchMode='new';$('mode-new').classList.add('selected');$('mode-repeat').classList.remove('selected');drawExtra()};$('mode-repeat').onclick=()=>{s.catchMode='repeat';$('mode-repeat').classList.add('selected');$('mode-new').classList.remove('selected');drawExtra()};$('save-catch').onclick=saveCatch;findPossibleMatches(image,request)}
async function locationPrompt(){return new Promise(resolve=>{let settled=false;const timer=setTimeout(()=>{if(!settled){settled=true;resolve(null)}},14000);const finish=coords=>{if(settled)return;settled=true;clearTimeout(timer);resolve(coords)};if(window.whiskerNativeReady){window.whiskerNativeLocation=(lat,lng)=>finish({lat:Number(lat),lng:Number(lng)});window.whiskerNativeLocationError=()=>finish(null);location.href='whiskerhunt://location';return}if(!navigator.geolocation){finish(null);return}navigator.geolocation.getCurrentPosition(pos=>finish({lat:pos.coords.latitude,lng:pos.coords.longitude}),()=>finish(null),{timeout:10500,enableHighAccuracy:false,maximumAge:60000})})}
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
  cat=s.cats.find(c=>c.id===$('repeat-cat')?.value);if(!cat)return toast('Choose a cat from your CatDex.');
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
  const firstOfCoat=mode==='new'&&!s.cats.some(c=>c.coat===cat.coat);
  earned=(mode==='new'?100:cooldown?0:30)+(firstOfCoat?25:0);
  cat.sightings.push({id:id(),visualHash:hash,at:new Date().toISOString(),note,photo:mode==='new'?null:s.image,signature:sig,lat:loc&&Number.isFinite(loc.lat)&&Math.abs(loc.lat)<=90?loc.lat:null,lng:loc&&Number.isFinite(loc.lng)&&Math.abs(loc.lng)<=180?loc.lng:null});appended=true;
  if(mode==='new'){s.cats.push(cat);added=true}
  s.profile.xp+=earned;
  await persistCatchAtomic(cat);
  closeModal();navigate('dex');toast(`${mode==='new'?'🐱 New cat added!':'🐾 Reunited with '+cat.name+'!'} +${earned} XP`);
 }catch(e){console.error(e);s.profile.xp-=earned;if(appended)cat.sightings.pop();if(added)s.cats=s.cats.filter(c=>c.id!==cat.id);toast('Save failed. Please try again.');btn.disabled=false;btn.textContent='Add to my CatDex →';}
 finally{s.busy=false}
}
function openDetail(catId){
 const cat=s.cats.find(c=>c.id===catId);if(!cat)return;
 const journal=cat.sightings.slice().reverse().map((x,idx)=>`<div class="sighting journal-row"><div class="sighting-top"><span>🐾 ${dateDisplay(x.at)}${x.lat!=null?' · 📍 Private pin':''}</span><button class="text-btn" data-edit-sighting="${esc(x.id)}">Edit ✎</button></div>${x.photo?`<img class="sighting-thumb" src="${x.photo}" alt="Cat sighting">`:''}${x.note?`<small>${esc(x.note)}</small>`:''}${x.photo?`<div class="cover-actions"><button class="text-btn" data-cover-sighting="${esc(x.id)}" ${x.photo===cat.photo?'disabled':''}>${x.photo===cat.photo?'✓ Current cover':'🖼 Make CatDex cover'}</button></div>`:''}</div>`).join('');
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
// Set the CatDex cover to an existing sighting without losing the original
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
  openDetail(cat.id);render();toast('CatDex cover updated. Original discovery photo preserved!');
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
 openModal(`<div class="sheet-head"><h2>Edit sighting 🐾</h2><button class="close-btn" data-close>×</button></div><p class="dim">${dateDisplay(entry.at)}${isFirst?' · First discovery':''}</p><div class="field-group"><label for="sighting-note">What happened?</label><textarea id="sighting-note" maxlength="140" rows="4" class="field">${esc(entry.note||'')}</textarea></div>${entry.lat!=null?'<label class="check-row"><input type="checkbox" id="forget-pin"><span>Remove the precise location pin for this sighting</span></label>':'<p class="footnote">No location was stored for this sighting.</p>'}<div class="actions"><button id="save-sighting" class="primary">Save entry</button></div>${!isFirst?'<button id="delete-sighting" class="text-btn red" style="margin-top:18px">Delete this return sighting</button>':'<p class="footnote">The first sighting cannot be deleted separately. You can delete the complete cat entry in the CatDex.</p>'}`);
 $('save-sighting').onclick=async()=>{const before={note:entry.note,lat:entry.lat,lng:entry.lng};entry.note=$('sighting-note').value.trim().slice(0,140);if($('forget-pin')?.checked){entry.lat=null;entry.lng=null}try{await saveCat(cat);openDetail(cat.id);render();toast('Sighting updated!')}catch(e){Object.assign(entry,before);toast('Could not save sighting.')}};
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
async function deleteCat(cat){openModal(`<div class="sheet-head"><h2>Delete ${esc(cat.name)}?</h2><button class="close-btn" data-close>×</button></div><p class="dim">This permanently removes the cat, its photos and sighting journal from this device. XP already earned will remain.</p><div class="actions"><button class="secondary" id="cancel-delete">Cancel</button><button class="primary" id="confirm-delete">Delete forever</button></div>`);$('cancel-delete').onclick=closeModal;$('confirm-delete').onclick=async()=>{if(s.busy)return;s.busy=true;const previous=s.cats;s.cats=s.cats.filter(c=>c.id!==cat.id);try{await removeCat(cat);closeModal();render();toast('Cat removed from your CatDex.')}catch(e){s.cats=previous;toast('Could not delete cat. Your collection was kept.')}finally{s.busy=false}}}
async function shareCat(cat){const message=`🐾 Meet ${cat.name}, a ${cat.coat.toLowerCase()} cat in my Whisker Hunt CatDex! ${catches(cat)} sighting${catches(cat)!==1?'s':''}. #WhiskerHunt`;if(window.whiskerNativeReady){location.href='whiskerhunt://share?text='+encodeURIComponent(message);return}try{if(navigator.share)await navigator.share({title:'Whisker Hunt',text:message});else if(navigator.clipboard){await navigator.clipboard.writeText(message);toast('Caption copied!')}}catch(e){if(e.name!=='AbortError')toast('Could not share on this browser.')}}
function action(kind){if(kind.startsWith('osm:')){const [lat,lng]=kind.slice(4).split(',').map(Number);if(!Number.isFinite(lat)||!Number.isFinite(lng))return;if(!confirm('Open OpenStreetMap? This sends this selected location to OpenStreetMap in your browser.'))return;const url=`https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=17/${lat}/${lng}`;if(window.whiskerNativeReady)location.href='whiskerhunt://open?url='+encodeURIComponent(url);else window.open(url,'_blank','noopener,noreferrer');return}if(kind==='privacy-tools')return openPrivacyTools();if(kind==='health-check')return openCollectionHealth();if(kind==='rename-profile')return editProfile();if(kind==='export')return exportBackup();if(kind==='import'){if(window.whiskerNativeReady){location.href='whiskerhunt://restore';return}return $('backup-input').click()}if(kind==='about')return openModal(`<div class="sheet-head"><h2>Privacy & cat safety 🐾</h2><button class="close-btn" data-close>×</button></div><p class="dim">Whisker Hunt v1.1 saves your photos, cat names, sightings and optional coordinates <strong>on this device only</strong>. We don't have a server, accounts, adverts or analytics.</p><p class="dim">Choose whether to attach a location to each encounter. Locations do not appear in shared text. You decide before opening an external map.</p><p class="dim">Keep a respectful distance. Do not trespass, lure cats into dangerous places, follow them into roads, or reveal somebody's home or garden.</p><p class="dim">Export backups before uninstalling or resetting app/browser storage. Photo resemblance hints run on-device, can be wrong, and never automatically identify or merge cats. The app cannot verify whether an image contains a cat.</p>`) }
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
  const seenSightingIds=new Set();const sightings=c.sightings.filter(v=>{if(!v||!validId(v.id)||seenSightingIds.has(v.id))return false;seenSightingIds.add(v.id);return typeof v.at==='string'&&Number.isFinite(Date.parse(v.at))&&(v.photo==null||validPhoto(v.photo))}).map(v=>({id:v.id.slice(0,100),at:v.at,note:String(v.note||'').slice(0,140),photo:v.photo||null,signature:String(v.signature||''),visualHash:/^[a-f0-9]{16}$/i.test(v.visualHash||'')?v.visualHash:null,lat:safePin(v.lat)&&v.lat!=null&&Number(v.lat)>=-90&&Number(v.lat)<=90?Number(v.lat):null,lng:safePin(v.lng)&&v.lng!=null?Number(v.lng):null}));
  if(!sightings.length){skipped++;continue}
  accepted.push({id:c.id,name:c.name.slice(0,36),coat:COATS.includes(c.coat)?c.coat:'Other',personality:PERSONALITIES.includes(c.personality)?c.personality:'Unknown',note:String(c.note||'').slice(0,140),photo:c.photo,signature:String(c.signature||photoSignature(c.photo)),visualHash:/^[a-f0-9]{16}$/i.test(c.visualHash||'')?c.visualHash:null,createdAt:Number.isFinite(Date.parse(c.createdAt))?c.createdAt:sightings[0].at,fav:!!c.fav,sightings});
 }
 if(data.cats.length&&!accepted.length)return toast('No valid cats were found in this backup.');
 if(!confirm('Merge '+accepted.length+' cats into your CatDex? Matching IDs will be updated, other cats stay, and XP will never decrease.'))return;
 const oldCats=s.cats.slice(),oldProfile={...s.profile};
 try{
  const merged=new Map(s.cats.map(c=>[c.id,c]));let newSightings=0;for(const c of accepted){const local=merged.get(c.id);const combined=mergeCatRecord(local,c);newSightings+=combined.sightings.length-(local?.sightings?.length||0);merged.set(c.id,combined)}
  const nextProfile={name:String(s.profile.name||data.profile.name||'Cat Explorer').slice(0,30),xp:Math.max(s.profile.xp,data.profile.xp),claimed:[...new Set([...(s.profile.claimed||[]),...(Array.isArray(data.profile.claimed)?data.profile.claimed.filter(x=>typeof x==='string'&&x.length<120):[])])].slice(-1200)};
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
 s.cats=[];s.profile={name:'Cat Explorer',xp:0,claimed:[]};render();
 openModal('<div class="sheet-head"><h2>Collection needs recovery ⚠️</h2></div><p class="dim">Your local save and recovery snapshot could not be read. Whisker Hunt will not overwrite them with an empty collection.</p><p class="dim">Retry reading the device storage, or explicitly restore an exported JSON backup. Do not uninstall the app.</p><div class="actions"><button class="secondary" id="retry-native">Retry reading</button><button class="primary" id="restore-native">Restore JSON backup</button></div>');
 $('retry-native').onclick=()=>{closeModal();if(window.whiskerRequestNativeReady)window.whiskerRequestNativeReady();else location.href='whiskerhunt://ready'};
 $('restore-native').onclick=()=>{closeModal();location.href='whiskerhunt://restore'};
 console.warn('Native storage recovery required:',String(message||''));
};
window.whiskerUseNativeStorage=function(json){s.native=true;s.db={native:true};s.storageBlocked=false;s.recoveryApproved=false;window.whiskerNativeReady=true;s.cats=[];s.profile={name:'Cat Explorer',xp:0,claimed:[]};if(json){try{const data=JSON.parse(json);if(data.app==='Whisker Hunt'&&Array.isArray(data.cats)){s.cats=data.cats;s.profile={name:String(data.profile?.name||'Cat Explorer').slice(0,30),xp:Math.max(0,Number(data.profile?.xp)||0),claimed:Array.isArray(data.profile?.claimed)?data.profile.claimed:[]}}}catch(e){console.error(e);toast('Could not load your saved local collection.')}}render()};
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
function randomArModel(except=''){const pool=AR_CAT_MODELS.filter(m=>m.key!==except);return pool[Math.floor(Math.random()*pool.length)]||AR_CAT_MODELS[0]}
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
 const label=esc(model.name);
 return `<svg class="ar-cat-svg" viewBox="0 0 200 160" role="img" aria-label="${label}"><ellipse cx="100" cy="144" rx="46" ry="10" fill="#00000022"/><path d="M153 110c18-11 25-34 10-47-6-5-14-8-22-8" fill="none" stroke="${model.accent}" stroke-width="13" stroke-linecap="round"/><ellipse cx="104" cy="98" rx="50" ry="36" fill="${model.base}"/><ellipse cx="104" cy="110" rx="28" ry="18" fill="${model.belly}" opacity=".96"/><g>${arModelPattern(model)}</g><ellipse cx="97" cy="57" rx="34" ry="30" fill="${model.base}"/><path d="M67 41 80 20 89 44Z" fill="${model.base}"/><path d="M106 44 118 20 128 42Z" fill="${model.base}"/><path d="M73 39 80 26 86 40Z" fill="${model.ear}" opacity=".92"/><path d="M110 40 118 26 124 39Z" fill="${model.ear}" opacity=".92"/><ellipse cx="86" cy="58" rx="5" ry="7" fill="${model.eye}"/><ellipse cx="108" cy="58" rx="5" ry="7" fill="${model.eye}"/><ellipse cx="86" cy="58" rx="2" ry="3" fill="#1b1b1b"/><ellipse cx="108" cy="58" rx="2" ry="3" fill="#1b1b1b"/><path d="M97 66 92 72h10Z" fill="#ef8fa8"/><path d="M92 74c5 5 10 5 15 0" fill="none" stroke="#7a4b55" stroke-width="2.3" stroke-linecap="round"/><g stroke="#f0f3ff" stroke-width="2" stroke-linecap="round" opacity=".85"><path d="M89 70 67 65"/><path d="M89 74 66 75"/><path d="M105 70 127 65"/><path d="M105 74 128 75"/></g><g fill="${model.base}"><ellipse cx="77" cy="127" rx="9" ry="13"/><ellipse cx="96" cy="129" rx="9" ry="14"/><ellipse cx="118" cy="129" rx="9" ry="14"/><ellipse cx="136" cy="126" rx="9" ry="13"/></g></svg>`
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
 if($('encounter-status')&&s.encounterAr&&!s.encounterCaptured){$('encounter-status').textContent=`A ${model.name} appeared. Tap the scene to place it, then drag the paw to catch it.`}
}
const originalOpenModal=openModal;
openModal=function(content,keepLive=false,modalClass=''){
 if(!keepLive)stopLiveCamera();
 encounterResizeObserver?.disconnect();encounterResizeObserver=null;
 const layer=$('modal-layer');layer.classList.remove('hidden');layer.setAttribute('aria-hidden','false');
 layer.innerHTML=`<div class="sheet ${modalClass||''}" role="dialog" aria-modal="true"><div class="sheet-handle"></div><div class="whisker-build-stamp">Whisker Hunt v${WHISKER_BUILD} · build ${WHISKER_BUILD_NUMBER}</div>${content}</div>`;
 layer.onclick=modalBackdrop;const b=layer.querySelector('[data-close]');if(b)b.addEventListener('click',closeModal)
};
startCatch=function(catId=null){
 captureShots=[];nativePhotoRequestToken=null;photoSelectionEpoch++;
 if(s.busy)return toast('Please wait for the current save to finish.');
 if(s.storageBlocked)return toast('Restore your CatDex backup before adding cats.');
 s.image='';s.encounterLive=false;s.encounterAr=false;s.arModelManual=false;s.arModelSuggested='';
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
 openModal(`<div class="sheet-head"><h2>${title}</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim">${hint}</p><div class="live-loading" aria-live="polite">🎥 Preparing preview…</div><div class="actions"><button id="live-fallback" class="secondary">Use normal camera instead</button></div>`,false,mode==='ar'?'ar-sheet live-start-sheet':'');
 $('live-fallback').onclick=useNormalCameraFromLiveStartup;
 let stream=null;
 try{
  if(!navigator.mediaDevices?.getUserMedia||!globalThis.isSecureContext)throw Error('Live camera is not available in this WebView or browser context.');
  if(!await requestNativeLivePermission())throw Error('Camera permission was not granted.');
  if(request!==liveRequestEpoch||$('modal-layer')?.classList.contains('hidden'))return;
  stream=await navigator.mediaDevices.getUserMedia({audio:false,video:{facingMode:{ideal:'environment'},width:{ideal:960},height:{ideal:540},frameRate:{ideal:24,max:30}}});
  if(request!==liveRequestEpoch||$('modal-layer')?.classList.contains('hidden'))return;
  const video=document.createElement('video');video.autoplay=true;video.muted=true;video.playsInline=true;video.srcObject=stream;
  await Promise.race([video.play(),new Promise((_,reject)=>setTimeout(()=>reject(Error('Camera preview timed out.')),6000))]);
  if(!video.videoWidth||!video.videoHeight)await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('No camera frames received.')),4500);video.addEventListener('loadedmetadata',()=>{clearTimeout(timer);resolve()},{once:true})});
  if(request!==liveRequestEpoch||$('modal-layer')?.classList.contains('hidden'))return;
  const first=frameFromVideo(video,LIVE_SAMPLE_SIZE,.72); if(!first)throw Error('Camera did not provide a usable frame.');
  liveCamera={stream,video,frames:[],timer:null,active:true,sampling:false,dragging:false}; stream=null;
  if(request!==liveRequestEpoch||!liveCamera?.active)return;
  beginEncounter(first,{live:true,ar:mode==='ar'});
 }catch(error){
  if(request!==liveRequestEpoch)return;
  console.debug('Live camera unavailable',error);
  openModal(`<div class="sheet-head"><h2>${mode==='ar'?'AR safari unavailable':'Live camera unavailable'}</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="dim">${esc(error?.message||'Your camera could not be opened.')} Your CatDex is safe. You can still take a normal photo or choose one from your gallery.</p><div class="actions"><button id="live-normal-camera" class="primary">📸 Take a photo</button><button id="live-normal-gallery" class="secondary">🖼️ Gallery</button></div>`);
  $('live-normal-camera').onclick=useNormalCameraFromLiveStartup;
  $('live-normal-gallery').onclick=()=>{s.encounterLive=false;s.encounterAr=false;requestEncounterPhoto(false)};
 }finally{ if(stream)for(const track of stream.getTracks())track.stop(); }
}
startLiveEncounter=function(){return startCameraEncounter('live')};
function startArEncounter(){return startCameraEncounter('ar')}
beginEncounter=function(image,options={}){
 captureShots=[]; if(!options.live)stopLiveCamera();
 const generation=++encounterEpoch;
 s.image=image; s.encounterLive=Boolean(options.live); s.encounterAr=Boolean(options.ar); s.encounterTool='ball'; s.encounterLured=false; s.encounterCaptured=false; s.captureSummary=null; s.arModelManual=false;
 if(s.encounterAr) s.arModelKey=randomArModel().key;
 assessPhotoQuality(image).then(quality=>{ if(generation!==encounterEpoch||s.image!==image)return; showEncounter(image,quality,options); }).catch(()=>toast('Could not prepare encounter image. Please try another photo.'));
};
showEncounter=function(image,quality,options={}){
 const liveMode=Boolean(options.live||s.encounterLive), arMode=Boolean(options.ar||s.encounterAr);
 s.encounterLive=liveMode; s.encounterAr=arMode; s.encounterFocus={x:.52,y:(arMode ? .58 : .40)}; s.captureSummary={quality,throwRating:null};
 const model=getArModel(s.arModelKey);
 const help=arMode?'① Move the virtual cat · ② Pick a model · ③ Drag the paw to catch!':'① Tap the cat · ② Drag the paw · ③ Catch!';
 const summary=arMode?`<div class="encounter-ar-tools"><div class="ar-model-badge" id="ar-model-badge">Virtual cat: ${esc(model.name)}</div><button type="button" class="secondary ar-reroll" id="ar-reroll">↻ New virtual cat</button></div><div id="ar-model-strip" class="ar-model-strip">${renderArModelButtons()}</div><div id="ar-smart-note" class="ar-smart-note">Smart matching the live scene…</div>`:'';
 openModal(`<div class="sheet-head"><h2>${arMode?'AR safari ✨':liveMode?'Live encounter 🎥':'Encounter! 🐾'}</h2><button class="close-btn" data-close aria-label="Close">×</button></div><p class="encounter-quick-help">${help}</p><details class="encounter-help"><summary>${arMode?'How does AR safari work?':'How do the tools work?'}</summary><p>${arMode?'This prototype overlays a stylised virtual cat on your live camera so you can explore a Pokémon Go-style full-screen encounter. It uses recent still frames only; no video is stored. Smart match gives a simple coat-style guess from the current frame, not real cat recognition.':'Tap the cat to place your target. Drag the Whisker Paw onto the target to catch it, or use the Dangle Lure first to make catching easier. Stay at a safe distance from real cats.'}</p></details><div id="encounter-aim-guide" class="encounter-aim-guide hidden" aria-hidden="true"></div><div id="encounter-stage" class="encounter-stage ${arMode?'encounter-stage-ar':''}"><img id="encounter-photo" class="encounter-backdrop" src="${image}" alt="${arMode?'Live encounter backdrop':'Your selected cat photo'}"><div class="encounter-vignette"></div><div id="encounter-cat" class="encounter-cat ${arMode?'ar-model-target':''}"><div class="encounter-cat-ring"></div>${arMode?`<div id="encounter-ar-cat" class="encounter-ar-cat">${renderArCatSvg(model)}</div><span id="encounter-ar-label">${esc(model.name)}</span>`:`<img id="encounter-cat-crop" src="${image}" alt="Selected cat photo crop"><span>Your cat target</span>`}</div><div class="encounter-capture-tag">${arMode?'● AR SAFARI':'Capture preview'}</div><div class="encounter-tool-dock" aria-label="Capture tools"><button type="button" id="tool-ball" class="dock-tool selected" aria-pressed="true" title="Whisker Paw"><span>🐾</span><small>Paw</small></button><button type="button" id="tool-lure" class="dock-tool" aria-pressed="false" title="Dangle Lure"><span>🪶</span><small>Lure</small></button><div id="throw-item" class="throw-item throw-ball" role="button" aria-label="Drag ${encounterToolLabel('ball')} to the cat" tabindex="0"><svg class="whisker-paw-svg" viewBox="0 0 100 110" aria-hidden="true" focusable="false"><defs><linearGradient id="whisker-paw-shine" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffe5f3"/><stop offset=".4" stop-color="#fb80b7"/><stop offset="1" stop-color="#8553d8"/></linearGradient></defs><g class="paw-digits"><ellipse cx="19" cy="34" rx="11" ry="15" transform="rotate(-23 19 34)"/><ellipse cx="40" cy="20" rx="11" ry="16" transform="rotate(-9 40 20)"/><ellipse cx="62" cy="19" rx="11" ry="16" transform="rotate(9 62 19)"/><ellipse cx="82" cy="32" rx="10" ry="15" transform="rotate(24 82 32)"/></g><path class="paw-center" d="M51 47 C65 45 71 55 80 65 C90 78 84 94 71 98 C62 101 57 95 51 95 C43 95 37 102 27 98 C12 95 10 79 20 66 C29 53 35 46 51 47Z"/><path class="paw-detail" d="M33 77 Q42 69 50 75 Q58 69 68 77"/></svg><span class="throw-stick">🎣</span><span class="throw-lure-body">🧶</span><span class="drag-prompt">DRAG</span></div></div><div id="encounter-orb" class="encounter-orb hidden"><svg class="whisker-paw-svg capture-paw" viewBox="0 0 100 110" aria-hidden="true" focusable="false"><defs><linearGradient id="whisker-paw-shine-captured" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffe5f3"/><stop offset=".4" stop-color="#fb80b7"/><stop offset="1" stop-color="#8553d8"/></linearGradient></defs><g class="paw-digits"><ellipse cx="19" cy="34" rx="11" ry="15" transform="rotate(-23 19 34)"/><ellipse cx="40" cy="20" rx="11" ry="16" transform="rotate(-9 40 20)"/><ellipse cx="62" cy="19" rx="11" ry="16" transform="rotate(9 62 19)"/><ellipse cx="82" cy="32" rx="10" ry="15" transform="rotate(24 82 32)"/></g><path class="paw-center" d="M51 47 C65 45 71 55 80 65 C90 78 84 94 71 98 C62 101 57 95 51 95 C43 95 37 102 27 98 C12 95 10 79 20 66 C29 53 35 46 51 47Z"/><path class="paw-detail" d="M33 77 Q42 69 50 75 Q58 69 68 77"/></svg></div><div id="encounter-status" class="encounter-status" role="status" aria-live="polite">${arMode?'A virtual cat appeared. Tap the scene to place it, then drag the paw to catch it.':'Tap the cat to move the target. Then drag an item from the tool dock on the right.'}</div><div id="encounter-meow" class="encounter-meow hidden" aria-hidden="true">Meow!</div></div><div id="encounter-quality" class="encounter-quality">${liveMode?'🎥 Live preview · <span id="live-frame-count">1 recent frame</span> · Whisker Hunt keeps a few recent stills and picks the clearest one near your target when you capture.':'Photo clarity estimate: <strong>'+esc(quality.label)+'</strong> · '+esc(quality.note)} <small>${arMode?'AR safari uses a virtual cat overlay and local frame snapshots only.':'No video recording or upload.'}</small></div>${summary}<div id="encounter-shots" class="encounter-shots hidden" aria-label="Choose best frame"></div><div class="encounter-photo-actions"><button type="button" id="encounter-retake" class="secondary">${liveMode?'🎥 Retake live capture':'📸 Retake photo'}</button><button type="button" id="encounter-replace" class="secondary">🖼️ Choose another</button></div><div class="encounter-launch"><div class="encounter-instructions">${arMode?'Move the virtual cat with a tap if it spawns somewhere awkward.':'Drag the paw from the right. A green ring means your throw is on target.'}</div></div><div class="actions"><button id="encounter-skip" class="secondary">Save photo without game</button><button id="encounter-continue" class="primary hidden">Continue to CatDex →</button></div><p class="footnote">${arMode?'Prototype AR safari: the built-in virtual cat models are offline illustrations and can be swapped manually.':'Live camera is local to your device; only the selected still is saved. No cat recognition.'} Stay a safe distance from real cats.</p>`,liveMode,arMode?'ar-sheet':'');
 if(liveMode&&liveCamera?.active){
  const stage=$('encounter-stage'),video=liveCamera.video;
  video.id='encounter-video';video.className='encounter-backdrop encounter-live-video'; stage.prepend(video);stage.classList.add('live-encounter');
  const tag=stage.querySelector('.encounter-capture-tag');if(tag)tag.textContent=arMode?'● LIVE · AR':'● LIVE · private';
  const crop=$('encounter-cat-crop');if(crop)crop.style.display='none';
  const status=$('encounter-status');if(status&& !arMode)status.textContent='Tap the cat to place the target, then drag a tool from the right.';
  scheduleLiveSampling(liveCamera);
 }
 const selectTool=kind=>{if(s.encounterCaptured)return; s.encounterTool=kind; $('tool-ball').classList.toggle('selected',kind==='ball');$('tool-lure').classList.toggle('selected',kind==='lure'); $('tool-ball').setAttribute('aria-pressed',String(kind==='ball'));$('tool-lure').setAttribute('aria-pressed',String(kind==='lure')); const item=$('throw-item'); item.classList.toggle('throw-ball',kind==='ball');item.classList.toggle('throw-lure',kind==='lure'); item.setAttribute('aria-label','Drag '+encounterToolLabel(kind)+' to the cat'); $('encounter-status').textContent=kind==='lure'?'Aim the Dangle Lure at the cat to enlarge the target.':'Drag the Whisker Paw onto the target for a capture!';};
 $('tool-ball').onclick=()=>selectTool('ball');$('tool-lure').onclick=()=>selectTool('lure');
 $('encounter-skip').onclick=async()=>{if(liveCamera)await freezeLiveEncounter();s.captureSummary=null;showCatForm(s.image)};
 $('encounter-continue').onclick=()=>showCatForm(s.image);
 $('encounter-retake').onclick=()=>s.encounterLive?(s.encounterAr?startArEncounter():startLiveEncounter()):requestEncounterPhoto(true);
 $('encounter-replace').onclick=()=>{s.encounterLive=false;s.encounterAr=false;requestEncounterPhoto(false)};
 const stage=$('encounter-stage'),backdrop=$('encounter-photo'); [stage,$('encounter-status'),$('encounter-quality'),$('encounter-meow'),$('tool-ball'),$('tool-lure'),$('throw-item')].filter(Boolean).forEach(el=>{el.oncontextmenu=e=>e.preventDefault();el.onselectstart=e=>e.preventDefault();el.ondragstart=()=>false;});
 stage.addEventListener('click',event=>{ const visual=$('encounter-video')||backdrop; if(s.encounterCaptured||!(event.target===stage||event.target===backdrop||event.target===visual))return; const point=encounterImagePoint(event.clientX,event.clientY,visual,visual.getBoundingClientRect()); if(point)setEncounterFocus(point.x,point.y); });
 backdrop.addEventListener('load',()=>positionEncounterFocus()); encounterResizeObserver?.disconnect(); encounterResizeObserver=typeof ResizeObserver==='function'?new ResizeObserver(()=>positionEncounterFocus()):null; encounterResizeObserver?.observe(stage); setEncounterFocus(s.encounterFocus.x,s.encounterFocus.y,false); setupEncounterDrag();
 if(arMode){
  document.querySelectorAll('[data-ar-model]').forEach(btn=>btn.addEventListener('click',()=>{s.arModelManual=true;s.arModelKey=btn.dataset.arModel;refreshArEncounterUi()}));
  $('ar-reroll')?.addEventListener('click',()=>{s.arModelManual=true;s.arModelKey=randomArModel(s.arModelKey).key;refreshArEncounterUi()});
  refreshArEncounterUi();
  suggestArModelFromImage(image).then(key=>{ if(!s.encounterAr||s.encounterCaptured)return; s.arModelSuggested=key; const note=$('ar-smart-note'); if(note) note.textContent='Smart match suggestion: '+getArModel(key).name+' · You can keep it or pick another.'; if(!s.arModelManual){ s.arModelKey=key; refreshArEncounterUi(); } });
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
 }else{ cat=s.cats.find(c=>c.id===$('repeat-cat')?.value);if(!cat)return toast('Choose a cat from your CatDex.'); }
 const btn=$('save-catch');s.busy=true;btn.disabled=true;btn.textContent='Saving your discovery…';
 let appended=false,added=false,earned=0;
 try{
  const hash=await visualFingerprint(s.image).catch(()=>null); if(mode==='new')cat.visualHash=hash;
  const loc=$('pin-check').checked?await locationPrompt():null; const note=mode==='new'?cat.note:$('repeat-note')?.value.trim();
  const now=Date.now(); const lastSeen=Math.max(0,...(cat.sightings||[]).map(v=>Date.parse(v.at)).filter(t=>Number.isFinite(t)&&t<=now));
  const cooldown=mode==='repeat'&&lastSeen>0&&(now-lastSeen<3600000); const firstOfCoat=mode==='new'&&!s.cats.some(c=>c.coat===cat.coat); earned=(mode==='new'?100:cooldown?0:30)+(firstOfCoat?25:0);
  cat.sightings.push({id:id(),visualHash:hash,at:new Date().toISOString(),note,photo:mode==='new'?null:s.image,signature:sig,lat:loc&&Number.isFinite(loc.lat)&&Math.abs(loc.lat)<=90?loc.lat:null,lng:loc&&Number.isFinite(loc.lng)&&Math.abs(loc.lng)<=180?loc.lng:null,captureMode:s.encounterAr?'ar-live':s.encounterLive?'live':'photo',arModel:s.encounterAr?s.arModelKey:null}); appended=true;
  if(mode==='new'){s.cats.push(cat);added=true}
  s.profile.xp+=earned; await persistCatchAtomic(cat);
  closeModal();navigate('dex');toast(`${mode==='new'?'🐱 New cat added!':'🐾 Reunited with '+cat.name+'!'} +${earned} XP`);
 }catch(e){ console.error(e);s.profile.xp-=earned;if(appended)cat.sightings.pop();if(added)s.cats=s.cats.filter(c=>c.id!==cat.id);toast('Save failed. Please try again.');btn.disabled=false;btn.textContent='Add to my CatDex →'; }
 finally{s.busy=false}
 })()};
