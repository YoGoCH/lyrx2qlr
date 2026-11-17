"""Allers-retours sur les vrais exemples : ce qui sort doit pouvoir revenir sans perte.

.lyrx → modèle → .qlr → modèle → .lyrx → modèle : les trois modèles doivent être égaux.
.qlr  → modèle → .lyrx → modèle → .qlr  → modèle : idem.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET

import pytest

from conftest import EXEMPLES_LYRX, EXEMPLES_QLR, avec_exemples_reels, comparer_documents
from lyrx2qlr import api
from lyrx2qlr.rapport import Rapport


def _id(p):
    return p.name


@pytest.mark.parametrize("chemin", EXEMPLES_LYRX, ids=_id)
def test_lyrx_qlr_lyrx(chemin, catalogue_sans_substitution):
    cat = catalogue_sans_substitution
    r = Rapport()
    doc1 = api.lire(chemin.read_bytes(), chemin.name, cat, r)
    assert doc1.couches, "aucune couche lue"
    qlr = api.ecrire(doc1, ".qlr", cat, r)
    ET.fromstring(qlr)  # XML bien formé
    doc2 = api.lire(qlr, "x.qlr", cat, Rapport())
    assert comparer_documents(doc1, doc2) == []
    lyrx = api.ecrire(doc2, ".lyrx", cat, Rapport())
    json.loads(lyrx)
    doc3 = api.lire(lyrx, "x.lyrx", cat, Rapport())
    assert comparer_documents(doc1, doc3) == []


# Différences connues et voulues, propres à un fichier source (motif de chemin → raison).
ECARTS_ADMIS = {
    "DGE.MN95_DGE_TPR_CDN_INO.qlr": {
        ".couches[0].geometrie": "le .qlr déclare des lignes mais n'a que des symboles de surface ; un .lyrx ne stocke pas la géométrie"},
}


# Différences annoncées dans le rapport, valables pour tous les fichiers (motif → raison).
ECARTS_ANNONCES = [
    (r"etiquettes\[\d+\]\.props\.placement : '(autour|toujours_horizontal)' avant, 'horizontal' après",
     "placements QGIS « autour du centroïde » et « décalé du centroïde » : ArcGIS n'a pas d'équivalent "
     "(la valeur écrite autrefois était refusée par ArcGIS, relecture du lot 2)"),
    (r"sous_symbole\.couches\[\d+\]\.props\.decalage : -?[\d.]+ avant, -?[\d.]+ après",
     "décalage du trait d'une hachure ramené dans l'écartement : même dessin (dessin croisé du lot 2)"),
    (r"rendu\.(etiquette_defaut : '' avant|symbole_defaut : None avant)",
     "classe NULL sans « autres valeurs » : QGIS dessine aussi les valeurs non listées avec elle (lot 2.1)"),
]


def _non_annonces(diffs: list[str], admis: dict) -> list[str]:
    return [d for d in diffs if d.split(" : ")[0] not in admis and not any(re.search(m, d) for m, _ in ECARTS_ANNONCES)]


@pytest.mark.parametrize("chemin", EXEMPLES_QLR, ids=_id)
def test_qlr_lyrx_qlr(chemin, catalogue_sans_substitution):
    cat = catalogue_sans_substitution
    admis = ECARTS_ADMIS.get(chemin.name, {})
    doc1 = api.lire(chemin.read_bytes(), chemin.name, cat, Rapport())
    lyrx = api.ecrire(doc1, ".lyrx", cat, Rapport())
    doc2 = api.lire(lyrx, "x.lyrx", cat, Rapport())
    assert _non_annonces(comparer_documents(doc1, doc2), admis) == []
    if admis:
        return
    qlr = api.ecrire(doc2, ".qlr", cat, Rapport())
    doc3 = api.lire(qlr, "x.qlr", cat, Rapport())
    assert _non_annonces(comparer_documents(doc1, doc3), {}) == []


@pytest.mark.parametrize("chemin", EXEMPLES_LYRX, ids=_id)
def test_conversion_sans_perte_inattendue(chemin, catalogue):
    """Le rapport ne doit pas contenir d'erreur interne ; les pertes éventuelles sont listées pour revue."""
    res = api.convertir(chemin.read_bytes(), chemin.name, catalogue)
    assert res.reussi, res.rapport.en_texte()
    assert "Conversion impossible" not in res.rapport.en_texte()


@avec_exemples_reels
def test_lot_produit_une_archive(catalogue):
    import io
    import zipfile
    fichiers = [(p.name, p.read_bytes()) for p in EXEMPLES_LYRX[:3]]
    archive, resultats = api.convertir_lot(fichiers, catalogue)
    noms = zipfile.ZipFile(io.BytesIO(archive)).namelist()
    assert "rapports/_resume.txt" in noms
    assert all(r.reussi for r in resultats)
    assert sum(n.endswith(".qlr") for n in noms) == 3
