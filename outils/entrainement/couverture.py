"""Couverture des catalogues : propriétés que QGIS connaît, comparées à celles que les catalogues décrivent.

    .\\outils\\py.ps1 outils\\entrainement\\couverture.py [--sortie docs/couverture_qgis.md]

Pour chaque type de couche de symbole QGIS (registre de QGIS), on crée une couche par défaut et on lit la
liste de ses propriétés. Chaque propriété est classée :
  - « convertie » : décrite par un catalogue (propriété, unité, condition ou valeur fixe) ;
  - « ignorée »   : listée dans ignorer.json (perdue sans être signalée : à relire) ;
  - « non couverte » : ni l'un ni l'autre (signalée dans le rapport en « info », perdue).
Les types de couches absents des catalogues sont listés à part.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "src"))

from lyrx2qlr.catalogue import Catalogue  # noqa: E402


def _cles_conditions(d) -> set[str]:
    if isinstance(d, dict):
        return set(d)
    if isinstance(d, list):
        return set().union(*(_cles_conditions(x) for x in d)) if d else set()
    return set()


def cles_connues(cat: Catalogue) -> dict[str, set[str]]:
    """Par classe QGIS : clés QGIS décrites par les catalogues."""
    connues: dict[str, set[str]] = {}
    entrees = list(cat.couches) + list(cat.placements)
    for e in entrees:
        q = e.get("qgis") or {}
        classe = q.get("classe")
        if not classe:
            continue
        s = connues.setdefault(classe, set())
        s |= set(q.get("fixe", {})) | _cles_conditions(q.get("si")) | _cles_conditions(q.get("si_ou"))
        for p in e.get("proprietes", []):
            for champ in ("qgis", "qgis_unite"):
                if p.get(champ):
                    s.add(p[champ])
            for champ in ("qgis_si", "qgis_si_present", "qgis_si_absent"):
                s |= _cles_conditions(p.get(champ))
    for d in cat.decompositions:
        s = connues.setdefault(d["classe"], set())
        s |= set(d.get("renommer", {})) | _cles_conditions(d.get("si"))
    return connues


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--sortie", default=str(RACINE / "docs" / "couverture_qgis.md"))
    args = a.parse_args()
    sortie = Path(args.sortie).resolve()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from qgis.core import Qgis, QgsApplication
    app = QgsApplication([], False)
    app.initQgis()
    cat = Catalogue.charger()
    connues = cles_connues(cat)
    registre = QgsApplication.symbolLayerRegistry()
    lignes = ["# Couverture des propriétés QGIS par les catalogues", "",
              f"Produit par `outils/entrainement/couverture.py` avec QGIS {Qgis.version()}. Ne pas modifier à la main.", "",
              "- **convertie** : décrite par un catalogue ;",
              "- **ignorée** : listée dans `ignorer.json`, perdue **sans être signalée** (à relire : certaines changent le dessin) ;",
              "- **non couverte** : perdue, signalée dans le rapport en « info ».", ""]
    absentes, total = [], {"convertie": 0, "ignorée": 0, "non couverte": 0}
    for nom in sorted(registre.symbolLayersForType(Qgis.SymbolType.Marker) + registre.symbolLayersForType(Qgis.SymbolType.Line)
                      + registre.symbolLayersForType(Qgis.SymbolType.Fill)):
        meta = registre.symbolLayerMetadata(nom)
        if nom not in connues:
            absentes.append(f"{nom} (« {meta.visibleName()} »)")
            continue
        couche = meta.createSymbolLayer({})
        if couche is None:
            continue
        classes = {"convertie": [], "ignorée": [], "non couverte": []}
        for cle in sorted(couche.properties()):
            if cle in connues[nom]:
                classes["convertie"].append(cle)
            elif cat.ignore("qgis", cle):
                classes["ignorée"].append(cle)
            else:
                classes["non couverte"].append(cle)
        lignes += [f"## {nom} (« {meta.visibleName()} »)", ""]
        for k, v in classes.items():
            total[k] += len(v)
            lignes.append(f"- **{k}** ({len(v)}) : " + (", ".join(f"`{c}`" for c in v) if v else "—"))
        lignes.append("")
    lignes += ["## Types de couches de symboles sans équivalent dans les catalogues", ""]
    lignes += [f"- {x}" for x in sorted(set(absentes))] + [""]
    lignes.insert(7, f"Total : {total['convertie']} convertie(s), {total['ignorée']} ignorée(s), "
                     f"{total['non couverte']} non couverte(s), {len(set(absentes))} type(s) de couche absent(s).\n")
    sortie.write_text("\n".join(lignes), encoding="utf-8")
    print(lignes[7].strip())
    print(f"→ {sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
