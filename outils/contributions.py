"""Trie les colis envoyés par l'outil « Contribuer » de la page web.

    .\\outils\\py.ps1 outils\\contributions.py DOSSIER_DES_COLIS [--sortie donnees_locales\\contributions]

Pour chaque colis (.zip) du dossier :
- relit l'archive sans rien exécuter et sans extraire hors du dossier prévu (taille plafonnée) ;
- revérifie qu'aucun secret ni donnée personnelle ne reste (confidentialite.reste_sensible) ;
- refait la conversion du fichier de départ avec la version actuelle du cœur, et l'aller-retour ;
- range le tout dans SORTIE/<numéro>/ et écrit SORTIE/tri.csv (une ligne par colis) pour le tri humain.

L'adresse de contact reste dans contribution.json du dossier rangé (ignoré par git) : elle ne va
jamais dans le corpus. Rien n'entre dans les catalogues ni dans le corpus sans relecture.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import zipfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "src"))

from lyrx2qlr import api  # noqa: E402
from lyrx2qlr.catalogue import Catalogue  # noqa: E402
from lyrx2qlr.confidentialite import reste_sensible  # noqa: E402

TAILLE_MAX = 20 * 1024 * 1024  # octets décompressés, pour tout le colis
DOSSIERS_PERMIS = ("fichiers/", "notre_resultat/", "rapports/")


def lire_colis(chemin: Path) -> dict[str, bytes]:
    """Contenu du colis, nom → octets. Lève ValueError si le colis est suspect."""
    with zipfile.ZipFile(chemin) as z:
        infos = z.infolist()
        if sum(i.file_size for i in infos) > TAILLE_MAX:
            raise ValueError("trop gros une fois décompressé")
        contenu = {}
        for i in infos:
            nom = i.filename
            if i.is_dir():
                continue
            if nom != "contribution.json" and (not nom.startswith(DOSSIERS_PERMIS) or ".." in nom or "/" in nom.split("/", 1)[1]):
                raise ValueError(f"chemin inattendu dans l'archive : {nom!r}")
            contenu[nom] = z.read(i)
    if "contribution.json" not in contenu:
        raise ValueError("contribution.json manquant")
    return contenu


def trier(colis: Path, sortie: Path, catalogue: Catalogue) -> dict:
    numero = colis.stem
    ligne = {"numero": numero}
    try:
        contenu = lire_colis(colis)
        infos = json.loads(contenu["contribution.json"])
    except (zipfile.BadZipFile, ValueError, json.JSONDecodeError) as e:
        return {**ligne, "etat": f"refusé : {e}"}
    ligne.update(type=infos.get("type"), licence=infos.get("licence"), version=infos.get("lyrx2qlr"),
                 problemes=" ".join(infos.get("problemes") or []), commentaire=(infos.get("commentaire") or "")[:200],
                 contact="oui" if infos.get("contact") else "")
    sensible = sorted({s for nom, d in contenu.items() if nom.startswith("fichiers/")
                       for s in reste_sensible(d.decode("utf-8", "replace"))})
    ligne["sensible"] = ", ".join(sensible)

    dossier = sortie / numero
    for nom, donnees in contenu.items():
        cible = dossier / nom
        cible.parent.mkdir(parents=True, exist_ok=True)
        cible.write_bytes(donnees)

    depart = next((f["nom"] for f in infos.get("fichiers", []) if f.get("role") == "depart"), None)
    if depart and f"fichiers/{depart}" in contenu:
        r = api.convertir(contenu[f"fichiers/{depart}"], depart, catalogue)
        ligne["aujourdhui"] = r.rapport.resume if r.reussi else f"échec : {r.erreur}"
        if r.reussi:
            (dossier / "conversion_actuelle").mkdir(exist_ok=True)
            (dossier / "conversion_actuelle" / r.nom_sortie).write_bytes(r.donnees)
            retour = api.convertir(r.donnees, r.nom_sortie, catalogue)
            ligne["aller_retour"] = "ok" if retour.reussi else f"échec : {retour.erreur}"
    ligne["etat"] = "à relire" if not sensible else "à relire — secret possible, ne pas publier"
    return ligne


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("dossier", type=Path, help="dossier qui contient les colis .zip récupérés du serveur")
    p.add_argument("--sortie", type=Path, default=RACINE / "donnees_locales" / "contributions")
    a = p.parse_args()
    catalogue = Catalogue.charger()
    a.sortie.mkdir(parents=True, exist_ok=True)
    lignes = [trier(c, a.sortie, catalogue) for c in sorted(a.dossier.glob("*.zip"))]
    champs = ["numero", "etat", "type", "problemes", "licence", "version", "aujourdhui", "aller_retour",
              "sensible", "contact", "commentaire"]
    tampon = io.StringIO()
    w = csv.DictWriter(tampon, champs, extrasaction="ignore", delimiter=";")
    w.writeheader()
    w.writerows(lignes)
    (a.sortie / "tri.csv").write_text(tampon.getvalue(), encoding="utf-8-sig", newline="")
    for l in lignes:
        print(f"{l['numero']:<28} {l.get('type') or '':<11} {l['etat']}")
    print(f"{len(lignes)} colis ; fiche de tri : {a.sortie / 'tri.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
