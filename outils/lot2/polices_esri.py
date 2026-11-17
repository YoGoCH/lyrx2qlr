"""Lot 2, contrôle D : vérifie les remplacements des polices ESRI (catalogues/polices.json) dans QGIS.

    .\\outils\\py.ps1 outils\\lot2\\polices_esri.py --sortie comparaisons_lot2\\polices

QGIS charge les polices ESRI depuis le dossier d'ArcGIS Pro (sans les installer). Pour chaque
remplacement du catalogue :

1. un .lyrx minimal avec ce caractère (CIMCharacterMarker, taille 40 pt) est converti par le cœur ;
2. QGIS dessine **le vrai glyphe** (marqueur de police) et **notre remplacement**, au même endroit ;
3. on mesure leur recouvrement (intersection / union des pixels dessinés) et l'écart de taille.

Résultat : `polices.png` (glyphe en noir, remplacement en rose par-dessus, à moitié transparent),
`polices.md` (tableau). Un recouvrement sous 70 % signale un remplacement à revoir.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from qgis.core import QgsApplication, QgsReadWriteContext, QgsRenderContext, QgsSymbolLayerUtils
from qgis.PyQt.QtCore import QPointF, QSize
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter
from qgis.PyQt.QtXml import QDomDocument

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from lyrx2qlr import api  # noqa: E402
from lyrx2qlr.catalogue import Catalogue  # noqa: E402

POLICES = Path(r"C:\Program Files\ArcGIS\Pro\Resources\Fonts")
CASE = 160      # pixels
TAILLE = 40     # points
DPI = 96


def lyrx_caractere(police: str, code: int) -> bytes:
    marqueur = {"type": "CIMCharacterMarker", "enable": True, "fontFamilyName": police, "characterIndex": code,
                "size": TAILLE, "anchorPointUnits": "Relative", "scaleX": 1,
                "symbol": {"type": "CIMPolygonSymbol", "symbolLayers": [
                    {"type": "CIMSolidFill", "enable": True, "color": {"type": "CIMRGBColor", "values": [0, 0, 0, 100]}}]}}
    couche = {"type": "CIMFeatureLayer", "name": "p", "uRI": "CIMPATH=p.json", "visibility": True,
              "featureTable": {"type": "CIMFeatureTable", "dataConnection": {
                  "type": "CIMStandardDataConnection", "workspaceConnectionString": "DATABASE=.", "workspaceFactory": "Shapefile",
                  "dataset": "p.shp", "datasetType": "esriDTFeatureClass"}},
              "renderer": {"type": "CIMSimpleRenderer", "symbol": {"type": "CIMSymbolReference", "symbol": {
                  "type": "CIMPointSymbol", "symbolLayers": [marqueur]}}}}
    return json.dumps({"type": "CIMLayerDocument", "layers": ["CIMPATH=p.json"], "layerDefinitions": [couche]}).encode()


def symbole_qgis(qlr: bytes):
    doc = QDomDocument()
    doc.setContent(qlr)
    elem = doc.elementsByTagName("symbol").at(0).toElement()
    return QgsSymbolLayerUtils.loadSymbol(elem, QgsReadWriteContext())


def dessiner(symbole) -> QImage:
    image = QImage(QSize(CASE, CASE), QImage.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    p = QPainter(image)
    ctx = QgsRenderContext.fromQPainter(p)
    ctx.setScaleFactor(DPI / 25.4)
    symbole.startRender(ctx)
    symbole.renderPoint(QPointF(CASE / 2, CASE / 2), None, ctx)
    symbole.stopRender(ctx)
    p.end()
    return image


def masque(image: QImage) -> set:
    return {(x, y) for y in range(image.height()) for x in range(image.width()) if QColor.fromRgba(image.pixel(x, y)).alpha() > 128}


def centrer(m: set) -> set:
    """Masque recentré sur le centre de son cadre : QGIS place un glyphe de police un peu plus bas que
    le point (ligne de base), ce qu'on ne veut pas compter comme une différence de forme."""
    if not m:
        return m
    xs, ys = [x for x, _ in m], [y for _, y in m]
    dx, dy = round((min(xs) + max(xs)) / 2), round((min(ys) + max(ys)) / 2)
    return {(x - dx, y - dy) for x, y in m}


