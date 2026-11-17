"""Colis de contribution : ce qu'un utilisateur envoie pour aider à améliorer lyrx2qlr.

Le colis est un ZIP préparé sur le poste de l'utilisateur (page web, plus tard extension QGIS) :

    contribution.json           ce que l'utilisateur a dit (type, problèmes, commentaire, licence…)
    fichiers/<nom>              ses fichiers, nettoyés (voir confidentialite.py)
    notre_resultat/<nom>        ce que lyrx2qlr produit à partir du fichier de départ
    rapports/<nom>.txt          le rapport de cette conversion

Rien n'est envoyé ici : ce module ne fait que préparer le colis. L'envoi est un geste séparé du
visiteur, après avoir vu l'aperçu.
"""
from __future__ import annotations

import datetime
import hashlib
import io
import json
import re
import zipfile
from typing import Iterable, Optional

from . import __version__, api
from .catalogue import Catalogue
from .confidentialite import nettoyer, nettoyer_octets

FORMAT = 1
TAILLE_MAX = 4 * 1024 * 1024   # octets, pour tous les fichiers ensemble (le serveur refuse au-delà de 5 Mo)
EXTENSIONS = (".lyrx", ".qlr", ".qml")

# Sortes de contribution, et ce que chacune veut dire pour l'entraînement
TYPES = {
    "bon": "conversion juste : exemple à garder comme référence",
    "a_corriger": "conversion fausse ou incomplète : à corriger (entraînement correctif)",
    "paire": "paire de référence : le même rendu fait à la main dans les deux logiciels",
    "remarque": "idée, remarque ou correspondance manquante",
}
PROBLEMES = ("couleurs", "epaisseurs", "symboles", "remplissages", "etiquettes", "echelles", "classes",
             "expressions", "source", "ouverture", "autre")
LICENCES = {"tests": "pour les tests de lyrx2qlr seulement, jamais publié",
            "corpus": "peut rejoindre le corpus public (CC-BY 4.0)"}
_EMAIL_VALIDE = re.compile(r"^[^@\s<>\"']{1,64}@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$")


class ErreurColis(ValueError):
    """Contribution incomplète ou refusée : le message est fait pour être montré au visiteur ;
    `code` permet à la page de le traduire."""

    def __init__(self, code: str, message: str, **valeurs):
        super().__init__(message)
        self.code = code
        self.valeurs = valeurs


def _nom_sur(nom: str) -> str:
    """Nom de fichier sans dossier ni caractère gênant."""
    nom = re.split(r"[\\/]", nom)[-1]
    nom = re.sub(r"[^\w.() -]", "_", nom).strip(" .") or "fichier"
    return nom[:120]


def _texte(valeur, longueur: int) -> str:
    return str(valeur or "").strip()[:longueur]


