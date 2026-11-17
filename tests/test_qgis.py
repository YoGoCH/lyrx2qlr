"""Vérification dans QGIS lui-même (sauté si PyQGIS n'est pas disponible).

Pour chaque exemple .lyrx :
  1. conversion en .qlr par le cœur ;
  2. QGIS charge ce .qlr (sur un shapefile vide créé pour l'occasion, de la bonne géométrie) ;
  3. QGIS réenregistre la couche en .qlr ;
  4. le cœur relit le .qlr écrit par QGIS : le modèle doit être identique à celui du .lyrx.
Si QGIS a ignoré ou mal compris une partie du .qlr produit, l'étape 4 le montre.
"""
from __future__ import annotations

import copy
import re
from pathlib import Path

import pytest

qgis_core = pytest.importorskip("qgis.core")

from conftest import EXEMPLES_LYRX, EXEMPLES_QLR, avec_exemples_reels, comparer_documents  # noqa: E402
from lyrx2qlr import api  # noqa: E402
from lyrx2qlr.modele import Source  # noqa: E402
from lyrx2qlr.rapport import Rapport  # noqa: E402

_TYPES = {"point": "Point", "ligne": "LineString", "surface": "Polygon"}


@pytest.fixture(scope="module")
def qgis_app():
    from qgis.core import QgsApplication
    app = QgsApplication.instance()
    if app is None:
        app = QgsApplication([], False)
        app.initQgis()
    yield app


def _nom_simple(n: str) -> bool:
    return n.replace("_", "").isalnum()


def _donnees_vides(dossier: Path, nom: str, couche) -> None:
    """GeoPackage vide avec la bonne géométrie et les champs cités (alias, rendu, filtre)."""
    from qgis.core import (QgsCoordinateReferenceSystem, QgsCoordinateTransformContext, QgsField, QgsFields,
                           QgsVectorFileWriter, QgsWkbTypes)
    from qgis.PyQt.QtCore import QVariant
    champs = QgsFields()
    numeriques = set(re.findall(r'"?([A-Za-z_][A-Za-z0-9_]*)"?\s*(?:=|<>|>=|<=|<|>)\s*-?\d', couche.filtre or ""))
    noms = list(couche.alias) + (couche.rendu.champs if couche.rendu else []) + sorted(numeriques)
    noms += re.findall(r'"?([A-Za-z_][A-Za-z0-9_]*)"?\s*(?:=|<>|\bIN\b|\bLIKE\b)', couche.filtre or "")
    for n in dict.fromkeys(noms):
        if _nom_simple(n):
            champs.append(QgsField(n, QVariant.Double if n in numeriques else QVariant.String))
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = nom
    wkb = QgsWkbTypes.parseType(_TYPES.get(couche.geometrie, "Polygon"))
    w = QgsVectorFileWriter.create(str(dossier / f"{nom}.gpkg"), champs, wkb,
                                   QgsCoordinateReferenceSystem("EPSG:2056"), QgsCoordinateTransformContext(), options)
    del w


def _alias_possibles(doc):
    for c in doc.couches:
        c.alias = {k: v for k, v in c.alias.items() if _nom_simple(k)}
    return doc


def _passer_par_qgis(doc, cat, dossier: Path) -> bytes:
    """Écrit le .qlr, le fait charger puis réenregistrer par QGIS ; renvoie le .qlr écrit par QGIS."""
    from qgis.core import QgsLayerDefinition, QgsProject
    doc = copy.deepcopy(doc)
    for i, c in enumerate(doc.couches):
        nom = f"donnees_{i}"
        _donnees_vides(dossier, nom, c)
        c.source = Source(type="geopackage", dossier=f"./{nom}.gpkg", jeu=nom)
    entree = dossier / "entree.qlr"
    entree.write_bytes(api.ecrire(doc, ".qlr", cat, Rapport()))
    projet = QgsProject()
    ok, erreur = QgsLayerDefinition.loadLayerDefinition(str(entree), projet, projet.layerTreeRoot())
    assert ok, erreur
    couches = list(projet.mapLayers().values())
    assert len(couches) == len(doc.couches)
    for c in couches:
        assert c.isValid(), f"couche invalide dans QGIS : {c.name()}"
        assert c.renderer() is not None
    sortie = dossier / "sortie.qlr"
    ok, erreur = QgsLayerDefinition.exportLayerDefinition(str(sortie), projet.layerTreeRoot().findLayers())
    assert ok, erreur
    return sortie.read_bytes()


def _sans_source(doc):
    for c in doc.couches:
        c.source = Source()
    return doc


@pytest.mark.parametrize("chemin", EXEMPLES_LYRX, ids=lambda p: p.name)
def test_qgis_comprend_le_qlr_produit(chemin, qgis_app, catalogue_sans_substitution, tmp_path):
    cat = catalogue_sans_substitution
    doc = api.lire(chemin.read_bytes(), chemin.name, cat, Rapport())
    relu = api.lire(_passer_par_qgis(doc, cat, tmp_path), "qgis.qlr", cat, Rapport())
    assert comparer_documents(_alias_possibles(_sans_source(doc)), _sans_source(relu)) == []


@avec_exemples_reels
@pytest.mark.parametrize("chemin", EXEMPLES_QLR[:12], ids=lambda p: p.name)
def test_qgis_relit_les_exemples_qlr(chemin, qgis_app, catalogue_sans_substitution, tmp_path):
    """Les .qlr d'exemple repassés par le cœur restent compris de la même façon par QGIS."""
    cat = catalogue_sans_substitution
    doc = api.lire(chemin.read_bytes(), chemin.name, cat, Rapport())
    relu = api.lire(_passer_par_qgis(doc, cat, tmp_path), "qgis.qlr", cat, Rapport())
    assert comparer_documents(_alias_possibles(_sans_source(doc)), _sans_source(relu)) == []
