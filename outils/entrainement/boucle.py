"""Boucle d'entraînement : cas inventés → conversion aller-retour → comparaison → écarts regroupés.

    .\\outils\\py.ps1 outils\\entrainement\\boucle.py [--cas 300] [--graine 1] [--mutations] [--figer N...]

Deux sources de cas :
  - symbologies QGIS inventées (tirage dans les types de couches que les catalogues convertissent), construites
    par l'API de QGIS : elles sont donc forcément valides. Parcours .qlr → .lyrx → .qlr ;
  - avec --mutations : les vrais .lyrx d'exemple, dont on modifie au hasard couleurs, épaisseurs, tailles et
    angles. Parcours .lyrx → .qlr → .lyrx.
Pour chaque cas, deux comparaisons :
  1. le modèle neutre avant / après (toute valeur perdue ou déformée) ;
  2. l'image de chaque symbole dessinée par QGIS, avant / après (part de pixels différents).
Un écart est « annoncé » si le rapport de conversion le signale, « silencieux » sinon : ce sont les silencieux
qu'il faut corriger en priorité. Résultats dans sorties/entrainement/ (rapport.md, images, fichiers des cas).
--figer N copie le cas N dans exemples/fabriques/ : il devient un test permanent.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import random
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "src"))
sys.path.insert(0, str(RACINE / "tests"))

from conftest import comparer_documents  # noqa: E402
from lyrx2qlr import api  # noqa: E402
from lyrx2qlr.catalogue import Catalogue  # noqa: E402
from lyrx2qlr.rapport import Rapport  # noqa: E402

TAILLE_ECHANTILLON = 200
SEUIL_PIXELS = 0.015  # au-delà de 1,5 % de pixels nettement différents, l'image a changé
TOLERANCE_CANAL = 48  # différence tolérée par canal (lissage des bords)


# --- données inventées ---------------------------------------------------------------------
def creer_donnees(chemin: Path) -> None:
    """GeoPackage avec trois couches (surfaces, lignes, points) et des valeurs pièges (NULL, accents, vide)."""
    from qgis.core import (QgsCoordinateReferenceSystem, QgsCoordinateTransformContext, QgsFeature, QgsField,
                           QgsFields, QgsGeometry, QgsVectorFileWriter, QgsWkbTypes)
    from qgis.PyQt.QtCore import QVariant
    if chemin.exists():
        chemin.unlink()
    champs = QgsFields()
    champs.append(QgsField("classe", QVariant.String))
    champs.append(QgsField("valeur", QVariant.Double))
    champs.append(QgsField("code", QVariant.Int))
    classes = ["forêt", "lac", "zone à bâtir", "", None, "A", "B"]
    hasard = random.Random(0)
    geometries = {
        "surfaces": ("Polygon", lambda i, j: QgsGeometry.fromWkt(
            f"POLYGON(({i*100} {j*100},{i*100+90} {j*100},{i*100+90} {j*100+90},{i*100} {j*100+90},{i*100} {j*100}),"
            f"({i*100+30} {j*100+30},{i*100+60} {j*100+30},{i*100+60} {j*100+60},{i*100+30} {j*100+60},{i*100+30} {j*100+30}))")),
        "lignes": ("LineString", lambda i, j: QgsGeometry.fromWkt(
            f"LINESTRING({i*100} {j*100},{i*100+40} {j*100+70},{i*100+90} {j*100+20})")),
        "points": ("Point", lambda i, j: QgsGeometry.fromWkt(f"POINT({i*100+45} {j*100+45})")),
    }
    for n, (nom, (type_, fabrique)) in enumerate(geometries.items()):
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.layerName = nom
        if n:
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        w = QgsVectorFileWriter.create(str(chemin), champs, QgsWkbTypes.parseType(type_),
                                       QgsCoordinateReferenceSystem("EPSG:2056"), QgsCoordinateTransformContext(), options)
        for i in range(6):
            for j in range(6):
                f = QgsFeature(champs)
                f.setGeometry(fabrique(i, j))
                f.setAttributes([hasard.choice(classes), hasard.uniform(0, 100), hasard.randint(1, 5)])
                w.addFeature(f)
        del w


# --- symbologies inventées -------------------------------------------------------------------
class Generateur:
    UNITES = ["MM"] * 6 + ["Point"] * 3 + ["Pixel"]
    FORMES = ["circle", "square", "diamond", "equilateral_triangle", "triangle", "pentagon", "hexagon", "star",
              "cross", "cross2", "line"]

    def __init__(self, hasard: random.Random):
        self.h = hasard

    def couleur(self, opaque: bool = False) -> str:
        a = 255 if opaque or self.h.random() < 0.7 else self.h.randint(60, 254)
        return f"{self.h.randint(0, 255)},{self.h.randint(0, 255)},{self.h.randint(0, 255)},{a}"

    def mm(self, a: float, b: float) -> str:
        return f"{self.h.uniform(a, b):.2f}"

    def unite(self) -> str:
        return self.h.choice(self.UNITES)

    def creer(self, classe: str, props: dict):
        from qgis.core import QgsApplication
        return QgsApplication.symbolLayerRegistry().symbolLayerMetadata(classe).createSymbolLayer(props)

    # couches ponctuelles
    def marqueur(self):
        from qgis.core import QgsMarkerSymbol
        couches = [self.couche_marqueur() for _ in range(self.h.choice([1, 1, 2]))]
        return QgsMarkerSymbol(couches)

    def couche_marqueur(self):
        u = self.unite()
        if self.h.random() < 0.75:
            p = {"name": self.h.choice(self.FORMES), "size": self.mm(1, 6), "size_unit": u, "color": self.couleur(),
                 "outline_color": self.couleur(True), "outline_width": self.mm(0, 0.8), "outline_width_unit": u,
                 "outline_style": self.h.choice(["solid", "solid", "no"]), "angle": str(self.h.choice([0, 0, 15, 45, 90])),
                 "offset": f"{self.mm(-1, 1)},{self.mm(-1, 1)}" if self.h.random() < 0.3 else "0,0", "offset_unit": u}
            return self.creer("SimpleMarker", p)
        p = {"font": "Arial", "chr": self.h.choice("ABXZ#*+"), "size": self.mm(2, 8), "size_unit": u,
             "color": self.couleur(True), "angle": str(self.h.choice([0, 30])),
             "outline_width": self.h.choice(["0", "0", self.mm(0.1, 0.5)]), "outline_width_unit": u,
             "outline_color": self.couleur(True)}
        return self.creer("FontMarker", p)

    # couches linéaires
    def ligne(self):
        from qgis.core import QgsLineSymbol
        couches = [self.couche_ligne() for _ in range(self.h.choice([1, 1, 2, 3]))]
        return QgsLineSymbol(couches)

    def couche_ligne(self, dans_surface: bool = False):
        u = self.unite()
        if dans_surface or self.h.random() < 0.7:
            p = {"line_color": self.couleur(), "line_width": self.mm(0.1, 2), "line_width_unit": u,
                 "capstyle": self.h.choice(["round", "flat", "square"]), "joinstyle": self.h.choice(["round", "miter", "bevel"])}
            tirage = self.h.random()
            if tirage < 0.25:
                p.update({"use_custom_dash": "1", "customdash": f"{self.mm(1, 5)};{self.mm(0.5, 3)}", "customdash_unit": u})
                if self.h.random() < 0.5:
                    p.update({"dash_pattern_offset": self.mm(0.5, 2), "dash_pattern_offset_unit": u})
            elif tirage < 0.4:
                p["line_style"] = self.h.choice(["dash", "dot", "dash dot"])
            if not dans_surface and self.h.random() < 0.25:
                p.update({"offset": self.mm(-1.5, 1.5), "offset_unit": u})
            if not dans_surface and self.h.random() < 0.2:
                p.update({"trim_distance_start": self.mm(1, 5), "trim_distance_end": self.mm(0, 5),
                          "trim_distance_start_unit": u, "trim_distance_end_unit": u})
            return self.creer("SimpleLine", p)
        placement = self.h.choice(["Interval", "Interval", "Vertex", "FirstVertex|LastVertex", "LastVertex"])
        p = {"placements": placement, "interval": self.mm(3, 12), "interval_unit": u,
             "rotate": self.h.choice(["1", "1", "0"]), "offset": self.h.choice(["0", self.mm(-1, 1)]), "offset_unit": u}
        if placement == "Interval" and self.h.random() < 0.4:
            p.update({"offset_along_line": self.mm(0.5, 4), "offset_along_line_unit": u})
        c = self.creer("MarkerLine", p)
        c.setSubSymbol(self.marqueur())
        return c

    # couches surfaciques
    def surface(self):
        from qgis.core import QgsFillSymbol
        n = self.h.choice([1, 1, 2, 3])
        couches = [self.couche_surface() for _ in range(n)]
        if self.h.random() < 0.3:
            couches.append(self.couche_ligne(dans_surface=True))  # contour indépendant
        return QgsFillSymbol(couches)

    def couche_surface(self):
        u = self.unite()
        t = self.h.random()
        if t < 0.5:
            p = {"color": self.couleur(), "style": self.h.choice(["solid"] * 5 + ["no"]),
                 "outline_color": self.couleur(True), "outline_width": self.mm(0.1, 1.5), "outline_width_unit": u,
                 "outline_style": self.h.choice(["solid", "solid", "no", "dash"]),
                 "joinstyle": self.h.choice(["round", "miter", "bevel"])}
            if self.h.random() < 0.2:
                p.update({"offset": f"{self.mm(-1, 1)},{self.mm(-1, 1)}", "offset_unit": u})
            return self.creer("SimpleFill", p)
        if t < 0.75:
            c = self.creer("LinePatternFill", {"angle": str(self.h.choice([0, 30, 45, 90, 135])), "distance": self.mm(1, 6),
                                               "distance_unit": u, "offset": self.h.choice(["0", self.mm(0, 1)]),
                                               "offset_unit": u})
            from qgis.core import QgsLineSymbol
            c.setSubSymbol(QgsLineSymbol([self.couche_ligne(dans_surface=True)]))
            return c
        if t < 0.92:
            c = self.creer("PointPatternFill", {"distance_x": self.mm(2, 8), "distance_y": self.mm(2, 8),
                                                "distance_x_unit": u, "distance_y_unit": u,
                                                "displacement_x": self.h.choice(["0", self.mm(1, 4)]), "displacement_x_unit": u,
                                                "offset_x": self.h.choice(["0", self.mm(0, 2)]), "offset_x_unit": u,
                                                "offset_y": self.h.choice(["0", self.mm(0, 2)]), "offset_y_unit": u,
                                                "angle": str(self.h.choice([0, 0, 30])), "coordinate_reference": "feature"})
            c.setSubSymbol(self.marqueur())
            return c
        c = self.creer("CentroidFill", {"point_on_surface": self.h.choice(["0", "1"]), "point_on_all_parts": "1"})
        c.setSubSymbol(self.marqueur())
        return c

    def symbole(self, genre: str):
        return {"surface": self.surface, "ligne": self.ligne, "point": self.marqueur}[genre]()

    def rendu(self, genre: str):
        from qgis.core import (QgsCategorizedSymbolRenderer, QgsGraduatedSymbolRenderer, QgsRendererCategory,
                               QgsRendererRange, QgsSingleSymbolRenderer)
        t = self.h.random()
        if t < 0.6:
            return QgsSingleSymbolRenderer(self.symbole(genre))
        if t < 0.85:
            valeurs = self.h.sample(["forêt", "lac", "zone à bâtir", "A", "B"], self.h.randint(2, 4))
            cats = [QgsRendererCategory(v, self.symbole(genre), v) for v in valeurs]
            return QgsCategorizedSymbolRenderer("classe", cats)
        bornes = sorted(self.h.sample(range(5, 95), 3))
        limites = [0] + bornes + [100]
        rangs = [QgsRendererRange(limites[i], limites[i + 1], self.symbole(genre), f"{limites[i]} – {limites[i + 1]}")
                 for i in range(len(limites) - 1)]
        return QgsGraduatedSymbolRenderer("valeur", rangs)

    def etiquettes(self, couche) -> None:
        if self.h.random() > 0.3:
            return
        from qgis.core import QgsPalLayerSettings, QgsTextBufferSettings, QgsTextFormat, QgsVectorLayerSimpleLabeling
        from qgis.PyQt.QtGui import QColor
        r = QgsPalLayerSettings()
        r.fieldName = self.h.choice(["classe", "upper(\"classe\")", "\"classe\" || ' ' || \"code\""])
        r.isExpression = r.fieldName != "classe"
        f = QgsTextFormat()
        f.setSize(self.h.choice([8, 9, 10, 12]))
        f.setColor(QColor(*[self.h.randint(0, 120) for _ in range(3)]))
        if self.h.random() < 0.5:
            b = QgsTextBufferSettings()
            b.setEnabled(True)
            b.setSize(self.h.choice([0.5, 1.0]))
            b.setColor(QColor("white"))
            f.setBuffer(b)
        r.setFormat(f)
        couche.setLabeling(QgsVectorLayerSimpleLabeling(r))
        couche.setLabelsEnabled(True)


# --- conversion et comparaison --------------------------------------------------------------
def qlr_de_couche(couche) -> bytes:
    from qgis.core import QgsLayerDefinition, QgsPathResolver, QgsProject, QgsReadWriteContext
    from qgis.PyQt.QtXml import QDomDocument
    projet = QgsProject.instance()
    noeud = projet.layerTreeRoot().findLayer(couche.id())
    doc = QDomDocument("qgis-layer-definition")
    ctx = QgsReadWriteContext()
    ctx.setPathResolver(QgsPathResolver())
    ok, erreur = QgsLayerDefinition.exportLayerDefinition(doc, [noeud], ctx)
    if not ok:
        raise RuntimeError(erreur)
    return bytes(doc.toByteArray())


def symboles_de_qlr(donnees: bytes) -> list:
    """Charge un .qlr dans un projet à part et renvoie ses symboles (copies), dans l'ordre du rendu."""
    from qgis.core import QgsLayerDefinition, QgsProject, QgsReadWriteContext, QgsRenderContext
    from qgis.PyQt.QtXml import QDomDocument
    projet = QgsProject()
    doc = QDomDocument()
    doc.setContent(donnees)
    ok, erreur = QgsLayerDefinition.loadLayerDefinition(doc, projet, projet.layerTreeRoot(), QgsReadWriteContext())
    couches = list(projet.mapLayers().values())
    if not ok or not couches or couches[0].renderer() is None:
        return []
    return [s.clone() for s in couches[0].renderer().symbols(QgsRenderContext())]