def preparer(infos: dict, fichiers: Iterable[tuple[str, bytes]], catalogue: Optional[Catalogue] = None,
             maintenant: Optional[datetime.datetime] = None) -> tuple[bytes, dict]:
    """Prépare le colis. Renvoie (ZIP, aperçu) ; l'aperçu dit ce qui part et ce qui a été retiré.

    infos : type, problemes, commentaire, depart (nom du fichier de départ), logiciels {arcgis, qgis},
            licence, contact (e-mail facultatif), langue.
    Lève ErreurColis si la contribution n'est pas envoyable (message pour le visiteur)."""
    type_ = infos.get("type")
    if type_ not in TYPES:
        raise ErreurColis("type", "Choisissez de quelle sorte de contribution il s'agit.")
    licence = infos.get("licence") if infos.get("licence") in LICENCES else "tests"
    commentaire, retraits_commentaire = nettoyer(_texte(infos.get("commentaire"), 4000))
    contact = _texte(infos.get("contact"), 200)
    if contact and not _EMAIL_VALIDE.match(contact):
        raise ErreurColis("contact", "L'adresse e-mail de contact ne semble pas valable (elle est facultative).")

    recus = []
    vus = set()
    for nom, donnees in fichiers:
        nom = _nom_sur(nom)
        if not nom.lower().endswith(EXTENSIONS):
            raise ErreurColis("extension", f"« {nom} » : seuls les fichiers .lyrx, .qlr et .qml sont acceptés.", nom=nom)
        if nom.lower() in vus:
            raise ErreurColis("double", f"« {nom} » est joint deux fois.", nom=nom)
        vus.add(nom.lower())
        try:
            propre, retraits = nettoyer_octets(bytes(donnees))
        except ValueError as e:
            raise ErreurColis("texte", f"« {nom} » : {e}.", nom=nom) from e
        recus.append((nom, propre, retraits))

    if sum(len(p) for _, p, _ in recus) > TAILLE_MAX:
        raise ErreurColis("taille", "Les fichiers dépassent 4 Mo en tout : retirez les images intégrées ou envoyez-les séparément.")
    if type_ == "paire" and not ({".lyrx"} <= {n[n.rfind("."):].lower() for n, _, _ in recus}
                                 and {".qlr", ".qml"} & {n[n.rfind("."):].lower() for n, _, _ in recus}):
        raise ErreurColis("paire", "Une paire de référence demande un .lyrx et un .qlr (ou .qml).")
    if type_ in ("bon", "a_corriger") and not recus:
        raise ErreurColis("depart", "Joignez au moins le fichier de départ.")
    if type_ == "remarque" and not recus and not commentaire:
        raise ErreurColis("remarque", "Écrivez votre remarque dans le commentaire.")
    if type_ == "a_corriger" and not commentaire and not infos.get("problemes"):
        raise ErreurColis("probleme", "Dites ce qui ne va pas : cochez un problème ou écrivez un commentaire.")

    # Fichier de départ : celui que l'utilisateur indique, sinon le seul joint
    noms = [n for n, _, _ in recus]
    depart = _nom_sur(infos["depart"]) if infos.get("depart") else None
    if depart not in noms:
        depart = noms[0] if len(noms) == 1 else (next((n for n in noms if n.lower().endswith(".lyrx")), None) if noms else None)

    catalogue = catalogue or Catalogue.charger()
    maintenant = maintenant or datetime.datetime.now(datetime.timezone.utc)
    tampon = io.BytesIO()
    apercu_fichiers = []
    conversion = None
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        for nom, propre, retraits in recus:
            role = "depart" if nom == depart else "attendu"
            z.writestr(f"fichiers/{nom}", propre)
            apercu_fichiers.append({"nom": nom, "role": role, "taille": len(propre),
                                    "sha256": hashlib.sha256(propre).hexdigest(), "retraits": retraits})
        if depart:
            # Notre conversion, refaite sur le fichier nettoyé : c'est elle qu'on évalue
            r = api.convertir(dict((n, p) for n, p, _ in recus)[depart], depart, catalogue, True)
            conversion = {"entree": depart, "sortie": r.nom_sortie, "reussi": r.reussi, "erreur": r.erreur,
                          "resume": r.rapport.resume, "pertes": r.rapport.compter("perte"),
                          "avertissements": r.rapport.compter("avertissement")}
            if r.reussi:
                z.writestr(f"notre_resultat/{r.nom_sortie}", r.donnees)
            z.writestr(f"rapports/{depart}.txt", r.rapport.en_texte())
        infos_colis = {
            "format": FORMAT,
            "lyrx2qlr": __version__,
            "date": maintenant.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "type": type_,
            "type_texte": TYPES[type_],
            "problemes": [p for p in (infos.get("problemes") or []) if p in PROBLEMES],
            "commentaire": commentaire,
            "logiciels": {k: _texte((infos.get("logiciels") or {}).get(k), 40) for k in ("arcgis", "qgis")},
            "licence": licence,
            "licence_texte": LICENCES[licence],
            "langue": "en" if infos.get("langue") == "en" else "fr",
            "contact": contact,  # facultatif ; jamais rangé avec le fichier dans le corpus
            "fichiers": apercu_fichiers,
            "conversion": conversion,
        }
        z.writestr("contribution.json", json.dumps(infos_colis, ensure_ascii=False, indent=1))
    donnees = tampon.getvalue()
    apercu = {"taille": len(donnees), "fichiers": apercu_fichiers, "conversion": conversion,
              "retraits_commentaire": retraits_commentaire,
              "nom": f"lyrx2qlr_contribution_{maintenant.strftime('%Y%m%d-%H%M%S')}.zip"}
    return donnees, apercu
