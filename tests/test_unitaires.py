"""Tests des briques du cœur : couleurs, unités, expressions, chemins, catalogues, rapport."""
from __future__ import annotations

import json

import pytest

from lyrx2qlr import api, chemins
from lyrx2qlr.catalogue import Catalogue, ErreurCatalogue
from lyrx2qlr.expressions import Traducteur
from lyrx2qlr.proprietes import Convertisseur
from lyrx2qlr.rapport import Rapport


@pytest.fixture()
def outils(catalogue):
    r = Rapport()
    return Convertisseur(catalogue, r), Traducteur(catalogue, r), r


# --- couleurs ---------------------------------------------------------------------------------
@pytest.mark.parametrize("cim, attendu", [
    ({"type": "CIMRGBColor", "values": [255, 0, 0, 50]}, [255, 0, 0, 128]),        # opacité ArcGIS en %
    ({"type": "CIMHSVColor", "values": [120, 100, 100, 100]}, [0, 255, 0, 255]),
    ({"type": "CIMCMYKColor", "values": [0, 100, 100, 0, 100]}, [255, 0, 0, 255]),
    ({"type": "CIMGrayColor", "values": [50, 100]}, [50, 50, 50, 255]),
    ({"type": "CIMLABColor", "values": [53.24, 80.09, 67.2, 100]}, [255, 0, 0, 255]),
])
def test_couleurs_arcgis(outils, cim, attendu):
    conv, _, _ = outils
    assert conv.couleur_lyrx_vers_pivot(cim, "essai") == attendu


def test_couleurs_qgis(outils):
    conv, _, _ = outils
    assert conv.couleur_qgis_vers_pivot("255,0,0,128") == [255, 0, 0, 128]
    assert conv.couleur_qgis_vers_pivot("255,0,0,128,rgb:1,0,0,0.5") == [255, 0, 0, 128]  # format QGIS 3.40+
    assert conv.couleur_qgis_vers_pivot("300,0,0,255") == [255, 0, 0, 255]  # bornée
    assert conv.couleur_pivot_vers_qgis([1, 2, 3, 4]) == "1,2,3,4"


def test_modele_de_couleur_inconnu_signale(outils):
    conv, _, r = outils
    assert conv.couleur_lyrx_vers_pivot({"type": "CIMXYZColor", "values": [1, 2, 3]}, "essai") == [128, 128, 128, 255]
    assert r.compter("avertissement") == 1


# --- unités -------------------------------------------------------------------------------------
def test_unites(outils):
    conv, _, _ = outils
    assert conv.vers_points(1, "MM", "essai") == pytest.approx(72 / 25.4)
    assert conv.vers_points(1, "Pixel", "essai") == pytest.approx(0.75)
    assert conv.depuis_points(72 / 25.4) == ("1", "MM")


# --- expressions ------------------------------------------------------------------------------
@pytest.mark.parametrize("texte, moteur, attendu", [
    ('[NOM] & " - " & [NUM]', "VBScript", "\"NOM\" || ' - ' || \"NUM\""),
    ("UCase([NOM])", "VBScript", 'upper("NOM")'),
    ("$feature.NOM", "Arcade", '"NOM"'),
])
def test_expressions_vers_qgis(outils, texte, moteur, attendu):
    _, trad, _ = outils
    assert trad.vers_qgis(texte, moteur, "essai") == attendu


def test_expressions_depuis_qgis(outils):
    _, trad, _ = outils
    assert trad.depuis_qgis("\"NOM\" || ' x'", "Arcade", "essai") == ('$feature.NOM + " x"', "Arcade")
    assert trad.depuis_qgis('"NOM"', "SQL", "essai") == ("NOM", "SQL")


# --- chemins dans le JSON ---------------------------------------------------------------------
def test_chemins():
    objet = {}
    chemins.ecrire(objet, "a.b[0].c", 1)
    assert objet == {"a": {"b": [{"c": 1}]}}
    liste = {"l": [{"type": "A", "v": 1}, {"type": "B", "v": 2}]}
    assert chemins.lire(liste, "l[type=B].v") == 2
    assert chemins.lire(liste, "l[type=C].v") is None


# --- catalogues ---------------------------------------------------------------------------------
def test_catalogues_du_projet_valides(catalogue):
    assert catalogue.verifier() == []


def test_catalogue_complementaire_prioritaire(tmp_path):
    (tmp_path / "polices.json").write_text(json.dumps({"substitutions": [
        {"police": "ESRI Default Marker", "caractere": 33, "forme": "star", "facteur_taille": 1}]}), encoding="utf-8")
    cat = Catalogue.charger([tmp_path])
    premiere = cat.polices["substitutions"][0]
    assert premiere["forme"] == "star"


def test_catalogue_casse_refuse(tmp_path):
    (tmp_path / "listes.json").write_text("{ pas du json", encoding="utf-8")
    with pytest.raises(ErreurCatalogue):
        Catalogue.charger([tmp_path])


# --- rapport et cas inconnus -----------------------------------------------------------------
def test_rapport_compte_les_doublons():
    r = Rapport(fichier="f")
    for _ in range(3):
        r.perte("ici", "même message")
    assert len(r.entrees) == 1 and r.entrees[0].nombre == 3
    assert "(×3)" in r.en_texte()


