"""Écriture d'un fichier .lyrx (ArcGIS Pro, JSON « CIM ») depuis le modèle neutre."""
from __future__ import annotations

import copy
import json
from typing import Optional

from . import chemins, sources
from .catalogue import Catalogue
from .ecriture_qlr import identifiant
from .modele import Classe, ClasseEtiquette, Couche, CoucheSymbole, Document, Rendu, Symbole
from .proprietes import Convertisseur, ecrire_lyrx
from .rapport import Rapport

_GEOM_MAPLEX = {"point": "Point", "ligne": "Line", "surface": "Polygon"}


class EcrivainLyrx:
    def __init__(self, catalogue: Catalogue, rapport: Rapport):
        self.cat = catalogue
        self.rapport = rapport
        self.conv = Convertisseur(catalogue, rapport)

    def ecrire(self, doc: Document) -> bytes:
        ecr = self.cat.formats["lyrx"]["ecriture"]
        definitions = []
        uris = []
        for i, couche in enumerate(doc.couches):
            uri = f"CIMPATH=map/{identifiant(couche.nom, str(i)).lower()}.json"
            uris.append(uri)
            definitions.append(self.ecrire_couche(couche, uri))
        document = {"type": "CIMLayerDocument", "version": ecr["version"], "build": ecr["build"],
                    "layers": uris, "layerDefinitions": definitions}
        return json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")

    # -- couche ---------------------------------------------------------------
    def ecrire_couche(self, couche: Couche, uri: str) -> dict:
        ou = f"Couche « {couche.nom} »"
        c = self.cat.modele("lyrx_couche_entites.json")
        c["name"] = couche.nom
        c["uRI"] = uri
        c["visibility"] = couche.visible
        if couche.opacite < 1:
            c["transparency"] = round((1 - couche.opacite) * 100, 2)
        if couche.echelle_min:
            c["minScale"] = couche.echelle_min
        if couche.echelle_max:
            c["maxScale"] = couche.echelle_max
        table = c["featureTable"]
        table["dataConnection"] = self._source(couche, ou)
        if couche.champ_affichage:
            table["displayField"] = couche.champ_affichage
        else:
            del table["displayField"]
        if couche.filtre:
            table["definitionExpression"], _ = self.conv.expr.depuis_qgis(couche.filtre, "SQL", ou + " > filtre")
        table["fieldDescriptions"] = [
            {"type": "CIMFieldDescription", "alias": alias, "fieldName": champ, "visible": True, "searchMode": "Exact"}
            for champ, alias in couche.alias.items()]
        if couche.rendu:
            c["renderer"] = self.ecrire_rendu(couche.rendu, couche.geometrie, ou + " > rendu")
        else:
            del c["renderer"]
        c["labelVisibility"] = bool(couche.etiquettes_actives and couche.etiquettes)
        c["labelClasses"] = [self.ecrire_etiquette(k, couche.geometrie, f"{ou} > étiquettes « {k.nom} »") for k in couche.etiquettes]
        return c

    def _source(self, couche: Couche, ou: str) -> dict:
        return sources.ecrire_lyrx(self.cat, self.rapport, couche, ou)

    # -- rendu ----------------------------------------------------------------
    def ecrire_rendu(self, rendu: Rendu, geometrie: str, ou: str) -> dict:
        type_cim = self.cat.rendu(rendu.type)["lyrx"]
        if rendu.type == "unique":
            classe = rendu.classes[0] if rendu.classes else Classe(rendu.symbole_defaut)
            return {"type": type_cim, "patch": "Default", "symbol": self.reference(classe.symbole, geometrie, ou), "label": classe.etiquette}
        r: dict = {"type": type_cim}
        if rendu.type == "categories":
            classes = []
            for k in rendu.classes:
                valeurs = [{"type": "CIMUniqueValue", "fieldValues": [self._valeur(v, ou) for v in tuple_]} for tuple_ in (k.valeurs or [[""]])]
                classes.append({"type": "CIMUniqueValueClass", "label": k.etiquette, "patch": "Default",
                                "symbol": self.reference(k.symbole, geometrie, f"{ou} > classe « {k.etiquette} »"),
                                "values": valeurs, "visible": k.visible})
            r.update({"defaultLabel": rendu.etiquette_defaut,
                      "defaultSymbol": self.reference(rendu.symbole_defaut, geometrie, ou + " > autres valeurs"),
                      "defaultSymbolPatch": "Default", "fields": list(rendu.champs),
                      "groups": [{"type": "CIMUniqueValueGroup", "classes": classes, "heading": ", ".join(rendu.champs)}],
                      "useDefaultSymbol": rendu.symbole_defaut is not None, "polygonSymbolColorTarget": "Fill"})
            if rendu.expression:
                texte, _ = self.conv.expr.depuis_qgis(rendu.expression, "Arcade", ou)
                r["valueExpressionInfo"] = {"type": "CIMExpressionInfo", "title": "Expression", "expression": texte, "returnType": "Default"}
            return r
        # classes de valeurs
        breaks = []
        precedent: Optional[float] = None
        for k in rendu.classes:
            if precedent is not None and k.min is not None and abs(k.min - precedent) > 1e-9:
                self.rapport.avertir(ou, f"Classe « {k.etiquette} » : ArcGIS ne connaît que des classes contiguës ; la borne basse {k.min:g} devient {precedent:g}.")
            breaks.append({"type": "CIMClassBreak", "label": k.etiquette, "patch": "Default",
                           "symbol": self.reference(k.symbole, geometrie, f"{ou} > classe « {k.etiquette} »"), "upperBound": k.max})
            precedent = k.max
        methode, _ = self.conv.liste_depuis_pivot("methodes_classification", "lyrx", rendu.methode or "manuelle", ou)
        type_classes = self.cat.rendus.get("classe_type_lyrx", "GraduatedColor")
        # ArcGIS n'accepte un poids d'obstacle aux étiquettes que pour les symboles proportionnels (relecture du lot 2)
        r.update({"barrierWeight": "High" if type_classes == "GraduatedSymbol" else "None", "breaks": breaks, "classBreakType": type_classes,
                  "classificationMethod": methode or "Manual", "field": rendu.champs[0] if rendu.champs else "",
                  "minimumBreak": rendu.classes[0].min if rendu.classes else 0,
                  "numberFormat": {"type": "CIMNumericFormat", "alignmentOption": "esriAlignRight", "alignmentWidth": 0,
                                   "roundingOption": "esriRoundNumberOfDecimals", "roundingValue": 6, "zeroPad": True},
                  "showInAscendingOrder": True, "heading": rendu.champs[0] if rendu.champs else "", "sampleSize": 10000,
                  "defaultSymbolPatch": "Default", "polygonSymbolColorTarget": "Fill", "normalizationType": "Nothing",
                  "useExclusionSymbol": False})
        if rendu.expression:
            texte, _ = self.conv.expr.depuis_qgis(rendu.expression, "Arcade", ou)
            r["valueExpressionInfo"] = {"type": "CIMExpressionInfo", "title": "Expression", "expression": texte, "returnType": "Default"}
        return r

    def _valeur(self, v: Optional[str], ou: str) -> str:
        if v is None:
            brut, _ = self.conv.liste_depuis_pivot("valeurs_speciales", "lyrx", None, ou)
            return brut or "<Null>"
        return str(v)

    # -- symboles -------------------------------------------------------------
    def reference(self, symbole: Optional[Symbole], geometrie: str, ou: str) -> Optional[dict]:
        if symbole is None:
            return None
        return {"type": "CIMSymbolReference", "symbol": self.symbole(symbole, ou)}

    def symbole(self, symbole: Symbole, ou: str) -> dict:
        type_cim = self.cat.genre(symbole.genre)["lyrx"]
        couches = []
        for i, cs in enumerate(symbole.couches):
            cim = self.couche_symbole(cs, symbole.genre, f"{ou} > couche {i + 1}")
            if cim is not None:
                couches.append(cim)
        couches.reverse()  # CIM : la première couche est dessinée au-dessus
        s: dict = {"type": type_cim, "symbolLayers": couches}
        if symbole.genre == "point":
            s.update({"haloSize": 1, "scaleX": 1, "angleAlignment": "Display"})
        if symbole.opacite < 1:
            self.rapport.avertir(ou, f"Opacité du symbole ({symbole.opacite:g}) non reprise : régler la transparence de la couche dans ArcGIS Pro.")
        return s

    def couche_symbole(self, cs: CoucheSymbole, genre: str, ou: str) -> Optional[dict]:
        entree = self.cat.couche_pour_ecriture(cs.type, "lyrx")
        if entree is None:
            self.rapport.perte(ou, f"Couche de symbole « {cs.type} » sans équivalent ArcGIS Pro.",
                               "Ajouter la correspondance dans catalogues/symboles.json.")
            return None
        objet = copy.deepcopy(entree["lyrx"].get("modele") or {"type": entree["lyrx"]["type"]})
        ecrire_lyrx(self.conv, entree.get("proprietes", []), cs.props, objet, ou)
        objet["enable"] = cs.actif
        if entree.get("sous_symbole"):
            sous = cs.sous_symbole or Symbole(genre=entree["sous_symbole"]["genre"])
            chemins.ecrire(objet, entree["sous_symbole"]["lyrx"], self.symbole(sous, ou + " > sous-symbole"))
        if cs.placement is not None and genre != "point":
            p = self.cat.placement(cs.placement.type)
            if p is None:
                self.rapport.perte(ou, f"Placement « {cs.placement.type} » sans équivalent ArcGIS Pro.")
            else:
                mp = copy.deepcopy(p["lyrx"].get("modele") or {"type": p["lyrx"]["type"]})
                ecrire_lyrx(self.conv, p.get("proprietes", []), cs.placement.props, mp, ou + " > placement")
                objet["markerPlacement"] = mp
        return chemins.nettoyer_facultatifs(objet)

    # -- étiquettes -----------------------------------------------------------------
    def ecrire_etiquette(self, k: ClasseEtiquette, geometrie: str, ou: str) -> dict:
        lc = copy.deepcopy(self.cat.etiquettes["lyrx_modele"])
        lc["name"] = k.nom or "Classe 1"
        if geometrie in _GEOM_MAPLEX:
            lc["maplexLabelPlacementProperties"]["featureType"] = _GEOM_MAPLEX[geometrie]
            lc["standardLabelPlacementProperties"]["featureType"] = _GEOM_MAPLEX[geometrie]
        ecrire_lyrx(self.conv, self.cat.etiquettes["proprietes"], k.props, lc, ou, geometrie)
        if k.filtre:
            lc["whereClause"], _ = self.conv.expr.depuis_qgis(k.filtre, "SQL", ou + " > filtre")
        return chemins.nettoyer_facultatifs(lc)
