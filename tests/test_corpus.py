"""Tests des corrections trouvées grâce au corpus de symbologies réelles (lot 1.5, docs/corpus.md)."""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET

import pytest

from conftest import RACINE
from lyrx2qlr import api

sys.path.insert(0, str(RACINE / "outils" / "entrainement"))


# --- petits fichiers d'essai ----------------------------------------------------------------
def _qml(rendu: str, symboles: str = "", geometrie: str = "Polygon", etiquettes: str = "") -> bytes:
    return f"""<!DOCTYPE qgis><qgis version="3.34" styleCategories="AllStyleCategories">
<renderer-v2 {rendu}<symbols>{symboles}</symbols></renderer-v2>{etiquettes}
<layerGeometryType>{ {"Point": 0, "Line": 1, "Polygon": 2}[geometrie] }</layerGeometryType></qgis>""".encode()


def _aplat(nom: str, couleur: str = "255,0,0,255") -> str:
    return f"""<symbol type="fill" name="{nom}" alpha="1"><layer class="SimpleFill" enabled="1" locked="0" pass="0">
<Option type="Map"><Option name="color" value="{couleur}" type="QString"/><Option name="style" value="solid" type="QString"/>
<Option name="outline_style" value="no" type="QString"/></Option></layer></symbol>"""


def _lyrx(couche: dict) -> bytes:
    base = {"type": "CIMFeatureLayer", "name": "essai"}
    return json.dumps({"type": "CIMLayerDocument", "version": "3.1.0", "layerDefinitions": [base | couche]}).encode()


def _ligne(marqueur_placement: dict) -> dict:
    marqueur = {"type": "CIMVectorMarker", "enable": True, "size": 4, "markerPlacement": marqueur_placement}
    return {"renderer": {"type": "CIMSimpleRenderer", "symbol": {"type": "CIMSymbolReference", "symbol": {
        "type": "CIMLineSymbol", "symbolLayers": [marqueur]}}}}


def _options_qlr(qlr: bytes) -> list[dict]:
    racine = ET.fromstring(qlr)
    return [{o.get("name"): o.get("value") for o in c.iter("Option") if o.get("name")} | {"_classe": c.get("class")}
            for c in racine.iter("layer") if c.get("class")]


# --- ensembles de règles simples → valeurs uniques -----------------------------------------------
def test_regles_simples_deviennent_des_valeurs_uniques(catalogue):
    regles = """type="RuleRenderer"><rules key="r"><rule key="a" filter="&quot;usage&quot; = 'forêt'" symbol="0" label="Forêt"/>
<rule key="b" filter="&quot;usage&quot; IN ('pré', 'champ')" symbol="1" label="Cultures"/>
<rule key="c" filter="ELSE" symbol="2" label="Autre"/></rules>"""
    doc = api.lire(_qml(regles, _aplat("0") + _aplat("1") + _aplat("2")), "essai.qml", catalogue)
    rendu = doc.couches[0].rendu
    assert rendu.type == "categories" and rendu.champs == ["usage"]
    assert [k.valeurs for k in rendu.classes] == [[["forêt"]], [["pré"], ["champ"]]] or \
           [k.valeurs for k in rendu.classes] == [["forêt"], ["pré", "champ"]]
    assert rendu.symbole_defaut is not None and rendu.etiquette_defaut == "Autre"


def test_regles_complexes_restent_signalees(catalogue):
    regles = """type="RuleRenderer"><rules key="r"><rule key="a" filter="&quot;surface&quot; &gt; 100" symbol="0" label="Grand"/></rules>"""
    r = api.convertir(_qml(regles, _aplat("0")), "essai.qml", catalogue)
    assert "valeurs uniques" not in r.rapport.en_texte()


# --- lecture ArcGIS robuste ----------------------------------------------------------------------
def test_nan_ecrit_en_texte_est_absent(catalogue):
    trait = {"type": "CIMSolidStroke", "enable": True, "width": "NaN", "color": {"type": "CIMRGBColor", "values": [0, 0, 0, 100]}}
    couche = {"renderer": {"type": "CIMSimpleRenderer", "symbol": {"type": "CIMSymbolReference", "symbol": {
        "type": "CIMLineSymbol", "symbolLayers": [trait]}}}}
    r = api.convertir(_lyrx(couche), "essai.lyrx", catalogue)
    assert r.reussi and "erreur interne" not in r.rapport.en_texte().lower()


def test_nan_json_est_absent(catalogue):
    texte = _lyrx({"minScale": 1}).replace(b'"minScale": 1', b'"minScale": NaN')
    r = api.convertir(texte, "essai.lyrx", catalogue)
    assert r.reussi


