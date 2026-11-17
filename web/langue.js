// Langue de la page (français / anglais). Chargé avant schema.js et app.js.
// Choix : ?lang= dans l'adresse, sinon le dernier choix du visiteur, sinon la langue du navigateur.
"use strict";

(() => {
  const TEXTES = {
    fr: {
      "logo-titre": "Logo : deux flèches en cercle, de lyrx vers qlr et de qlr vers lyrx",
      "bouton-langue": "English",
      "bouton-langue-titre": "Read this page in English",
      "theme-sombre": "☾ Sombre",
      "theme-clair": "☀ Clair",
      "theme-sombre-titre": "Passer en mode sombre",
      "theme-clair-titre": "Passer en mode clair",
      "style-papetche": "Style : papetche",
      "style-sobre": "Style : sobre",
      "style-titre": "Passer du style papetche (couleurs, ombres) à un style sobre et carré, et inversement",
      "avis-limite": "<b>Pas toujours parfait.</b> Selon la complexité de la symbologie, le résultat peut demander une retouche. Le rapport dit ce qui n'a pas été converti, et l'outil s'améliore à chaque version (voir les <a href=\"#nouveautes\">nouveautés</a>). Une conversion ratée, ou réussie ? <a href=\"#contribuer\">Envoyez-la</a> pour aider à l'entraîner.",
      "avis-qgis": "<b>Bientôt :</b> l'extension QGIS dans le gestionnaire d'extensions de QGIS, pour importer un .lyrx ou exporter une couche sans quitter QGIS.",
      "nouveautes-titre": "Nouveautés",
      "nouveautes-intro": "Ce qui change à chaque version, et ce qui a été ajouté au modèle neutre et aux catalogues de correspondances.",
      "a-venir": "À venir",
      "a-venir-texte": "L'extension QGIS publiée dans le gestionnaire d'extensions de QGIS, et de nouvelles correspondances à chaque version.",
      "versions-anciennes": "Versions précédentes",
      "ajout-modele": "Modèle neutre : +{n} lignes",
      "ajout-catalogues": "Catalogues : +{n} lignes",
      "ajout-regles": "+{n} règles de correspondance",
      "ajout-aucun": "Sans changement du modèle ni des catalogues",
      "sous-titre": "Symbologies ArcGIS Pro <b>.lyrx</b> ⇄ QGIS <b>.qlr</b>, dans les deux sens.",
      "preface-1": "Dans nos métiers, l'<strong>interopérabilité</strong> ne devrait pas être un argument de vente, encore moins une arme pour garder ses clients. Ingénieurs, géomaticiens, spécialistes de l'environnement : nous devons communiquer et partager notre travail. Passer une carte d'un logiciel à l'autre sans en perdre le sens, c'est ce qui rend cette collaboration possible.",
      "preface-2": "lyrx2qlr est gratuit, et il dit honnêtement ce qu'il n'a pas su convertir.",
      "depot-zone": "Déposer des fichiers",
      "depot-grand": "Déposez vos fichiers ici",
      "depot-ou": "ou ",
      "depot-choisir": "choisissez-les",
      "depot-formats": ".lyrx → .qlr &nbsp;·&nbsp; .qlr ou .qml → .lyrx &nbsp;·&nbsp; plusieurs fichiers à la fois",
      "source-titre": "Garder la source de données",
      "source-aide": "Le fichier produit pointe sur les mêmes données (fichier, GeoPackage ou base Oracle, PostgreSQL, SQL Server), sans mot de passe : le logiciel le demandera. Décochée, seul le nom du jeu de données reste, à reconnecter.",
      "resultats": "Résultats",
      "tout": "Tout télécharger (.zip)",
      "logique-titre": "Comment ça marche",
      "logique-intro": "Une logique simple, pensée pour durer et pour être relue par des géomaticiens.",
      "principe-1": "<b>Un seul code.</b> Cette page, la ligne de commande et l'extension QGIS utilisent le même cœur : mêmes règles, mêmes résultats.",
      "principe-2": "<b>Des règles, pas du code.</b> Les correspondances entre ArcGIS et QGIS sont écrites dans des catalogues lisibles. Améliorer la conversion, c'est ajouter une ligne.",
      "principe-3": "<b>Chez vous.</b> Python tourne dans votre navigateur. Vos fichiers ne sont envoyés nulle part, sauf si vous choisissez de contribuer.",
      "ordi": "💻 Votre ordinateur — rien ne sort d'ici",
      "inverser": "⇄ Inverser le sens",
      "pause": "⏸ Pause",
      "animer": "▶ Animer",
      "modele-nom": "Modèle neutre",
      "modele-sous": "ni ArcGIS, ni QGIS",
      "consulte": "↑ consulte",
      "catalogues-nom": "Catalogues de règles",
      "regles-dans": "règles dans",
      "fichiers-json": "fichiers JSON",
      "rapport-sous": "ce qui n'est pas converti",
      "chiffres-titre": "Construit et testé sur du concret",
      "chiffre-tests": "tests automatiques",
      "chiffre-lyrx": "fichiers <b>.lyrx</b> réels",
      "chiffre-qgis": "fichiers <b>.qlr / .qml</b> réels",
      "chiffre-regles": "règles dans les catalogues",
      "chiffre-arcgis": "fichiers produits <b>relus par ArcGIS Pro</b>",
      "chiffres-texte": "Chaque fichier fait l'aller-retour (ArcGIS → QGIS → ArcGIS, et l'inverse) et doit revenir identique, sauf écart connu et annoncé. Fichiers venant d'Ordnance Survey, des portails de données ouvertes du Royaume-Uni et du Québec, de projets publics et de couches de travail, plus des centaines de symbologies inventées pour chercher les cas limites. Les .lyrx produits sont ouverts, réenregistrés et dessinés par ArcGIS Pro 3.7, à côté de l'original.",
      "chiffres-date": "Chiffres du {date}.",
      "pied-1": "Vos fichiers ne quittent pas votre ordinateur : la conversion se fait dans cet onglet. Seul le bouton « Envoyer » de l'outil « Contribuer » transmet des fichiers, nettoyés et après un aperçu. Les connexions aux bases de données d'entreprise ne sont jamais recopiées.",
      "pied-auteur": "Yoann · géomaticien · <a href=\"https://papetche.ch/\">papetche.ch</a> · code sous licence GPL-3.0",
      // messages de app.js
      "chargement": "Chargement de Python dans le navigateur…",
      "pret": "Prêt. Déposez un ou plusieurs fichiers.",
      "echec-chargement": "Impossible de charger le convertisseur : {erreur}",
      "aucun-fichier": "Aucun fichier .lyrx, .qlr ou .qml dans la sélection.",
      "conversion": "Conversion de {n} fichier(s)…",
      "bilan": "{reussis} fichier(s) converti(s) sur {n}.",
      "echec": "Échec : {erreur}",
      "conversion-impossible": "conversion impossible",
      "telecharger": "Télécharger",
      "rapport-detaille": "Rapport détaillé",
      "version": "Version {v} · Pyodide {p} (Python dans le navigateur)",
      "complet": "Conversion complète.",
      "resume": "{p} perte(s), {a} avertissement(s), {i} info(s).",
      "titre-rapport": "Rapport de conversion — {fichier}",
      "perte": "NON CONVERTI",
      "avertissement": "À VÉRIFIER",
      "info": "INFO",
      "note-rapport": "",
    },
    en: {
      "logo-titre": "Logo: two arrows forming a circle, from lyrx to qlr and from qlr to lyrx",
      "bouton-langue": "Français",
      "bouton-langue-titre": "Lire cette page en français",
      "theme-sombre": "☾ Dark",
      "theme-clair": "☀ Light",
      "theme-sombre-titre": "Switch to dark mode",
      "theme-clair-titre": "Switch to light mode",
      "style-papetche": "Style: papetche",
      "style-sobre": "Style: plain",
      "style-titre": "Switch between the papetche style (colours, shadows) and a plain, square style",
      "avis-limite": "<b>Not always perfect.</b> Depending on how complex the symbology is, the result may need a touch-up. The report lists what could not be converted, and the tool improves with every version (see <a href=\"#nouveautes\">what's new</a>). A failed, or successful, conversion? <a href=\"#contribuer\">Send it</a> to help train it.",
      "avis-qgis": "<b>Coming soon:</b> the QGIS plugin in the QGIS plugin manager, to import a .lyrx or export a layer without leaving QGIS.",
      "nouveautes-titre": "What's new",
      "nouveautes-intro": "What changes with each version, and what was added to the neutral model and to the matching catalogues.",
      "a-venir": "Coming next",
      "a-venir-texte": "The QGIS plugin published in the QGIS plugin manager, and new matches with every version.",
      "versions-anciennes": "Earlier versions",
      "ajout-modele": "Neutral model: +{n} lines",
      "ajout-catalogues": "Catalogues: +{n} lines",
      "ajout-regles": "+{n} matching rules",
      "ajout-aucun": "No change to the model or the catalogues",
      "sous-titre": "ArcGIS Pro <b>.lyrx</b> ⇄ QGIS <b>.qlr</b> symbology, both ways.",
      "preface-1": "In our fields, <strong>interoperability</strong> should not be a sales pitch, let alone a way to lock customers in. Engineers, GIS specialists, environmental scientists: we need to communicate and share our work. Moving a map from one software to another without losing its meaning is what makes that collaboration possible.",
      "preface-2": "lyrx2qlr is free, and it tells you honestly what it could not convert.",
      "depot-zone": "Drop files",
      "depot-grand": "Drop your files here",
      "depot-ou": "or ",
      "depot-choisir": "browse",
      "depot-formats": ".lyrx → .qlr &nbsp;·&nbsp; .qlr or .qml → .lyrx &nbsp;·&nbsp; several files at once",
      "source-titre": "Keep the data source",
      "source-aide": "The output file points to the same data (file, GeoPackage or Oracle, PostgreSQL, SQL Server database), without the password: the software will ask for it. Unchecked, only the dataset name is kept, to be reconnected.",
      "resultats": "Results",
      "tout": "Download all (.zip)",
      "logique-titre": "How it works",
      "logique-intro": "Simple logic, built to last and to be reviewed by GIS professionals.",
      "principe-1": "<b>One codebase.</b> This page, the command line and the QGIS plugin share the same core: same rules, same results.",
      "principe-2": "<b>Rules, not code.</b> The ArcGIS ⇄ QGIS mappings are written in readable catalogues. Improving the conversion means adding a line.",
      "principe-3": "<b>On your machine.</b> Python runs in your browser. Your files are not sent anywhere, unless you choose to contribute.",
      "ordi": "💻 Your computer — nothing leaves it",
      "inverser": "⇄ Reverse direction",
      "pause": "⏸ Pause",
      "animer": "▶ Play",
      "modele-nom": "Neutral model",
      "modele-sous": "neither ArcGIS nor QGIS",
      "consulte": "↑ looks up",
      "catalogues-nom": "Rule catalogues",
      "regles-dans": "rules in",
      "fichiers-json": "JSON files",
      "rapport-sous": "what was not converted",
      "chiffres-titre": "Built and tested on real files",
      "chiffre-tests": "automated tests",
      "chiffre-lyrx": "real <b>.lyrx</b> files",
      "chiffre-qgis": "real <b>.qlr / .qml</b> files",
      "chiffre-regles": "rules in the catalogues",
      "chiffre-arcgis": "output files <b>re-read by ArcGIS Pro</b>",
      "chiffres-texte": "Every file makes the round trip (ArcGIS → QGIS → ArcGIS, and back) and must come back identical, except for known, reported differences. Files from Ordnance Survey, the UK and Québec open data portals, public projects and working layers, plus hundreds of generated symbologies to hunt for edge cases. The .lyrx files produced are opened, re-saved and drawn by ArcGIS Pro 3.7, next to the original.",
      "chiffres-date": "Figures as of {date}.",
      "pied-1": "Your files never leave your computer: the conversion runs in this tab. Only the “Send” button of the “Contribute” panel transmits files, cleaned and after a preview. Enterprise database connections are never copied.",
      "pied-auteur": "Yoann · GIS specialist · <a href=\"https://papetche.ch/\">papetche.ch</a> · code licensed under GPL-3.0",
      "chargement": "Loading Python in your browser…",
      "pret": "Ready. Drop one or more files.",
      "echec-chargement": "Could not load the converter: {erreur}",
      "aucun-fichier": "No .lyrx, .qlr or .qml file in the selection.",
      "conversion": "Converting {n} file(s)…",
      "bilan": "{reussis} of {n} file(s) converted.",
      "echec": "Failed: {erreur}",
      "conversion-impossible": "conversion not possible",
      "telecharger": "Download",
      "rapport-detaille": "Detailed report",
      "version": "Version {v} · Pyodide {p} (Python in the browser)",
      "complet": "Complete conversion.",
      "resume": "{p} loss(es), {a} warning(s), {i} note(s).",
      "titre-rapport": "Conversion report — {fichier}",
      "perte": "NOT CONVERTED",
      "avertissement": "TO CHECK",
      "info": "NOTE",
      "note-rapport": "The detailed messages are in French for now.",
    },
  };

  const lire = () => { try { return localStorage.getItem("lyrx2qlr-langue"); } catch { return null; } };
  const garder = l => { try { localStorage.setItem("lyrx2qlr-langue", l); } catch { /* navigation privée */ } };

  // L'adresse fait foi : « / » est la page française, « ?lang=en » la page anglaise (une adresse par
  // langue, pour les moteurs de recherche). Le dernier choix du visiteur est repris sur « / » ; la
  // langue du navigateur ne change jamais la page d'elle-même : elle fait seulement apparaître une
  // invitation vers la version anglaise.
  const demandee = new URLSearchParams(location.search).get("lang");
  let langue = TEXTES[demandee] ? demandee : lire() === "en" ? "en" : "fr";
  const francophone = (navigator.languages || [navigator.language || "fr"]).some(l => /^fr\b/i.test(l));

  const ADRESSE = { fr: "https://lyrx2qlr.papetche.ch/", en: "https://lyrx2qlr.papetche.ch/?lang=en" };
  const META_EN = {
    description: "Convert ArcGIS Pro (.lyrx) symbology to QGIS (.qlr) and back, in your browser. One codebase, readable rules, and your files stay on your machine.",
    "og:description": "Converts ArcGIS Pro symbology (.lyrx) to QGIS layer files (.qlr), and back. Free, in the browser, with a report of what could not be converted.",
    "og:image:alt": "lyrx2qlr: ArcGIS Pro .lyrx ⇄ QGIS .qlr symbology",
  };
  const balise = nom => document.querySelector(`meta[name="${nom}"], meta[property="${nom}"]`);
  const META_FR = Object.fromEntries(Object.keys(META_EN).map(n => [n, balise(n)?.getAttribute("content")]));

  // Balises lues par les moteurs de recherche et les réseaux sociaux, selon la langue affichée.
  function appliquerTete() {
    const canonique = document.querySelector('link[rel="canonical"]');
    if (canonique) canonique.href = ADRESSE[langue];
    const url = balise("og:url");
    if (url) url.setAttribute("content", ADRESSE[langue]);
    const textes = langue === "en" ? META_EN : META_FR;
    Object.entries(textes).forEach(([n, v]) => { if (v != null) balise(n)?.setAttribute("content", v); });
    const locale = balise("og:locale"), autre = balise("og:locale:alternate");
    if (locale) locale.setAttribute("content", langue === "en" ? "en_GB" : "fr_CH");
    if (autre) autre.setAttribute("content", langue === "en" ? "fr_CH" : "en_GB");
    const invitation = document.getElementById("invitation-langue");
    if (invitation) invitation.hidden = langue === "en" || francophone;
  }

  // Retour sur « / » avec l'anglais choisi la dernière fois : l'adresse suit la page affichée.
  if (langue === "en" && demandee !== "en") {
    const adresse = new URL(location.href);
    adresse.searchParams.set("lang", "en");
    history.replaceState(null, "", adresse);
  }

  const abonnes = [];

  function t(cle, valeurs = {}) {
    const brut = TEXTES[langue][cle] ?? TEXTES.fr[cle] ?? cle;
    return brut.replace(/\{(\w+)\}/g, (_, n) => (n in valeurs ? valeurs[n] : `{${n}}`));
  }

  // Les textes viennent tous du dictionnaire ci-dessus (jamais d'un fichier déposé) : innerHTML est sûr ici.
  function appliquer() {
    document.documentElement.lang = langue;
    appliquerTete();
    document.querySelectorAll("[data-i18n]").forEach(el => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll("[data-i18n-html]").forEach(el => { el.innerHTML = t(el.dataset.i18nHtml); });
    document.querySelectorAll("[data-i18n-attr]").forEach(el => {
      el.dataset.i18nAttr.split(";").forEach(paire => {
        const [attr, cle] = paire.split(":");
        el.setAttribute(attr, t(cle));
      });
    });
    const bouton = document.getElementById("langue");
    if (bouton) bouton.lang = langue === "fr" ? "en" : "fr";
    abonnes.forEach(f => f(langue));
  }

  function changer(l) {
    if (!TEXTES[l] || l === langue) return;
    langue = l;
    garder(l);
    const adresse = new URL(location.href);
    if (l === "fr") adresse.searchParams.delete("lang"); else adresse.searchParams.set("lang", l);
    history.replaceState(null, "", adresse);
    appliquer();
  }

  window.I18N = {
    t,
    get langue() { return langue; },
    get locale() { return langue === "fr" ? "fr-CH" : "en-GB"; },
    surChangement: f => abonnes.push(f),
    // Textes propres à un autre script de la page (par exemple contribuer.js), chargé avant l'affichage
    ajouter: dico => Object.keys(dico).forEach(l => Object.assign(TEXTES[l] || (TEXTES[l] = {}), dico[l])),
    changer,
  };

  document.addEventListener("DOMContentLoaded", () => {
    const bouton = document.getElementById("langue");
    if (bouton) bouton.addEventListener("click", () => changer(langue === "fr" ? "en" : "fr"));
    appliquer();
  });
})();
