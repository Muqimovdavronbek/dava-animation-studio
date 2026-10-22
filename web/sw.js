'use strict';
const CACHE='dava-animation-studio-web-v2';
const BASE=new URL('./',self.location.href);
const ASSETS=['./','./index.html','./icon.svg','./manifest.webmanifest'].map(path=>new URL(path,BASE).href);
self.addEventListener('install',event=>{
 event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',event=>{
 event.waitUntil(caches.keys().then(keys=>Promise.all(
  keys.filter(key=>(key.startsWith('dava-space-')||key.startsWith('dava-animation-studio-'))&&key!==CACHE).map(key=>caches.delete(key))
 )).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url);
 if(event.request.method!=='GET'||url.origin!==BASE.origin||!url.pathname.startsWith(BASE.pathname))return;
 event.respondWith(fetch(event.request).then(response=>{
  if(response.ok&&response.type==='basic'){
   const copy=response.clone();
   event.waitUntil(caches.open(CACHE).then(cache=>cache.put(event.request,copy)));
  }
  return response;
 }).catch(()=>caches.match(event.request).then(cached=>cached||(
  event.request.mode==='navigate'?caches.match(new URL('./index.html',BASE).href):Response.error()
 ))));
});
