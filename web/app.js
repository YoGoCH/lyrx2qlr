// Page web de lyrx2qlr : charge Python (Pyodide), le cœur (lyrx2qlr.zip) et convertit les fichiers déposés.
// Le code de conversion est le même que celui de la ligne de commande et de l'extension QGIS.
"use strict";

const I = window.I18N;
const etat = document.getElementById("etat");
const depot = document.getElementById("depot");
const choix = document.getElementById("choix");
const liste = document.getElementById("liste");
const blocResultats = document.getElementById("resultats");
const boutonTout = document.getElementById("tout");

let passerelle = null;   // module Python « passerelle »
let archive = null;      // dernier ZIP produit (Uint8Array)
let dernier = null;      // derniers résultats, pour les réafficher si la langue change
let message = ["chargement", {}, ""];  // message d'état courant : [clé, valeurs, classe]
let versions = null;
let derniersFichiers = null;  // derniers fichiers déposés, reconvertis si la coche « Garder la source » change

function dire(cle, valeurs = {}, classe = "") {
  message = [cle, valeurs, classe];
  etat.textContent = I.t(cle, valeurs);
  etat.className = "etat" + (classe ? " " + classe : "");
}

async function demarrer() {
  try {
    const pyodide = await loadPyodide({ indexURL: "https://cdn.jsdelivr.net/npm/pyodide@0.29.4/" });
    const [coeur, code] = await Promise.all([
      fetch("lyrx2qlr.zip", { cache: "no-cache" }).then(verifier).then(r => r.arrayBuffer()),
      fetch("passerelle.py", { cache: "no-cache" }).then(verifier).then(r => r.text()),
    ]);
    pyodide.unpackArchive(coeur, "zip", { extractDir: "/coeur" });
    pyodide.FS.writeFile("/coeur/passerelle.py", code);
    pyodide.runPython("import sys; sys.path.insert(0, '/coeur')");
    passerelle = pyodide.pyimport("passerelle");
    window.LYRX2QLR = { passerelle: () => passerelle };  // pour contribuer.js
    versions = { v: passerelle.version(), p: pyodide.version };
    afficherVersion();
    dire("pret", {}, "pret");
  } catch (e) {
    dire("echec-chargement", { erreur: e.message }, "erreur");
    console.error(e);
  }
}

function afficherVersion() {
  if (versions) document.getElementById("version").textContent = I.t("version", versions);
}

function verifier(r) {
  if (!r.ok) throw new Error(`${r.url} : ${r.status}`);
  return r;
}

async function convertir(fichiers) {
  fichiers = [...fichiers].filter(f => /\.(lyrx|qlr|qml)$/i.test(f.name));
  if (!fichiers.length) { dire("aucun-fichier", {}, "erreur"); return; }
  if (!passerelle) return;
  derniersFichiers = fichiers;
  dire("conversion", { n: fichiers.length });
  const entrees = await Promise.all(fichiers.map(async f => [f.name, new Uint8Array(await f.arrayBuffer())]));
  const reponse = passerelle.convertir(entrees, document.getElementById("garder-source").checked);
  const [zip, json, donnees] = reponse.toJs();
  reponse.destroy();
  archive = zip;
  dernier = [JSON.parse(json), donnees];
  afficher(...dernier);
  if (window.LYRX2QLR_COMPTER) window.LYRX2QLR_COMPTER(dernier[0].length, dernier[0].filter(r => r.reussi).length);
}

const NIVEAUX = ["perte", "avertissement", "info"];

function compter(r) {
  const n = Object.fromEntries(NIVEAUX.map(x => [x, 0]));
  r.entrees.forEach(e => { if (e.niveau in n) n[e.niveau]++; });
  return n;
}

function resume(r) {
  const n = compter(r);
  return n.perte || n.avertissement ? I.t("resume", { p: n.perte, a: n.avertissement, i: n.info }) : I.t("complet");
}

