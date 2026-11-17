// Apparence de la page : style papetche (couleurs, ombres) ou sobre (carré, neutre), mode clair ou sombre.
// Les deux choix sont indépendants et gardés dans ce navigateur seulement (rien n'est envoyé).
// Sans choix, le mode suit l'ordinateur (réglage « prefers-color-scheme »). Chargé après langue.js.
"use strict";

(() => {
  const I = window.I18N;
  const racine = document.documentElement;
  const systemeSombre = window.matchMedia("(prefers-color-scheme: dark)");
  const garder = (cle, valeur) => { try { localStorage.setItem(cle, valeur); } catch { /* stockage indisponible : tant pis */ } };

  // Repli si le navigateur a gardé en cache un ancien langue.js, sans ces textes
  const REPLI = {
    "theme-sombre": "☾ Sombre", "theme-clair": "☀ Clair", "theme-sombre-titre": "", "theme-clair-titre": "",
    "style-papetche": "Style : papetche", "style-sobre": "Style : sobre", "style-titre": "",
  };
  const t = cle => { const texte = I.t(cle); return texte === cle ? REPLI[cle] : texte; };

  const estSobre = () => racine.dataset.style === "sobre";
  const estSombre = () => (racine.dataset.theme ? racine.dataset.theme === "dark" : systemeSombre.matches);

  // Couleur de la barre du navigateur sur téléphone : le fond de la page
  const COULEUR_BARRE = { papetche: ["#fff6ec", "#160f22"], sobre: ["#f3f4f6", "#14171c"] };

  function majBoutons() {
    const sombre = estSombre(), sobre = estSobre();
    const theme = document.getElementById("theme");
    theme.textContent = t(sombre ? "theme-clair" : "theme-sombre");
    theme.title = t(sombre ? "theme-clair-titre" : "theme-sombre-titre");
    theme.setAttribute("aria-pressed", String(sombre));
    const style = document.getElementById("style");
    style.textContent = t(sobre ? "style-sobre" : "style-papetche");
    style.title = t("style-titre");
    style.setAttribute("aria-pressed", String(sobre));
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = COULEUR_BARRE[sobre ? "sobre" : "papetche"][sombre ? 1 : 0];
  }

  function changerStyle() {
    if (estSobre()) delete racine.dataset.style; else racine.dataset.style = "sobre";
    garder("lyrx2qlr-style", estSobre() ? "sobre" : "papetche");
    majBoutons();
  }

  function changerTheme() {
    racine.dataset.theme = estSombre() ? "light" : "dark";
    garder("lyrx2qlr-theme", racine.dataset.theme);
    majBoutons();
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("style").addEventListener("click", changerStyle);
    document.getElementById("theme").addEventListener("click", changerTheme);
    systemeSombre.addEventListener("change", majBoutons);
    I.surChangement(majBoutons);
    majBoutons();
  });
})();
