"""Lecture d'un fichier .qlr (ou .qml) de QGIS vers le modèle neutre."""
from __future__ import annotations

import copy
import re
# Contrôle de sécurité (B405) : éléments seulement ; la lecture passe par xml_sur.lire
import xml.etree.ElementTree as ET  # nosec B405
from typing import Optional

from . import sources, xml_sur
from .catalogue import Catalogue, conditions_remplies
from .modele import (Classe, ClasseEtiquette, Couche, CoucheSymbole, Document, Placement, Rendu,
                     Source, Symbole)
from .proprietes import Convertisseur, ProprietesXml, est_trivial, lire_qgis
from .rapport import Rapport

_GEOM = {"Point": "point", "Line": "ligne", "Polygon": "surface", "0": "point", "1": "ligne", "2": "surface"}


def proprietes_couche_xml(couche: ET.Element) -> dict[str, str]:
    """Propriétés d'une couche de symbole QGIS, au format récent (<Option>) ou ancien (<prop k= v=>)."""
    props: dict[str, str] = {}
    carte = couche.find("Option")
    if carte is not None:
        for o in carte.findall("Option"):
            if o.get("name") is not None:
                props[o.get("name")] = o.get("value", "")
    for p in couche.findall("prop"):
        props.setdefault(p.get("k"), p.get("v", ""))
    return props