def test_symbole_inconnu_signale_sans_planter(catalogue):
    lyrx = {
        "type": "CIMLayerDocument", "version": "3.1.0",
        "layerDefinitions": [{
            "type": "CIMFeatureLayer", "name": "essai",
            "renderer": {"type": "CIMSimpleRenderer", "symbol": {"type": "CIMSymbolReference", "symbol": {
                "type": "CIMPolygonSymbol", "symbolLayers": [
                    {"type": "CIMGradientFill", "enable": True},
                    {"type": "CIMSolidFill", "enable": True, "color": {"type": "CIMRGBColor", "values": [1, 2, 3, 100]}}]}}},
            "featureTable": {"type": "CIMFeatureTable", "dataConnection": {
                "type": "CIMStandardDataConnection", "workspaceFactory": "Shapefile",
                "workspaceConnectionString": "DATABASE=.", "dataset": "a.shp"}},
        }],
    }
    r = api.convertir(json.dumps(lyrx).encode(), "essai.lyrx", catalogue)
    assert r.reussi
    assert any("CIMGradientFill" in e.message for e in r.rapport.entrees if e.niveau == "perte")
    assert b"1,2,3,255" in r.donnees


def test_fichier_illisible(catalogue):
    r = api.convertir(b"pas un fichier", "x.lyrx", catalogue)
    assert not r.reussi and r.rapport.compter("perte") == 1


def test_etiquette_sans_visibilite_est_eteinte(catalogue):
    """ArcGIS n'écrit pas les valeurs fausses : une classe d'étiquettes sans « visibility » est éteinte."""
    lyrx = {
        "type": "CIMLayerDocument", "version": "3.1.0",
        "layerDefinitions": [{
            "type": "CIMFeatureLayer", "name": "essai", "labelVisibility": True,
            "labelClasses": [{"type": "CIMLabelClass", "name": "a", "expression": "[NOM]", "expressionEngine": "VBScript"}],
            "renderer": {"type": "CIMSimpleRenderer", "symbol": {"type": "CIMSymbolReference", "symbol": {
                "type": "CIMPolygonSymbol", "symbolLayers": [{"type": "CIMSolidFill", "enable": True}]}}},
        }],
    }
    doc = api.lire(json.dumps(lyrx).encode(), "essai.lyrx", catalogue, Rapport())
    assert doc.couches[0].etiquettes[0].props["visible"] is False


# --- corrections issues de la boucle d'entraînement (outils/entrainement) ---------------------
def _document(genre_cim, couches):
    """Petit .lyrx d'une couche, symbole unique, sans source de données."""
    return json.dumps({
        "type": "CIMLayerDocument", "version": "3.1.0",
        "layerDefinitions": [{
            "type": "CIMFeatureLayer", "name": "essai",
            "renderer": {"type": "CIMSimpleRenderer", "symbol": {"type": "CIMSymbolReference", "symbol": {
                "type": genre_cim, "symbolLayers": couches}}},
        }],
    }).encode()


def _options(qlr: bytes) -> list[dict]:
    """Options de chaque couche de symbole du .qlr, dans l'ordre du fichier."""
    import xml.etree.ElementTree as ET
    racine = ET.fromstring(qlr)
    return [{o.get("name"): o.get("value") for o in c.iter("Option") if o.get("name")}
            | {"_classe": c.get("class")} for c in racine.iter("layer") if c.get("class")]


def _vers_qlr(catalogue, donnees):
    r = api.convertir(donnees, "essai.lyrx", catalogue)
    assert r.reussi, r.rapport.en_texte()
    return r


def test_coupe_et_decalage_des_tirets(catalogue):
    trait = {"type": "CIMSolidStroke", "enable": True, "width": 1, "color": {"type": "CIMRGBColor", "values": [0, 0, 0, 100]},
             "effects": [{"type": "CIMGeometricEffectCut", "beginCut": 2, "endCut": 3},
                         {"type": "CIMGeometricEffectDashes", "dashTemplate": [4, 2], "offsetAlongLine": 1}]}
    opt = _options(_vers_qlr(catalogue, _document("CIMLineSymbol", [trait])).donnees)[0]
    assert float(opt["trim_distance_start"]) > 0 and float(opt["trim_distance_end"]) > float(opt["trim_distance_start"])
    assert float(opt["dash_pattern_offset"]) > 0


def test_marqueurs_a_demi_intervalle(catalogue):
    """ArcGIS « WithHalfGap » : le premier marqueur est à un demi-intervalle du début."""
    marqueur = {"type": "CIMVectorMarker", "enable": True, "size": 4,
                "markerPlacement": {"type": "CIMMarkerPlacementAlongLineSameSize", "placementTemplate": [10],
                                    "endings": "WithHalfGap", "angleToLine": True}}
    opt = _options(_vers_qlr(catalogue, _document("CIMLineSymbol", [marqueur])).donnees)
    ligne = next(o for o in opt if o["_classe"] == "MarkerLine")
    assert float(ligne["offset_along_line"]) == pytest.approx(float(ligne["interval"]) / 2, rel=1e-3)


def test_marqueurs_avec_marqueurs_aux_bouts_annonce(catalogue):
    marqueur = {"type": "CIMVectorMarker", "enable": True, "size": 4,
                "markerPlacement": {"type": "CIMMarkerPlacementAlongLineSameSize", "placementTemplate": [10],
                                    "endings": "WithMarkers"}}
    r = _vers_qlr(catalogue, _document("CIMLineSymbol", [marqueur]))
    assert "WithMarkers" in r.rapport.en_texte()


def test_aplat_deplace(catalogue):
    aplat = {"type": "CIMSolidFill", "enable": True, "color": {"type": "CIMRGBColor", "values": [9, 9, 9, 100]},
             "effects": [{"type": "CIMGeometricEffectMove", "offsetX": 2, "offsetY": 1}]}
    opt = _options(_vers_qlr(catalogue, _document("CIMPolygonSymbol", [aplat])).donnees)[0]
    x, y = (float(v) for v in opt["offset"].split(","))
    assert x > 0 and y < 0  # QGIS compte les y vers le bas