// Le rapport détaillé est mis en forme ici, dans la langue de la page. Les messages eux-mêmes viennent
// du cœur et sont encore en français.
function texteRapport(r) {
  const lignes = [I.t("titre-rapport", { fichier: r.entree }), resume(r)];
  const note = I.t("note-rapport");
  if (note) lignes.push(note);
  NIVEAUX.forEach(niveau => {
    const choisies = r.entrees.filter(e => e.niveau === niveau);
    if (!choisies.length) return;
    lignes.push("", `${I.t(niveau)} (${choisies.length})`);
    choisies.forEach(e => {
      lignes.push(`  - ${e.ou} : ${e.message}${e.nombre > 1 ? ` (×${e.nombre})` : ""}`);
      if (e.conseil) lignes.push(`      → ${e.conseil}`);
    });
  });
  return lignes.join("\n");
}

function afficher(resultats, donnees) {
  liste.replaceChildren();
  let reussis = 0;
  resultats.forEach((r, i) => {
    if (r.reussi) reussis++;
    const li = document.createElement("li");
    li.className = "resultat " + (!r.reussi ? "echec" : r.pertes ? "pertes" : r.avertissements ? "avert" : "ok");
    const tete = document.createElement("div");
    tete.className = "tete";
    const titre = document.createElement("span");
    titre.className = "nom";
    titre.textContent = r.reussi ? `${r.entree} → ${r.sortie}` : r.entree;
    const bilan = document.createElement("span");
    bilan.className = "resume";
    bilan.textContent = r.reussi ? resume(r) : I.t("echec", { erreur: r.erreur || I.t("conversion-impossible") });
    tete.append(titre, bilan);
    if (r.reussi) {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = I.t("telecharger");
      b.addEventListener("click", () => telecharger(donnees[i], r.sortie));
      tete.append(b);
    }
    const original = (derniersFichiers || []).find(f => f.name === r.entree);
    if (original && window.Contribuer) {
      const c = document.createElement("button");
      c.type = "button";
      c.className = "secondaire contribuer-resultat";
      c.textContent = I.t("contribuer-resultat");
      c.title = I.t("contribuer-resultat-titre");
      c.addEventListener("click", () => window.Contribuer.ouvrir({ fichier: original, type: !r.reussi || r.pertes || r.avertissements ? "a_corriger" : "bon" }));
      tete.append(c);
    }
    li.append(tete);
    if (r.entrees.length) {
      const details = document.createElement("details");
      const s = document.createElement("summary");
      s.textContent = I.t("rapport-detaille");
      const pre = document.createElement("pre");
      pre.textContent = texteRapport(r);
      details.append(s, pre);
      li.append(details);
    }
    liste.append(li);
  });
  blocResultats.hidden = false;
  dire("bilan", { reussis, n: resultats.length }, reussis === resultats.length ? "pret" : "erreur");
}

function telecharger(octets, nom) {
  const url = URL.createObjectURL(new Blob([octets], { type: "application/octet-stream" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = nom;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

I.surChangement(() => {
  dire(...message);
  afficherVersion();
  if (dernier) {
    // garder ouverts les rapports que le visiteur lisait
    const ouverts = [...liste.querySelectorAll("details")].map(d => d.open);
    afficher(...dernier);
    liste.querySelectorAll("details").forEach((d, i) => { d.open = !!ouverts[i]; });
  }
});

boutonTout.addEventListener("click", () => archive && telecharger(archive, "lyrx2qlr_conversions.zip"));
choix.addEventListener("change", () => { convertir(choix.files); choix.value = ""; });
depot.addEventListener("click", e => { if (e.target === depot) choix.click(); });
depot.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); choix.click(); } });
["dragenter", "dragover"].forEach(t => depot.addEventListener(t, e => { e.preventDefault(); depot.classList.add("survol"); }));
["dragleave", "drop"].forEach(t => depot.addEventListener(t, e => { e.preventDefault(); depot.classList.remove("survol"); }));
depot.addEventListener("drop", e => convertir(e.dataTransfer.files));
document.getElementById("garder-source").addEventListener("change", () => { if (derniersFichiers) convertir(derniersFichiers); });

dire("chargement");
demarrer();
