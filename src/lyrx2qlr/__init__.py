"""lyrx2qlr — conversion de symbologies entre ArcGIS Pro (.lyrx) et QGIS (.qlr), dans les deux sens.

Usage minimal :
    from lyrx2qlr import convertir_fichier
    resultat = convertir_fichier("ma_couche.lyrx")      # écrit ma_couche.qlr à côté
    print(resultat.rapport.en_texte())                  # ce qui n'a pas été converti

Le cœur n'utilise que la bibliothèque standard de Python : il tourne tel quel
dans QGIS, dans un navigateur (Pyodide) ou en ligne de commande.
"""
from .api import Resultat, convertir, convertir_fichier, convertir_lot, ecrire, lire, lister_fichiers
from .catalogue import Catalogue, ErreurCatalogue, catalogue_defaut
from .rapport import Rapport

__version__ = "1.9.1"

__all__ = ["Catalogue", "ErreurCatalogue", "Rapport", "Resultat", "catalogue_defaut", "convertir",
           "convertir_fichier", "convertir_lot", "ecrire", "lire", "lister_fichiers", "__version__"]
