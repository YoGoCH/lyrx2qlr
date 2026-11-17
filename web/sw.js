// Usage hors ligne de lyrx2qlr : ce « service worker » garde dans le navigateur la page, le cœur
// Python (lyrx2qlr.zip) et Pyodide, pour que la conversion marche sans internet.
// Il n'est installé que si l'utilisateur clique sur « Utiliser hors ligne » (hors_ligne.js).
// Fichiers de la page : le réseau d'abord (les nouvelles versions arrivent dès qu'on est en ligne),
// la copie gardée sinon. Pyodide : version épinglée, donc la copie gardée d'abord.
// VERSION est mise à jour par outils/construire.py ; changer de version efface les anciennes copies.
"use strict";

const VERSION = "1.8.2";
const CACHE = `lyrx2qlr-${VERSION}`;
const PYODIDE = "https://cdn.jsdelivr.net/npm/pyodide@0.29.4/";
const PAGE = [
  "./", "index.html", "style.css", "langue.js", "apparence.js", "schema.js", "nouveautes.js",
  "contribuer.js", "hors_ligne.js", "app.js", "passerelle.py", "lyrx2qlr.zip", "chiffres.json",
  "nouveautes.json", "manifest.webmanifest", "icon.svg", "favicon.ico", "apple-touch-icon.png",
  "icone-192.png", "icone-512.png",
];
const MOTEUR = ["pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]
  .map(f => PYODIDE + f);

self.addEventListener("install", evenement => {
  evenement.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    // cache: "reload" : copie fraîche, pas celle du cache HTTP du navigateur
    await cache.addAll([...PAGE, ...MOTEUR].map(u => new Request(u, { cache: "reload" })));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", evenement => {
  evenement.waitUntil((async () => {
    for (const nom of await caches.keys()) {
      if (nom.startsWith("lyrx2qlr-") && nom !== CACHE) await caches.delete(nom);
    }
    await self.clients.claim();
  })());
});

self.addEventListener("message", evenement => {
  if (evenement.data === "etat") {
    caches.has(CACHE).then(pret => evenement.source.postMessage({ hors_ligne: pret, version: VERSION }));
  }
});

self.addEventListener("fetch", evenement => {
  const requete = evenement.request;
  if (requete.method !== "GET") return;  // l'envoi d'une contribution passe toujours par le réseau
  const url = new URL(requete.url);
  if (url.href.startsWith(PYODIDE)) {
    evenement.respondWith(copie(requete).then(r => r || fetch(requete)));
  } else if (url.origin === self.location.origin && !url.pathname.startsWith("/api/")) {
    evenement.respondWith(reseauPuisCopie(requete));
  }
});

// Dans notre copie seulement : caches.match chercherait aussi dans celles d'autres pages de la même adresse
async function copie(requete) {
  return (await caches.open(CACHE)).match(requete, { ignoreSearch: true });
}

async function reseauPuisCopie(requete) {
  try {
    // « no-cache » : toujours demander au serveur. Sinon le cache ordinaire du navigateur peut rendre
    // une très vieille page, même serveur éteint, au lieu de la copie hors ligne.
    const reponse = await fetch(requete.url, { cache: "no-cache", credentials: "same-origin" });
    if (reponse.ok) {
      const cache = await caches.open(CACHE);
      // Rangé sans le « ?v=… » : la copie sert quelle que soit l'empreinte demandée
      const url = new URL(requete.url);
      url.search = "";
      await cache.put(url.href, reponse.clone());
    }
    return reponse;
  } catch (e) {
    const gardee = await copie(requete) || (requete.mode === "navigate" ? await copie("index.html") : undefined);
    if (gardee) return gardee;
    throw e;
  }
}