def test_contour_d_un_aplat_deplace_suit_l_aplat(catalogue):
    """Un aplat QGIS décalé décale aussi son contour : côté ArcGIS, le trait reçoit le même effet « Déplacer »."""
    aplat = {"type": "CIMSolidFill", "enable": True, "color": {"type": "CIMRGBColor", "values": [9, 9, 9, 100]},
             "effects": [{"type": "CIMGeometricEffectMove", "offsetX": 2, "offsetY": 1}]}
    qlr = _vers_qlr(catalogue, _document("CIMPolygonSymbol", [aplat])).donnees
    qlr = qlr.replace(b'name="outline_style" value="no"', b'name="outline_style" value="solid"')
    qlr = qlr.replace(b'name="outline_width" value="0"', b'name="outline_width" value="0.5"').replace(b'value="0,0,0,0"', b'value="0,0,0,255"')
    assert b'name="outline_style" value="solid"' in qlr
    r = api.convertir(qlr, "essai.qlr", catalogue)
    couches = json.loads(r.donnees)["layerDefinitions"][0]["renderer"]["symbol"]["symbol"]["symbolLayers"]
    trait = next(c for c in couches if c["type"] == "CIMSolidStroke")
    deplacement = next(e for e in trait["effects"] if e["type"] == "CIMGeometricEffectMove")
    assert deplacement["offsetX"] == pytest.approx(2, abs=0.01) and deplacement["offsetY"] == pytest.approx(1, abs=0.01)
    # Retour vers QGIS : le trait seul ne peut pas être déplacé, c'est annoncé.
    retour = api.convertir(r.donnees, "essai.lyrx", catalogue)
    assert "Trait déplacé" in retour.rapport.en_texte()


def test_symbole_sans_couche_reste_invisible(catalogue):
    """Sans couche, QGIS mettrait un symbole par défaut : on écrit une couche qui ne dessine rien."""
    opt = _options(_vers_qlr(catalogue, _document("CIMPolygonSymbol", [])).donnees)
    assert opt == [opt[0]] and opt[0]["_classe"] == "SimpleFill"
    assert opt[0]["style"] == "no" and opt[0]["outline_style"] == "no"


def test_police_esri_remplacee_est_annoncee(catalogue):
    marqueur = {"type": "CIMCharacterMarker", "enable": True, "size": 8, "fontFamilyName": "ESRI Default Marker",
                "characterIndex": 33, "symbol": {"type": "CIMPolygonSymbol", "symbolLayers": [
                    {"type": "CIMSolidFill", "enable": True, "color": {"type": "CIMRGBColor", "values": [0, 0, 0, 100]}}]}}
    r = _vers_qlr(catalogue, _document("CIMPointSymbol", [marqueur]))
    assert "ESRI Default Marker" in r.rapport.en_texte() and "remplacé" in r.rapport.en_texte()


def test_valeurs_neutres_et_visibles(catalogue):
    assert catalogue.ignore("qgis", "alpha", "1") and catalogue.ignore("qgis", "ring_filter", "false")
    assert not catalogue.ignore("qgis", "alpha", "0.5") and catalogue.visible("qgis", "alpha")
    assert catalogue.visible("qgis", "draw_inside_polygon")


# == lot 2 : ce qu'ArcGIS Pro a refusé ou corrigé en relisant nos fichiers ==================

def test_fichier_sans_couche_vectorielle_ne_produit_rien(catalogue):
    """Un .lyrx sans couche ne s'ouvre pas dans ArcGIS : pas de fichier, une erreur claire."""
    raster = {"type": "CIMLayerDocument", "layers": ["CIMPATH=x.json"],
              "layerDefinitions": [{"type": "CIMRasterLayer", "name": "image", "uRI": "CIMPATH=x.json"}]}
    r = api.convertir(json.dumps(raster).encode(), "raster.lyrx", catalogue)
    assert not r.reussi and r.donnees is None and "raster" in r.erreur
    assert r.rapport.compter("perte") >= 1


def test_valeurs_ecrites_existent_dans_le_cim(catalogue):
    """Valeurs refusées par ArcGIS Pro 3.7 lors de la relecture du lot 2 : ne plus jamais les écrire."""
    refusees = {"AroundPolygon", "OffsetStraightAroundPolygon", "RemovePartialMarkers"}
    for nom in ("placement_etiquette_surface", "decoupage_grille"):
        assert not refusees & {v.get("lyrx") for v in catalogue.liste(nom)["valeurs"]}


def test_trait_a_toujours_une_epaisseur(catalogue):
    """Sans épaisseur, ArcGIS met 4 points à un trait (contour de marqueur…) : on écrit toujours « width »."""
    from conftest import EXEMPLES_LYRX, EXEMPLES_QLR

    def traits(x):
        if isinstance(x, dict):
            if x.get("type") == "CIMSolidStroke":
                yield x
            for v in x.values():
                yield from traits(v)
        elif isinstance(x, list):
            for v in x:
                yield from traits(v)

    for chemin in EXEMPLES_QLR + EXEMPLES_LYRX:
        r = api.convertir(chemin.read_bytes(), chemin.name, catalogue)
        lyrx = r.donnees if chemin.suffix == ".qlr" else api.convertir(r.donnees, "x.qlr", catalogue).donnees
        assert all("width" in s for s in traits(json.loads(lyrx))), chemin.name


