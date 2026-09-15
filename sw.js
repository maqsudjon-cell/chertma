// Offline cache. The build (tools/build_site.py) fills in VERSION and ASSETS.
const VERSION = "chertma-234839d26cee";
const ASSETS = ["./", "index.html", "style.css", "app.js", "manifest.json", "icon.svg", "icons/apple-touch-icon.png", "icons/icon-192.png", "icons/icon-512.png", "fonts/JetBrainsMono-Regular.ttf", "fonts/JetBrainsMono-Bold.ttf", "data/lexicon-lite.bin.gz", "engine/constants.js", "engine/index.js", "engine/learn.js", "engine/lexicon.js", "engine/normalize.js", "engine/rank.js", "engine/skeleton.js", "engine/translit.js"];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(VERSION).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin) return;
  event.respondWith(
    caches.match(req, { ignoreSearch: true }).then((hit) => hit || fetch(req).then((res) => {
      if (res.ok) {
        const copy = res.clone();
        caches.open(VERSION).then((cache) => cache.put(req, copy));
      }
      return res;
    })),
  );
});
