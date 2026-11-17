"""Écriture d'un fichier .qlr (QGIS, XML « Layer Definition ») depuis le modèle neutre."""
from __future__ import annotations

import copy
import hashlib
import re
import xml.etree.ElementTree as ET
from typing import Optional

from . import sources
from .catalogue import DOSSIER_MODELES, Catalogue
from .modele import Classe, ClasseEtiquette, Couche, CoucheSymbole, Document, Rendu, Symbole
from .proprietes import Convertisseur, ProprietesXml, ecrire_qgis
from .rapport import Rapport

_GEOM_QGIS = {"point": "Point", "ligne": "Line", "surface": "Polygon"}
_GEOM_ETIQUETTES = {"point": "PointGeometry", "ligne": "LineGeometry", "surface": "PolygonGeometry"}


def identifiant(nom: str, graine: str = "") -> str:
    """Identifiant stable (le même nom donne toujours le même identifiant)."""
    propre = re.sub(r"[^A-Za-z0-9_]", "_", nom)[:40] or "couche"
    return f"{propre}_{hashlib.md5((graine + nom).encode('utf-8')).hexdigest()[:8]}"


def _uuid(*morceaux: str) -> str:
    h = hashlib.md5("|".join(morceaux).encode("utf-8")).hexdigest()
    return "{%s-%s-%s-%s-%s}" % (h[:8], h[8:12], h[12:16], h[16:20], h[20:32])


def _option_map(parent: ET.Element, props: dict) -> ET.Element:
    carte = ET.SubElement(parent, "Option", type="Map")
    for cle in sorted(props):
        ET.SubElement(carte, "Option", name=cle, value=str(props[cle]), type="QString")
    return carte


