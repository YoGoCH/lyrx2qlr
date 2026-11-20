"""Ligne de commande : python -m lyrx2qlr --aide"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .api import convertir_fichier, lister_fichiers
from .catalogue import Catalogue, ErreurCatalogue


def principal(arguments: list[str] | None = None) -> int:
    for flux in (sys.stdout, sys.stderr):
        if hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(
        prog="lyrx2qlr", add_help=False,
        description="Convertit des symbologies ArcGIS Pro (.lyrx) en couches QGIS (.qlr), et inversement (.qlr ou .qml → .lyrx).")
    p.add_argument("entrees", nargs="*", help="fichiers ou dossiers à convertir (les dossiers sont parcourus)")
    p.add_argument("-o", "--sortie", help="dossier où écrire les résultats (par défaut : à côté de chaque fichier)")
    p.add_argument("-c", "--catalogues", action="append", default=[],
                   help="dossier de catalogues complémentaires (prioritaires sur ceux du paquet) ; répétable")
    p.add_argument("-r", "--rapport", choices=["texte", "json", "aucun"], default="texte", help="forme du rapport affiché")
    p.add_argument("--sans-source", action="store_true",
                   help="ne garde pas la source de données (seul le nom du jeu reste, à reconnecter) ; "
                        "par défaut, le fichier produit pointe sur les mêmes données, sans mot de passe")
    p.add_argument("-l", "--langue", choices=["fr", "en"], default="fr", help="langue du rapport (fr : français, en : anglais)")
    p.add_argument("--verifier-catalogues", action="store_true", help="vérifie les catalogues et s'arrête")
    p.add_argument("--version", action="version", version=f"lyrx2qlr {__version__}")
    p.add_argument("-h", "--aide", "--help", action="help", help="affiche cette aide")
    a = p.parse_args(arguments)
    try:
        cat = Catalogue.charger(a.catalogues)
    except ErreurCatalogue as e:
        print(e, file=sys.stderr)
        return 2
    if a.verifier_catalogues:
        print("Catalogues valides.")
        return 0
    fichiers = lister_fichiers(a.entrees)
    if not fichiers:
        p.print_usage()
        print("Aucun fichier .lyrx, .qlr ou .qml trouvé.", file=sys.stderr)
        return 1
    echecs = 0
    rapports = []
    for f in fichiers:
        sortie = a.sortie
        if sortie and len(a.entrees) == 1 and Path(a.entrees[0]).is_dir():
            # garder l'arborescence des sous-dossiers
            sortie = Path(a.sortie) / f.parent.relative_to(Path(a.entrees[0]))
        r = convertir_fichier(f, sortie, cat, garder_source=not a.sans_source)
        echecs += 0 if r.reussi else 1
        if a.rapport == "texte":
            print(r.rapport.en_texte(a.langue))
            print()
        elif a.rapport == "json":
            rapports.append(r.rapport.en_dict(a.langue))
    if a.rapport == "json":
        print(json.dumps(rapports, ensure_ascii=False, indent=2))
    print(f"{len(fichiers) - echecs} fichier(s) converti(s), {echecs} échec(s).", file=sys.stderr)
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(principal())
