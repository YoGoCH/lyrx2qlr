"""Lecture prudente des .qlr / .qml : les déclarations d'entités (attaques XML) sont refusées."""
from __future__ import annotations

import pytest

from conftest import EXEMPLES_QLR, avec_exemples_reels
from lyrx2qlr import api, xml_sur

MILLIARD_DE_RIRES = b"""<?xml version="1.0"?>
<!DOCTYPE qlr [
  <!ENTITY rire "ha">
  <!ENTITY rires "&rire;&rire;&rire;&rire;&rire;&rire;&rire;&rire;&rire;&rire;">
]>
<qlr><layer-tree-group name="&rires;"/></qlr>"""

ENTITE_EXTERNE = b"""<?xml version="1.0"?>
<!DOCTYPE qlr [<!ENTITY fichier SYSTEM "file:///etc/passwd">]>
<qlr><layer-tree-group name="&fichier;"/></qlr>"""


@pytest.mark.parametrize("donnees", [MILLIARD_DE_RIRES, ENTITE_EXTERNE,
                                     MILLIARD_DE_RIRES.decode().encode("utf-16")])
def test_declarations_refusees(donnees):
    with pytest.raises(xml_sur.XmlRefuse):
        xml_sur.lire(donnees)


def test_doctype_simple_accepte():
    racine = xml_sur.lire(b"<!DOCTYPE qgis-layer-definition>\n<qlr><layers/></qlr>")
    assert racine.tag == "qlr"
    racine = xml_sur.lire(b"<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>\n<qgis version='3.40'/>")
    assert racine.get("version") == "3.40"


def test_texte_dans_un_commentaire_apres_la_racine_accepte():
    assert xml_sur.lire(b"<qlr><!-- <!ENTITY x 'y'> --></qlr>").tag == "qlr"


def test_convertir_ne_leve_pas():
    r = api.convertir(MILLIARD_DE_RIRES, "piege.qlr")
    assert not r.reussi and "entités" in r.erreur


@avec_exemples_reels
@pytest.mark.parametrize("chemin", EXEMPLES_QLR, ids=lambda p: p.name)
def test_exemples_reels_acceptes(chemin):
    xml_sur.verifier(chemin.read_bytes())
