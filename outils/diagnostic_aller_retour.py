"""Affiche, regroupées, les différences d'aller-retour sur tous les exemples (aide au développement).

    python outils/diagnostic_aller_retour.py
"""
import collections
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))
from conftest import EXEMPLES_LYRX, EXEMPLES_QLR, comparer_documents  # noqa: E402
import copy  # noqa: E402
from lyrx2qlr import api  # noqa: E402
from lyrx2qlr.catalogue import Catalogue  # noqa: E402
from lyrx2qlr.rapport import Rapport  # noqa: E402

cat = Catalogue.charger()
d = copy.deepcopy(cat.d)
d["polices"]["substitutions"] = []
cat = Catalogue(d)
groupes = collections.defaultdict(list)
for p in EXEMPLES_LYRX + EXEMPLES_QLR:
    ext, sortie = api.sens_conversion(p.name)
    doc1 = api.lire(p.read_bytes(), p.name, cat, Rapport())
    doc2 = api.lire(api.ecrire(doc1, sortie, cat, Rapport()), "x" + sortie, cat, Rapport())
    for diff in comparer_documents(doc1, doc2):
        cle = re.sub(r"\[\d+\]", "[]", diff.split(" : ")[0])
        groupes[cle].append(f"{p.name}: {diff}")
for cle, liste in sorted(groupes.items(), key=lambda x: -len(x[1])):
    print(f"{len(liste):4d}  {cle}\n        ex. {liste[0][:220]}")
print("fichiers :", len(EXEMPLES_LYRX + EXEMPLES_QLR), "groupes de différences :", len(groupes))
