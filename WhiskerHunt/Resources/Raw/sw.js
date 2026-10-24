/* v3.1.1: versioned assets and cleanup, preventing stale encounter UI */
const CACHE='whisker-hunt-shell-v88';
const ASSETS=['./','./index.html','./index_v88.html','./app_v88.js','./style_v88.css','./icon.svg','./icon-192.png','./icon-512.png'];
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(Promise.all([caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('whisker-hunt-shell-')&&key!==CACHE).map(key=>caches.delete(key)))),self.clients.claim()])));
self.addEventListener('fetch',e=>{if(e.request.method!=='GET'||new URL(e.request.url).origin!==self.location.origin)return;e.respondWith(caches.open(CACHE).then(async cache=>{const path=new URL(e.request.url).pathname;const fresh=/\/(index(?:_v\d+)?\.html|app(?:_v\d+)?\.js|style(?:_v\d+)?\.css)$/.test(path)||path.endsWith('/');if(fresh){try{const response=await fetch(e.request);if(response.ok)cache.put(e.request,response.clone());return response}catch{return await cache.match(e.request)||Response.error()}}return await cache.match(e.request)||fetch(e.request)}))});
