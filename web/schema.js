// Schéma « Comment ça marche » et compteurs de la page. Indépendant du convertisseur (app.js).
// Les textes suivent la langue choisie (langue.js).
"use strict";

(() => {
  const calme = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const I = window.I18N;
  const en = () => I.langue === "en";

  // --- sens de conversion ----------------------------------------------------------------------
  const SENS = {
    arcgis: { source: ".lyrx", "source-app": "ArcGIS Pro", cible: ".qlr", "cible-app": "QGIS", lecteur: "cim", ecrivain: "qgis" },
    qgis: { source: ".qlr / .qml", "source-app": "QGIS", cible: ".lyrx", "cible-app": "ArcGIS Pro", lecteur: "qgis", ecrivain: "cim" },
  };
  const FORMAT = { fr: { cim: "JSON « CIM »", qgis: "XML QGIS" }, en: { cim: "CIM JSON", qgis: "QGIS XML" } };
  const format = f => FORMAT[I.langue][f];
  let sens = "arcgis";

  const textes = () => {
    const s = SENS[sens], lu = format(s.lecteur), ecrit = format(s.ecrivain);
    if (en()) return {
      source: [`The input file: ${s.source}`,
        `A ${s["source-app"]} symbology: symbols, classes, labels, filters, scales. You drop it on the page; it is read in this tab, never uploaded.`],
      lire: ["The reader",
        `The reader walks through the ${lu} and translates every setting into a neutral vocabulary, following the catalogues. It never guesses: whatever it does not know is noted for the report.`],
      modele: ["The neutral model",
        "A description shared by both programs: lengths in points, colours as red-green-blue-alpha, angles in degrees, scales as denominators. Because everything goes through it, one reader and one writer per format are enough, in both directions."],
      ecrire: ["The writer",
        `The writer produces the ${ecrit} from the neutral model, again following the catalogues. A font that only exists in ArcGIS, a unit the other program does not know: every substitution is reported.`],
      cible: [`The output file: ${s.cible}`,
        `Ready to open in ${s["cible-app"]}. Every tested file makes the full round trip and must come back identical, except for known, reported differences.`],
      catalogues: ["The rule catalogues",
        "All the “ArcGIS ⇄ QGIS” knowledge lives in readable JSON files: line caps, symbol types, placements, fonts, expressions… The code only applies these rules. Fixing or adding a mapping means adding a line, without touching the program."],
      rapport: ["The report",
        "Nothing is lost silently. What could not be converted is listed as “NOT CONVERTED”, what was approximated as “TO CHECK”, the rest as “NOTE”. You know exactly what to check."],
    };
    return {
      source: [`Le fichier de départ : ${s.source}`,
        `Une symbologie ${s["source-app"]} : symboles, classes, étiquettes, filtres, échelles. Vous le déposez dans la page ; il est lu dans cet onglet, sans être envoyé.`],
      lire: ["Le reader",
        `Le reader parcourt le ${lu} et traduit chaque réglage dans un vocabulaire neutre, en suivant les catalogues. Il ne devine rien : ce qu'il ne connaît pas est noté pour le rapport.`],
      modele: ["Le modèle neutre",
        "Une description commune aux deux logiciels : longueurs en points, couleurs en rouge-vert-bleu-opacité, angles en degrés, échelles en dénominateur. Comme tout passe par lui, un seul reader et un seul writer par format suffisent, dans les deux sens."],
      ecrire: ["Le writer",
        `Le writer produit le ${ecrit} à partir du modèle neutre, toujours d'après les catalogues. Une police propre à ArcGIS, une unité inconnue de l'autre logiciel : tout remplacement est annoncé.`],
      cible: [`Le fichier produit : ${s.cible}`,
        `Prêt à ouvrir dans ${s["cible-app"]}. Chaque fichier testé fait l'aller-retour complet et doit revenir identique, sauf écart connu et annoncé.`],
      catalogues: ["Les catalogues de règles",
        "Toute la connaissance « ArcGIS ⇄ QGIS » est rangée dans des fichiers JSON lisibles : extrémités de lignes, types de symboles, placements, polices, expressions… Le code ne fait qu'appliquer ces règles. Corriger ou compléter une correspondance, c'est ajouter une ligne, sans toucher au programme."],
      rapport: ["Le rapport",
        "Rien ne se perd en silence. Ce qui n'a pas pu être converti est listé en « NON CONVERTI », ce qui a été approché en « À VÉRIFIER », le reste en « INFO ». Vous savez exactement quoi contrôler."],
    };
  };

  // Exemples réels tirés des catalogues : [ArcGIS, QGIS, quoi (fr), quoi (en)].
  const REGLES = [
    ["Round", "round", "extrémité de ligne", "line cap"],
    ["CIMSolidStroke", "SimpleLine", "trait", "stroke"],
    ["CIMHatchFill", "LinePatternFill", "hachures", "hatching"],
    ["Miter", "miter", "jointure", "line join"],
    ["CIMCharacterMarker", "FontMarker", "marqueur de police", "font marker"],
    ["[NOM]", "\"NOM\"", "expression", "expression"],
  ];

  const schema = document.getElementById("schema");
  if (!schema) return;
  const etapes = [...schema.querySelectorAll(".etape")];
  const parNom = Object.fromEntries(etapes.map(e => [e.dataset.etape, e]));
  const ordre = ["source", "lire", "modele", "ecrire", "cible", "rapport"];
  const titre = document.getElementById("explication-titre");
  const texte = document.getElementById("explication-texte");
  const boutonSens = document.getElementById("sens");
  const boutonLecture = document.getElementById("lecture");
  const regle = document.getElementById("regle");

  let indice = 0, nRegle = 0, minuterie = null;

  function montrer(nom) {
    etapes.forEach(e => e.classList.toggle("actif", e.dataset.etape === nom));
    parNom.catalogues.classList.toggle("consulte", nom === "lire" || nom === "ecrire");
    const [t, p] = textes()[nom];
    titre.textContent = t;
    texte.textContent = p;
  }

  function etapeActive() {
    const actif = etapes.find(e => e.classList.contains("actif"));
    return actif ? actif.dataset.etape : "source";
  }

  function afficherRegle() {
    const [a, q, quoiFr, quoiEn] = REGLES[nRegle % REGLES.length];
    const [gauche, droite] = sens === "arcgis" ? [a, q] : [q, a];
    regle.classList.add("cache");
    setTimeout(() => {
      regle.replaceChildren();
      const c1 = document.createElement("code"); c1.textContent = gauche;
      const c2 = document.createElement("code"); c2.textContent = droite;
      regle.append(c1, " → ", c2);
      regle.title = en() ? quoiEn : quoiFr;
      regle.classList.remove("cache");
    }, calme ? 0 : 250);
  }

  function pas() {
    montrer(ordre[indice]);
    if (ordre[indice] === "lire" || ordre[indice] === "ecrire") { nRegle++; afficherRegle(); }
    indice = (indice + 1) % ordre.length;
  }

  function jouer(oui) {
    clearInterval(minuterie);
    minuterie = oui ? setInterval(pas, 2600) : null;
    boutonLecture.textContent = I.t(oui ? "pause" : "animer");
    boutonLecture.setAttribute("aria-pressed", String(oui));
  }

  function appliquerSens() {
    const s = SENS[sens];
    schema.querySelectorAll("[data-sens-texte]").forEach(el => {
      const cle = el.dataset.sensTexte;
      el.textContent = cle === "lecteur" || cle === "ecrivain" ? format(s[cle]) : s[cle];
    });
    boutonSens.setAttribute("aria-pressed", String(sens === "qgis"));
    afficherRegle();
  }

  etapes.forEach(e => e.addEventListener("click", () => {
    jouer(false);
    indice = ordre.indexOf(e.dataset.etape) + 1;
    montrer(e.dataset.etape);
  }));
  boutonLecture.addEventListener("click", () => jouer(!minuterie));
  boutonSens.addEventListener("click", () => {
    sens = sens === "arcgis" ? "qgis" : "arcgis";
    appliquerSens();
    montrer(etapeActive());
  });

  appliquerSens();
  pas();
  jouer(!calme);

  // --- compteurs (web/chiffres.json, produit par outils/chiffres.py) ----------------------------
  const nombre = v => Number(v).toLocaleString(I.locale);

  const animer = (el, cible) => {
    const fin = () => { el.textContent = nombre(cible); el.dataset.fini = "1"; };
    if (calme) { fin(); return; }
    const debut = performance.now(), duree = 1200;
    const tic = t => {
      const x = Math.min(1, (t - debut) / duree);
      el.textContent = nombre(Math.round(cible * (1 - Math.pow(1 - x, 3))));
      if (x < 1) requestAnimationFrame(tic); else fin();
    };
    requestAnimationFrame(tic);
  };

  let dateChiffres = null;
  function afficherChiffres() {
    document.querySelectorAll("[data-chiffre]").forEach(el => {
      const grand = el.classList.contains("nombre");
      if (!grand && el.dataset.valeur) el.textContent = el.dataset.valeur;
      else if (grand && el.dataset.fini) el.textContent = nombre(el.dataset.valeur || el.textContent);
    });
    if (!dateChiffres) return;
    const d = new Date(dateChiffres + "T12:00:00");
    document.getElementById("chiffres-date").textContent =
      I.t("chiffres-date", { date: d.toLocaleDateString(I.locale, { day: "numeric", month: "long", year: "numeric" }) });
  }

  I.surChangement(() => {
    appliquerSens();
    montrer(etapeActive());
    boutonLecture.textContent = I.t(minuterie ? "pause" : "animer");
    afficherChiffres();
  });

  fetch("chiffres.json", { cache: "no-cache" })
    .then(r => (r.ok ? r.json() : null))
    .catch(() => null)
    .then(chiffres => {
      const elements = [...document.querySelectorAll("[data-chiffre]")];
      if (chiffres) {
        elements.forEach(el => { const v = chiffres[el.dataset.chiffre]; if (typeof v === "number") el.dataset.valeur = v; });
        dateChiffres = chiffres.date || null;
      }
      afficherChiffres();
      const vus = new IntersectionObserver(entrees => entrees.forEach(e => {
        if (!e.isIntersecting) return;
        vus.unobserve(e.target);
        animer(e.target, Number(e.target.dataset.valeur || e.target.textContent));
      }), { threshold: 0.4 });
      elements.filter(el => el.classList.contains("nombre")).forEach(el => vus.observe(el));
    });
})();
