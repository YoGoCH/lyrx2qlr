"""Lot 2 : vérifie les .lyrx produits par lyrx2qlr d'après la spécification CIM publiée par Esri.

    .\\outils\\py.ps1 outils\\lot2\\verifier_cim.py --spec CHEMIN\\cim-spec\\docs\\v3 FICHIERS_OU_DOSSIERS...

La spécification (https://github.com/Esri/cim-spec, licence Apache 2.0) n'est pas copiée dans le
dépôt : la cloner à part (`git clone --depth 1 https://github.com/Esri/cim-spec.git`).

Pour chaque fichier QGIS (.qlr, .qml) : conversion en .lyrx ; pour chaque .lyrx : aller-retour
.lyrx → .qlr → .lyrx. Dans le .lyrx produit, chaque objet `{"type": "CIM…"}` est contrôlé :

- **type inconnu** : la classe n'existe pas dans la spécification ;
- **propriété inconnue** : la classe (ou ses parents) n'a pas cette propriété ;
- **valeur hors liste** : une propriété de type « enumeration » reçoit une valeur absente de la liste.

Ne lance pas ArcGIS : rapide, utilisable dans les tests.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "src"))
from lyrx2qlr import api  # noqa: E402
from lyrx2qlr.catalogue import Catalogue  # noqa: E402

import json  # noqa: E402
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # noms de fichiers en hébreu, etc.

# Propriétés communes que la spécification ne liste pas classe par classe.
TOUJOURS = {"type", "uri"}  # uRI : écrit par ArcGIS sur chaque couche, absent des tables


def lire_spec(dossier: Path) -> tuple[dict, dict]:
    """classes : nom → {propriété: nom d'énumération ou None} ; enums : nom → valeurs permises."""
    classes, enums = {}, {}
    for md in sorted(dossier.glob("*.md")):
        classe = enum = None
        for ligne in md.read_text(encoding="utf-8").splitlines():
            if ligne.startswith("## "):
                classe, enum = ligne[3:].strip(), None
                classes.setdefault(classe, {})
            elif ligne.startswith("### Enumeration: "):
                enum, classe = ligne[len("### Enumeration: "):].strip(), None
                enums.setdefault(enum, set())
            elif ligne.startswith("|") and not ligne.startswith("|Property") and not ligne.startswith("|---"):
                cellules = [c.strip() for c in ligne.strip("|").split("|")]
                if enum and cellules and cellules[0]:
                    enums[enum].add(cellules[0])
                elif classe and len(cellules) >= 2 and cellules[0]:
                    m = re.search(r"enumeration (\w+)", cellules[1])
                    classes[classe][cellules[0].lower()] = m.group(1) if m else None  # JSON : « URL » s'écrit « url »
    return classes, enums


def verifier(objet, classes: dict, enums: dict, chemin: str, sortie: list) -> None:
    if isinstance(objet, list):
        for i, x in enumerate(objet):
            verifier(x, classes, enums, f"{chemin}[{i}]", sortie)
        return
    if not isinstance(objet, dict):
        return
    t = objet.get("type")
    proprietes = classes.get(t) if isinstance(t, str) else None
    if isinstance(t, str) and t.startswith("CIM") and proprietes is None:
        sortie.append(("type inconnu", t, chemin))
    for k, v in objet.items():
        if proprietes is not None and k.lower() not in proprietes and k.lower() not in TOUJOURS:
            sortie.append(("propriété inconnue", f"{t}.{k}", f"{chemin}.{k}"))
        elif proprietes is not None and proprietes.get(k.lower()) and isinstance(v, str):
            permis = enums.get(proprietes[k.lower()])
            if permis and v not in permis:
                sortie.append(("valeur hors liste", f"{t}.{k} = {v!r} (permis : {', '.join(sorted(permis))})", f"{chemin}.{k}"))
        verifier(v, classes, enums, f"{chemin}.{k}", sortie)


def lister(entrees: list[str]) -> list[Path]:
    fichiers = []
    for e in entrees:
        p = Path(e)
        fichiers += sorted(x for x in p.rglob("*") if x.suffix.lower() in (".lyrx", ".qlr", ".qml")) if p.is_dir() else [p]
    return fichiers


def produire(f: Path, cat: Catalogue, originaux: bool = False) -> bytes | None:
    donnees, nom = f.read_bytes(), f.name
    if originaux:
        return donnees if f.suffix.lower() == ".lyrx" else None
    if f.suffix.lower() == ".lyrx":
        res = api.convertir(donnees, nom, cat)
        if not res.reussi:
            return None
        donnees, nom = res.donnees, res.nom_sortie
    res = api.convertir(donnees, nom, cat)
    return res.donnees if res.reussi else None


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("entrees", nargs="+")
    a.add_argument("--spec", required=True)
    a.add_argument("--sortie", help="fichier Markdown du résumé")
    a.add_argument("--originaux", action="store_true",
                   help="vérifier les .lyrx d'origine (faits par ArcGIS) : sert à étalonner l'outil")
    args = a.parse_args()
    classes, enums = lire_spec(Path(args.spec))
    cat = Catalogue.charger()
    fichiers = lister(args.entrees)
    motifs, exemples, par_fichier = Counter(), {}, defaultdict(set)
    produits = 0
    for f in fichiers:
        lyrx = produire(f, cat, args.originaux)
        if lyrx is None:
            continue
        produits += 1
        trouves = []
        verifier(json.loads(lyrx.decode("utf-8-sig")), classes, enums, "", trouves)
        for genre, motif, chemin in trouves:
            cle = f"{genre} : {motif}"
            motifs[cle] += 1
            par_fichier[cle].add(f.name)
            exemples.setdefault(cle, f"{f.name} {chemin}")
    lignes = [f"# Vérification CIM des .lyrx produits", "",
              f"{len(classes)} classes et {len(enums)} listes lues dans la spécification ; "
              f"{produits} .lyrx produits sur {len(fichiers)} fichiers ; "
              f"{sum(1 for f in fichiers) and len({x for s in par_fichier.values() for x in s})} fichiers avec au moins un écart.", "",
              "| Écart | Fois | Fichiers | Exemple |", "|---|---|---|---|"]
    for cle, n in motifs.most_common():
        lignes.append(f"| {cle} | {n} | {len(par_fichier[cle])} | `{exemples[cle][:110]}` |")
    texte = "\n".join(lignes) + "\n"
    if args.sortie:
        Path(args.sortie).parent.mkdir(parents=True, exist_ok=True)
        Path(args.sortie).write_text(texte, encoding="utf-8")
    sys.stdout.buffer.write(texte.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