def ecart_image(a, b):
    """Part de pixels nettement différents entre deux images de même taille."""
    if a.size() != b.size():
        return 1.0
    def proches(p, q):
        return p == q or max(abs(((p >> s) & 255) - ((q >> s) & 255)) for s in (0, 8, 16, 24)) <= TOLERANCE_CANAL

    diff = 0
    l, h = a.width(), a.height()
    for y in range(1, h - 1, 2):
        for x in range(1, l - 1, 2):
            p = a.pixel(x, y)
            if proches(p, b.pixel(x, y)):
                continue
            # décalage d'un pixel (lissage des bords) : un voisin identique suffit
            if not any(proches(p, b.pixel(x + dx, y + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                diff += 1
    return diff / (((l - 2) // 2) * ((h - 2) // 2))


def image(symbole):
    """Dessine le symbole sur une géométrie type avec une marge (pas l'aperçu de QGIS, qui rogne les bords)."""
    from qgis.core import QgsFillSymbol, QgsLineSymbol, QgsRenderContext
    from qgis.PyQt.QtCore import QPointF
    from qgis.PyQt.QtGui import QColor, QImage, QPainter, QPolygonF
    t = TAILLE_ECHANTILLON
    img = QImage(t, t, QImage.Format_ARGB32)
    img.fill(QColor("white"))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    ctx = QgsRenderContext.fromQPainter(p)
    ctx.setScaleFactor(96 / 25.4)  # 96 points par pouce, comme l'aperçu de QGIS
    symbole = symbole.clone()
    symbole.startRender(ctx)
    m = t * 0.2
    if isinstance(symbole, QgsFillSymbol):
        exterieur = QPolygonF([QPointF(m, m), QPointF(t - m, m * 1.4), QPointF(t - m, t - m), QPointF(m * 1.3, t - m), QPointF(m, m)])
        trou = QPolygonF([QPointF(t * .45, t * .45), QPointF(t * .6, t * .45), QPointF(t * .6, t * .6), QPointF(t * .45, t * .45)])
        symbole.renderPolygon(exterieur, [trou], None, ctx)
    elif isinstance(symbole, QgsLineSymbol):
        symbole.renderPolyline(QPolygonF([QPointF(m, t - m), QPointF(t * .4, m), QPointF(t * .65, t * .7), QPointF(t - m, m * 1.5)]), None, ctx)
    else:
        symbole.renderPoint(QPointF(t / 2, t / 2), None, ctx)
    symbole.stopRender(ctx)
    p.end()
    return img


def signature_modele(diff: str) -> str:
    """Regroupe les différences par chemin sans indices ni valeurs : « couches.rendu.classes.symbole.couches.props.x »."""
    chemin = diff.split(" : ")[0]
    return re.sub(r"\[\d+\]", "", chemin)


def annonces(*rapports: Rapport) -> list[str]:
    return [f"{e.niveau} : {e.message}" for r in rapports for e in r.entrees if e.niveau in ("perte", "avertissement")]


def comparer(cat, nom: str, original: bytes, ext: str, dossier: Path, id_cas: str) -> dict:
    """Aller-retour d'un fichier (.qlr ou .lyrx) et comparaisons. Renvoie la fiche du cas."""
    r1 = api.convertir(original, nom, cat)
    fiche = {"id": id_cas, "fichier": nom, "ecarts_modele": [], "ecarts_image": [], "annonces": annonces(r1.rapport)}
    if not r1.reussi:
        fiche["erreur"] = r1.erreur or "échec à l'aller"
        return fiche
    r2 = api.convertir(r1.donnees, r1.nom_sortie, cat)
    fiche["annonces"] += annonces(r2.rapport)
    if not r2.reussi:
        fiche["erreur"] = r2.erreur or "échec au retour"
        return fiche
    avant = api.lire(original, nom, cat, Rapport())
    apres = api.lire(r2.donnees, r2.nom_sortie, cat, Rapport())
    fiche["ecarts_modele"] = comparer_documents(avant, apres)
    # images : QGIS dessine les symboles de l'original et du retour (côté .qlr)
    qlr_avant = original if ext == ".qlr" else r1.donnees
    qlr_apres = r2.donnees if ext == ".qlr" else api.convertir(r2.donnees, "retour.lyrx", cat).donnees
    sa, sb = symboles_de_qlr(qlr_avant), symboles_de_qlr(qlr_apres)
    if len(sa) != len(sb):
        fiche["ecarts_image"].append({"symbole": -1, "ecart": 1.0, "message": f"{len(sa)} symboles avant, {len(sb)} après"})
    for i, (a, b) in enumerate(zip(sa, sb)):
        ia, ib = image(a), image(b)
        e = ecart_image(ia, ib)
        if e > SEUIL_PIXELS:
            classes = "+".join(c.layerType() for c in a.symbolLayers())
            fiche["ecarts_image"].append({"symbole": i, "ecart": round(e, 3), "classes": classes})
            from qgis.PyQt.QtGui import QColor, QImage, QPainter
            planche = QImage(TAILLE_ECHANTILLON * 2 + 10, TAILLE_ECHANTILLON, QImage.Format_ARGB32)
            planche.fill(QColor("white"))
            p = QPainter(planche)
            p.drawImage(0, 0, ia)
            p.drawImage(TAILLE_ECHANTILLON + 10, 0, ib)
            p.end()
            planche.save(str(dossier / f"{id_cas}_symbole{i}.png"))
    fiche["silencieux"] = bool((fiche["ecarts_modele"] or fiche["ecarts_image"]) and not fiche["annonces"])
    (dossier / f"{id_cas}{ext}").write_bytes(original)
    return fiche


def muter_lyrx(donnees: bytes, h: random.Random) -> bytes:
    """Change au hasard couleurs, épaisseurs, tailles et angles des couches de symboles d'un vrai .lyrx."""
    doc = json.loads(donnees.decode("utf-8-sig"))

    def parcourir(o):
        if isinstance(o, dict):
            for k, v in list(o.items()):
                if k == "values" and o.get("type") == "CIMRGBColor" and isinstance(v, list) and h.random() < 0.5:
                    o[k] = [h.randint(0, 255) for _ in range(3)] + [h.choice([100, 100, 60])]
                elif k in ("width", "size", "separation", "stepX", "stepY") and isinstance(v, (int, float)) and h.random() < 0.5:
                    o[k] = round(v * h.uniform(0.5, 2), 2)
                elif k in ("rotation", "angle") and isinstance(v, (int, float)) and h.random() < 0.3:
                    o[k] = h.choice([0, 15, 45, 90])
                else:
                    parcourir(v)
        elif isinstance(o, list):
            for x in o:
                parcourir(x)
    parcourir(doc.get("layerDefinitions"))
    return json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8")


# --- boucle --------------------------------------------------------------------------------
def main() -> int:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--cas", type=int, default=300, help="nombre de symbologies QGIS inventées")
    a.add_argument("--graine", type=int, default=1, help="graine du hasard (même graine = mêmes cas)")
    a.add_argument("--mutations", type=int, default=0, help="nombre de mutations par .lyrx d'exemple")
    a.add_argument("--sortie", default=str(RACINE / "sorties" / "entrainement"))
    a.add_argument("--figer", nargs="*", default=[], help="identifiants de cas à copier dans exemples/fabriques/")
    args = a.parse_args()
    sortie = Path(args.sortie).resolve()
    if args.figer:
        dest = RACINE / "exemples" / "fabriques"
        dest.mkdir(parents=True, exist_ok=True)
        for id_cas in args.figer:
            for f in (sortie / "cas").glob(f"{id_cas}.*"):
                if f.suffix in (".qlr", ".lyrx"):
                    # Chemin des données rendu relatif : aucun chemin de poste dans le dépôt.
                    texte = f.read_text(encoding="utf-8")
                    for absolu in (str(sortie), str(sortie).replace("\\", "/"), json.dumps(str(sortie))[1:-1]):
                        texte = texte.replace(absolu, ".")
                    (dest / f"{id_cas}{f.suffix}").write_text(texte, encoding="utf-8")
                    print(f"figé : exemples/fabriques/{id_cas}{f.suffix}")
        return 0
    if sortie.exists():
        shutil.rmtree(sortie)
    (sortie / "cas").mkdir(parents=True)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from qgis.core import QgsApplication, QgsProject, QgsVectorLayer
    app = QgsApplication([], False)
    app.initQgis()
    cat = Catalogue.charger()
    gpkg = sortie / "donnees.gpkg"
    creer_donnees(gpkg)
    h = random.Random(args.graine)
    gen = Generateur(h)
    fiches = []
    couches = {"surface": "surfaces", "ligne": "lignes", "point": "points"}
    for n in range(args.cas):
        genre = h.choice(list(couches))
        couche = QgsVectorLayer(f"{gpkg}|layername={couches[genre]}", f"cas_{n:04d}", "ogr")
        couche.setRenderer(gen.rendu(genre))
        gen.etiquettes(couche)
        QgsProject.instance().addMapLayer(couche)
        try:
            qlr = qlr_de_couche(couche)
            fiches.append(comparer(cat, f"cas_{n:04d}.qlr", qlr, ".qlr", sortie / "cas", f"q{args.graine}_{n:04d}"))
        except Exception as e:  # le générateur lui-même ne doit pas arrêter la boucle
            fiches.append({"id": f"q{args.graine}_{n:04d}", "erreur": f"{type(e).__name__} : {e}",
                           "ecarts_modele": [], "ecarts_image": [], "annonces": []})
        QgsProject.instance().removeMapLayer(couche.id())
    for f in sorted((RACINE / "exemples" / "lyrx").glob("*.lyrx")):
        for m in range(args.mutations):
            donnees = muter_lyrx(f.read_bytes(), h)
            fiches.append(comparer(cat, f.name, donnees, ".lyrx", sortie / "cas", f"m{args.graine}_{f.stem[:30]}_{m}"))
    ecrire_rapport(fiches, sortie)
    return 0


def ecrire_rapport(fiches: list[dict], sortie: Path) -> None:
    groupes: dict[str, list[str]] = defaultdict(list)
    exemples: dict[str, str] = {}
    for f in fiches:
        etat = "silencieux" if f.get("silencieux") else "annoncé"
        for d in f.get("ecarts_modele", []):
            cle = f"{etat} | modèle | {signature_modele(d)}"
            groupes[cle].append(f["id"])
            exemples.setdefault(cle, d)
        for e in f.get("ecarts_image", []):
            cle = f"{etat} | image | {e.get('classes', e.get('message'))}"
            groupes[cle].append(f["id"])
            exemples.setdefault(cle, f"écart {e['ecart']:.1%}, symbole {e['symbole']}")
        if f.get("erreur"):
            cle = f"erreur | {f['erreur'][:80]}"
            groupes[cle].append(f["id"])
    nb = len(fiches)
    propres = sum(1 for f in fiches if not (f.get("ecarts_modele") or f.get("ecarts_image") or f.get("erreur")))
    silencieux = sum(1 for f in fiches if f.get("silencieux"))
    lignes = ["# Boucle d'entraînement : résultats", "",
              f"- {nb} cas ; **{propres} identiques** après l'aller-retour ;",
              f"- {silencieux} cas avec un écart **silencieux** (non signalé par le rapport) : à corriger d'abord ;",
              f"- {sum(1 for f in fiches if f.get('erreur'))} erreur(s).", "",
              "| Nombre | État | Nature | Groupe | Exemple | Cas |", "|---|---|---|---|---|---|"]
    for cle, ids in sorted(groupes.items(), key=lambda kv: (not kv[0].startswith("silencieux"), -len(kv[1]))):
        parts = cle.split(" | ")
        etat, nature, groupe = (parts + ["", ""])[:3] if len(parts) >= 3 else (parts[0], "", parts[1])
        ex = exemples.get(cle, "").replace("|", "/")[:120]
        lignes.append(f"| {len(ids)} | {etat} | {nature} | `{groupe}` | {ex} | {', '.join(sorted(set(ids))[:4])} |")
    (sortie / "rapport.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    (sortie / "fiches.json").write_text(json.dumps(fiches, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(lignes[2:5]))
    print(f"→ {sortie / 'rapport.md'}")


if __name__ == "__main__":
    sys.exit(main())