def test_decalage_des_hachures_ramene_dans_l_ecartement(catalogue):
    """Lot 2 : un trait de hachures décalé d'une période entière (−3 pt pour 3 pt d'écartement) est le
    même dessin pour ArcGIS, mais QGIS n'affiche alors aucune hachure. Le décalage est ramené à 0."""
    import re

    trait = {"type": "CIMSolidStroke", "enable": True, "width": 1,
             "color": {"type": "CIMRGBColor", "values": [250, 143, 117, 100]},
             "effects": [{"type": "CIMGeometricEffectOffset", "method": "Square", "offset": -3, "option": "Fast"}]}
    hachures = {"type": "CIMHatchFill", "enable": True, "separation": 3,
                "lineSymbol": {"type": "CIMLineSymbol", "symbolLayers": [trait]}}
    couche = {"type": "CIMFeatureLayer", "name": "h", "uRI": "CIMPATH=h.json", "visibility": True,
              "featureTable": {"type": "CIMFeatureTable", "dataConnection": {
                  "type": "CIMStandardDataConnection", "workspaceConnectionString": "DATABASE=.",
                  "workspaceFactory": "Shapefile", "dataset": "h.shp", "datasetType": "esriDTFeatureClass"}},
              "renderer": {"type": "CIMSimpleRenderer", "symbol": {"type": "CIMSymbolReference", "symbol": {
                  "type": "CIMPolygonSymbol", "symbolLayers": [hachures]}}}}
    doc = {"type": "CIMLayerDocument", "layers": ["CIMPATH=h.json"], "layerDefinitions": [couche]}
    r = api.convertir(json.dumps(doc).encode(), "h.lyrx", catalogue)
    decalages = [float(v) for v in re.findall(r'name="offset" value="([^"]+)"', r.donnees.decode())]
    assert decalages and all(abs(d) < 3 * 0.3528 / 2 for d in decalages)
    assert "ramené" in r.rapport.en_texte()


@pytest.mark.skipif(not __import__("conftest").EXEMPLES_REELS, reason="symbologies réelles absentes")
def test_anciens_noms_des_options_qgis(catalogue):
    """Lot 2 : un .qlr ancien écrit son trait avec « outline_color » / « outline_width ». QGIS les lit
    encore ; lus comme absents, le trait devenait noir de 1 pt (aller-retour stable, donc invisible
    sans le dessin croisé)."""
    from conftest import EXEMPLES_QLR

    chemin = next(c for c in EXEMPLES_QLR if "ITIN_CONV_EXCEPT" in c.name)
    r = api.convertir(chemin.read_bytes(), chemin.name, catalogue)
    classes = json.loads(r.donnees)["layerDefinitions"][0]["renderer"]["groups"][0]["classes"]
    traits = [c["symbol"]["symbol"]["symbolLayers"][0] for c in classes]
    assert traits[0]["color"]["values"][:3] == [255, 0, 0]
    assert all(t["width"] == 3 for t in traits)
    assert "outline_color" not in r.rapport.en_texte()


def test_contour_de_marqueur_agrandi_avec_le_marqueur(catalogue):
    """Lot 2 : avec « scaleSymbolsProportionally », ArcGIS agrandit le contour d'un marqueur dans le
    rapport taille / hauteur du cadre ; QGIS non. Lu d'ArcGIS : épaisseur multipliée ; écrit vers
    ArcGIS : sans agrandissement, pour garder l'épaisseur de QGIS."""
    trait = {"type": "CIMSolidStroke", "enable": True, "width": 1, "color": {"type": "CIMRGBColor", "values": [0, 0, 0, 100]}}
    marqueur = {"type": "CIMVectorMarker", "enable": True, "size": 18, "scaleSymbolsProportionally": True,
                "frame": {"xmin": -2, "ymin": -2, "xmax": 2, "ymax": 2},
                "markerGraphics": [{"type": "CIMMarkerGraphic",
                                    "geometry": {"curveRings": [[[0, 2], {"a": [[0, 2], [0, 0], 0, 1]}]]},
                                    "symbol": {"type": "CIMPolygonSymbol", "symbolLayers": [trait]}}]}
    couche = {"type": "CIMFeatureLayer", "name": "p", "uRI": "CIMPATH=p.json", "visibility": True,
              "featureTable": {"type": "CIMFeatureTable", "dataConnection": {
                  "type": "CIMStandardDataConnection", "workspaceConnectionString": "DATABASE=.",
                  "workspaceFactory": "Shapefile", "dataset": "p.shp", "datasetType": "esriDTFeatureClass"}},
              "renderer": {"type": "CIMSimpleRenderer", "symbol": {"type": "CIMSymbolReference", "symbol": {
                  "type": "CIMPointSymbol", "symbolLayers": [marqueur]}}}}
    lyrx = json.dumps({"type": "CIMLayerDocument", "layers": ["CIMPATH=p.json"], "layerDefinitions": [couche]}).encode()
    doc = api.lire(lyrx, "p.lyrx", catalogue)
    cs = doc.couches[0].rendu.classes[0].symbole.couches[0]
    assert cs.props["largeur_contour"] == pytest.approx(4.5)
    ecrit = json.loads(api.ecrire(doc, ".lyrx", catalogue))
    m = ecrit["layerDefinitions"][0]["renderer"]["symbol"]["symbol"]["symbolLayers"][0]
    assert not m.get("scaleSymbolsProportionally")
    assert m["markerGraphics"][0]["symbol"]["symbolLayers"][0]["width"] == pytest.approx(4.5)


def _qml_trait_unites_carte(echelles: str) -> bytes:
    return f"""<qgis version="3.34" {echelles}><renderer-v2 type="singleSymbol"><symbols>
<symbol type="line" name="0" alpha="1"><layer class="SimpleLine" enabled="1" pass="0" locked="0"><Option type="Map">
<Option name="line_color" type="QString" value="0,0,0,255"/><Option name="line_style" type="QString" value="solid"/>
<Option name="line_width" type="QString" value="0.2"/><Option name="line_width_unit" type="QString" value="MapUnit"/>
</Option></layer></symbol></symbols></renderer-v2></qgis>""".encode()


