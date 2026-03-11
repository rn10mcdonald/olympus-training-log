const CACHE = "olympus-v5";
const ASSETS = [
  "/", "/static/index.html", "/static/style.css",
  "/static/main.js", "/static/manifest.json", "/static/coin.png"
];

self.addEventListener("install", evt=>{
  evt.waitUntil(
    caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting())
  );
});
self.addEventListener("activate", evt=>{
  evt.waitUntil(
    caches.keys().then(keys=>
      Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))
    ).then(()=>self.clients.claim())
  );
});
self.addEventListener("fetch", evt=>{
  evt.respondWith(
    caches.match(evt.request).then(r=> r || fetch(evt.request))
  );
});
