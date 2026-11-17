"""Lecture d'un fichier .lyrx (ArcGIS Pro, JSON « CIM ») vers le modèle neutre."""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from . import chemins, sources
from .catalogue import Catalogue
from .modele import (Classe, ClasseEtiquette, Couche, CoucheSymbole, Document, Placement, Rendu,
                     Source, Symbole)
from .proprietes import Convertisseur, est_trivial, lire_lyrx
from .rapport import Rapport

_GEOM_MAPLEX = {"Polygon": "surface", "Line": "ligne", "Point": "point"}


def charger_json(donnees: bytes | str) -> Any:
    if isinstance(donnees, bytes):
        donnees = donnees.decode("utf-8-sig")
    # ArcGIS écrit parfois NaN ou Infinity pour une valeur non définie : on les lit comme absentes.
    return json.loads(donnees.lstrip("﻿"), parse_constant=lambda _: None)


class LecteurLyrx:
    def __init__(self, catalogue: Catalogue, rapport: Rapport):
        self.cat = catalogue
        self.rapport = rapport
        self.conv = Convertisseur(catalogue, rapport)
        self._types_effets = self._effets_connus()

    def _effets_connus(self) -> set[str]:
        types = set()
        for c in self.cat.couches:
            for p in c.get("proprietes", []):
                for m in re.finditer(r"effects\[type=([A-Za-z]+)\]", p.get("lyrx") or ""):
                    types.add(m.group(1))
        return types

    # -- document ------------------------------------------------------------
    def lire(self, donnees: bytes | str) -> Document:
        d = charger_json(donnees)
        doc = Document(format_source="lyrx", version_source=str(d.get("version", "")))
        if not any(doc.version_source.startswith(v) for v in self.cat.formats["lyrx"]["lecture_versions"]):
            self.rapport.avertir("fichier", f"Version de .lyrx « {doc.version_source} » non testée : conversion tentée quand même.",
                                 "Ajouter la version dans catalogues/formats.json après l'avoir testée.")
        if d.get("type") == "CIMLayerDocument":
            definitions = d.get("layerDefinitions") or []
        elif str(d.get("type", "")).startswith("CIM") and "Layer" in str(d.get("type")):
            definitions = [d]
        else:
            raise ValueError("Ce fichier n'est pas un fichier de couche ArcGIS Pro (.lyrx) : type « %s »." % d.get("type"))
        for definition in definitions:
            t = definition.get("type")
            nom = definition.get("name", "?")
            if t == "CIMFeatureLayer":
                doc.couches.append(self.lire_couche(definition))
            elif t == "CIMGroupLayer":
                self.rapport.info(f"Groupe « {nom} »", "Couche de groupe : ses couches sont converties une à une, sans le groupe.")
            else:
                self.rapport.perte(f"Couche « {nom} »", f"Type de couche « {t} » non pris en charge (seules les couches d'entités vectorielles le sont).")
        if not doc.couches:
            self.rapport.perte("fichier", "Aucune couche d'entités vectorielles trouvée dans le fichier.")
        return doc

    # -- couche ---------------------------------------------------------------
    def lire_couche(self, c: dict) -> Couche:
        ou = f"Couche « {c.get('name', '?')} »"
        couche = Couche(nom=c.get("name") or "couche")
        couche.visible = c.get("visibility", True)
        couche.opacite = round(1 - float(c.get("transparency") or 0) / 100, 4)
        couche.echelle_min = float(c["minScale"]) if c.get("minScale") else None
        couche.echelle_max = float(c["maxScale"]) if c.get("maxScale") else None
        table = c.get("featureTable") or {}
        couche.source = self.lire_source(table.get("dataConnection") or {}, ou)
        if table.get("definitionExpression"):
            couche.filtre = self.conv.expr.vers_qgis(table["definitionExpression"], "SQL", ou + " > requête de définition")
        couche.champ_affichage = table.get("displayField")
        for fd in table.get("fieldDescriptions") or []:
            if fd.get("alias") and fd.get("fieldName") and fd["alias"] != fd["fieldName"]:
                couche.alias[fd["fieldName"]] = fd["alias"]
        self._signaler(c, self.cat.rendus.get("signaler_lyrx", {}).get("couche", {}), ou)
        if c.get("renderer"):
            couche.rendu = self.lire_rendu(c["renderer"], ou + " > rendu")
        else:
            self.rapport.perte(ou, "Pas de rendu (symbologie) dans la couche.")
        couche.geometrie = self._geometrie(couche, c)
        couche.etiquettes_actives = bool(c.get("labelVisibility", False))
        for i, lc in enumerate(c.get("labelClasses") or []):
            couche.etiquettes.append(self.lire_etiquette(lc, couche.geometrie, f"{ou} > étiquettes « {lc.get('name', i + 1)} »"))
        return couche

    def _signaler(self, objet: dict, liste: dict, ou: str) -> None:
        for chemin, libelle in liste.items():
            if chemin.startswith("_"):
                continue
            if not est_trivial(chemins.lire(objet, chemin)):
                self.rapport.perte(ou, f"{libelle} : non converti.", "Voir docs/limites.md ; à ajouter dans une prochaine version.")

    def _geometrie(self, couche: Couche, c: dict) -> str:
        r = couche.rendu
        if r:
            for s in [r.symbole_defaut] + [k.symbole for k in r.classes]:
                if s is not None:
                    return s.genre
        for lc in c.get("labelClasses") or []:
            g = _GEOM_MAPLEX.get(chemins.lire(lc, "maplexLabelPlacementProperties.featureType"))
            if g:
                return g
        return "inconnu"

    def lire_source(self, dc: dict, ou: str) -> Source:
        return sources.lire_lyrx(self.cat, self.rapport, dc, ou)

    # -- rendu -----------------------------------------------------------------
    def lire_rendu(self, r: dict, ou: str) -> Optional[Rendu]:
        t = r.get("type")
        pivot = self.cat.rendu_par("lyrx", t)
        self._signaler(r, self.cat.rendus.get("signaler_lyrx", {}).get("rendu", {}), ou)
        if pivot is None:
            nom = self.cat.rendus["non_pris_en_charge"]["lyrx"].get(t, t)
            self.rapport.perte(ou, f"Méthode de rendu « {nom} » non prise en charge.",
                               "Seul le symbole par défaut est repris s'il existe.")
            if r.get("defaultSymbol"):
                return Rendu(type="unique", classes=[Classe(self.lire_symbole(r["defaultSymbol"], ou), r.get("defaultLabel", ""))])
            return None
        rendu = Rendu(type=pivot)
        if pivot == "unique":
            rendu.classes.append(Classe(self.lire_symbole(r.get("symbol"), ou + " > symbole"), r.get("label") or ""))
        elif pivot == "categories":
            rendu.champs = list(r.get("fields") or [])
            if r.get("valueExpressionInfo"):
                vei = r["valueExpressionInfo"]
                rendu.expression = self.conv.expr.vers_qgis(vei.get("expression", ""), "Arcade", ou)
            for g in r.get("groups") or []:
                for k in g.get("classes") or []:
                    valeurs = []
                    for uv in k.get("values") or []:
                        valeurs.append([self.conv.liste_vers_pivot("valeurs_speciales", "lyrx", v, ou) for v in uv.get("fieldValues") or []])
                    rendu.classes.append(Classe(
                        symbole=self.lire_symbole(k.get("symbol"), f"{ou} > classe « {k.get('label', '')} »"),
                        etiquette=k.get("label") or "", valeurs=valeurs, visible=k.get("visible", True)))
            if r.get("useDefaultSymbol") and r.get("defaultSymbol"):
                rendu.symbole_defaut = self.lire_symbole(r["defaultSymbol"], ou + " > autres valeurs")
                rendu.etiquette_defaut = r.get("defaultLabel") or ""
        elif pivot == "classes":
            rendu.champs = [r["field"]] if r.get("field") else []
            if r.get("valueExpressionInfo"):
                rendu.expression = self.conv.expr.vers_qgis(r["valueExpressionInfo"].get("expression", ""), "Arcade", ou)
            if r.get("normalizationType") not in (None, "Nothing"):
                self.rapport.perte(ou, f"Normalisation « {r.get('normalizationType')} » non convertie : les bornes portent sur la valeur brute.")
            rendu.methode = self.conv.liste_vers_pivot("methodes_classification", "lyrx", r.get("classificationMethod"), ou, "manuelle")
            bas = r.get("minimumBreak")
            for i, b in enumerate(r.get("breaks") or []):
                if b.get("upperBound") is None:
                    self.rapport.perte(ou, f"Classe « {b.get('label', i + 1)} » sans borne supérieure : ignorée.")
                    continue
                haut = float(b.get("upperBound"))
                if bas is None:
                    bas = 0.0 if haut >= 0 else haut - abs(haut)
                    self.rapport.avertir(ou, f"Borne inférieure de la première classe absente du .lyrx : fixée à {bas:g}.",
                                         "Vérifier la première classe dans QGIS.")
                rendu.classes.append(Classe(
                    symbole=self.lire_symbole(b.get("symbol"), f"{ou} > classe « {b.get('label', '')} »"),
                    etiquette=b.get("label") or "", min=float(bas), max=haut))
                bas = haut
            if r.get("useDefaultSymbol") and r.get("defaultSymbol"):
                rendu.symbole_defaut = self.lire_symbole(r["defaultSymbol"], ou + " > autres valeurs")
                rendu.etiquette_defaut = r.get("defaultLabel") or ""
        return rendu

    # -- symboles ------------------------------------------------------------------
    def lire_symbole(self, ref: Optional[dict], ou: str) -> Optional[Symbole]:
        if not ref:
            return None
        sym = ref.get("symbol") if ref.get("type") == "CIMSymbolReference" else ref
        if not sym:
            return None
        genre = self.cat.genre_par_lyrx(sym.get("type"))
        if genre is None:
            self.rapport.perte(ou, f"Type de symbole « {sym.get('type')} » non pris en charge.",
                               "Ajouter le genre dans catalogues/symboles.json (« genres »).")
            return None
        symbole = Symbole(genre=genre)
        for i, sl in enumerate(reversed(sym.get("symbolLayers") or [])):
            cs = self.lire_couche_symbole(sl, f"{ou} > couche {i + 1}")
            if cs is not None:
                symbole.couches.append(cs)
        for e in sym.get("effects") or []:
            self.rapport.perte(ou, f"Effet géométrique « {e.get('type')} » sur le symbole entier non converti.")
        return symbole

    def lire_couche_symbole(self, sl: dict, ou: str) -> Optional[CoucheSymbole]:
        entree = self.cat.couche_par_lyrx(sl)
        if entree is None:
            self.rapport.perte(ou, f"Couche de symbole « {sl.get('type')} » non convertie.",
                               "Ajouter la correspondance dans catalogues/symboles.json.")
            return None
        if entree.get("pivot") is None:
            return None
        message = entree.get("avertissement_lyrx") or entree.get("avertissement")
        if message:
            self.rapport.avertir(ou, message)
        props, utilisees = lire_lyrx(self.conv, entree.get("proprietes", []), sl, ou)
        cs = CoucheSymbole(type=entree["pivot"], props=props, actif=bool(sl.get("enable", True)))
        if entree.get("sous_symbole"):
            chemin = entree["sous_symbole"]["lyrx"]
            utilisees.add(chemin)
            cs.sous_symbole = self.lire_symbole(chemins.lire(sl, chemin), ou + " > sous-symbole")
        if sl.get("markerPlacement"):
            cs.placement = self.lire_placement(sl["markerPlacement"], ou)
        for e in sl.get("effects") or []:
            if e.get("type") not in self._types_effets:
                self.rapport.perte(ou, f"Effet géométrique « {e.get('type')} » non converti.",
                                   "Ajouter l'effet dans catalogues/symboles.json (propriété avec un chemin effects[type=…]).")
        self._non_utilisees(sl, utilisees | {"effects", "markerPlacement"}, ou)
        return cs

    def lire_placement(self, mp: dict, ou: str) -> Optional[Placement]:
        entree = self.cat.placement_par_lyrx(mp)
        if entree is None:
            self.rapport.perte(ou, f"Placement de marqueur « {mp.get('type')} » non converti : marqueur placé simplement.",
                               "Ajouter le placement dans catalogues/placements.json.")
            return None
        if entree.get("avertissement"):
            self.rapport.avertir(ou, entree["avertissement"])
        props, utilisees = lire_lyrx(self.conv, entree.get("proprietes", []), mp, ou)
        fins = entree.get("lyrx_fins")
        if fins:
            # Une énumération absente vaut sa première valeur (ArcGIS n'écrit pas les valeurs par défaut).
            valeur = mp.get(fins["cle"]) or next(iter(fins["facteurs"]))
            utilisees |= {fins["cle"], "controlPointPlacement"}
            facteur = fins["facteurs"].get(valeur)
            if facteur is None:
                self.rapport.avertir(ou + " > placement", fins["avertissement"].format(valeur=valeur))
            elif facteur and props.get(fins["base"]) and not props.get(fins["propriete"]):
                props[fins["propriete"]] = props[fins["base"]] * facteur
        self._non_utilisees(mp, utilisees, ou + " > placement")
        return Placement(type=entree["pivot"], props=props)

    def _non_utilisees(self, objet: dict, utilisees: set[str], ou: str) -> None:
        for cle, valeur in objet.items():
            if cle in utilisees or self.cat.ignore("lyrx", cle) or est_trivial(valeur):
                continue
            apercu = json.dumps(valeur, ensure_ascii=False)
            apercu = apercu if len(apercu) <= 40 else apercu[:37] + "…"
            self.rapport.info(ou, f"Propriété « {cle} » de {objet.get('type')} sans correspondance ({apercu}).",
                              "Si elle compte pour le rendu, l'ajouter dans le catalogue, ou l'ignorer dans catalogues/ignorer.json.")

    # -- étiquettes -----------------------------------------------------------------
    def lire_etiquette(self, lc: dict, geometrie: str, ou: str) -> ClasseEtiquette:
        props, _ = lire_lyrx(self.conv, self.cat.etiquettes["proprietes"], lc, ou, geometrie)
        filtre = None
        if lc.get("whereClause"):
            filtre = self.conv.expr.vers_qgis(lc["whereClause"], "SQL", ou + " > filtre")
        ts = chemins.lire(lc, "textSymbol.symbol") or {}
        if ts.get("haloSymbol") and len((ts["haloSymbol"].get("symbolLayers") or [])) > 1:
            self.rapport.info(ou, "Halo à plusieurs couches : seule la couleur d'aplat est reprise.")
        if ts.get("callout") or ts.get("shadowColor") and ts.get("shadowOffsetX"):
            self.rapport.info(ou, "Bulle ou ombre portée des étiquettes non convertie.")
        return ClasseEtiquette(nom=lc.get("name") or "", filtre=filtre, props=props)