class EcrivainQlr:
    def __init__(self, catalogue: Catalogue, rapport: Rapport):
        self.cat = catalogue
        self.rapport = rapport
        self.conv = Convertisseur(catalogue, rapport)

    # -- document -------------------------------------------------------------
    def ecrire(self, doc: Document) -> bytes:
        racine = ET.Element("qlr")
        groupe = ET.SubElement(racine, "layer-tree-group", expanded="1", checked="Qt::Checked", name="")
        ET.SubElement(groupe, "customproperties")
        couches_xml = ET.SubElement(racine, "maplayers")
        noms_vus: dict[str, int] = {}
        for couche in doc.couches:
            n = noms_vus.get(couche.nom, 0)
            noms_vus[couche.nom] = n + 1
            ident = identifiant(couche.nom, str(n))
            maplayer = self.ecrire_couche(couche, ident)
            couches_xml.append(maplayer)
            noeud = ET.SubElement(groupe, "layer-tree-layer", expanded="1", name=couche.nom, id=ident,
                                  providerKey=maplayer.findtext("provider") or "ogr",
                                  source=maplayer.findtext("datasource") or "",
                                  checked="Qt::Checked" if couche.visible else "Qt::Unchecked")
            ET.SubElement(noeud, "customproperties")
        ET.indent(racine, space="  ")
        corps = ET.tostring(racine, encoding="unicode")
        return ("<!DOCTYPE qgis-layer-definition>\n" + corps + "\n").encode("utf-8")

    # -- couche ---------------------------------------------------------------
    def ecrire_couche(self, couche: Couche, ident: str) -> ET.Element:
        ou = f"Couche « {couche.nom} »"
        attributs = {
            "type": "vector",
            "geometry": _GEOM_QGIS.get(couche.geometrie, "Unknown"),
            "styleCategories": "AllStyleCategories",
            "hasScaleBasedVisibilityFlag": "1" if (couche.echelle_min or couche.echelle_max) else "0",
            "minScale": _nombre(couche.echelle_min or 1e8),
            "maxScale": _nombre(couche.echelle_max or 0),
            "labelsEnabled": "1" if couche.etiquettes_actives and couche.etiquettes else "0",
            "readOnly": "0",
            "simplifyDrawingHints": "1", "simplifyDrawingTol": "1", "simplifyLocal": "1", "simplifyAlgorithm": "0",
            "simplifyMaxScale": "1",
        }
        ml = ET.Element("maplayer", attributs)
        ET.SubElement(ml, "id").text = ident
        fournisseur, chemin = self._source(couche, ou)
        ET.SubElement(ml, "datasource").text = chemin
        ET.SubElement(ml, "layername").text = couche.nom
        srs = self.cat.formats["qgis"].get("srs_defaut")
        if srs:
            ET.SubElement(ET.SubElement(ml, "srs"), "spatialrefsys").append(_texte("authid", srs))
        ET.SubElement(ml, "provider", encoding="UTF-8").text = fournisseur
        ET.SubElement(ml, "legend", type="default-vector")
        if couche.rendu:
            ml.append(self.ecrire_rendu(couche.rendu, couche.geometrie, ou + " > rendu"))
        if couche.etiquettes:
            ml.append(self.ecrire_etiquettes(couche.etiquettes, couche.geometrie, ou + " > étiquettes"))
        ET.SubElement(ml, "blendMode").text = "0"
        ET.SubElement(ml, "featureBlendMode").text = "0"
        ET.SubElement(ml, "layerOpacity").text = _nombre(couche.opacite)
        if couche.alias:
            alias = ET.SubElement(ml, "aliases")
            for champ, nom in couche.alias.items():
                ET.SubElement(alias, "alias", field=champ, name=nom)
        if couche.champ_affichage:
            ET.SubElement(ml, "previewExpression").text = '"%s"' % couche.champ_affichage.replace('"', '""')
        return ml

    def _source(self, couche: Couche, ou: str) -> tuple[str, str]:
        return sources.ecrire_qgis(self.cat, self.rapport, couche, ou)

    # -- rendu ----------------------------------------------------------------
    def ecrire_rendu(self, rendu: Rendu, geometrie: str, ou: str) -> ET.Element:
        type_qgis = self.cat.rendu(rendu.type)["qgis"]
        r = ET.Element("renderer-v2", type=type_qgis, symbollevels="0", forceraster="0", enableorderby="0", referencescale="-1")
        symboles = ET.Element("symbols")
        if rendu.type == "unique":
            classe = rendu.classes[0] if rendu.classes else Classe(rendu.symbole_defaut)
            if classe.etiquette:
                self.rapport.info(ou, f"Libellé de légende « {classe.etiquette} » du symbole unique non repris : "
                                      "QGIS affiche le nom de la couche.")
            symboles.append(self.ecrire_symbole(classe.symbole or _symbole_vide(geometrie), "0", ou))
        else:
            r.set("attr", self._attribut(rendu, ou))
            if rendu.type == "categories":
                conteneur = ET.SubElement(r, "categories")
                for i, k in enumerate(rendu.classes):
                    cat_xml = ET.SubElement(conteneur, "category", symbol=str(i), label=k.etiquette,
                                            render="true" if k.visible else "false", uuid=_uuid(ou, str(i)))
                    valeurs = [self._valeur(v) for v in k.valeurs] or [""]
                    if len(valeurs) == 1:
                        self._poser_valeur(cat_xml, valeurs[0])
                    else:
                        for v in valeurs:
                            self._poser_valeur(ET.SubElement(cat_xml, "val"), v)
                    symboles.append(self.ecrire_symbole(k.symbole or _symbole_vide(geometrie), str(i), f"{ou} > classe « {k.etiquette} »"))
                nulle = next((k for k in rendu.classes if k.valeurs == [[None]]), None)
                if nulle is not None and rendu.symbole_defaut is not None and nulle.symbole == rendu.symbole_defaut:
                    pass  # la catégorie NULL de QGIS sert déjà pour les autres valeurs (voir lecture_qlr)
                elif nulle is not None and rendu.symbole_defaut is None and nulle.visible:
                    self.rapport.avertir(ou, f"Dans QGIS, la catégorie NULL « {nulle.etiquette} » dessine aussi toutes les "
                                             "valeurs non listées, qu'ArcGIS ne dessinait pas.",
                                         "Dans QGIS, passer à un ensemble de règles (« \"champ\" IS NULL ») pour ne dessiner que NULL.")
                elif rendu.symbole_defaut is not None:
                    if nulle is not None:
                        self.rapport.perte(ou, f"QGIS ne distingue pas les valeurs NULL des « autres valeurs » : la classe "
                                               f"« {nulle.etiquette} » (NULL) sera dessinée avec le symbole « autres valeurs ».",
                                           "Dans QGIS, passer à un ensemble de règles (« \"champ\" IS NULL » puis « ELSE ») "
                                           "pour garder deux symboles.")
                    i = len(rendu.classes)
                    ET.SubElement(conteneur, "category", symbol=str(i), value="", type="string", render="true",
                                  label=rendu.etiquette_defaut, uuid=_uuid(ou, "defaut"))
                    symboles.append(self.ecrire_symbole(rendu.symbole_defaut, str(i), ou + " > autres valeurs"))
            else:
                r.set("graduatedMethod", "GraduatedColor")
                conteneur = ET.SubElement(r, "ranges")
                for i, k in enumerate(rendu.classes):
                    ET.SubElement(conteneur, "range", symbol=str(i), label=k.etiquette, render="true" if k.visible else "false",
                                  lower=_nombre(k.min, 12), upper=_nombre(k.max, 12), uuid=_uuid(ou, str(i)))
                    symboles.append(self.ecrire_symbole(k.symbole or _symbole_vide(geometrie), str(i), f"{ou} > classe « {k.etiquette} »"))
                if rendu.symbole_defaut is not None:
                    self.rapport.perte(ou, "Symbole « autres valeurs » des classes : QGIS n'a pas d'équivalent pour les valeurs hors classes.")
                methode, _ = self.conv.liste_depuis_pivot("methodes_classification", "qgis", rendu.methode or "manuelle", ou)
                ET.SubElement(r, "classificationMethod", id=methode or "Custom")
        if rendu.type == "unique":
            r.append(symboles)
        else:
            r.insert(1, symboles)  # après <categories> ou <ranges>, comme QGIS
        return r

    def _attribut(self, rendu: Rendu, ou: str) -> str:
        if rendu.expression:
            return rendu.expression
        if len(rendu.champs) == 1:
            return rendu.champs[0]
        if not rendu.champs:
            self.rapport.perte(ou, "Aucun champ de classement trouvé.")
            return ""
        sep = self.cat.rendus.get("separateur_valeurs", ", ")
        morceaux = []
        for i, champ in enumerate(rendu.champs):
            if i:
                morceaux.append("'" + sep.replace("'", "''") + "'")
            morceaux.append('"' + champ.replace('"', '""') + '"')
        self.rapport.info(ou, f"Catégories sur {len(rendu.champs)} champs : QGIS classe sur l'expression concat({', '.join(morceaux)}).")
        return "concat(" + ", ".join(morceaux) + ")"

    def _valeur(self, valeurs: list) -> Optional[str]:
        if len(valeurs) == 1:
            return valeurs[0]
        sep = self.cat.rendus.get("separateur_valeurs", ", ")
        return sep.join("" if v is None else str(v) for v in valeurs)

    def _poser_valeur(self, element: ET.Element, valeur: Optional[str]) -> None:
        if valeur is None:
            element.set("value", "NULL")
            element.set("type", "NULL")
        else:
            element.set("value", str(valeur))
            element.set("type", "string")

    # -- symboles -------------------------------------------------------------
    def ecrire_symbole(self, symbole: Symbole, nom: str, ou: str) -> ET.Element:
        avant, self.conv.genre_symbole = self.conv.genre_symbole, symbole.genre
        try:
            return self._ecrire_symbole(symbole, nom, ou)
        finally:
            self.conv.genre_symbole = avant

    def _ecrire_symbole(self, symbole: Symbole, nom: str, ou: str) -> ET.Element:
        genre = self.cat.genre(symbole.genre)["qgis"]
        s = ET.Element("symbol", type=genre, name=nom, alpha=_nombre(symbole.opacite), clip_to_extent="1", force_rhr="0")
        couches = [self._substituer_police(c, ou) for c in symbole.couches]
        i = 0
        numero = 0
        while i < len(couches):
            cs = couches[i]
            entree = self.cat.couche_pour_ecriture(cs.type, "qgis")
            if entree is None:
                self.rapport.perte(ou, f"Couche de symbole « {cs.type} » sans équivalent QGIS.",
                                   "Ajouter la correspondance dans catalogues/symboles.json.")
                i += 1
                continue
            if entree.get("famille") == "marqueur" and symbole.genre != "point":
                groupe = [cs]
                while i + 1 < len(couches) and couches[i + 1].placement == cs.placement and \
                        (self.cat.couche_pour_ecriture(couches[i + 1].type, "qgis") or {}).get("famille") == "marqueur":
                    i += 1
                    groupe.append(couches[i])
                s.append(self._enveloppe(groupe, symbole.genre, f"@{nom}@{numero}", ou))
            else:
                if cs.placement is not None and symbole.genre == "point":
                    self.rapport.info(ou, "Placement de marqueur ignoré dans un symbole ponctuel.")
                if entree.get("famille") == "remplissage" and symbole.genre != "surface":
                    self.rapport.perte(ou, f"Couche de remplissage « {cs.type} » dans un symbole de {symbole.genre} : ignorée par QGIS.")
                    i += 1
                    continue
                s.append(self.ecrire_couche_symbole(cs, entree, f"@{nom}@{numero}", ou))
            numero += 1
            i += 1
        vide = self.cat.genre(symbole.genre).get("qgis_vide")
        if numero == 0 and vide:
            # Sans aucune couche, QGIS remplacerait le symbole par un symbole par défaut (visible) :
            # on écrit une couche invisible pour garder un symbole qui ne dessine rien.
            couche = ET.SubElement(s, "layer", {"class": vide["classe"], "enabled": "1", "pass": "0", "locked": "0"})
            _option_map(couche, dict(vide["props"]))
        return s

    def ecrire_couche_symbole(self, cs: CoucheSymbole, entree: dict, nom_sous: str, ou: str) -> ET.Element:
        props = dict(entree["qgis"].get("fixe", {}))
        ecrire_qgis(self.conv, entree.get("proprietes", []), cs.props, props, ou)
        couche = ET.Element("layer", {"class": entree["qgis"]["classe"], "enabled": "1" if cs.actif else "0", "pass": "0", "locked": "0"})
        _option_map(couche, props)
        if entree.get("sous_symbole"):
            sous = cs.sous_symbole or _symbole_vide(entree["sous_symbole"]["genre"])
            periode = cs.props.get(entree["sous_symbole"].get("qgis_decalage_dans") or "")
            if isinstance(periode, (int, float)) and periode > 0:
                ramene = _decalage_dans_periode(sous, float(periode))
                if ramene is not sous:
                    self.rapport.info(ou, "Décalage du trait des hachures ramené dans l'écartement des lignes "
                                          "(même dessin ; QGIS n'affiche rien au-delà).")
                sous = ramene
            couche.append(self.ecrire_symbole(sous, nom_sous, ou + " > sous-symbole"))
        return couche

    def _enveloppe(self, marqueurs: list[CoucheSymbole], genre: str, nom_sous: str, ou: str) -> ET.Element:
        """Un marqueur dans une ligne ou une surface : QGIS l'enveloppe dans une couche de placement."""
        placement = marqueurs[0].placement
        entree = self.cat.placement(placement.type) if placement else None
        if entree is None:
            pivot = "centre_surface" if genre == "surface" else "sommets"
            self.rapport.avertir(ou, f"Marqueur sans placement dans un symbole de {genre} : placé {'au centre' if genre == 'surface' else 'sur les sommets'}.")
            entree = self.cat.placement(pivot)
            props_placement: dict = {}
        else:
            props_placement = placement.props
        props = dict(entree["qgis"].get("fixe", {}))
        ecrire_qgis(self.conv, entree.get("proprietes", []), props_placement, props, ou)
        couche = ET.Element("layer", {"class": entree["qgis"]["classe"], "enabled": "1" if marqueurs[0].actif else "0", "pass": "0", "locked": "0"})
        _option_map(couche, props)
        sous = Symbole(genre="point", couches=[CoucheSymbole(type=m.type, props=m.props, actif=m.actif) for m in marqueurs])
        couche.append(self.ecrire_symbole(sous, nom_sous, ou + " > marqueur"))
        return couche

    def _substituer_police(self, cs: CoucheSymbole, ou: str) -> CoucheSymbole:
        if cs.type != "marqueur_police":
            return cs
        police = cs.props.get("police")
        code = cs.props.get("caractere")
        for s in self.cat.polices.get("substitutions", []):
            if s["police"] == police and int(s["caractere"]) == int(code or -1):
                self.rapport.avertir(ou, f"Caractère n° {code} de la police « {police} » remplacé par la forme "
                                         f"« {s['forme']} » (police propre à ArcGIS, absente de QGIS).",
                                     "Table de remplacement : catalogues/polices.json.")
                taille_police = float(cs.props.get("taille") or 10)
                couleur = cs.props.get("couleur")
                props = {"forme": s["forme"], "taille": round(taille_police * float(s.get("facteur_taille", 1)), 4),
                         "angle": (cs.props.get("angle") or 0) + float(s.get("angle", 0))}
                if s.get("rendu", "plein") == "plein":
                    # contour de la même couleur, le plus fin possible : le glyphe n'a pas de contour
                    props.update({"couleur": couleur, "couleur_contour": couleur, "largeur_contour": 0})
                else:
                    # « creux » (forme vide) ou « trait » (croix…) : seul le contour dessine, à l'épaisseur du glyphe
                    props.update({"couleur": [0, 0, 0, 0], "couleur_contour": couleur,
                                  "largeur_contour": round(taille_police * float(s.get("epaisseur", 0.05)), 4)})
                for k in ("decalage_x", "decalage_y"):
                    if k in cs.props:
                        props[k] = cs.props[k]
                return CoucheSymbole(type="marqueur_simple", props=props, actif=cs.actif, placement=cs.placement)
        if police in self.cat.polices.get("polices_esri", []):
            self.rapport.avertir(ou, f"Police « {police} » (caractère n° {code}) : police propre à ArcGIS, sans doute absente du poste QGIS.",
                                 "Installer la police, ou ajouter une substitution dans catalogues/polices.json.")
        return cs

    # -- étiquettes -------------------------------------------------------------
    def ecrire_etiquettes(self, classes: list[ClasseEtiquette], geometrie: str, ou: str) -> ET.Element:
        if len(classes) == 1 and not classes[0].filtre:
            lab = ET.Element("labeling", type="simple")
            lab.append(self._reglage(classes[0], geometrie, ou))
            return lab
        lab = ET.Element("labeling", type="rule-based")
        regles = ET.SubElement(lab, "rules", key=_uuid(ou, "racine"))
        for i, k in enumerate(classes):
            attrs = {"key": _uuid(ou, str(i)), "description": k.nom}
            if k.filtre:
                attrs["filter"] = k.filtre
            if not k.props.get("visible", True):
                attrs["active"] = "0"
            regle = ET.SubElement(regles, "rule", attrs)
            regle.append(self._reglage(k, geometrie, f"{ou} « {k.nom} »"))
        return lab

    def _reglage(self, k: ClasseEtiquette, geometrie: str, ou: str) -> ET.Element:
        reglage = copy.deepcopy(_gabarit_etiquettes())
        reglage.find("placement").set("layerType", _GEOM_ETIQUETTES.get(geometrie, "UnknownGeometry"))
        ecrire_qgis(self.conv, self.cat.etiquettes["proprietes"], k.props, ProprietesXml(reglage), ou, geometrie)
        return reglage