def test_classe_sans_borne_superieure_est_signalee(catalogue):
    couche = {"renderer": {"type": "CIMClassBreaksRenderer", "field": "pop", "breaks": [
        {"type": "CIMClassBreak", "label": "sans borne"},
        {"type": "CIMClassBreak", "label": "ok", "upperBound": 10}]}}
    r = api.convertir(_lyrx(couche), "essai.lyrx", catalogue)
    assert r.reussi and "sans borne" in r.rapport.en_texte()


# --- placements des marqueurs le long d'une ligne ------------------------------------------------
def test_marqueur_au_milieu(catalogue):
    r = api.convertir(_lyrx(_ligne({"type": "CIMMarkerPlacementAtRatioPositions", "positionArray": [0.5]})), "essai.lyrx", catalogue)
    ligne = next(o for o in _options_qlr(r.donnees) if o["_classe"] == "MarkerLine")
    assert "CentralPoint" in (ligne.get("placements") or ligne.get("placement") or "").replace("centralpoint", "CentralPoint")


def test_marqueurs_aux_extremites_par_positions(catalogue):
    r = api.convertir(_lyrx(_ligne({"type": "CIMMarkerPlacementAtRatioPositions", "positionArray": [0, 1]})), "essai.lyrx", catalogue)
    ligne = next(o for o in _options_qlr(r.donnees) if o["_classe"] == "MarkerLine")
    valeur = (ligne.get("placements") or ligne.get("placement") or "").lower()
    assert "first" in valeur and "last" in valeur


# --- catalogue : conditions et motifs -------------------------------------------------------------
def test_condition_nombre_positif():
    from lyrx2qlr.catalogue import _condition_valeur
    assert _condition_valeur(">0", 0.5) and not _condition_valeur(">0", 0) and not _condition_valeur(">0", None)


def test_motif_propre_a_une_classe(catalogue):
    assert catalogue.ignore("qgis", "outline_width", "0.26", classe="SimpleLine")
    assert not catalogue.ignore("qgis", "outline_width", "0.26", classe="SimpleFill")
    assert catalogue.visible("qgis", "outline_width", classe="SimpleFill")


# --- étiquettes : placements et casse ---------------------------------------------------------------
def test_casse_titre_annoncee_vers_arcgis(catalogue):
    etiquettes = """<labeling type="simple"><settings><text-style fieldName="nom" fontFamily="Arial" fontSize="10"
 capitalization="1004"/><placement placement="1" quadOffset="2"/></settings></labeling>"""
    r = api.convertir(_qml('type="singleSymbol">', _aplat("0"), "Point", etiquettes), "essai.qml", catalogue)
    assert r.reussi
    texte = r.rapport.en_texte().lower()
    assert "casse" in texte or "titre" in texte, texte


# --- diagrammes désactivés -------------------------------------------------------------------------
def test_diagramme_desactive_non_signale(catalogue):
    diag = """<SingleCategoryDiagramRenderer diagramType="Pie"><DiagramCategory enabled="0"/></SingleCategoryDiagramRenderer>"""
    qml = _qml('type="singleSymbol">', _aplat("0")).replace(b"</qgis>", diag.encode() + b"</qgis>")
    r = api.convertir(qml, "essai.qml", catalogue)
    assert "diagramme" not in r.rapport.en_texte().lower()


# --- images intégrées : format reconnu aux premiers octets ---------------------------------------
@pytest.mark.parametrize("debut, format_", [("Qk", "bmp"), ("iVBOR", "png"), ("/9j/", "jpeg"), ("R0lG", "gif")])
def test_format_image_integree(outils_conv, debut, format_):
    from lyrx2qlr.proprietes import _qgis_vers_pivot
    image = _qgis_vers_pivot(outils_conv, {"type": "image", "qgis": "x"}, lambda _: "base64:" + debut + "AAAA", {}, "essai")
    assert image.startswith(f"data:image/{format_};base64,")


@pytest.fixture()
def outils_conv(catalogue):
    from lyrx2qlr.proprietes import Convertisseur
    from lyrx2qlr.rapport import Rapport
    return Convertisseur(catalogue, Rapport())


# --- outil corpus : jamais de secret dans le dépôt -------------------------------------------------
def test_nettoyage_des_secrets(tmp_path):
    import corpus
    f = tmp_path / "x.lyrx"
    f.write_text('{"workspaceConnectionString": "SERVER=s;USER=u;ENCRYPTED_PASSWORD=00022e68;TOKEN=abc;DATABASE=d"}', encoding="utf-8")
    assert corpus.nettoyer(f)
    texte = f.read_text(encoding="utf-8")
    assert "00022e68" not in texte and "abc" not in texte and "DATABASE=d" in texte
    assert not corpus.nettoyer(f)  # déjà propre