def encombrement(m: set) -> float:
    if not m:
        return 0
    xs, ys = [x for x, _ in m], [y for _, y in m]
    return max(max(xs) - min(xs), max(ys) - min(ys)) + 1


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--sortie", required=True)
    args = a.parse_args()
    sortie = Path(args.sortie).resolve()
    sortie.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QgsApplication([], False)
    app.initQgis()
    for f in POLICES.glob("esri_*.ttf"):
        QFontDatabase.addApplicationFont(str(f))
    cat = Catalogue.charger()
    subs = cat.polices["substitutions"]
    colonnes = 8
    feuille = QImage(QSize(colonnes * CASE, ((len(subs) + colonnes - 1) // colonnes) * (CASE + 20)), QImage.Format_ARGB32)
    feuille.fill(QColor("#fff6ec"))
    peintre = QPainter(feuille)
    mesures = []
    lignes = ["# Remplacements des polices ESRI vérifiés dans QGIS", "",
              "Glyphe d'origine dessiné par QGIS avec la police d'ArcGIS Pro, comparé au marqueur simple "
              "écrit par lyrx2qlr.", "",
              "| Police | Caractère | Forme | Rendu | Recouvrement | Taille (remplacement / glyphe) |", "|---|---|---|---|---|---|"]
    for i, s in enumerate(subs):
        lyrx = lyrx_caractere(s["police"], s["caractere"])
        doc = api.lire(lyrx, "p.lyrx", cat)
        # le glyphe : marqueur de police, sans remplacement
        sans = Catalogue(json.loads(json.dumps(cat.d)))
        sans.d["polices"]["substitutions"] = []
        glyphe = dessiner(symbole_qgis(api.ecrire(doc, ".qlr", sans)))
        rempl = dessiner(symbole_qgis(api.ecrire(doc, ".qlr", cat)))
        mg, mr = masque(glyphe), masque(rempl)
        cg, cr = centrer(mg), centrer(mr)
        recouvrement = len(cg & cr) / max(1, len(cg | cr))
        rapport_taille = encombrement(mr) / max(1, encombrement(mg))
        x, y = (i % colonnes) * CASE, (i // colonnes) * (CASE + 20)
        case = QImage(QSize(CASE, CASE), QImage.Format_ARGB32)
        case.fill(QColor("white"))
        p = QPainter(case)
        p.drawImage(0, 0, glyphe)
        p.setOpacity(0.55)
        teinte = QImage(rempl)
        for yy in range(teinte.height()):
            for xx in range(teinte.width()):
                if QColor.fromRgba(teinte.pixel(xx, yy)).alpha() > 128:
                    teinte.setPixelColor(xx, yy, QColor(255, 95, 162))
        p.drawImage(0, 0, teinte)
        p.end()
        peintre.drawImage(x, y + 20, case)
        lignes.append(f"| {s['police']} | {s['caractere']} | {s['forme']} | {s.get('rendu', 'plein')} | "
                      f"{recouvrement:.0%} | {rapport_taille:.2f} |")
        mesures.append({"caractere": s["caractere"], "recouvrement": round(recouvrement, 3), "taille": round(rapport_taille, 3)})
        print(f"{s['caractere']:4} {s['forme']:22} recouvrement {recouvrement:.0%}  taille {rapport_taille:.2f}", flush=True)
    # les cases suivent l'ordre du tableau polices.md (Qt n'écrit pas de texte lisible une fois les polices ESRI chargées)
    peintre.end()
    feuille.save(str(sortie / "polices.png"), "PNG")
    (sortie / "polices.json").write_text(json.dumps(mesures, indent=1), encoding="utf-8")
    (sortie / "polices.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    app.exitQgis()
    return 0


if __name__ == "__main__":
    sys.exit(main())
