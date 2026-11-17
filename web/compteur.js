// Comptage anonyme, pour savoir combien la page sert : une « visite » par onglet ouvert, et le
// nombre de fichiers convertis (dont réussis). Seuls ces nombres partent, vers /api/compter du même
// serveur : ni nom ni contenu de fichier, ni cookie, ni identifiant. Le serveur additionne les
// nombres par jour, sans garder d'adresse IP, et efface les jours de plus de 100 jours.
// Rien n'est envoyé hors du site en ligne (localhost, fichier ouvert à la main) ni hors ligne.
"use strict";

(() => {
  const ADRESSE = "/api/compter";
  const EN_LIGNE = location.protocol === "https:" && !/^(localhost|127\.|\[::1\])/.test(location.hostname);

  function envoyer(texte) {
    if (!EN_LIGNE || !navigator.onLine || !navigator.sendBeacon) return;
    try { navigator.sendBeacon(ADRESSE, texte); } catch { /* le comptage ne doit jamais gêner la page */ }
  }

  // Appelé par app.js après chaque conversion
  window.LYRX2QLR_COMPTER = (fichiers, reussis) => envoyer(`fichiers=${fichiers};reussis=${reussis}`);

  // Une visite par onglet : un rechargement ne compte pas deux fois
  let dejaCompte = false;
  try { dejaCompte = sessionStorage.getItem("lyrx2qlr-visite") === "1"; sessionStorage.setItem("lyrx2qlr-visite", "1"); } catch { /* stockage indisponible */ }
  if (!dejaCompte) envoyer("visite");
})();