def test_unites_de_carte_converties_a_l_echelle_de_la_couche(catalogue):
    """Lot 2.1 (styles Ordnance Survey) : un trait de 0,2 m en unités de carte, couche visible jusqu'au
    1:4 000. Il est traduit en points pour le 1:2 000 (milieu de la plage), où il fait 0,1 mm."""
    xml = _qml_trait_unites_carte('hasScaleBasedVisibilityFlag="1" minScale="4000" maxScale="1"')
    r = api.convertir(xml, "trait.qml", catalogue)
    trait = json.loads(r.donnees)["layerDefinitions"][0]["renderer"]["symbol"]["symbol"]["symbolLayers"][0]
    assert abs(trait["width"] - 0.2 * 2834.645669 / 2000) < 0.001
    assert "1:2 000" in r.rapport.en_texte()


def test_unites_de_carte_sans_plage_de_visibilite(catalogue):
    """Sans plage de visibilité, aucune échelle ne s'impose : la valeur reste telle quelle (annoncé)."""
    r = api.convertir(_qml_trait_unites_carte(""), "trait.qml", catalogue)
    trait = json.loads(r.donnees)["layerDefinitions"][0]["renderer"]["symbol"]["symbol"]["symbolLayers"][0]
    assert trait["width"] == 0.2
    assert "gardée telle quelle" in r.rapport.en_texte()


def test_decalage_du_contour_d_une_surface_change_de_signe(catalogue):
    """Lot 2.1 (dessin croisé du corpus) : ArcGIS décale vers l'intérieur un contour de surface à
    décalage négatif ; QGIS le pousse vers l'extérieur, quel que soit le sens du polygone. Le signe
    change donc pour les contours de surfaces, pas pour les lignes."""
    import xml.etree.ElementTree as ET

    trait = {"type": "CIMSolidStroke", "enable": True, "width": 2, "color": {"type": "CIMRGBColor", "values": [204, 0, 0, 100]},
             "effects": [{"type": "CIMGeometricEffectOffset", "method": "Mitered", "offset": -2.83464567, "option": "Fast"}]}

    def couche(symbole):
        return {"type": "CIMLayerDocument", "layerDefinitions": [{
            "type": "CIMFeatureLayer", "name": "s", "uRI": "CIMPATH=s.json", "visibility": True,
            "featureTable": {"type": "CIMFeatureTable", "dataConnection": {
                "type": "CIMStandardDataConnection", "workspaceConnectionString": "DATABASE=.",
                "workspaceFactory": "Shapefile", "dataset": "s.shp", "datasetType": "esriDTFeatureClass"}},
            "renderer": {"type": "CIMSimpleRenderer", "symbol": {"type": "CIMSymbolReference", "symbol": symbole}}}]}

    surface = couche({"type": "CIMPolygonSymbol", "symbolLayers": [trait]})
    ligne = couche({"type": "CIMLineSymbol", "symbolLayers": [trait]})
    for doc, attendu in ((surface, 1.0), (ligne, -1.0)):
        qlr = api.convertir(json.dumps(doc).encode(), "s.lyrx", catalogue).donnees
        offsets = [o.get("value") for o in ET.fromstring(qlr).iter("Option") if o.get("name") == "offset"]
        assert [float(v) for v in offsets] == [attendu]
        retour = api.lire(qlr, "s.qlr", catalogue, Rapport())
        props = retour.couches[0].rendu.classes[0].symbole.couches[0].props
        assert abs(props["decalage"] + 2.83464567) < 0.001  # le sens ArcGIS revient intact


def test_forme_en_courbes_de_bezier_n_est_pas_un_cercle(catalogue):
    """Lot 2.1 (corpus geostyler) : une épingle dessinée en courbes de Bézier devenait un rond sans
    le dire. Seule une forme faite d'arcs est un cercle ; le reste est annoncé."""
    conv = Convertisseur(catalogue, Rapport())
    cercle = {"geometry": {"curveRings": [[[0, 5], {"a": [[0, 5], [0, 0], 0, 1]}]]}}
    epingle = {"geometry": {"curveRings": [[[0, -2], {"b": [[-5, 10], [-1, 5], [-5, 7]]}, {"b": [[0, 15], [-5, 13], [-3, 15]]},
                                            {"b": [[5, 10], [3, 15], [5, 13]]}, {"b": [[0, -2], [5, 7], [1, 5]]}]]}}
    assert conv.forme_depuis_graphique(cercle, "x") == "circle"
    assert not conv.rapport.en_texte().count("non reconnue")
    conv.forme_depuis_graphique(epingle, "x")
    assert "non reconnue" in conv.rapport.en_texte()


def _qml_categories(categories: str) -> bytes:
    symboles = "".join(f'<symbol type="line" name="{i}" alpha="1"><layer class="SimpleLine" enabled="1" pass="0" locked="0">'
                       f'<Option type="Map"><Option name="line_color" type="QString" value="{c}"/></Option></layer></symbol>'
                       for i, c in enumerate(["255,0,0,255", "0,0,255,255"]))
    return (f'<qgis version="3.44"><renderer-v2 type="categorizedSymbol" attr="niveau"><categories>{categories}</categories>'
            f'<symbols>{symboles}</symbols></renderer-v2></qgis>').encode()


