"""L'extension QGIS, pilotée sans écran : import d'un .lyrx, export en .lyrx, conversion d'un dossier.

Sauté si PyQGIS n'est pas disponible. Les boîtes de dialogue sont remplacées par des réponses fixes.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

pytest.importorskip("qgis.core")

from conftest import EXEMPLES_LYRX, EXEMPLES_QLR, avec_exemples_reels  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def extension():
    from qgis.core import QgsApplication
    if QgsApplication.instance() is None:
        app = QgsApplication([], False)
        app.initQgis()
    sys.path.insert(0, str(RACINE / "outils"))
    import construire
    construire.construire_extension()
    sys.path.insert(0, str(RACINE / "qgis_plugin"))
    import lyrx2qlr_qgis
    import lyrx2qlr_qgis.plugin as module
    from qgis.testing.mocked import get_iface
    iface = get_iface()
    plug = lyrx2qlr_qgis.classFactory(iface)
    plug.initGui()
    fenetres = []
    module.FenetreRapport.exec_ = lambda self: fenetres.append(self.texte)
    yield plug, module, iface, fenetres
    plug.unload()


def test_menu(extension):
    plug, *_ = extension
    assert len(plug.actions) == 5  # 4 commandes + la coche « Garder la source de données »
    coches = [a for a in plug.actions if a.isCheckable()]
    assert len(coches) == 1 and coches[0].isChecked() == plug.garder_source


@avec_exemples_reels
def test_importer_puis_exporter(extension, tmp_path, monkeypatch):
    from qgis.core import QgsProject
    plug, module, iface, _ = extension
    QgsProject.instance().clear()
    lyrx = EXEMPLES_LYRX[0]
    monkeypatch.setattr(module.QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(lyrx), "")))
    plug.importer_lyrx()
    couches = list(QgsProject.instance().mapLayers().values())
    assert len(couches) == 1 and couches[0].renderer() is not None

    sortie = tmp_path / "export.lyrx"
    monkeypatch.setattr(iface, "activeLayer", lambda: couches[0])
    monkeypatch.setattr(module.QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(sortie), "")))
    plug.exporter_lyrx()
    doc = json.loads(sortie.read_text(encoding="utf-8"))
    assert doc["layerDefinitions"][0]["renderer"]["type"]


@avec_exemples_reels
def test_convertir_dossier(extension, tmp_path, monkeypatch):
    plug, module, _, fenetres = extension
    entree, sortie = tmp_path / "entree", tmp_path / "sortie"
    (entree / "sous").mkdir(parents=True)
    sortie.mkdir()
    shutil.copy(EXEMPLES_LYRX[0], entree / "a.lyrx")
    shutil.copy(EXEMPLES_QLR[0], entree / "sous" / "b.qlr")
    reponses = iter([str(entree), str(sortie)])
    monkeypatch.setattr(module.QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: next(reponses)))
    plug.convertir_dossier()
    produits = sorted(p.relative_to(sortie).as_posix() for p in sortie.rglob("*") if p.is_file())
    assert produits == ["a.qlr", "rapport_lyrx2qlr.txt", "sous/b.lyrx"]
    assert "a.lyrx" in fenetres[-1]
