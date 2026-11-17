// Bouton « Utiliser hors ligne » : garde la page, le cœur Python et Pyodide dans le navigateur (sw.js),
// pour convertir sans internet ; propose ensuite d'installer lyrx2qlr comme une application.
// Rien n'est installé sans le clic. Une ligne d'aide permet de retirer la copie hors ligne.
// Chargé après langue.js.
"use strict";

(() => {
  const I = window.I18N;
  I.ajouter({
    fr: {
      "hl-utiliser": "Utiliser hors ligne",
      "hl-utiliser-titre": "Garder lyrx2qlr dans ce navigateur (environ 15 Mo) pour convertir sans internet, et l'installer comme une application",
      "hl-preparation": "Préparation…",
      "hl-pret": "Hors ligne : prêt",
      "hl-installer": "Installer l'application",
      "hl-installer-titre": "Ajouter lyrx2qlr aux applications de cet ordinateur (fenêtre à part, marche sans internet)",
      "hl-message-pret": "Prêt : cette page marche maintenant sans internet, dans ce navigateur. Les fichiers restent sur votre ordinateur ; seul l'envoi d'une contribution demande internet.",
      "hl-message-installer": "Pour l'avoir comme une application : dans Chrome ou Edge, « Installer » dans la barre d'adresse ; sur iPhone ou iPad, « Partager » puis « Sur l'écran d'accueil ». Firefox ne sait pas installer, mais la page marche hors ligne.",
      "hl-message-installee": "lyrx2qlr est installé comme application et marche sans internet.",
      "hl-retirer": "Retirer la copie hors ligne",
      "hl-retiree": "Copie hors ligne retirée : la page a de nouveau besoin d'internet.",
      "hl-echec": "Impossible de préparer l'usage hors ligne : {erreur}",
    },
    en: {
      "hl-utiliser": "Use offline",
      "hl-utiliser-titre": "Keep lyrx2qlr in this browser (about 15 MB) to convert without internet, and install it as an app",
      "hl-preparation": "Preparing…",
      "hl-pret": "Offline: ready",
      "hl-installer": "Install the app",
      "hl-installer-titre": "Add lyrx2qlr to this computer's apps (own window, works without internet)",
      "hl-message-pret": "Ready: this page now works without internet, in this browser. Files stay on your computer; only sending a contribution needs internet.",
      "hl-message-installer": "To have it as an app: in Chrome or Edge, “Install” in the address bar; on iPhone or iPad, “Share” then “Add to Home Screen”. Firefox cannot install apps, but the page works offline.",
      "hl-message-installee": "lyrx2qlr is installed as an app and works without internet.",
      "hl-retirer": "Remove the offline copy",
      "hl-retiree": "Offline copy removed: the page needs internet again.",
      "hl-echec": "Could not prepare offline use: {erreur}",
    },
  });

  const bouton = document.getElementById("hors-ligne");
  const info = document.getElementById("info-hors-ligne");
  if (!bouton || !("serviceWorker" in navigator) || !window.isSecureContext || !window.caches) return;

  let etat = "absent";           // absent | preparation | pret
  let demandeInstallation = null; // événement « beforeinstallprompt » (Chrome, Edge)
  let messages = [], messageValeurs = {};  // clés des phrases affichées sous les réglages
  const installee = () => window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;

  function maj() {
    bouton.hidden = false;
    bouton.disabled = etat === "preparation";
    const cle = etat === "preparation" ? "hl-preparation"
      : etat === "pret" ? (demandeInstallation && !installee() ? "hl-installer" : "hl-pret") : "hl-utiliser";
    bouton.textContent = I.t(cle);
    bouton.title = I.t(cle === "hl-installer" ? "hl-installer-titre" : "hl-utiliser-titre");
    bouton.setAttribute("aria-pressed", String(etat === "pret"));
    if (messages.length) {
      info.hidden = false;
      info.textContent = messages.map(c => I.t(c, messageValeurs)).join(" ") + " ";
      if (etat === "pret") {
        const retirer = document.createElement("a");
        retirer.href = "#";
        retirer.textContent = I.t("hl-retirer");
        retirer.addEventListener("click", e => { e.preventDefault(); retirerCopie(); });
        info.append(retirer);
      }
    }
  }

  function dire(cles, valeurs = {}) { messages = [].concat(cles); messageValeurs = valeurs; maj(); }
  // Ce que la page peut faire maintenant, et comment l'installer si le navigateur ne le propose pas lui-même
  const messagesPret = () => installee() ? ["hl-message-installee"]
    : demandeInstallation ? ["hl-message-pret"] : ["hl-message-pret", "hl-message-installer"];

  async function copiePrete() {
    const enregistrement = await navigator.serviceWorker.getRegistration();
    return !!(enregistrement && enregistrement.active && (await caches.keys()).some(n => n.startsWith("lyrx2qlr-")));
  }

  async function preparer() {
    etat = "preparation"; maj();
    try {
      await navigator.serviceWorker.register("sw.js");
      await navigator.serviceWorker.ready;
      etat = "pret";
      dire(messagesPret());
    } catch (e) {
      etat = "absent";
      dire("hl-echec", { erreur: e.message });
    }
  }

  async function retirerCopie() {
    for (const r of await navigator.serviceWorker.getRegistrations()) await r.unregister();
    for (const n of await caches.keys()) if (n.startsWith("lyrx2qlr-")) await caches.delete(n);
    etat = "absent";
    dire("hl-retiree");
    info.querySelector("a")?.remove();
  }

  bouton.addEventListener("click", async () => {
    if (etat === "absent") return preparer();
    if (etat === "pret" && demandeInstallation && !installee()) {
      demandeInstallation.prompt();
      await demandeInstallation.userChoice;
      demandeInstallation = null;
      maj();
      return;
    }
    dire(messagesPret());
  });

  window.addEventListener("beforeinstallprompt", e => { e.preventDefault(); demandeInstallation = e; maj(); });
  window.addEventListener("appinstalled", () => { demandeInstallation = null; dire("hl-message-installee"); });
  I.surChangement(maj);

  copiePrete().then(pret => { etat = pret ? "pret" : "absent"; maj(); });
})();