def test_categorie_null_de_qgis_sert_aussi_aux_autres_valeurs(catalogue):
    """Lot 2.1 (styles Ordnance Survey) : dans QGIS, la catégorie NULL dessine aussi les valeurs non
    listées. ArcGIS reçoit donc le même symbole en « autres valeurs » ; au retour, pas de doublon."""
    xml = _qml_categories('<category value="a" label="A" type="string" symbol="0" render="true"/>'
                          '<category value="NULL" label="inconnu" type="NULL" symbol="1" render="true"/>')
    r = api.convertir(xml, "n.qml", catalogue)
    rendu = json.loads(r.donnees)["layerDefinitions"][0]["renderer"]
    assert rendu["useDefaultSymbol"] is True
    assert rendu["defaultSymbol"]["symbol"]["symbolLayers"][0]["color"]["values"][:3] == [0, 0, 255]
    retour = api.convertir(r.donnees, "n.lyrx", catalogue)
    assert retour.donnees.count(b"<category ") == 2  # pas de catégorie « autres valeurs » en plus


def test_classe_null_et_autres_valeurs_differentes_vers_qgis(catalogue):
    """ArcGIS distingue NULL et « autres valeurs » ; QGIS non (la dernière catégorie l'emporte) : annoncé."""
    from lyrx2qlr.modele import Classe, Couche, Document, Rendu, Symbole
    rouge = Symbole(genre="ligne")
    bleu = Symbole(genre="ligne", opacite=0.5)
    doc = Document(couches=[Couche(nom="c", geometrie="ligne", rendu=Rendu(
        type="categories", champs=["niveau"], classes=[Classe(rouge, "inconnu", [[None]])], symbole_defaut=bleu))])
    rapport = Rapport()
    api.ecrire(doc, ".qlr", catalogue, rapport)
    assert "ne distingue pas les valeurs NULL" in rapport.en_texte()


def test_decalage_des_hachures_dans_le_repere_de_la_carte(catalogue):
    """Lot 2.1 (corpus, hachures intercalées) : ArcGIS exprime offsetX / offsetY d'une hachure dans le
    repère de la carte ; QGIS a un seul « offset » perpendiculaire, dont le sens dépend du quadrant de
    l'angle. Mesuré dans les deux logiciels : à 45°, offsetX = 5 pt décale de 5 · sin 45° = 3,54 pt le
    long de la normale, soit « offset » = −3,54 pt dans QGIS."""
    import xml.etree.ElementTree as ET
    hachure = {"type": "CIMHatchFill", "enable": True, "rotation": 45, "separation": 20, "offsetX": 5,
               "lineSymbol": {"type": "CIMLineSymbol", "symbolLayers": [
                   {"type": "CIMSolidStroke", "enable": True, "width": 1, "color": {"type": "CIMRGBColor", "values": [0, 0, 0, 100]}}]}}
    doc = {"type": "CIMLayerDocument", "layerDefinitions": [{
        "type": "CIMFeatureLayer", "name": "h", "uRI": "CIMPATH=h.json", "visibility": True,
        "featureTable": {"type": "CIMFeatureTable", "dataConnection": {
            "type": "CIMStandardDataConnection", "workspaceConnectionString": "DATABASE=.",
            "workspaceFactory": "Shapefile", "dataset": "h.shp", "datasetType": "esriDTFeatureClass"}},
        "renderer": {"type": "CIMSimpleRenderer", "symbol": {"type": "CIMSymbolReference", "symbol": {
            "type": "CIMPolygonSymbol", "symbolLayers": [hachure]}}}}]}
    r = api.convertir(json.dumps(doc).encode(), "h.lyrx", catalogue)
    assert "offsetX" not in r.rapport.en_texte()
    motif = next(c for c in ET.fromstring(r.donnees).iter("layer") if c.get("class") == "LinePatternFill")
    options = {o.get("name"): o.get("value") for o in motif.iter("Option") if o.get("name")}
    assert abs(float(options["offset"]) - (-3.5355 / 2.834645669)) < 0.001
    retour = json.loads(api.convertir(r.donnees, "h.qlr", catalogue).donnees)
    h = retour["layerDefinitions"][0]["renderer"]["symbol"]["symbol"]["symbolLayers"][0]
    perpendiculaire = h.get("offsetX", 0) * 0.70710678 - h.get("offsetY", 0) * 0.70710678
    assert abs(perpendiculaire - 3.5355) < 0.001


def _bmp_1_bit() -> bytes:
    """Petit BMP 1 bit de 3 × 2 pixels (noir sur blanc), comme les motifs du corpus arc2qgis."""
    import struct
    lignes = bytes([0b10100000, 0, 0, 0, 0b01000000, 0, 0, 0])  # 2 lignes de 4 octets (de bas en haut)
    palette = bytes([0, 0, 0, 0, 255, 255, 255, 0])  # index 0 = noir, 1 = blanc (BGR0)
    entete = struct.pack("<IiiHHIIiiII", 40, 3, 2, 1, 1, 0, len(lignes), 2835, 2835, 2, 0)
    debut = 14 + len(entete) + len(palette)
    return b"BM" + struct.pack("<IHHI", debut + len(lignes), 0, 0, debut) + entete + palette + lignes


