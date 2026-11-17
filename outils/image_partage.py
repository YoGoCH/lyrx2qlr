"""Dessine l'image d'aperçu de partage de la page web (web/apercu.png, 1200 × 630, balise og:image).

    .\\outils\\py.ps1 outils\\image_partage.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from qgis.PyQt.QtCore import QPointF, QRectF, Qt
from qgis.PyQt.QtGui import QBrush, QColor, QFont, QGuiApplication, QImage, QPainter, QPainterPath, QPen, QPolygonF

RACINE = Path(__file__).resolve().parent.parent
FOND, TEXTE, DOUX, ACCENT, CLAIR = "#f6f7f5", "#1d2321", "#5c6662", "#2f6b4f", "#e3efe8"


def carte(p: QPainter, x: float, titre: str, hachures: bool) -> None:
    """Une « carte » de fichier avec une petite surface symbolisée."""
    cadre = QRectF(x, 250, 300, 300)
    p.setPen(QPen(QColor("#d6dbd8"), 3))
    p.setBrush(QColor("white"))
    p.drawRoundedRect(cadre, 24, 24)
    forme = QPolygonF([QPointF(x + 60, 330), QPointF(x + 210, 300), QPointF(x + 255, 400),
                       QPointF(x + 190, 470), QPointF(x + 75, 450)])
    chemin = QPainterPath()
    chemin.addPolygon(forme)
    chemin.closeSubpath()
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(CLAIR))
    p.drawPath(chemin)
    p.save()
    p.setClipPath(chemin)
    if hachures:
        p.setPen(QPen(QColor(ACCENT), 4))
        for i in range(-300, 300, 22):
            p.drawLine(QPointF(x + i, 500), QPointF(x + i + 300, 280))
    else:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(ACCENT))
        for cx in range(int(x) + 50, int(x) + 280, 30):
            for cy in range(290, 490, 30):
                p.drawEllipse(QPointF(cx, cy), 6, 6)
    p.restore()
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(TEXTE), 4))
    p.drawPath(chemin)
    p.setPen(QColor(TEXTE))
    p.setFont(QFont("Segoe UI", 30, QFont.Bold))
    p.drawText(QRectF(x, 485, 300, 60), Qt.AlignCenter, titre)


def main() -> int:
    app = QGuiApplication(sys.argv)  # noqa: F841 (nécessaire pour les polices)
    image = QImage(1200, 630, QImage.Format_RGB32)
    image.fill(QColor(FOND))
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    p.setPen(QColor(TEXTE))
    p.setFont(QFont("Segoe UI", 64, QFont.Bold))
    p.drawText(QRectF(80, 50, 1040, 100), Qt.AlignLeft | Qt.AlignVCenter, "lyrx2qlr")
    p.setPen(QColor(DOUX))
    p.setFont(QFont("Segoe UI", 26))
    p.drawText(QRectF(80, 145, 1040, 60), Qt.AlignLeft | Qt.AlignVCenter,
               "Symbologies ArcGIS Pro ⇄ QGIS, dans le navigateur")
    carte(p, 80, ".lyrx", True)
    carte(p, 480, ".qlr", True)
    # flèches aller-retour
    p.setPen(QPen(QColor(ACCENT), 8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    for y, sens in ((370, 1), (430, -1)):
        a, b = (395, 465) if sens == 1 else (465, 395)
        p.drawLine(QPointF(a, y), QPointF(b, y))
        p.drawLine(QPointF(b, y), QPointF(b - 18 * sens, y - 14))
        p.drawLine(QPointF(b, y), QPointF(b - 18 * sens, y + 14))
    # points forts
    p.setFont(QFont("Segoe UI", 24))
    for i, ligne in enumerate(["Dans les deux sens,", "et par lots", "Rapport de ce qui", "n'est pas converti",
                               "Gratuit, sans envoi", "de vos fichiers"]):
        if i % 2 == 0:
            p.setBrush(QColor(ACCENT))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(855, 292 + i * 44), 7, 7)
        p.setPen(QColor(TEXTE))
        p.drawText(QRectF(878, 270 + i * 44, 300, 44), Qt.AlignLeft | Qt.AlignVCenter, ligne)
    p.setPen(QColor(DOUX))
    p.setFont(QFont("Segoe UI", 20))
    p.drawText(QRectF(80, 570, 1040, 40), Qt.AlignRight | Qt.AlignVCenter, "lyrx2qlr.papetche.ch")
    p.end()
    sortie = RACINE / "web" / "apercu.png"
    if not image.save(str(sortie), "PNG"):
        print("Image non enregistrée", file=sys.stderr)
        return 1
    print(f"{sortie.relative_to(RACINE)} : {image.width()} × {image.height()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
