// Section « Nouveautés » : lit nouveautes.json (textes écrits à la main, ajouts calculés par
// outils/nouveautes.py) et l'affiche dans la langue de la page. Chargé après langue.js.
"use strict";

(() => {
  const I = window.I18N;
  const VISIBLES = 2;  // versions montrées d'emblée ; les autres sous « Versions précédentes »
  let versions = null;

  const nombre = n => Number(n).toLocaleString(I.locale);

  function element(balise, classe, texte) {
    const el = document.createElement(balise);
    if (classe) el.className = classe;
    if (texte != null) el.textContent = texte;
    return el;
  }

  function article(v) {
    const li = element("li", "version");
    const tete = element("div", "version-tete");
    tete.append(element("b", "", "v" + v.version));
    const date = new Date(v.date + "T12:00:00");
    tete.append(element("time", "petit", date.toLocaleDateString(I.locale, { day: "numeric", month: "long", year: "numeric" })));
    tete.lastChild.dateTime = v.date;
    li.append(tete, element("p", "", v[I.langue] || v.fr));

    const a = v.ajouts || {};
    const pastilles = element("p", "ajouts");
    if (a.modele) pastilles.append(element("span", "ajout modele", I.t("ajout-modele", { n: nombre(a.modele) })));
    if (a.catalogues) pastilles.append(element("span", "ajout catalogues", I.t("ajout-catalogues", { n: nombre(a.catalogues) })));
    if (a.regles > 0) pastilles.append(element("span", "ajout regles", I.t("ajout-regles", { n: nombre(a.regles) })));
    // Sans ajout, rien : la liste reste discrète
    if (pastilles.childElementCount) li.append(pastilles);
    return li;
  }

  function afficher() {
    if (!versions) return;
    const recentes = document.getElementById("versions");
    const anciennes = document.getElementById("versions-anciennes");
    recentes.replaceChildren(...versions.slice(0, VISIBLES).map(article));
    anciennes.querySelector("ul").replaceChildren(...versions.slice(VISIBLES).map(article));
    anciennes.hidden = versions.length <= VISIBLES;
  }

  document.addEventListener("DOMContentLoaded", () => {
    fetch("nouveautes.json", { cache: "no-cache" })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(r.status))))
      .then(d => { versions = d.versions; afficher(); })
      .catch(e => console.warn("nouveautes.json :", e));
    I.surChangement(afficher);
  });
})();