class LecteurQlr:
    def __init__(self, catalogue: Catalogue, rapport: Rapport):
        self.cat = catalogue
        self.rapport = rapport
        self.conv = Convertisseur(catalogue, rapport)

    # -- document -------------------------------------------------------------
    def lire(self, donnees: bytes | str) -> Document:
        if isinstance(donnees, str):
            donnees = donnees.encode("utf-8")
        racine = xml_sur.lire(donnees)
        doc = Document(format_source="qlr")
        if racine.tag == "qgis":  # fichier de style .qml
            doc.format_source = "qml"
            doc.version_source = racine.get("version", "")
            couche = self.lire_couche(racine, visible=True)
            couche.nom = couche.nom if couche.nom != "couche" else "style"
            doc.couches.append(couche)
            return doc
        if racine.tag != "qlr":
            raise ValueError(f"Ce fichier n'est pas un fichier de couche QGIS (.qlr) : élément racine « {racine.tag} ».")
        visibles = {n.get("id"): n.get("checked", "Qt::Checked") != "Qt::Unchecked" for n in racine.iter("layer-tree-layer")}
        for ml in racine.iter("maplayer"):
            nom = ml.findtext("layername") or "?"
            if ml.get("type") != "vector":
                self.rapport.perte(f"Couche « {nom} »", f"Couche de type « {ml.get('type')} » non prise en charge (seules les couches vectorielles le sont).")
                continue
            doc.couches.append(self.lire_couche(ml, visibles.get(ml.findtext("id"), True)))
        if not doc.couches:
            self.rapport.perte("fichier", "Aucune couche vectorielle trouvée dans le fichier.")
        return doc

    # -- couche ---------------------------------------------------------------
    def lire_couche(self, ml: ET.Element, visible: bool) -> Couche:
        nom = ml.findtext("layername") or "couche"
        ou = f"Couche « {nom} »"
        couche = Couche(nom=nom, visible=visible)
        couche.geometrie = _GEOM.get(ml.get("geometry", ""), "inconnu")
        if ml.get("hasScaleBasedVisibilityFlag") == "1":
            mini = float(ml.get("minScale") or 0)
            maxi = float(ml.get("maxScale") or 0)
            couche.echelle_min = mini if 0 < mini < 1e8 else None
            couche.echelle_max = maxi if maxi > 0 else None
        try:
            couche.opacite = float(ml.findtext("layerOpacity") or 1)
        except ValueError:
            couche.opacite = 1.0
        if ml.find("datasource") is not None:
            couche.source, couche.filtre = self.lire_source(ml.findtext("datasource") or "", ml.findtext("provider") or "", ou)
        for a in ml.iter("alias"):
            if a.get("field") and a.get("name") and a.get("name") != a.get("field"):
                couche.alias[a.get("field")] = a.get("name")
        apercu = (ml.findtext("previewExpression") or "").strip()
        m = re.fullmatch(r'"((?:[^"]|"")+)"', apercu)
        if m:
            couche.champ_affichage = m.group(1).replace('""', '"')
        self.conv.echelle_reference = couche.echelle_de_reference()  # tailles en unités de carte (lot 2.1)
        r = ml.find("renderer-v2")
        if r is not None:
            couche.rendu = self.lire_rendu(r, ou + " > rendu")
        else:
            self.rapport.perte(ou, "Pas de rendu (symbologie) dans la couche.")
        genres = [s.genre for s in ([couche.rendu.symbole_defaut] + [k.symbole for k in couche.rendu.classes]) if s is not None] if couche.rendu else []
        if couche.geometrie == "inconnu" and genres:
            couche.geometrie = genres[0]
        elif genres and couche.geometrie not in genres:
            self.rapport.avertir(ou, f"La couche est déclarée « {couche.geometrie} » mais ses symboles sont de type « {genres[0]} » : "
                                 "le .lyrx produit suivra les symboles.")
        couche.etiquettes_actives = ml.get("labelsEnabled") == "1"
        lab = ml.find("labeling")
        if lab is not None:
            couche.etiquettes = self.lire_etiquettes(lab, couche.geometrie, ou + " > étiquettes")
        # QGIS écrit un réglage de diagramme même désactivé : seule une catégorie active compte.
        categories = ml.findall(".//DiagramCategory")
        if any(c.get("enabled", "1") != "0" for c in categories):
            self.rapport.perte(ou, "Diagrammes non convertis.")
        return couche

    def lire_source(self, datasource: str, fournisseur: str, ou: str) -> tuple[Source, Optional[str]]:
        return sources.lire_qgis(self.cat, self.rapport, datasource, fournisseur, ou)

    # -- rendu ----------------------------------------------------------------
    def lire_rendu(self, r: ET.Element, ou: str) -> Optional[Rendu]:
        t = r.get("type")
        pivot = self.cat.rendu_par("qgis", t)
        symboles = {s.get("name"): s for s in r.findall("symbols/symbol")}
        if t == "RuleRenderer":
            rendu = self._regles_simples(r, symboles, ou)
            if rendu is not None:
                return rendu
        if pivot is None:
            nom = self.cat.rendus["non_pris_en_charge"]["qgis"].get(t, t)
            premier = next(iter(r.iter("symbol")), None)
            self.rapport.perte(ou, f"Méthode de rendu QGIS « {nom} » non prise en charge" + (" : seul le premier symbole est repris." if premier is not None else "."))
            if premier is not None:
                return Rendu(type="unique", classes=[Classe(self.lire_symbole(premier, ou))])
            return None
        rendu = Rendu(type=pivot)
        if pivot == "unique":
            s = symboles.get("0")
            if s is None:
                s = next(iter(symboles.values()), None)
            rendu.classes.append(Classe(self.lire_symbole(s, ou + " > symbole") if s is not None else None))
            return rendu
        self._champs(rendu, r.get("attr") or "", ou)
        if pivot == "categories":
            for c in r.findall("categories/category"):
                sym = symboles.get(c.get("symbol"))
                symbole = self.lire_symbole(sym, f"{ou} > classe « {c.get('label', '')} »") if sym is not None else None
                vals = c.findall("val")
                brutes = [(v.get("value"), v.get("type")) for v in vals] if vals else [(c.get("value"), c.get("type"))]
                if not vals and (c.get("value") or "") == "" and c.get("type") != "NULL":
                    rendu.symbole_defaut = symbole
                    rendu.etiquette_defaut = c.get("label") or ""
                    continue
                valeurs = [self._valeur(v, t_, len(rendu.champs)) for v, t_ in brutes]
                if any("�" in (v or "") for v, _ in brutes):
                    # Lot 2 : shapefile sans .cpg lu par QGIS avec le mauvais encodage ; ArcGIS lit le bon
                    # caractère, et la classe ne correspond alors à aucune entité.
                    self.rapport.avertir(f"{ou} > classe « {c.get('label', '')} »",
                                         "La valeur contient un caractère illisible (�) : le fichier de données a sans doute "
                                         "été lu par QGIS avec un mauvais encodage (shapefile sans fichier .cpg). ArcGIS "
                                         "lira le bon caractère et cette classe ne correspondra à aucune entité.",
                                         "Corriger la valeur, ou ajouter un fichier .cpg au shapefile et refaire la classe dans QGIS.")
                rendu.classes.append(Classe(symbole=symbole, etiquette=c.get("label") or "", valeurs=valeurs,
                                            visible=c.get("render", "true") != "false"))
            nulle = next((k for k in rendu.classes if k.valeurs == [[None]] and k.visible), None)
            if rendu.symbole_defaut is None and nulle is not None and len(rendu.champs) == 1:
                # QGIS dessine avec la catégorie NULL aussi toutes les valeurs non listées (lot 2.1, vérifié
                # dans QGIS 3.44) ; ArcGIS ne le fait qu'avec son symbole « autres valeurs ».
                rendu.symbole_defaut = copy.deepcopy(nulle.symbole)
                rendu.etiquette_defaut = nulle.etiquette
                self.rapport.info(ou, f"La catégorie NULL « {nulle.etiquette} » sert aussi, dans QGIS, à toutes les valeurs "
                                      "non listées : ArcGIS reçoit le même symbole en « autres valeurs ».")
        else:
            for x in r.findall("ranges/range"):
                sym = symboles.get(x.get("symbol"))
                rendu.classes.append(Classe(
                    symbole=self.lire_symbole(sym, f"{ou} > classe « {x.get('label', '')} »") if sym is not None else None,
                    etiquette=x.get("label") or "", min=float(x.get("lower")), max=float(x.get("upper")),
                    visible=x.get("render", "true") != "false"))
            cm = r.find("classificationMethod")
            rendu.methode = self.conv.liste_vers_pivot("methodes_classification", "qgis", cm.get("id") if cm is not None else None, ou, "manuelle")
            if r.find("sizescale") is not None and r.find("sizescale").get("scalemethod"):
                pass
        if r.find("rotation") is not None and r.find("rotation").get("field"):
            self.rapport.perte(ou, "Rotation selon un champ non convertie.")
        return rendu

    def _regles_simples(self, r: ET.Element, symboles: dict, ou: str) -> Optional[Rendu]:
        """Ensemble de règles « une valeur par règle » sur un même champ → valeurs uniques.

        Accepté : un seul niveau de règles, chacune avec un symbole et un filtre « champ = valeur »,
        « champ IN (valeurs) » ou « ELSE ». Sinon : None (le rendu reste « non pris en charge »)."""
        motifs = self.cat.rendus.get("regles_qgis_simples", {})
        racine = r.find("rules")
        regles = racine.findall("rule") if racine is not None else []
        if not regles or not motifs:
            return None
        champ_commun: Optional[str] = None
        classes: list[Classe] = []
        defaut = None
        etiquette_defaut = ""
        echelles = False
        for regle in regles:
            if regle.find("rule") is not None or regle.get("symbol") is None:
                return None
            filtre = (regle.get("filter") or "").strip()
            sym = symboles.get(regle.get("symbol"))
            libelle = regle.get("label") or ""
            echelles = echelles or bool(regle.get("scalemaxdenom") or regle.get("scalemindenom"))
            if filtre.upper() == "ELSE" or regle.get("else") == "1":
                defaut = self.lire_symbole(sym, f"{ou} > autres valeurs") if sym is not None else None
                etiquette_defaut = libelle
                continue
            champ, valeurs = None, None
            m = re.fullmatch(motifs["egal"], filtre, re.S | re.I)
            if m:
                champ, valeurs = m.group(1) or m.group(2), [m.group(3)]
            else:
                m = re.fullmatch(motifs["dans"], filtre, re.S | re.I)
                if m:
                    champ = m.group(1) or m.group(2)
                    valeurs = [v.strip() for v in re.split(r",(?=(?:[^']*'[^']*')*[^']*$)", m.group(3))]
            if champ is None or (champ_commun is not None and champ != champ_commun):
                return None
            champ_commun = champ
            textes = []
            for v in valeurs:
                if v.startswith("'") and v.endswith("'") and len(v) >= 2:
                    textes.append(v[1:-1].replace("''", "'"))
                elif re.fullmatch(r"-?\d+(?:\.\d+)?", v):
                    textes.append(v)
                else:
                    return None
            symbole = self.lire_symbole(sym, f"{ou} > classe « {libelle} »") if sym is not None else None
            classes.append(Classe(symbole=symbole, etiquette=libelle, valeurs=[[v] for v in textes],
                                  visible=regle.get("checkstate", "1") != "0"))
        if not classes:
            return None
        self.rapport.info(ou, f"Ensemble de règles QGIS (une valeur par règle sur « {champ_commun} ») converti en valeurs uniques.")
        if echelles:
            self.rapport.avertir(ou, "Échelles de visibilité propres à certaines règles : non reprises (ArcGIS les règle par couche).")
        return Rendu(type="categories", champs=[champ_commun], classes=classes,
                     symbole_defaut=defaut, etiquette_defaut=etiquette_defaut)

    def _champs(self, rendu: Rendu, attr: str, ou: str) -> None:
        sep = self.cat.rendus.get("separateur_valeurs", ", ")
        m = re.fullmatch(r"concat\((.*)\)", attr.strip(), re.S)
        if m:
            morceaux = [x.strip() for x in re.split(r",(?=(?:[^']*'[^']*')*[^']*$)", m.group(1))]
            champs = [x for x in morceaux if x.startswith('"')]
            seps = [x for x in morceaux if x.startswith("'")]
            if champs and len(champs) == len(seps) + 1 and all(s == "'" + sep.replace("'", "''") + "'" for s in seps):
                rendu.champs = [c[1:-1].replace('""', '"') for c in champs]
                return
        m = re.fullmatch(r'"((?:[^"]|"")+)"', attr.strip())
        if m:
            rendu.champs = [m.group(1).replace('""', '"')]
        elif re.fullmatch(r"[^\s()\"'|+*/-]+", attr.strip()):
            rendu.champs = [attr.strip()]
        else:
            rendu.expression = attr
            self.rapport.info(ou, f"Classement sur une expression QGIS : {attr!r}.")

    def _valeur(self, valeur: Optional[str], type_: Optional[str], nb_champs: int) -> list:
        if type_ == "NULL":
            return [None]
        if nb_champs > 1 and valeur is not None:
            # concat() de QGIS écrit une valeur vide pour un champ NULL : on la relit comme « pas de valeur ».
            return [v if v != "" else None for v in valeur.split(self.cat.rendus.get("separateur_valeurs", ", "))]
        return [valeur]

    # -- symboles -------------------------------------------------------------
    def lire_symbole(self, s: Optional[ET.Element], ou: str) -> Optional[Symbole]:
        if s is None:
            return None
        genre = self.cat.genre_par_qgis(s.get("type", ""))
        if genre is None:
            self.rapport.perte(ou, f"Type de symbole QGIS « {s.get('type')} » non pris en charge.")
            return None
        symbole = Symbole(genre=genre, opacite=float(s.get("alpha") or 1))
        avant, self.conv.genre_symbole = self.conv.genre_symbole, genre
        try:
            return self._lire_couches(s, symbole, ou)
        finally:
            self.conv.genre_symbole = avant

    def _lire_couches(self, s: ET.Element, symbole: Symbole, ou: str) -> Symbole:
        genre = symbole.genre
        enveloppes = self.cat.classes_enveloppes_qgis()
        couches_xml = s.findall("layer")
        vide = self.cat.genre(genre).get("qgis_vide")
        if vide and len(couches_xml) == 1 and couches_xml[0].get("class") == vide["classe"]:
            props = proprietes_couche_xml(couches_xml[0])
            if props == vide["props"]:  # exactement la couche écrite par ecriture_qlr, rien d'autre
                return symbole  # la couche invisible écrite pour un symbole sans couche (voir ecriture_qlr)
        for i, couche in enumerate(couches_xml):
            ou_c = f"{ou} > couche {i + 1}"
            classe = couche.get("class", "")
            props = self._noms_actuels(classe, proprietes_couche_xml(couche))
            actif = couche.get("enabled", "1") != "0"
            placement_entree = self.cat.placement_par_qgis(classe, props) if classe in enveloppes else None
            if placement_entree is not None:
                pprops, utilisees = lire_qgis(self.conv, placement_entree.get("proprietes", []), props.get, ou_c)
                self._non_utilisees(classe, props, utilisees, ou_c)
                placement = Placement(type=placement_entree["pivot"], props=pprops)
                sous = self.lire_symbole(couche.find("symbol"), ou_c + " > marqueur")
                for cs in (sous.couches if sous else []):
                    cs.placement = placement
                    cs.actif = cs.actif and actif
                    symbole.couches.append(cs)
                continue
            virtuelles = [(classe, props, couche.find("symbol"))]
            for d in self.cat.decompositions:
                if d["classe"] == classe and conditions_remplies(d.get("si"), props.get):
                    renomme = {d["renommer"].get(k, k): v for k, v in props.items() if k in d["renommer"]}
                    renomme.update(d.get("fixe", {}))
                    virtuelles.append((d["classe_cible"], renomme, None))
            for classe_v, props_v, sous_v in virtuelles:
                cs = self.lire_couche_symbole(classe_v, props_v, sous_v, ou_c)
                if cs is not None:
                    cs.actif = actif
                    symbole.couches.append(cs)
        return symbole

    def _noms_actuels(self, classe: str, props: dict) -> dict:
        """Renomme les anciennes options QGIS (« outline_color » d'un trait…) selon
        symboles.json « anciens_noms_qgis ». QGIS ne lit l'ancien nom que si l'actuel manque."""
        anciens = self.cat.d["symboles"].get("anciens_noms_qgis", {}).get(classe)
        if not anciens:
            return props
        props = dict(props)
        for actuel, noms in anciens.items():
            for nom in noms:
                if nom in props:
                    valeur = props.pop(nom)
                    props.setdefault(actuel, valeur)
        return props

    def lire_couche_symbole(self, classe: str, props: dict, sous: Optional[ET.Element], ou: str) -> Optional[CoucheSymbole]:
        entree = self.cat.couche_par_qgis(classe, props)
        if entree is None:
            self.rapport.perte(ou, f"Couche de symbole QGIS « {classe} » non convertie.",
                               "Ajouter la correspondance dans catalogues/symboles.json.")
            return None
        if entree.get("pivot") is None:
            return None
        message = entree.get("avertissement_qgis") or (entree.get("avertissement") if entree.get("sens") == "lecture_qgis" else None)
        if message:
            self.rapport.avertir(ou, message.format(**props) if "{" in message else message)
        valeurs, utilisees = lire_qgis(self.conv, entree.get("proprietes", []), props.get, ou)
        utilisees |= set(entree["qgis"].get("fixe", {}))
        self._non_utilisees(classe, props, utilisees, ou)
        cs = CoucheSymbole(type=entree["pivot"], props=valeurs)
        if entree.get("sous_symbole"):
            cs.sous_symbole = self.lire_symbole(sous, ou + " > sous-symbole")
        return cs

    def _non_utilisees(self, classe: str, props: dict, utilisees: set[str], ou: str) -> None:
        for cle, valeur in props.items():
            if cle in utilisees or self.cat.ignore("qgis", cle, valeur, classe) or est_trivial(valeur):
                continue
            if self.cat.visible("qgis", cle, classe):
                self.rapport.avertir(ou, f"Propriété QGIS « {cle} » de {classe} ({valeur[:40]}) non convertie : le dessin "
                                         "dans ArcGIS Pro sera différent.", "Voir docs/limites.md.")
                continue
            self.rapport.info(ou, f"Propriété QGIS « {cle} » de {classe} sans correspondance ({valeur[:40]}).",
                              "Si elle compte pour le rendu, l'ajouter dans le catalogue, ou l'ignorer dans catalogues/ignorer.json.")

    # -- étiquettes -----------------------------------------------------------------
    def lire_etiquettes(self, lab: ET.Element, geometrie: str, ou: str) -> list[ClasseEtiquette]:
        t = lab.get("type")
        if t == "simple":
            reglage = lab.find("settings")
            return [self._classe_etiquette(reglage, "Classe 1", None, True, geometrie, ou)] if reglage is not None else []
        if t == "rule-based":
            classes: list[ClasseEtiquette] = []
            racine = lab.find("rules")
            if racine is not None:
                self._regles(racine, None, True, classes, geometrie, ou)
            return classes
        self.rapport.perte(ou, f"Type d'étiquetage QGIS « {t} » non pris en charge.")
        return []

    def _regles(self, parent: ET.Element, filtre_parent: Optional[str], actif_parent: bool,
                classes: list, geometrie: str, ou: str) -> None:
        for regle in parent.findall("rule"):
            filtre = (regle.get("filter") or "").strip() or None
            if regle.get("filter") == "ELSE":
                self.rapport.avertir(ou, "Règle d'étiquettes « sinon » (ELSE) convertie sans filtre.")
                filtre = None
            if filtre_parent and filtre:
                filtre = f"({filtre_parent}) AND ({filtre})"
            else:
                filtre = filtre or filtre_parent
            actif = actif_parent and regle.get("active", "1") != "0"
            if regle.get("scalemindenom") or regle.get("scalemaxdenom"):
                self.rapport.avertir(ou, "Échelles fixées sur une règle d'étiquettes : seules les échelles du réglage sont reprises.")
            reglage = regle.find("settings")
            if reglage is not None:
                classes.append(self._classe_etiquette(reglage, regle.get("description") or f"Classe {len(classes) + 1}",
                                                      filtre, actif, geometrie, ou))
            self._regles(regle, filtre, actif, classes, geometrie, ou)

    def _classe_etiquette(self, reglage: ET.Element, nom: str, filtre: Optional[str], actif: bool,
                          geometrie: str, ou: str) -> ClasseEtiquette:
        props, _ = lire_qgis(self.conv, self.cat.etiquettes["proprietes"], ProprietesXml(reglage).get, f"{ou} « {nom} »", geometrie)
        if not actif:
            props["visible"] = False
        if reglage.find("background") is not None and reglage.find("background").get("shapeDraw") == "1":
            self.rapport.perte(f"{ou} « {nom} »", "Fond (cadre) des étiquettes non converti.")
        return ClasseEtiquette(nom=nom, filtre=filtre, props=props)
