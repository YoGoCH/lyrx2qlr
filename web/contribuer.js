// Outil « Contribuer » : panneau latéral pour envoyer un exemple qui aide à entraîner lyrx2qlr.
// Les fichiers sont nettoyés dans le navigateur par le cœur Python (lyrx2qlr.contribution), un
// aperçu montre ce qui part et ce qui a été retiré, et rien n'est transmis sans le bouton « Envoyer ».
// Chargé après langue.js et avant app.js (qui fournit window.LYRX2QLR.passerelle()).
"use strict";

(() => {
  const I = window.I18N;
  const ADRESSE_ENVOI = "/api/contribuer";

  I.ajouter({
    fr: {
      "contrib-onglet": "Contribuer",
      "contrib-onglet-titre": "Aider à améliorer lyrx2qlr : envoyer un exemple, bon ou mauvais",
      "contrib-titre": "Contribuer",
      "contrib-fermer": "Fermer",
      "contrib-intro": "Aidez à entraîner lyrx2qlr : un exemple réel, qu'il soit bien ou mal converti, devient un cas de test et améliore les catalogues de correspondances.",
      "contrib-type": "1. Ce que vous envoyez",
      "type-a_corriger": "Conversion à corriger",
      "type-a_corriger-aide": "Le résultat est faux ou incomplet : il servira d'entraînement correctif.",
      "type-bon": "Bonne conversion",
      "type-bon-aide": "Le résultat est juste : il sera gardé comme exemple de référence.",
      "type-paire": "Paire de référence",
      "type-paire-aide": "Le même rendu fait à la main dans ArcGIS Pro (.lyrx) et dans QGIS (.qlr) : le modèle à atteindre.",
      "type-remarque": "Idée ou remarque",
      "type-remarque-aide": "Une correspondance manquante, un cas à prendre en charge, un avis.",
      "contrib-fichiers": "2. Vos fichiers",
      "aucun-fichier-choisi": "aucun fichier",
      "contrib-depart": "Fichier de départ :",
      "vers-qgis": "(vers QGIS)",
      "vers-arcgis": "(vers ArcGIS)",
      "contrib-fichiers-aide": "Un seul fichier suffit. Avec les deux, l'autre est le résultat attendu.",
      "contrib-retirer": "Retirer {nom}",
      "contrib-problemes": "3. Ce qui ne va pas",
      "pb-couleurs": "Couleurs", "pb-epaisseurs": "Épaisseurs, tailles", "pb-symboles": "Symboles, marqueurs",
      "pb-remplissages": "Remplissages, hachures", "pb-etiquettes": "Étiquettes", "pb-echelles": "Échelles de visibilité",
      "pb-classes": "Classes, catégories", "pb-expressions": "Expressions, filtres", "pb-source": "Source de données",
      "pb-ouverture": "Ne s'ouvre pas", "pb-autre": "Autre",
      "contrib-commentaire": "Commentaire",
      "contrib-commentaire-exemple": "Par exemple : les étiquettes sont décalées vers le haut, les hachures sont trop serrées…",
      "contrib-arcgis": "Version d'ArcGIS Pro",
      "contrib-qgisv": "Version de QGIS",
      "contrib-licence": "Utilisation",
      "licence-tests": "Pour les tests de lyrx2qlr seulement, jamais publié",
      "licence-corpus": "Peut rejoindre le corpus public d'exemples (licence CC-BY 4.0)",
      "contrib-contact": "E-mail, facultatif (pour vous recontacter)",
      "contrib-preparer": "Préparer l'aperçu",
      "apercu-titre": "Ce qui partira",
      "apercu-fichier": "{nom} ({taille}) — {role}",
      "role-depart": "fichier de départ",
      "role-attendu": "résultat attendu",
      "apercu-retire": "Retiré : {liste}",
      "apercu-rien": "Rien à retirer",
      "apercu-commentaire": "Commentaire — retiré : {liste}",
      "apercu-conversion": "Notre conversion de {entree}, jointe au colis avec son rapport : {resume}",
      "apercu-conversion-echec": "Notre conversion de {entree} a échoué ({erreur}) : le rapport est joint.",
      "apercu-taille": "Colis de {taille} en tout.",
      "contrib-accord": "J'accepte d'envoyer ces fichiers nettoyés à lyrx2qlr, pour l'usage choisi ci-dessus. Je peux en demander la suppression.",
      "contrib-envoyer": "Envoyer",
      "contrib-telecharger": "Télécharger le colis",
      "contrib-confidentialite": "Avant l'aperçu, votre navigateur retire des fichiers et du commentaire les mots de passe, jetons, noms d'utilisateur, de serveurs et de bases, adresses e-mail et dossiers personnels. Les colis sont gardés hors du site, au plus 12 mois s'ils ne sont pas retenus.",
      "contrib-attente-python": "Python se charge encore dans la page, un instant…",
      "contrib-preparation": "Nettoyage et préparation du colis…",
      "contrib-modifie": "Le formulaire a changé : préparez de nouveau l'aperçu.",
      "contrib-envoi": "Envoi…",
      "contrib-merci": "Merci ! Contribution reçue sous le numéro {numero}.",
      "contrib-indisponible": "L'envoi n'est pas possible pour l'instant ({raison}). Vous pouvez télécharger le colis et le garder ; réessayez plus tard.",
      "contrib-trop": "Trop d'envois depuis votre connexion : réessayez dans une heure.",
      "contrib-refuse": "Envoi refusé par le serveur : {erreur} Vous pouvez aussi télécharger le colis.",
      "contrib-telecharge": "Colis téléchargé : {nom}.",
      "err-type": "Choisissez de quelle sorte de contribution il s'agit.",
      "err-contact": "L'adresse e-mail de contact ne semble pas valable (elle est facultative).",
      "err-extension": "« {nom} » : seuls les fichiers .lyrx, .qlr et .qml sont acceptés.",
      "err-double": "« {nom} » est joint deux fois.",
      "err-texte": "« {nom} » n'est pas un texte lisible (.lyrx, .qlr ou .qml attendu).",
      "err-taille": "Les fichiers dépassent 4 Mo en tout : retirez les images intégrées ou envoyez-les séparément.",
      "err-paire": "Une paire de référence demande un .lyrx et un .qlr (ou .qml).",
      "err-depart": "Joignez au moins le fichier de départ.",
      "err-remarque": "Écrivez votre remarque dans le commentaire.",
      "err-probleme": "Dites ce qui ne va pas : cochez un problème ou écrivez un commentaire.",
      "contribuer-resultat": "Contribuer",
      "contribuer-resultat-titre": "Envoyer ce fichier pour améliorer lyrx2qlr (bon ou mauvais résultat)",
    },
    en: {
      "contrib-onglet": "Contribute",
      "contrib-onglet-titre": "Help improve lyrx2qlr: send an example, good or bad",
      "contrib-titre": "Contribute",
      "contrib-fermer": "Close",
      "contrib-intro": "Help train lyrx2qlr: a real example, well or badly converted, becomes a test case and improves the mapping catalogues.",
      "contrib-type": "1. What you are sending",
      "type-a_corriger": "Conversion to fix",
      "type-a_corriger-aide": "The result is wrong or incomplete: it will be used for corrective training.",
      "type-bon": "Good conversion",
      "type-bon-aide": "The result is right: it will be kept as a reference example.",
      "type-paire": "Reference pair",
      "type-paire-aide": "The same rendering made by hand in ArcGIS Pro (.lyrx) and in QGIS (.qlr): the target to reach.",
      "type-remarque": "Idea or remark",
      "type-remarque-aide": "A missing mapping, a case to support, an opinion.",
      "contrib-fichiers": "2. Your files",
      "aucun-fichier-choisi": "no file",
      "contrib-depart": "Starting file:",
      "vers-qgis": "(to QGIS)",
      "vers-arcgis": "(to ArcGIS)",
      "contrib-fichiers-aide": "One file is enough. With both, the other one is the expected result.",
      "contrib-retirer": "Remove {nom}",
      "contrib-problemes": "3. What is wrong",
      "pb-couleurs": "Colours", "pb-epaisseurs": "Widths, sizes", "pb-symboles": "Symbols, markers",
      "pb-remplissages": "Fills, hatching", "pb-etiquettes": "Labels", "pb-echelles": "Visibility scales",
      "pb-classes": "Classes, categories", "pb-expressions": "Expressions, filters", "pb-source": "Data source",
      "pb-ouverture": "Does not open", "pb-autre": "Other",
      "contrib-commentaire": "Comment",
      "contrib-commentaire-exemple": "For example: the labels are shifted upwards, the hatching is too dense…",
      "contrib-arcgis": "ArcGIS Pro version",
      "contrib-qgisv": "QGIS version",
      "contrib-licence": "Use",
      "licence-tests": "For lyrx2qlr tests only, never published",
      "licence-corpus": "May join the public example corpus (CC-BY 4.0 licence)",
      "contrib-contact": "E-mail, optional (to get back to you)",
      "contrib-preparer": "Prepare the preview",
      "apercu-titre": "What will be sent",
      "apercu-fichier": "{nom} ({taille}) — {role}",
      "role-depart": "starting file",
      "role-attendu": "expected result",
      "apercu-retire": "Removed: {liste}",
      "apercu-rien": "Nothing to remove",
      "apercu-commentaire": "Comment — removed: {liste}",
      "apercu-conversion": "Our conversion of {entree}, added to the package with its report: {resume}",
      "apercu-conversion-echec": "Our conversion of {entree} failed ({erreur}): the report is included.",
      "apercu-taille": "Package of {taille} in total.",
      "contrib-accord": "I agree to send these cleaned files to lyrx2qlr, for the use chosen above. I can ask for them to be deleted.",
      "contrib-envoyer": "Send",
      "contrib-telecharger": "Download the package",
      "contrib-confidentialite": "Before the preview, your browser removes passwords, tokens, user, server and database names, e-mail addresses and personal folders from the files and the comment. Packages are kept outside the website, for 12 months at most if not used.",
      "contrib-attente-python": "Python is still loading in the page, one moment…",
      "contrib-preparation": "Cleaning and preparing the package…",
      "contrib-modifie": "The form has changed: prepare the preview again.",
      "contrib-envoi": "Sending…",
      "contrib-merci": "Thank you! Contribution received as number {numero}.",
      "contrib-indisponible": "Sending is not possible right now ({raison}). You can download the package and keep it; try again later.",
      "contrib-trop": "Too many submissions from your connection: try again in an hour.",
      "contrib-refuse": "Sending refused by the server: {erreur} You can also download the package.",
      "contrib-telecharge": "Package downloaded: {nom}.",
      "err-type": "Choose what kind of contribution this is.",
      "err-contact": "The contact e-mail address does not look valid (it is optional).",
      "err-extension": "“{nom}”: only .lyrx, .qlr and .qml files are accepted.",
      "err-double": "“{nom}” is attached twice.",
      "err-texte": "“{nom}” is not readable text (.lyrx, .qlr or .qml expected).",
      "err-taille": "The files exceed 4 MB in total: remove embedded images or send them separately.",
      "err-paire": "A reference pair needs a .lyrx and a .qlr (or .qml).",
      "err-depart": "Attach at least the starting file.",
      "err-remarque": "Write your remark in the comment.",
      "err-probleme": "Say what is wrong: tick a problem or write a comment.",
      "contribuer-resultat": "Contribute",
      "contribuer-resultat-titre": "Send this file to help improve lyrx2qlr (good or bad result)",
    },
  });

  const RETRAITS_EN = {
    "mot de passe, jeton ou clé": "password, token or key", "nom d'utilisateur": "user name",
    "nom de serveur": "server name", "nom de base de données": "database name", "adresse e-mail": "e-mail address",
    "dossier personnel": "personal folder", "serveur d'un chemin réseau": "network path server",
  };

  const $ = id => document.getElementById(id);
  const fichiers = { lyrx: null, qgis: null };
  let colis = null;       // { octets, apercu } : dernier colis préparé
  let dernierEtat = null; // [clé, valeurs, classe], réaffiché si la langue change
  let retourFocus = null;

  function dire(cle, valeurs = {}, classe = "") {
    dernierEtat = cle ? [cle, valeurs, classe] : null;
    const el = $("etat-contribution");
    el.textContent = cle ? I.t(cle, valeurs) : "";
    el.className = "etat-contrib" + (classe ? " " + classe : "");
  }

  const taille = n => n < 1024 ? `${n} o` : n < 1048576 ? `${(n / 1024).toLocaleString(I.locale, { maximumFractionDigits: 1 })} ko`
    : `${(n / 1048576).toLocaleString(I.locale, { maximumFractionDigits: 1 })} Mo`;
  const tailleLue = n => I.langue === "en" ? taille(n).replace(" o", " B").replace(" ko", " kB").replace(" Mo", " MB") : taille(n);

  // --- ouvrir / fermer le panneau -------------------------------------------------------
  function ouvrir(options = {}) {
    const panneau = $("panneau-contribuer");
    if (options.fichier) placerFichier(options.fichier);
    if (options.type) choisirType(options.type);
    if (panneau.hidden) {
      retourFocus = document.activeElement;
      panneau.hidden = false;
      $("voile-contribuer").hidden = false;
      document.body.classList.add("panneau-ouvert");
      $("onglet-contribuer").setAttribute("aria-expanded", "true");
      requestAnimationFrame(() => panneau.classList.add("ouvert"));
    }
    const cible = options.type ? $("contrib-commentaire") : panneau.querySelector('input[name="type"]:checked') || panneau.querySelector('input[name="type"]');
    setTimeout(() => cible.focus(), 30);
  }

  function fermer() {
    const panneau = $("panneau-contribuer");
    if (panneau.hidden) return;
    panneau.classList.remove("ouvert");
    panneau.hidden = true;
    $("voile-contribuer").hidden = true;
    document.body.classList.remove("panneau-ouvert");
    $("onglet-contribuer").setAttribute("aria-expanded", "false");
    if (location.hash === "#contribuer") history.replaceState(null, "", location.pathname + location.search);
    (retourFocus && document.contains(retourFocus) ? retourFocus : $("onglet-contribuer")).focus();
  }

  // Le focus reste dans le panneau tant qu'il est ouvert (Tab et Maj+Tab font le tour)
  function garderFocus(e) {
    if (e.key === "Escape") { e.preventDefault(); fermer(); return; }
    if (e.key !== "Tab") return;
    const elements = [...$("panneau-contribuer").querySelectorAll("button, input, textarea, select, a[href]")]
      .filter(el => !el.disabled && el.offsetParent !== null && el.tabIndex !== -1);
    if (!elements.length) return;
    const [premier, dernier] = [elements[0], elements[elements.length - 1]];
    if (e.shiftKey && document.activeElement === premier) { e.preventDefault(); dernier.focus(); }
    else if (!e.shiftKey && document.activeElement === dernier) { e.preventDefault(); premier.focus(); }
  }

  // --- formulaire ---------------------------------------------------------------------------
  function choisirType(type) {
    const radio = document.querySelector(`input[name="type"][value="${type}"]`);
    if (radio) { radio.checked = true; majFormulaire(); }
  }

  function placerFichier(fichier) {
    const cle = /\.lyrx$/i.test(fichier.name) ? "lyrx" : /\.(qlr|qml)$/i.test(fichier.name) ? "qgis" : null;
    if (!cle) return;
    fichiers[cle] = fichier;
    if (!fichiers.lyrx || !fichiers.qgis) document.querySelector(`input[name="depart"][value="${cle}"]`).checked = true;
    majFormulaire();
  }

  function majFichiers() {
    ["lyrx", "qgis"].forEach(cle => {
      const nom = $("nom-" + cle);
      const f = fichiers[cle];
      nom.replaceChildren();
      if (!f) {
        nom.dataset.i18n = "aucun-fichier-choisi";
        nom.textContent = I.t("aucun-fichier-choisi");
        nom.closest(".fichier-contrib").classList.remove("rempli");
        return;
      }
      delete nom.dataset.i18n;
      nom.closest(".fichier-contrib").classList.add("rempli");
      nom.append(document.createTextNode(f.name + " "));
      const retirer = document.createElement("button");
      retirer.type = "button";
      retirer.className = "retirer";
      retirer.textContent = "✕";
      retirer.setAttribute("aria-label", I.t("contrib-retirer", { nom: f.name }));
      retirer.addEventListener("click", e => { e.preventDefault(); e.stopPropagation(); fichiers[cle] = null; $("contrib-" + cle).value = ""; majFormulaire(); });
      nom.append(retirer);
    });
    $("choix-depart").hidden = !(fichiers.lyrx && fichiers.qgis);
  }

  function majFormulaire() {
    const type = document.querySelector('input[name="type"]:checked')?.value;
    $("bloc-problemes").hidden = type !== "a_corriger";
    majFichiers();
    invalider();
  }

  // Toute modification après l'aperçu oblige à le refaire : on n'envoie que ce qui a été montré
  function invalider() {
    if (!colis) return;
    colis = null;
    $("apercu-contribution").hidden = true;
    $("contrib-accord").checked = false;
    $("envoyer-contribution").disabled = true;
    dire("contrib-modifie");
  }

  function infos() {
    const type = document.querySelector('input[name="type"]:checked')?.value || "";
    const depart = document.querySelector('input[name="depart"]:checked')?.value;
    const choisi = fichiers.lyrx && fichiers.qgis ? fichiers[depart] : fichiers.lyrx || fichiers.qgis;
    return {
      type,
      problemes: [...document.querySelectorAll('input[name="probleme"]:checked')].map(c => c.value),
      commentaire: $("contrib-commentaire").value,
      depart: choisi ? choisi.name : null,
      logiciels: { arcgis: $("contrib-arcgis").value, qgis: $("contrib-qgisv").value },
      licence: document.querySelector('input[name="licence"]:checked')?.value || "tests",
      contact: $("contrib-contact").value.trim(),
      langue: I.langue,
    };
  }

  async function preparer(e) {
    e.preventDefault();
    const passerelle = window.LYRX2QLR && window.LYRX2QLR.passerelle();
    if (!passerelle) { dire("contrib-attente-python"); return; }
    dire("contrib-preparation");
    const liste = await Promise.all(Object.values(fichiers).filter(Boolean)
      .map(async f => [f.name, new Uint8Array(await f.arrayBuffer())]));
    let reponse;
    try {
      reponse = passerelle.preparer_contribution(JSON.stringify(infos()), liste);
    } catch (err) {
      console.error(err);
      dire("contrib-indisponible", { raison: String(err.message || err).split("\n").pop() }, "erreur");
      return;
    }
    const [octets, texte] = reponse.toJs();
    reponse.destroy();
    const apercu = JSON.parse(texte);
    if (apercu.erreur) {
      dire(apercu.code ? "err-" + apercu.code : "", apercu.valeurs || {}, "erreur");
      if (!apercu.code) $("etat-contribution").textContent = apercu.erreur;
      return;
    }
    colis = { octets, apercu };
    afficherApercu();
    dire("");
    $("apercu-contribution").scrollIntoView({ block: "nearest", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }

  function listeRetraits(retraits) {
    return Object.entries(retraits).map(([nom, n]) => `${I.langue === "en" ? RETRAITS_EN[nom] || nom : nom} ×${n}`).join(", ");
  }

  function afficherApercu() {
    if (!colis) return;
    const a = colis.apercu;
    const ul = $("apercu-liste");
    ul.replaceChildren();
    a.fichiers.forEach(f => {
      const li = document.createElement("li");
      const b = document.createElement("b");
      b.textContent = I.t("apercu-fichier", { nom: f.nom, taille: tailleLue(f.taille), role: I.t("role-" + f.role) });
      const p = document.createElement("span");
      p.className = "petit " + (Object.keys(f.retraits).length ? "retire" : "");
      p.textContent = Object.keys(f.retraits).length ? I.t("apercu-retire", { liste: listeRetraits(f.retraits) }) : I.t("apercu-rien");
      li.append(b, p);
      ul.append(li);
    });
    if (Object.keys(a.retraits_commentaire).length) {
      const li = document.createElement("li");
      li.className = "petit retire";
      li.textContent = I.t("apercu-commentaire", { liste: listeRetraits(a.retraits_commentaire) });
      ul.append(li);
    }
    const c = a.conversion;
    $("apercu-conversion").textContent = [
      c ? (c.reussi ? I.t("apercu-conversion", { entree: c.entree, resume: c.resume }) : I.t("apercu-conversion-echec", { entree: c.entree, erreur: c.erreur })) : "",
      I.t("apercu-taille", { taille: tailleLue(a.taille) }),
    ].filter(Boolean).join(" ");
    $("apercu-contribution").hidden = false;
    $("envoyer-contribution").disabled = !$("contrib-accord").checked;
  }

  async function envoyer() {
    if (!colis || !$("contrib-accord").checked) return;
    // Champ piège rempli : un robot. On fait comme si tout allait bien, sans rien envoyer.
    if ($("contrib-site").value) { dire("contrib-merci", { numero: "—" }, "pret"); return; }
    const bouton = $("envoyer-contribution");
    bouton.disabled = true;
    dire("contrib-envoi");
    try {
      const corps = new Blob([colis.octets], { type: "application/zip" });  // le Blob donne sa taille (Content-Length)
      const r = await fetch(ADRESSE_ENVOI, { method: "POST", headers: { "Content-Type": "application/zip" }, body: corps });
      const d = await r.json().catch(() => ({}));
      if (r.ok && d.ok) {
        dire("contrib-merci", { numero: d.numero || "?" }, "pret");
        colis = null;
        $("apercu-contribution").hidden = true;
        $("contrib-accord").checked = false;
        return;
      }
      // Le serveur explique son refus (trop gros, trop d'envois, boîte pleine…) : on l'affiche tel quel.
      // Sans explication (service arrêté, panne) : plan B, télécharger le colis.
      if (d.erreur) dire("contrib-refuse", { erreur: d.erreur }, "erreur");
      else dire("contrib-indisponible", { raison: `HTTP ${r.status}` }, "erreur");
    } catch (err) {
      dire("contrib-indisponible", { raison: I.langue === "en" ? "no answer from the server" : "pas de réponse du serveur" }, "erreur");
    }
    bouton.disabled = !colis;
  }

  function telechargerColis() {
    if (!colis) return;
    const url = URL.createObjectURL(new Blob([colis.octets], { type: "application/zip" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = colis.apercu.nom;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    dire("contrib-telecharge", { nom: colis.apercu.nom }, "pret");
  }

  document.addEventListener("DOMContentLoaded", () => {
    const panneau = $("panneau-contribuer");
    $("onglet-contribuer").addEventListener("click", () => (panneau.hidden ? ouvrir() : fermer()));
    $("fermer-contribuer").addEventListener("click", fermer);
    $("voile-contribuer").addEventListener("click", fermer);
    panneau.addEventListener("keydown", garderFocus);
    ["lyrx", "qgis"].forEach(cle => $("contrib-" + cle).addEventListener("change", e => {
      if (e.target.files[0]) placerFichier(e.target.files[0]);
    }));
    // Déposer un fichier sur une case du panneau
    panneau.querySelectorAll(".fichier-contrib").forEach(zone => {
      ["dragenter", "dragover"].forEach(t => zone.addEventListener(t, e => { e.preventDefault(); zone.classList.add("survol"); }));
      ["dragleave", "drop"].forEach(t => zone.addEventListener(t, e => { e.preventDefault(); zone.classList.remove("survol"); }));
      zone.addEventListener("drop", e => [...e.dataTransfer.files].forEach(placerFichier));
    });
    const form = $("form-contribuer");
    form.addEventListener("change", e => { if (e.target.type !== "file") majFormulaire(); });
    form.addEventListener("input", e => { if (e.target.tagName !== "INPUT" || e.target.type !== "radio") invalider(); });
    form.addEventListener("submit", preparer);
    $("contrib-accord").addEventListener("change", e => { $("envoyer-contribution").disabled = !(e.target.checked && colis); });
    $("envoyer-contribution").addEventListener("click", envoyer);
    $("telecharger-contribution").addEventListener("click", telechargerColis);
    document.addEventListener("click", e => {
      const lien = e.target.closest('a[href="#contribuer"]');
      if (lien) { e.preventDefault(); ouvrir(); }
    });
    window.addEventListener("hashchange", () => { if (location.hash === "#contribuer") ouvrir(); });
    if (location.hash === "#contribuer") ouvrir();
    I.surChangement(() => { majFichiers(); afficherApercu(); if (dernierEtat) dire(...dernierEtat); });
  });

  window.Contribuer = { ouvrir, fermer };
})();
