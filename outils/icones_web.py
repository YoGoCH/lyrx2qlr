r"""Icônes de l'application installable (web/icone-192.png, web/icone-512.png), sur fond crème.

    $env:QT_QPA_PLATFORM="offscreen"; .\outils\py.ps1 outils\icones_web.py

Part de l'icône de l'extension QGIS : ses pointes de flèche sont des triangles, que le moteur SVG
de Qt sait dessiner (web/icon.svg utilise des « markers », qu'il ignore).
"""
import sys
from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QColor, QGuiApplication, QImage, QPainter
from PyQt5.QtSvg import QSvgRenderer
app = QGuiApplication(sys.argv[:1])
svg = QSvgRenderer("qgis_plugin/lyrx2qlr_qgis/icon.svg")
for taille in (192, 512):
    image = QImage(taille, taille, QImage.Format_ARGB32)
    image.fill(QColor("#fff6ec"))
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)
    marge = taille * 0.16   # zone sûre des icônes « maskable » (80 %)
    svg.render(p, QRectF(marge, marge, taille - 2 * marge, taille - 2 * marge))
    p.end()
    image.save(f"web/icone-{taille}.png")
    print(taille, "ok")
