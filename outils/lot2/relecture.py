"""Lot 2, contrôle A : ArcGIS Pro ouvre et réenregistre les .lyrx produits par lyrx2qlr.

    & "C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe" outils\\lot2\\relecture.py ^
        FICHIERS_OU_DOSSIERS... --sortie comparaisons_lot2\\relecture_NOM

Pour chaque fichier :

- fichier QGIS (.qlr, .qml) : conversion en .lyrx ;
- fichier ArcGIS (.lyrx) : ouverture de l'original par ArcGIS, puis aller-retour .lyrx → .qlr → .lyrx.

Le .lyrx produit est ouvert par ArcGIS (`arcpy.mp.LayerFile`) puis réenregistré (`saveACopy`).
On compare alors :

1. **le JSON**, propriété par propriété : ce qu'ArcGIS efface ou modifie parmi ce que nous avons
   écrit signale une valeur mal formée (les propriétés qu'il ajoute sont ses valeurs par défaut) ;
2. **le modèle neutre** relu des deux fichiers : une différence est un vrai changement de sens.

Résultat : `resume.md` (chiffres et classement des écarts) et `details.json`.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "src"))
sys.path.insert(0, str(RACINE / "tests"))
from conftest import comparer_documents  # noqa: E402
from lyrx2qlr import api  # noqa: E402
from lyrx2qlr.catalogue import Catalogue  # noqa: E402
from lyrx2qlr.rapport import Rapport  # noqa: E402

import arcpy
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # noms de fichiers en hébreu, etc.  # noqa: E402

EXTENSIONS = (".lyrx", ".qlr", ".qml")
# Propriétés qu'ArcGIS réécrit toujours, sans rapport avec la symbologie.
IGNORER = re.compile(r"^(version|build|\$type)$|\.(version|build|uRI|sourceURI|sourceModifiedTime|"
                     r"layerElevation|expanded|useSourceMetadata|metadataURI|serviceLayerID|"
                     r"workspaceConnectionString)(\.|$)")
# Valeurs par défaut qu'ArcGIS n'écrit pas : les voir disparaître n'est pas une perte.
DEFAUTS_CIM = {"controlPointPlacement": "NoConstraint"}
# Changements du modèle neutre sans effet sur le dessin.
BRUIT_MODELE = [
    re.compile(r"\.source\.dossier : "),  # chemin relatif rendu absolu par ArcGIS
]


def aplatir(x, chemin="", sortie=None) -> dict:
    sortie = {} if sortie is None else sortie
    if isinstance(x, dict):
        for k, v in x.items():
            aplatir(v, f"{chemin}.{k}" if chemin else k, sortie)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            aplatir(v, f"{chemin}[{i}]", sortie)
    else:
        sortie[chemin] = x
    return sortie


def egaux(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(a - b) <= max(1e-6, abs(a) * 1e-6)
    return a == b


def ecarts_json(nous: dict, arcgis: dict) -> list[tuple[str, str]]:
    """(motif, détail) pour chaque propriété écrite par nous qu'ArcGIS a effacée ou changée."""
    a, b = aplatir(nous), aplatir(arcgis)
    sortie = []
    for chemin, v in a.items():
        if IGNORER.search(chemin):
            continue
        motif = re.sub(r"\[\d+\]", "[]", chemin)
        if chemin not in b:
            # une valeur fausse, nulle ou vide qu'ArcGIS n'écrit pas n'est pas une perte
            if v in (False, None, "", 0) or v == [] or DEFAUTS_CIM.get(chemin.rsplit(".", 1)[-1]) == v:
                continue
            sortie.append((f"effacé : {motif}", f"{chemin} = {v!r}"))
        elif not egaux(v, b[chemin]):
            sortie.append((f"modifié : {motif}", f"{chemin} : {v!r} → {b[chemin]!r}"))
    return sortie


def lister(entrees: list[str]) -> list[Path]:
    fichiers = []
    for e in entrees:
        p = Path(e)
        fichiers += sorted(x for x in p.rglob("*") if x.suffix.lower() in EXTENSIONS) if p.is_dir() else [p]
    return fichiers


