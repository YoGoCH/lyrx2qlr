"""Fait dessiner par QGIS les couches converties, sur de vraies données, pour un contrôle à l'œil.

    .\\outils\\py.ps1 outils\\apercu_qgis.py FICHIERS.lyrx... --donnees DOSSIER_SHP [--sortie sorties/apercus]
                                         [--reference DOSSIER_QLR]

Pour chaque .lyrx : conversion par le cœur, chargement dans QGIS sur le shapefile du même nom
trouvé dans --donnees, puis image PNG. Avec --reference, un .qlr de même nom (par exemple celui
produit autrefois par FME) est dessiné à droite pour comparer.
Les données ne sont jamais copiées dans le dépôt (dossier donnees_locales/ ignoré par git).
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from qgis.core import (QgsApplication, QgsLayerDefinition, QgsMapRendererParallelJob, QgsMapSettings, QgsProject,
                       QgsRectangle)
from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtGui import QColor, QFont, QImage, QPainter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from lyrx2qlr import api  # noqa: E402
from lyrx2qlr.catalogue import Catalogue  # noqa: E402
from lyrx2qlr.rapport import Rapport  # noqa: E402

TAILLE = QSize(800, 620)


def dessiner(qlr: Path, titre: str) -> tuple[QImage, str]:
    projet = QgsProject()
    ok, erreur = QgsLayerDefinition.loadLayerDefinition(str(qlr), projet, projet.layerTreeRoot())
    image = QImage(TAILLE, QImage.Format_ARGB32)
    image.fill(QColor("white"))
    couches = list(projet.mapLayers().values())
    if not ok or not couches or not couches[0].isValid():
        return image, f"{titre} : couche invalide ({erreur or 'source introuvable'})"
    c = couches[0]
    c.setScaleBasedVisibility(False)  # aperçu : on montre tout, quelle que soit l'échelle
    etendue = QgsRectangle(c.extent())
    etendue.scale(1.05)
    reglages = QgsMapSettings()
    reglages.setLayers(couches)
    reglages.setDestinationCrs(c.crs())
    reglages.setOutputSize(TAILLE)
    reglages.setExtent(etendue)
    reglages.setBackgroundColor(QColor("white"))
    travail = QgsMapRendererParallelJob(reglages)
    travail.start()
    travail.waitForFinished()
    image = travail.renderedImage()
    return image, f"{titre} : {c.featureCount()} entités, rendu {c.renderer().type()}"


def assembler(images: list[tuple[QImage, str]], chemin: Path) -> None:
    largeur = TAILLE.width() * len(images)
    hauteur = TAILLE.height() + 30
    feuille = QImage(QSize(largeur, hauteur), QImage.Format_ARGB32)
    feuille.fill(QColor("white"))
    p = QPainter(feuille)
    p.setFont(QFont("Arial", 10))
    for i, (img, texte) in enumerate(images):
        p.drawImage(i * TAILLE.width(), 30, img)
        p.setPen(QColor("black"))
        p.drawText(i * TAILLE.width() + 8, 20, texte)
        p.setPen(QColor(180, 180, 180))
        p.drawLine(i * TAILLE.width(), 0, i * TAILLE.width(), hauteur)
    p.end()
    if not feuille.save(str(chemin.resolve()), "PNG"):
        print(f"Image non enregistrée : {chemin}", file=sys.stderr)


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("fichiers", nargs="+")
    a.add_argument("--donnees", required=True)
    a.add_argument("--sortie", default="sorties/apercus")
    a.add_argument("--reference")
    args = a.parse_args()
    # Résolus tout de suite : QGIS change le dossier courant pendant son démarrage.
    fichiers = [Path(x).resolve() for x in args.fichiers]
    reference = Path(args.reference).resolve() if args.reference else None
    sortie = Path(args.sortie).resolve()
    donnees = Path(args.donnees).resolve()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QgsApplication([], True)
    app.initQgis()
    cat = Catalogue.charger()
    sortie.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        for f in fichiers:
            rapport = Rapport(fichier=f.name)
            doc = api.lire(f.read_bytes(), f.name, cat, rapport)
            for c in doc.couches:
                c.source.dossier = donnees.as_posix()
                c.source.a_reconnecter = False
                if c.source.type == "inconnu":
                    c.source.type = "shapefile"
            qlr = Path(tmp) / (f.stem + ".qlr")
            qlr.write_bytes(api.ecrire(doc, ".qlr", cat, rapport))
            images = [dessiner(qlr, "converti par lyrx2qlr")]
            if reference:
                ref = reference / (f.stem + ".qlr")
                if ref.exists():
                    copie = Path(tmp) / ("ref_" + ref.name)
                    copie.write_bytes(ref.read_bytes().replace(b"./", donnees.as_posix().encode() + b"/"))
                    images.append(dessiner(copie, "référence (ancien .qlr FME)"))
            assembler(images, sortie / (f.stem + ".png"))
            print(f"{f.name} : {images[0][1]} | {rapport.resume}")
    app.exitQgis()
    return 0


if __name__ == "__main__":
    sys.exit(main())
