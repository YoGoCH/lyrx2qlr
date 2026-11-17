"""Lot 2 : QGIS dessine une symbologie sur les vraies données (une image par fichier).

    .\\outils\\py.ps1 outils\\lot2\\dessin_qgis.py FICHIERS... --role avant|apres --donnees DOSSIER_SHP --sortie DOSSIER

- `--role avant` (fichiers .qlr / .qml d'origine) : QGIS dessine le fichier tel quel et note l'emprise
  exacte dans `<nom>.emprise.json`, que l'autre logiciel reprendra ;
- `--role apres` (fichiers .lyrx d'origine) : le cœur convertit le .lyrx en .qlr, puis QGIS le dessine
  sur l'emprise déjà notée par ArcGIS.

Image : `<nom>.avant.png` ou `<nom>.apres.png`. Les données restent dans leur dossier (ignoré par git).

Lot 2.1 (corpus sans données) : si `--donnees` contient `<nom>.plan.json` (fabriqué par
`fabriquer_donnees.py`), chaque couche est branchée sur sa table de `<nom>.gpkg` et l'image
couvre toute la grille de cases. Un .qml (style seul) est appliqué à une couche ouverte sur la table.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import xml.etree.ElementTree as ET

from qgis.core import (QgsApplication, QgsCoordinateReferenceSystem, QgsLayerDefinition, QgsMapRendererParallelJob,
                       QgsMapSettings, QgsProject, QgsRectangle, QgsVectorLayer)
from qgis.PyQt.QtCore import QCoreApplication, QSize
from qgis.PyQt.QtGui import QColor, QImage

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from lyrx2qlr import api  # noqa: E402
from lyrx2qlr.catalogue import Catalogue  # noqa: E402
from lyrx2qlr.rapport import Rapport  # noqa: E402

LARGEUR, HAUTEUR, DPI = 800, 620, 96
LIMITE = 60  # secondes par dessin


def zone_dense(image: QImage, e: dict) -> dict:
    """Emprise rapprochée (1/6 de la largeur) centrée sur la zone la plus dessinée de l'image."""
    import numpy as np
    image = image.convertToFormat(QImage.Format_RGB32)
    tampon = image.constBits()
    tampon.setsize(image.sizeInBytes())
    p = np.frombuffer(tampon, np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)[:, :image.width(), :3]
    dessine = (p.min(axis=2) < 245).astype(float)
    k = max(1, image.width() // 6)
    ligne = np.cumsum(np.cumsum(np.pad(dessine, ((1, 0), (1, 0))), 0), 1)
    somme = ligne[k:, k:] - ligne[:-k, k:] - ligne[k:, :-k] + ligne[:-k, :-k]
    y, x = np.unravel_index(somme.argmax(), somme.shape)
    cx, cy = (x + k / 2) / image.width(), (y + k / 2) / image.height()
    l, h = (e["xmax"] - e["xmin"]) / 6, (e["ymax"] - e["ymin"]) / 6
    mx, my = e["xmin"] + cx * (e["xmax"] - e["xmin"]), e["ymax"] - cy * (e["ymax"] - e["ymin"])
    return {"xmin": mx - l / 2, "ymin": my - h / 2, "xmax": mx + l / 2, "ymax": my + h / 2}


def rendre(r: QgsMapSettings) -> QImage | None:
    travail = QgsMapRendererParallelJob(r)
    debut = time.time()
    travail.start()
    while travail.isActive():  # hachures très serrées à petite échelle : on abandonne après LIMITE secondes
        QCoreApplication.processEvents()
        time.sleep(0.05)
        if time.time() - debut > LIMITE:
            travail.cancel()
            return None
    return travail.renderedImage()


def plan_corpus(donnees: Path, nom: str) -> dict | None:
    """Plan des données fabriquées (lot 2.1), ou None pour les exemples à vraies données."""
    f = donnees / f"{nom}.plan.json"
    if not f.exists():
        return None
    plan = json.loads(f.read_text(encoding="utf-8"))
    plan["gpkg"] = (donnees / f"{nom}.gpkg").as_posix()
    return plan


def emprise_plan(plan: dict) -> QgsRectangle:
    cases = [k for c in plan["couches"] for k in c["cases"]]
    r = QgsRectangle(min(k["xmin"] for k in cases), min(k["ymin"] for k in cases),
                     max(k["xmax"] for k in cases), max(k["ymax"] for k in cases))
    return r


def rebrancher_qlr(qlr: bytes, plan: dict) -> bytes:
    """.qlr d'origine dont les couches vectorielles lisent les tables fabriquées (dans l'ordre)."""
    racine = ET.fromstring(qlr)
    tables = {c["numero"]: c["table"] for c in plan["couches"]}
    for i, ml in enumerate(x for x in racine.iter("maplayer") if x.get("type") == "vector"):
        if i not in tables:
            continue
        ml.find("datasource").text = f"{plan['gpkg']}|layername={tables[i]}"
        fournisseur = ml.find("provider")
        if fournisseur is None:
            fournisseur = ET.SubElement(ml, "provider")
        fournisseur.text = "ogr"
    return ET.tostring(racine, encoding="utf-8")


def dessiner(qlr: Path, sortie: Path, nom: str, role: str, plan: dict | None = None) -> str:
    projet = QgsProject()
    if qlr.suffix.lower() == ".qml":  # style seul : appliqué à la table fabriquée
        c = plan["couches"][0]
        couche = QgsVectorLayer(f"{plan['gpkg']}|layername={c['table']}", c["nom"], "ogr")
        message, ok = couche.loadNamedStyle(str(qlr))
        erreur = "" if ok else message
        projet.addMapLayer(couche)
    else:
        ok, erreur = QgsLayerDefinition.loadLayerDefinition(str(qlr), projet, projet.layerTreeRoot())
    couches = [x for x in (n.layer() for n in projet.layerTreeRoot().findLayers()) if x is not None] or list(projet.mapLayers().values())
    if not ok or not couches or not couches[0].isValid():
        return f"couche invalide ({erreur or 'source introuvable'})"
    c = couches[0]
    for x in couches:
        if not isinstance(x, QgsVectorLayer):
            continue
        x.setScaleBasedVisibility(False)  # on montre tout, quelle que soit l'échelle
        # Étiquettes coupées : le dessin croisé juge les symboles. Les polices d'étiquettes manquent souvent
        # au rendu hors écran (pavés noirs) et ArcGIS place ses étiquettes autrement.
        x.setLabelsEnabled(False)
    r = QgsMapSettings()
    r.setLayers(couches)
    r.setOutputSize(QSize(LARGEUR, HAUTEUR))
    r.setOutputDpi(DPI)
    r.setBackgroundColor(QColor("white"))
    fichier_emprise = sortie / f"{nom}.emprise.json"
    if role == "apres":
        if not fichier_emprise.exists():
            return "pas d'emprise : l'image « avant » manque"
        e = json.loads(fichier_emprise.read_text(encoding="utf-8"))
        crs = QgsCoordinateReferenceSystem.fromWkt(e["wkt"])
        r.setDestinationCrs(crs if crs.isValid() else c.crs())
        r.setExtent(QgsRectangle(e["xmin"], e["ymin"], e["xmax"], e["ymax"]))
    else:
        etendue = emprise_plan(plan) if plan else QgsRectangle(c.extent())
        etendue.scale(1.05)
        r.setDestinationCrs(c.crs())
        r.setExtent(etendue)
    image = rendre(r)
    if image is None:
        return f"dessin abandonné après {LIMITE} s (trop d'éléments à cette échelle)"
    image.save(str(sortie / f"{nom}.{role}.png"), "PNG")
    if role == "avant":
        v = r.visibleExtent()  # étendue réellement dessinée (ajustée aux proportions de l'image)
        e = {"xmin": v.xMinimum(), "ymin": v.yMinimum(), "xmax": v.xMaximum(), "ymax": v.yMaximum(),
             "wkt": c.crs().toWkt(), "largeur": LARGEUR, "hauteur": HAUTEUR, "dpi": DPI,
             "logiciel_avant": "QGIS", "rendu_avant": c.renderer().type(), "echelle": r.scale()}
        e["zoom"] = zone_dense(image, e)
    else:
        e["logiciel_apres"], e["rendu_apres"] = "QGIS", c.renderer().type()
    z = e["zoom"]
    r.setExtent(QgsRectangle(z["xmin"], z["ymin"], z["xmax"], z["ymax"]))
    image = rendre(r)
    if image is not None:
        image.save(str(sortie / f"{nom}.{role}.zoom.png"), "PNG")
    fichier_emprise.write_text(json.dumps(e, indent=1), encoding="utf-8")
    return f"{c.featureCount()} entités, rendu {c.renderer().type()}"


def preparer(f: Path, donnees: Path, tmp: Path, role: str, cat: Catalogue, plan: dict | None) -> tuple[Path, str]:
    if role == "avant":
        copie = tmp / f.name
        if plan is None:
            copie.write_bytes(f.read_bytes().replace(b"./", donnees.as_posix().encode() + b"/"))
        elif f.suffix.lower() == ".qlr":
            copie.write_bytes(rebrancher_qlr(f.read_bytes(), plan))
        else:
            copie.write_bytes(f.read_bytes())
        return copie, ""
    rapport = Rapport(fichier=f.name)
    doc = api.lire(f.read_bytes(), f.name, cat, rapport)
    tables = {c["numero"]: c["table"] for c in plan["couches"]} if plan else {}
    for i, c in enumerate(doc.couches):
        c.source.dossier = donnees.as_posix()
        c.source.a_reconnecter = False
        if c.source.type == "inconnu":
            c.source.type = "shapefile"
        if plan:
            c.source.type, c.source.dossier, c.source.jeu = "geopackage", plan["gpkg"], tables.get(i, "absente")
            c.source.chemin_qgis = c.source.fournisseur_qgis = None
            c.filtre = None  # les données fabriquées ne suivent pas les requêtes de définition
    qlr = tmp / (f.stem + ".qlr")
    qlr.write_bytes(api.ecrire(doc, ".qlr", cat, rapport))
    return qlr, rapport.resume


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("fichiers", nargs="+")
    a.add_argument("--role", choices=("avant", "apres"), required=True)
    a.add_argument("--donnees", required=True)
    a.add_argument("--sortie", required=True)
    args = a.parse_args()
    # Résolus tout de suite : QGIS change le dossier courant pendant son démarrage.
    fichiers = [Path(x).resolve() for x in args.fichiers]
    donnees, sortie = Path(args.donnees).resolve(), Path(args.sortie).resolve()
    sortie.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QgsApplication([], True)
    app.initQgis()
    cat = Catalogue.charger()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        for f in fichiers:
            plan = plan_corpus(donnees, f.stem)
            qlr, resume = preparer(f, donnees, Path(tmp), args.role, cat, plan)
            info = dessiner(qlr, sortie, f.stem, args.role, plan)
            if resume:
                (sortie / f"{f.stem}.rapport.txt").write_text(resume, encoding="utf-8")
            print(f"{f.name} : {info}", flush=True)
    app.exitQgis()
    return 0


if __name__ == "__main__":
    sys.exit(main())