def test_substitutions_de_couleurs_appliquees_a_une_image_bmp():
    """Lot 2.1 (8 fichiers du corpus) : ArcGIS repeint les motifs BMP (« colorSubstitutions ») ;
    QGIS n'a pas cette notion, l'image est donc repeinte et devient un PNG à fond transparent."""
    import base64
    import struct
    import zlib
    from lyrx2qlr import images
    url = "data:image/bmp;base64," + base64.b64encode(_bmp_1_bit()).decode()
    assert images.recolorer(url, [([0, 0, 0, 255], [0, 0, 0, 255])]) == url  # rien ne change
    nouvelle = images.recolorer(url, [([0, 0, 0, 255], [38, 115, 0, 255]), ([255, 255, 255, 255], [212, 208, 200, 0])])
    png = base64.b64decode(nouvelle.split(",", 1)[1])
    assert nouvelle.startswith("data:image/png;base64,") and png[:8] == b"\x89PNG\r\n\x1a\n"
    morceaux, i = {}, 8
    while i < len(png):
        n = struct.unpack(">I", png[i:i + 4])[0]
        morceaux[png[i + 4:i + 8]] = png[i + 8:i + 8 + n]
        i += 12 + n
    assert struct.unpack(">IIBB", morceaux[b"IHDR"][:10]) == (3, 2, 1, 3)
    assert morceaux[b"PLTE"] == bytes([38, 115, 0, 212, 208, 200])
    assert morceaux[b"tRNS"] == bytes([255, 0])
    # première ligne PNG = dernière ligne BMP (le BMP est rangé de bas en haut)
    assert zlib.decompress(morceaux[b"IDAT"]) == bytes([0, 0b01000000, 0, 0b10100000])
    assert images.recolorer("data:image/png;base64,AAAA", [([0, 0, 0, 255], [1, 2, 3, 255])]) is None


def test_remplissage_image_avec_substitutions_vers_qgis(catalogue):
    import base64
    remplissage = {"type": "CIMPictureFill", "enable": True, "height": 20,
                   "url": "data:image/bmp;base64," + base64.b64encode(_bmp_1_bit()).decode(),
                   "colorSubstitutions": [{"type": "CIMColorSubstitution",
                                           "oldColor": {"type": "CIMRGBColor", "values": [0, 0, 0, 100]},
                                           "newColor": {"type": "CIMRGBColor", "values": [38, 115, 0, 100]}}]}
    doc = {"type": "CIMLayerDocument", "layerDefinitions": [{
        "type": "CIMFeatureLayer", "name": "i", "uRI": "CIMPATH=i.json", "visibility": True,
        "featureTable": {"type": "CIMFeatureTable", "dataConnection": {
            "type": "CIMStandardDataConnection", "workspaceConnectionString": "DATABASE=.",
            "workspaceFactory": "Shapefile", "dataset": "i.shp", "datasetType": "esriDTFeatureClass"}},
        "renderer": {"type": "CIMSimpleRenderer", "symbol": {"type": "CIMSymbolReference", "symbol": {
            "type": "CIMPolygonSymbol", "symbolLayers": [remplissage]}}}}]}
    r = api.convertir(json.dumps(doc).encode(), "i.lyrx", catalogue)
    texte = r.rapport.en_texte()
    assert "substitution" not in texte and "colorSubstitutions" not in texte
    assert b"base64:iVBORw0KGgo" in r.donnees


# -- sources de données (v1.5.0) : serveurs et utilisateurs inventés -------------------------------
def _lyrx_source(connexion: dict) -> bytes:
    doc = {"type": "CIMLayerDocument", "layerDefinitions": [{
        "type": "CIMFeatureLayer", "name": "s", "uRI": "CIMPATH=s.json", "visibility": True,
        "featureTable": {"type": "CIMFeatureTable", "dataConnection": connexion},
        "renderer": {"type": "CIMSimpleRenderer", "symbol": {"type": "CIMSymbolReference", "symbol": {
            "type": "CIMPolygonSymbol", "symbolLayers": [{"type": "CIMSolidFill", "enable": True,
                                                         "color": {"type": "CIMRGBColor", "values": [1, 2, 3, 100]}}]}}}}]}
    return json.dumps(doc).encode()


_SDE_ORACLE = {"type": "CIMStandardDataConnection", "workspaceFactory": "SDE", "dataset": "SCHEMA_EX.TABLE_EXEMPLE",
               "datasetType": "esriDTFeatureClass",
               "workspaceConnectionString": "AUTHENTICATION_MODE=DBMS;DBCLIENT=oracle;DB_CONNECTION_PROPERTIES=base_exemple;"
                                            "ENCRYPTED_PASSWORD=00022e68invente;INSTANCE=sde:oracle$base_exemple;"
                                            "SERVER=base_exemple;USER=lecteur"}


def _source_qlr(qlr: bytes) -> tuple[str, str]:
    import xml.etree.ElementTree as ET
    ml = ET.fromstring(qlr).find(".//maplayer")
    return ml.findtext("provider"), ml.findtext("datasource")


def test_source_oracle_gardee_vers_qgis_sans_mot_de_passe(catalogue):
    r = api.convertir(_lyrx_source(_SDE_ORACLE), "s.lyrx", catalogue)
    fournisseur, adresse = _source_qlr(r.donnees)
    assert fournisseur == "oracle"
    assert "dbname='base_exemple'" in adresse and "user='lecteur'" in adresse
    assert 'table="SCHEMA_EX"."TABLE_EXEMPLE" (SHAPE)' in adresse and "key='OBJECTID'" in adresse
    assert "password" not in adresse.lower() and b"00022e68invente" not in r.donnees
    texte = r.rapport.en_texte()
    assert "à reconnecter" not in texte and "mot de passe" in texte.lower()
    # et retour vers ArcGIS : la même connexion, toujours sans mot de passe
    retour = json.loads(api.convertir(r.donnees, "s.qlr", catalogue).donnees)
    dc = retour["layerDefinitions"][0]["featureTable"]["dataConnection"]
    assert dc["workspaceFactory"] == "SDE" and dc["dataset"] == "SCHEMA_EX.TABLE_EXEMPLE"
    assert dc["workspaceConnectionString"] == ("AUTHENTICATION_MODE=DBMS;DBCLIENT=oracle;DB_CONNECTION_PROPERTIES=base_exemple;"
                                               "INSTANCE=sde:oracle$base_exemple;SERVER=base_exemple;USER=lecteur")