_GABARIT: Optional[ET.Element] = None


def _gabarit_etiquettes() -> ET.Element:
    global _GABARIT
    if _GABARIT is None:
        _GABARIT = ET.parse(DOSSIER_MODELES / "qgis_reglage_etiquettes.xml").getroot()
    return _GABARIT


def _symbole_vide(genre: str) -> Symbole:
    return Symbole(genre=genre if genre in ("point", "ligne", "surface") else "surface", couches=[])


def _texte(balise: str, texte: str) -> ET.Element:
    e = ET.Element(balise)
    e.text = texte
    return e


def _nombre(x, decimales: int = 6) -> str:
    if x is None:
        return "0"
    r = round(float(x), decimales)
    if r == int(r) and abs(r) < 1e15:
        return str(int(r))
    return repr(r)


def _decalage_dans_periode(sous: Symbole, periode: float) -> Symbole:
    """Hachures : décaler le trait d'une période entière ne change pas le dessin, mais QGIS n'affiche
    plus rien quand le décalage du trait atteint la moitié de l'écartement des lignes (vérifié dans
    QGIS 3.44). On le ramène dans [−période/2, période/2[ (catalogue : « qgis_decalage_dans »)."""
    def a_ramener(d) -> bool:
        return isinstance(d, (int, float)) and not -periode / 2 < d < periode / 2
    if not any(a_ramener(c.props.get("decalage")) for c in sous.couches):
        return sous
    sous = copy.deepcopy(sous)
    for c in sous.couches:
        if a_ramener(c.props.get("decalage")):
            c.props["decalage"] = round((c.props["decalage"] + periode / 2) % periode - periode / 2, 4)
    return sous
