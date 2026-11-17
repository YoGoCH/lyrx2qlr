"""Passerelle entre la page web (JavaScript) et le cœur lyrx2qlr, exécutée par Pyodide dans le navigateur.

Rien ne quitte le poste : les fichiers sont lus et convertis dans l'onglet du navigateur.
"""
import json
import sys

sys.path.insert(0, "/coeur")

from lyrx2qlr import __version__, api  # noqa: E402
from lyrx2qlr.catalogue import Catalogue  # noqa: E402

_CATALOGUE = Catalogue.charger()


def version() -> str:
    return __version__


def convertir(fichiers, garder_source=True):
    """fichiers : liste de [nom, octets]. Renvoie (archive ZIP ou None, liste de résultats en JSON).

    garder_source : coche « Garder la source de données » de la page (les fichiers ne quittent pas le navigateur)."""
    if hasattr(fichiers, "to_py"):  # tableau JavaScript → liste Python
        fichiers = fichiers.to_py()
    lot = [(str(nom), bytes(donnees)) for nom, donnees in fichiers]
    archive, resultats = api.convertir_lot(lot, _CATALOGUE, bool(garder_source))
    sortie = []
    for r in resultats:
        sortie.append({
            "entree": r.nom_entree,
            "sortie": r.nom_sortie,
            "reussi": r.reussi,
            "erreur": r.erreur,
            "resume": r.rapport.resume,
            "pertes": r.rapport.compter("perte"),
            "avertissements": r.rapport.compter("avertissement"),
            "texte": r.rapport.en_texte(),
            "entrees": r.rapport.en_dict()["entrees"],
        })
    return archive, json.dumps(sortie, ensure_ascii=False), [r.donnees for r in resultats]


def preparer_contribution(infos, fichiers):
    """Outil « Contribuer » : nettoie les fichiers et prépare le colis, sans rien envoyer.

    infos : texte JSON du formulaire ; fichiers : liste de [nom, octets].
    Renvoie (colis ZIP ou None, texte JSON de l'aperçu ou {"erreur": message})."""
    from lyrx2qlr.contribution import ErreurColis, preparer

    if hasattr(fichiers, "to_py"):
        fichiers = fichiers.to_py()
    try:
        colis, apercu = preparer(json.loads(str(infos)), [(str(n), bytes(d)) for n, d in fichiers], _CATALOGUE)
    except ErreurColis as e:
        return None, json.dumps({"erreur": str(e), "code": e.code, "valeurs": e.valeurs}, ensure_ascii=False)
    return colis, json.dumps(apercu, ensure_ascii=False)
