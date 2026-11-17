"""Lot 2 : ArcGIS Pro dessine une symbologie sur les vraies données (une image par fichier).

    & "C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe" outils\\lot2\\dessin_arcgis.py ^
        FICHIERS... --role avant|apres --donnees DOSSIER_SHP --sortie DOSSIER

- `--role apres` (fichiers .qlr / .qml d'origine) : le cœur les convertit en .lyrx, ArcGIS les dessine
  sur l'emprise notée par QGIS (`<nom>.emprise.json`) ;
- `--role avant` (fichiers .lyrx d'origine) : ArcGIS dessine le fichier tel quel, sur ses propres
  données, et note l'emprise pour QGIS.

Lot 2.1 (corpus sans données) : si `--donnees` contient `<nom>.plan.json` (fabriqué par
`fabriquer_donnees.py`), chaque couche lit sa table de `<nom>.gpkg`, sans requête de définition,
et l'image couvre toute la grille de cases.

Aucun fond de plan : la carte est vidée avant d'ajouter la couche. Image : `<nom>.avant.png` ou
`<nom>.apres.png` ; les .lyrx produits sont gardés dans `<sortie>/lyrx/`.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "src"))
from lyrx2qlr import api  # noqa: E402
from lyrx2qlr.catalogue import Catalogue  # noqa: E402
from lyrx2qlr.rapport import Rapport  # noqa: E402

import arcpy  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # noms de fichiers en hébreu, etc.

PROJET_VIDE = Path(r"C:\Program Files\ArcGIS\Pro\Resources\ArcToolBox\Services\routingservices\data\Blank.aprx")
LARGEUR, HAUTEUR, DPI = 800, 620, 96


def plan_corpus(donnees: Path, nom: str) -> dict | None:
    """Plan des données fabriquées (lot 2.1), ou None pour les exemples à vraies données."""
    f = donnees / f"{nom}.plan.json"
    if not f.exists():
        return None
    plan = json.loads(f.read_text(encoding="utf-8"))
    plan["gpkg"] = str(donnees / f"{nom}.gpkg")
    return plan


def convertir(qlr: Path, donnees: Path, cible: Path, cat: Catalogue, plan: dict | None = None) -> str:
    rapport = Rapport(fichier=qlr.name)
    doc = api.lire(qlr.read_bytes(), qlr.name, cat, rapport)
    tables = {c["numero"]: c["table"] for c in plan["couches"]} if plan else {}
    for i, c in enumerate(doc.couches):
        c.source.dossier = str(donnees)
        c.source.a_reconnecter = False
        if c.source.type == "inconnu":
            c.source.type = "shapefile"
        if plan:
            c.source.type, c.source.dossier, c.source.jeu = "geopackage", plan["gpkg"], tables.get(i, "absente")
            c.filtre = None  # les données fabriquées ne suivent pas les requêtes de définition
    j = json.loads(api.ecrire(doc, ".lyrx", cat, rapport))
    cible.write_text(json.dumps(pour_le_dessin(j, donnees)), encoding="utf-8")
    return rapport.resume


SANS_POINT = RACINE / "comparaisons_lot2" / "_donnees_arcgis"


def brancher_plan(j: dict, plan: dict) -> dict:
    """.lyrx d'origine dont les couches d'entités lisent les tables fabriquées (dans l'ordre du cœur)."""
    tables = {c["numero"]: c["table"] for c in plan["couches"]}
    defs = j.get("layerDefinitions") or ([j] if "featureTable" in j else [])
    for i, d in enumerate(x for x in defs if x.get("type") == "CIMFeatureLayer"):
        table = d.setdefault("featureTable", {"type": "CIMFeatureTable"})
        table.pop("definitionExpression", None)
        table.pop("definitionFilterChoices", None)
        table["dataConnection"] = {"type": "CIMStandardDataConnection", "workspaceConnectionString": f"DATABASE={plan['gpkg']}",
                                   "workspaceFactory": "Sql", "dataset": tables.get(i, "absente"),
                                   "datasetType": "esriDTFeatureClass"}
    return j


def pour_le_dessin(j: dict, donnees: Path) -> dict:
    """Prépare un .lyrx au dessin, sans toucher à la symbologie :

    - couche rendue visible (plusieurs fichiers d'origine sont enregistrés couche masquée), sans
      étiquettes ;
    - source vers les données locales ; un shapefile dont le nom contient un point
      (« AGR.CADASTRE_VITICOLE.shp », lu sans peine par QGIS) est refusé par ArcGIS : on en dessine
      une copie nommée sans point, dans comparaisons_lot2/_donnees_arcgis/."""
    for d in j.get("layerDefinitions", []):
        if "featureTable" in d:
            d["visibility"] = True
            d["labelVisibility"] = False  # le dessin croisé juge les symboles (comme dessin_qgis)
        conn = (d.get("featureTable") or {}).get("dataConnection") or {}
        if conn.get("workspaceFactory") != "Shapefile":
            continue
        dossier, jeu = donnees, conn.get("dataset", "")
        if not jeu.lower().endswith(".shp") and (donnees / f"{jeu}.shp").exists():
            jeu += ".shp"
        nom = jeu[:-4] if jeu.lower().endswith(".shp") else jeu
        if "." in nom and (donnees / f"{nom}.shp").exists():
            SANS_POINT.mkdir(parents=True, exist_ok=True)
            propre = nom.replace(".", "_")
            for f in donnees.glob(f"{nom}.*"):
                copie = SANS_POINT / (propre + f.name[len(nom):])
                if not copie.exists():
                    shutil.copy2(f, copie)
            dossier, jeu = SANS_POINT, propre + ".shp"
        conn["workspaceConnectionString"] = f"DATABASE={dossier}"
        conn["dataset"] = jeu
    return j


def rebrancher(lyrx: Path, donnees: Path, cible: Path, plan: dict | None = None) -> None:
    """Copie d'un .lyrx d'origine prête à dessiner (voir pour_le_dessin)."""
    j = json.loads(lyrx.read_text(encoding="utf-8-sig"))
    if plan:
        j = brancher_plan(j, plan)
    cible.write_text(json.dumps(pour_le_dessin(j, donnees)), encoding="utf-8")


def emprise_ajustee(etendue, largeur: int, hauteur: int) -> tuple[float, float, float, float]:
    """Étendue agrandie de 5 % puis élargie aux proportions de l'image (comme QGIS)."""
    cx, cy = (etendue.XMin + etendue.XMax) / 2, (etendue.YMin + etendue.YMax) / 2
    l, h = etendue.width * 1.05, etendue.height * 1.05
    if l / h < largeur / hauteur:
        l = h * largeur / hauteur
    else:
        h = l * hauteur / largeur
    return cx - l / 2, cy - h / 2, cx + l / 2, cy + h / 2


def zone_dense(png: Path, e: dict) -> dict:
    """Emprise rapprochée (1/6 de la largeur) centrée sur la zone la plus dessinée de l'image."""
    import numpy as np
    from PIL import Image
    img = Image.open(png).convert("RGBA")
    p = np.asarray(Image.alpha_composite(Image.new("RGBA", img.size, "white"), img).convert("RGB")).astype(int)
    dessine = (p.min(axis=2) < 245).astype(float)
    k = max(1, img.width // 6)
    ligne = np.cumsum(np.cumsum(np.pad(dessine, ((1, 0), (1, 0))), 0), 1)
    somme = ligne[k:, k:] - ligne[:-k, k:] - ligne[k:, :-k] + ligne[:-k, :-k]
    y, x = np.unravel_index(somme.argmax(), somme.shape)
    cx, cy = (x + k / 2) / img.width, (y + k / 2) / img.height
    l, h = (e["xmax"] - e["xmin"]) / 6, (e["ymax"] - e["ymin"]) / 6
    mx, my = e["xmin"] + cx * (e["xmax"] - e["xmin"]), e["ymax"] - cy * (e["ymax"] - e["ymin"])
    return {"xmin": mx - l / 2, "ymin": my - h / 2, "xmax": mx + l / 2, "ymax": my + h / 2}


def dessiner(lyrx: Path, png: Path, projet: Path, emprise: dict | None, plan: dict | None = None) -> tuple[str, dict]:
    aprx = arcpy.mp.ArcGISProject(str(projet))
    for m in aprx.listMaps():
        aprx.deleteItem(m)
    carte = aprx.createMap("lot2")
    for fond in carte.listLayers():  # createMap ajoute un fond de carte : on le retire
        carte.removeLayer(fond)
    couches = carte.addLayer(arcpy.mp.LayerFile(str(lyrx)))
    couches = [y for x in couches for y in ([x] + (x.listLayers() if x.isGroupLayer else []))]
    c = next((x for x in couches if x.isFeatureLayer), couches[0])
    for x in couches:
        if x.supports("VISIBLE"):
            x.visible = True
        if x.isFeatureLayer and x.supports("SHOWLABELS"):
            x.showLabels = False
        if x.supports("MINTHRESHOLD"):
            x.minThreshold = 0
            x.maxThreshold = 0
    if emprise is None and plan:
        cases = [k for x in plan["couches"] for k in x["cases"]]
        sr = arcpy.SpatialReference(plan["epsg"])
        xmin, ymin, xmax, ymax = emprise_ajustee(arcpy.Extent(min(k["xmin"] for k in cases), min(k["ymin"] for k in cases),
                                                              max(k["xmax"] for k in cases), max(k["ymax"] for k in cases)),
                                                 LARGEUR, HAUTEUR)
        emprise = {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax, "wkt": sr.exportToString(),
                   "largeur": LARGEUR, "hauteur": HAUTEUR, "dpi": DPI}
    elif emprise is None:
        sr = arcpy.Describe(c.dataSource).spatialReference
        xmin, ymin, xmax, ymax = emprise_ajustee(arcpy.Describe(c.dataSource).extent, LARGEUR, HAUTEUR)
        emprise = {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax, "wkt": sr.exportToString(),
                   "largeur": LARGEUR, "hauteur": HAUTEUR, "dpi": DPI}
    try:
        carte.spatialReference = arcpy.SpatialReference(text=emprise["wkt"])
    except Exception:  # noqa: BLE001  (texte de projection écrit par QGIS non reconnu)
        carte.spatialReference = arcpy.Describe(c.dataSource).spatialReference
    vue = carte.defaultView
    vue.camera.setExtent(arcpy.Extent(emprise["xmin"], emprise["ymin"], emprise["xmax"], emprise["ymax"]))
    vue.exportToPNG(str(png), emprise["largeur"], emprise["hauteur"], emprise["dpi"])
    if "zoom" not in emprise:
        emprise["zoom"] = zone_dense(png, emprise)
    z = emprise["zoom"]
    vue.camera.setExtent(arcpy.Extent(z["xmin"], z["ymin"], z["xmax"], z["ymax"]))
    vue.exportToPNG(str(png.with_suffix(".zoom.png")), emprise["largeur"], emprise["hauteur"], emprise["dpi"])
    rendu = type(c.symbology.renderer).__name__ if hasattr(c.symbology, "renderer") else "?"
    return rendu, emprise


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("fichiers", nargs="+")
    a.add_argument("--role", choices=("avant", "apres"), required=True)
    a.add_argument("--donnees", required=True)
    a.add_argument("--sortie", required=True)
    args = a.parse_args()
    donnees, sortie = Path(args.donnees).resolve(), Path(args.sortie).resolve()
    (sortie / "lyrx").mkdir(parents=True, exist_ok=True)
    cat = Catalogue.charger()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        projet = Path(tmp) / "lot2.aprx"
        shutil.copy(PROJET_VIDE, projet)
        for f in [Path(x).resolve() for x in args.fichiers]:
            nom = f.stem
            fichier_emprise = sortie / f"{nom}.emprise.json"
            plan = plan_corpus(donnees, nom)
            try:
                if args.role == "apres":
                    if not fichier_emprise.exists():
                        print(f"{f.name} : pas d'emprise (image « avant » manquante)", flush=True)
                        continue
                    emprise = json.loads(fichier_emprise.read_text(encoding="utf-8"))
                    lyrx = sortie / "lyrx" / f"{nom}.lyrx"
                    (sortie / f"{nom}.rapport.txt").write_text(convertir(f, donnees, lyrx, cat, plan), encoding="utf-8")
                else:
                    emprise = None
                    lyrx = Path(tmp) / f"{nom}.lyrx"
                    rebrancher(f, donnees, lyrx, plan)
                rendu, emprise = dessiner(lyrx, sortie / f"{nom}.{args.role}.png", projet, emprise, plan)
                emprise[f"logiciel_{args.role}"], emprise[f"rendu_{args.role}"] = "ArcGIS Pro", rendu
                fichier_emprise.write_text(json.dumps(emprise, indent=1), encoding="utf-8")
                print(f"{f.name} : rendu {rendu}", flush=True)
            except Exception as e:  # noqa: BLE001
                (sortie / f"{nom}.{args.role}.erreur.txt").write_text(str(e), encoding="utf-8")
                print(f"{f.name} : ÉCHEC {str(e).strip().splitlines()[-1][:200]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