def test_source_oracle_qgis_connexion_directe_et_filtre(catalogue):
    import xml.etree.ElementTree as ET
    r = api.convertir(_lyrx_source(_SDE_ORACLE), "s.lyrx", catalogue)
    racine = ET.fromstring(r.donnees)
    ml = racine.find(".//maplayer")
    ml.find("datasource").text = ("dbname='SERVICE_EX' host=serveur.exemple port=1521 user='lecteur' password='secret_invente' "
                                  "key='OBJECTID' srid=2056 type=Polygon table=\"SCHEMA_EX\".\"TABLE_EXEMPLE\" (SHAPE) sql=\"ETAT\" = 'actif'")
    qlr = ET.tostring(racine)
    res = api.convertir(qlr, "s.qlr", catalogue)
    assert b"secret_invente" not in res.donnees
    table = json.loads(res.donnees)["layerDefinitions"][0]["featureTable"]
    chaine = table["dataConnection"]["workspaceConnectionString"]
    assert "DB_CONNECTION_PROPERTIES=serveur.exemple:1521/SERVICE_EX" in chaine and "PASSWORD" not in chaine
    assert table["definitionExpression"] == "ETAT = 'actif'"
    assert "mot de passe" in res.rapport.en_texte().lower()


def test_source_non_gardee_si_la_coche_est_decochee(catalogue):
    r = api.convertir(_lyrx_source(_SDE_ORACLE), "s.lyrx", catalogue, garder_source=False)
    fournisseur, adresse = _source_qlr(r.donnees)
    assert (fournisseur, adresse) == ("ogr", "SCHEMA_EX.TABLE_EXEMPLE")
    assert b"base_exemple" not in r.donnees and b"lecteur" not in r.donnees
    gpkg = dict(_SDE_ORACLE, workspaceFactory="Sql", dataset="main.routes",
                workspaceConnectionString=r"DATABASE=C:\donnees\exemple.gpkg")
    assert _source_qlr(api.convertir(_lyrx_source(gpkg), "s.lyrx", catalogue, garder_source=False).donnees)[1] == "routes"


def test_source_geopackage_sans_prefixe_main(catalogue):
    gpkg = dict(_SDE_ORACLE, workspaceFactory="Sql", dataset="main.routes",
                workspaceConnectionString=r"DATABASE=C:\donnees\exemple.gpkg")
    assert _source_qlr(api.convertir(_lyrx_source(gpkg), "s.lyrx", catalogue).donnees) == ("ogr", "C:/donnees/exemple.gpkg|layername=routes")


def test_source_ancienne_chaine_sans_dbclient(catalogue):
    """Anciens .lyrx : le moteur et le serveur ne sont que dans INSTANCE."""
    sqlserver = {"type": "CIMStandardDataConnection", "workspaceFactory": "SDE", "dataset": "base_ex.SCHEMA_EX.table_ex",
                 "workspaceConnectionString": "SERVER=serveur_ex;INSTANCE=sde:sqlserver:serveur_ex;DATABASE=base_ex;"
                                              "USER=lecteur;VERSION=sde.DEFAULT;AUTHENTICATION_MODE=DBMS;"
                                              "ENCRYPTED_PASSWORD=00022e68invente"}
    r = api.convertir(_lyrx_source(sqlserver), "s.lyrx", catalogue)
    fournisseur, adresse = _source_qlr(r.donnees)
    assert fournisseur == "mssql"
    assert "dbname='base_ex'" in adresse and "host=serveur_ex" in adresse and "user='lecteur'" in adresse
    assert 'table="SCHEMA_EX"."table_ex"' in adresse and b"00022e68invente" not in r.donnees
    oracle = {"type": "CIMStandardDataConnection", "workspaceFactory": "SDE", "dataset": "SCHEMA_EX.TABLE_EX",
              "workspaceConnectionString": "INSTANCE=sde:oracle11g:alias_ex;USER=lecteur;VERSION=SDE.DEFAULT"}
    fournisseur, adresse = _source_qlr(api.convertir(_lyrx_source(oracle), "o.lyrx", catalogue).donnees)
    assert fournisseur == "oracle" and "dbname='alias_ex'" in adresse


def test_source_postgresql(catalogue):
    pg = dict(_SDE_ORACLE, dataset="geo.public.routes",
              workspaceConnectionString="AUTHENTICATION_MODE=DBMS;DATABASE=geo;DBCLIENT=postgresql;"
                                        "DB_CONNECTION_PROPERTIES=serveur.exemple,5433;USER=lecteur")
    fournisseur, adresse = _source_qlr(api.convertir(_lyrx_source(pg), "s.lyrx", catalogue).donnees)
    assert fournisseur == "postgres"
    assert "dbname='geo'" in adresse and "host=serveur.exemple" in adresse and "port=5433" in adresse
    assert 'table="public"."routes" (shape)' in adresse


def test_lire_adresse_qgis():
    from lyrx2qlr.sources import lire_adresse_qgis
    cles, schema, table, geom, sql = lire_adresse_qgis(
        r"""dbname='a b' user='l\'x' key='OBJECTID' table="S"."T" (SHAPE) sql="X" = 1""")
    assert cles == {"dbname": "a b", "user": "l'x", "key": "OBJECTID"}
    assert (schema, table, geom, sql) == ("S", "T", "SHAPE", '"X" = 1')
