"""Compare, couche par couche, les propriétés QGIS d'un cas avant et après l'aller-retour.

    .\outils\py.ps1 outils\entrainement\diagnostic.py sorties\entrainement\cas\q1_0004.qlr [indice_symbole]
"""
import os
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import QgsApplication  # noqa: E402

from boucle import symboles_de_qlr  # noqa: E402
from lyrx2qlr import api  # noqa: E402

app = QgsApplication([], False)
app.initQgis()
chemin = Path(sys.argv[1])
seul = int(sys.argv[2]) if len(sys.argv) > 2 else None
avant = chemin.read_bytes()
r1 = api.convertir(avant, chemin.name)
r2 = api.convertir(r1.donnees, r1.nom_sortie)
print(r1.rapport.en_texte(), "\n", r2.rapport.en_texte(), sep="")


def couches(s, prefixe=""):
    for i, c in enumerate(s.symbolLayers()):
        yield f"{prefixe}{i}:{c.layerType()}", c.properties()
        if c.subSymbol():
            yield from couches(c.subSymbol(), f"{prefixe}{i}>")


for n, (a, b) in enumerate(zip(symboles_de_qlr(avant), symboles_de_qlr(r2.donnees))):
    if seul is not None and n != seul:
        continue
    print(f"\n=== symbole {n} (opacité {a.opacity()} / {b.opacity()})")
    la, lb = list(couches(a)), list(couches(b))
    for (na, pa), (nb, pb) in zip(la, lb):
        diffs = {k: (pa.get(k), pb.get(k)) for k in sorted(set(pa) | set(pb)) if str(pa.get(k)) != str(pb.get(k))}
        print(f"  {na} → {nb} : {diffs or 'identique'}")
    if len(la) != len(lb):
        print("  couches avant :", [x for x, _ in la], "après :", [x for x, _ in lb])
        for x, p in (la if len(la) > len(lb) else lb)[min(len(la), len(lb)):]:
            print("   en plus :", x, p)