def traiter(f: Path, tmp: Path, cat: Catalogue) -> dict:
    r = {"fichier": str(f), "sens": "lyrx" if f.suffix.lower() == ".lyrx" else "qgis"}
    donnees = f.read_bytes()
    if r["sens"] == "lyrx":
        try:
            arcpy.mp.LayerFile(str(f)).listLayers()
            r["original_ouvert"] = True
        except Exception as e:  # noqa: BLE001
            r["original_ouvert"] = False
            r["original_erreur"] = str(e).strip().splitlines()[-1][:200]
        res = api.convertir(donnees, f.name, cat)
        if not res.reussi:
            r["etat"] = "conversion impossible"
            r["erreur"] = res.erreur
            return r
        donnees, nom = res.donnees, res.nom_sortie
    else:
        nom = f.name
    res = api.convertir(donnees, nom, cat)
    if not res.reussi:
        r["etat"] = "conversion impossible"
        r["erreur"] = res.erreur
        return r
    r["pertes"] = sum(1 for e in res.rapport.entrees if e.niveau == "perte")
    nous = tmp / "nous.lyrx"
    nous.write_bytes(res.donnees)
    relu = tmp / "arcgis.lyrx"
    if relu.exists():
        relu.unlink()
    try:
        lf = arcpy.mp.LayerFile(str(nous))
        r["couches_arcgis"] = len(lf.listLayers())
        lf.saveACopy(str(relu))
    except Exception as e:  # noqa: BLE001
        r["etat"] = "refusé par ArcGIS"
        r["erreur"] = str(e).strip().splitlines()[-1][:200]
        return r
    j_nous = json.loads(nous.read_text(encoding="utf-8"))
    j_arcgis = json.loads(relu.read_text(encoding="utf-8-sig"))
    r["json"] = ecarts_json(j_nous, j_arcgis)
    try:
        rap = Rapport(fichier=nom)
        doc_a = api.lire(nous.read_bytes(), "nous.lyrx", cat, rap)
        doc_b = api.lire(relu.read_bytes(), "arcgis.lyrx", cat, Rapport(fichier=nom))
        sans_etiquettes = {i for i, c in enumerate(doc_a.couches) if not c.etiquettes_actives}
        r["modele"] = [d for d in comparer_documents(doc_a, doc_b)
                       if not any(b.search(d) for b in BRUIT_MODELE)
                       # classe d'étiquettes ajoutée par ArcGIS à une couche sans étiquettes actives
                       and not any(d.startswith(f".couches[{i}].etiquettes") for i in sans_etiquettes)]
    except Exception:  # noqa: BLE001
        r["modele"] = ["relecture impossible : " + traceback.format_exc().strip().splitlines()[-1]]
    r["etat"] = "identique" if not r["json"] and not r["modele"] else "modifié par ArcGIS"
    return r


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("entrees", nargs="+")
    a.add_argument("--sortie", required=True)
    args = a.parse_args()
    sortie = Path(args.sortie).resolve()
    sortie.mkdir(parents=True, exist_ok=True)
    cat = Catalogue.charger()
    fichiers = lister(args.entrees)
    resultats = []
    debut = time.time()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        for i, f in enumerate(fichiers, 1):
            try:
                r = traiter(f, Path(tmp), cat)
            except Exception:  # noqa: BLE001
                r = {"fichier": str(f), "etat": "erreur interne", "erreur": traceback.format_exc()[-400:]}
            resultats.append(r)
            print(f"[{i}/{len(fichiers)}] {r['etat']:22} {f.name}", flush=True)
    (sortie / "details.json").write_text(json.dumps(resultats, indent=1, ensure_ascii=False), encoding="utf-8")
    ecrire_resume(sortie, resultats, time.time() - debut)
    return 0


def ecrire_resume(sortie: Path, resultats: list, duree: float) -> None:
    etats = Counter(r["etat"] for r in resultats)
    motifs_json, exemples_json = Counter(), {}
    fichiers_json = defaultdict(set)
    for r in resultats:
        for motif, detail in r.get("json", []):
            motifs_json[motif] += 1
            fichiers_json[motif].add(Path(r["fichier"]).name)
            exemples_json.setdefault(motif, detail)
    motifs_modele, fichiers_modele, exemples_modele = Counter(), defaultdict(set), {}
    for r in resultats:
        for d in r.get("modele", []):
            m = re.sub(r"\[\d+\]", "[]", d.split(" : ")[0])
            motifs_modele[m] += 1
            fichiers_modele[m].add(Path(r["fichier"]).name)
            exemples_modele.setdefault(m, d[:200])
    originaux = [r for r in resultats if "original_ouvert" in r]
    t = [f"# Lot 2, contrôle A : relecture par ArcGIS Pro {arcpy.GetInstallInfo()['Version']}", "",
         f"{time.strftime('%d.%m.%Y %H:%M')} · {len(resultats)} fichiers · {duree / 60:.1f} min", ""]
    for etat, n in etats.most_common():
        t.append(f"- {etat} : **{n}**")
    if originaux:
        t.append(f"- .lyrx d'origine ouverts par ArcGIS : {sum(r['original_ouvert'] for r in originaux)} sur {len(originaux)}")
    t += ["", "## Propriétés effacées ou modifiées par ArcGIS (JSON)", "",
          "| Motif | Fois | Fichiers | Exemple |", "|---|---|---|---|"]
    for m, n in motifs_json.most_common(60):
        t.append(f"| `{m}` | {n} | {len(fichiers_json[m])} | `{exemples_json[m][:120]}` |")
    t += ["", "## Changements de sens (modèle neutre relu avant / après ArcGIS)", "",
          "| Endroit | Fois | Fichiers | Exemple |", "|---|---|---|---|"]
    for m, n in motifs_modele.most_common(60):
        t.append(f"| `{m}` | {n} | {len(fichiers_modele[m])} | {exemples_modele[m]} |")
    t += ["", "## Refus et erreurs", ""]
    for r in resultats:
        if r["etat"] in ("refusé par ArcGIS", "erreur interne", "conversion impossible"):
            t.append(f"- {Path(r['fichier']).name} : {r['etat']} : {r.get('erreur', '')[:200]}")
        if r.get("original_ouvert") is False:
            t.append(f"- {Path(r['fichier']).name} : l'original n'ouvre pas non plus : {r.get('original_erreur')}")
    (sortie / "resume.md").write_text("\n".join(t) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
