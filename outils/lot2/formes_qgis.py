"""Lot 2, contrôle D : mesure l'encombrement des formes de marqueurs simples de QGIS.

    .\\outils\\py.ps1 outils\\lot2\\formes_qgis.py --sortie comparaisons_lot2\\polices\\formes_qgis.json

Pour chaque forme, QGIS dessine un marqueur de taille 200 pixels ; on mesure la plus grande dimension
dessinée, rapportée à la taille demandée. Avec la taille d'un glyphe de police (mesurée par
polices_esri.py), on en tire le « facteur_taille » des remplacements de polices.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from qgis.core import QgsApplication, QgsMarkerSymbol, QgsRenderContext, QgsUnitTypes
from qgis.PyQt.QtCore import QPointF, QSize
from qgis.PyQt.QtGui import QColor, QImage, QPainter

FORMES = ["circle", "square", "equilateral_triangle", "triangle", "pentagon", "hexagon", "octagon", "diamond",
          "star", "cross", "cross2", "cross_fill", "line", "arrowhead", "heart", "trapezoid"]
TAILLE = 200


def mesurer(forme: str) -> dict:
    image = QImage(QSize(400, 400), QImage.Format_ARGB32)
    image.fill(QColor("white"))
    p = QPainter(image)
    ctx = QgsRenderContext.fromQPainter(p)
    s = QgsMarkerSymbol.createSimple({"name": forme, "size": str(TAILLE), "size_unit": "Pixel", "color": "0,0,0,255",
                                      "outline_style": "no", "outline_color": "0,0,0,255", "outline_width": "4",
                                      "outline_width_unit": "Pixel"})
    if forme in ("cross", "cross2", "line", "arrowhead"):  # formes faites de traits : dessinées par le contour
        s.symbolLayer(0).setStrokeStyle(1)
    s.startRender(ctx)
    s.renderPoint(QPointF(200, 200), None, ctx)
    s.stopRender(ctx)
    p.end()
    largeur = hauteur = 0
    xs, ys = [], []
    for y in range(image.height()):
        for x in range(0, image.width()):
            if QColor(image.pixel(x, y)).lightness() < 128:
                xs.append(x)
                ys.append(y)
    if xs:
        largeur, hauteur = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
    return {"largeur": round(largeur / TAILLE, 3), "hauteur": round(hauteur / TAILLE, 3),
            "encombrement": round(max(largeur, hauteur) / TAILLE, 3)}


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--sortie", required=True)
    args = a.parse_args()
    sortie = Path(args.sortie).resolve()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QgsApplication([], False)
    app.initQgis()
    mesures = {f: mesurer(f) for f in FORMES}
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps(mesures, indent=1), encoding="utf-8")
    for f, m in mesures.items():
        print(f"{f:22} {m}")
    app.exitQgis()
    return 0


if __name__ == "__main__":
    sys.exit(main())
