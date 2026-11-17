// Section « Comment ça marche » : repliée au départ, ses premières lignes visibles s'estompent ;
// « Lire la suite » la déplie, « Réduire » la replie. Repliée, le schéma (caché) n'est pas
// atteignable au clavier. Chargé après langue.js.
"use strict";

(() => {
  const I = window.I18N;

  document.addEventListener("DOMContentLoaded", () => {
    const contenu = document.getElementById("logique-contenu");
    const bouton = document.getElementById("logique-bouton");
    if (!contenu || !bouton) return;
    const schema = contenu.querySelector(".schema");

    function maj() {
      const replie = contenu.classList.contains("replie");
      bouton.setAttribute("aria-expanded", String(!replie));
      bouton.dataset.i18n = replie ? "logique-suite" : "logique-reduire";
      bouton.textContent = I.t(bouton.dataset.i18n);
      if (schema) schema.inert = replie;
    }

    bouton.addEventListener("click", () => {
      const replier = !contenu.classList.contains("replie");
      contenu.classList.toggle("replie", replier);
      maj();
      if (replier) {
        const titre = document.getElementById("titre-logique");
        if (titre.getBoundingClientRect().top < 0) titre.scrollIntoView({ block: "start" });
      }
    });
    I.surChangement(maj);
    maj();
  });
})();
