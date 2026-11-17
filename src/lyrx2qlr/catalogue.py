"""Chargement, fusion et vérification des catalogues de correspondances.

Les catalogues livrés avec le paquet sont dans le dossier « catalogues/ ».
On peut leur ajouter un dossier de catalogues complémentaires (mêmes noms de
fichiers, mêmes structures) : leurs entrées passent AVANT celles du paquet, ce
qui permet de corriger ou compléter une correspondance sans toucher au code.
"""
from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path
from typing import Any, Iterable, Optional

DOSSIER_CATALOGUES = Path(__file__).parent / "catalogues"
DOSSIER_MODELES = Path(__file__).parent / "modeles"

FICHIERS = ("symboles", "placements", "listes", "etiquettes", "formes", "polices", "unites",
            "couleurs", "sources", "expressions", "formats", "rendus", "ignorer")

TYPES_PROPRIETES = {"couleur", "longueur", "longueurs", "angle", "nombre", "entier", "texte", "booleen",
                    "liste", "caractere", "image", "forme", "expression", "tirets_qt", "decalage_impair"}


class ErreurCatalogue(Exception):
    pass


def _lire_json(chemin: Path) -> Any:
    try:
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ErreurCatalogue(f"Catalogue « {chemin} » mal écrit, ligne {e.lineno}, colonne {e.colno} : {e.msg}.") from e


def _fusionner(base: Any, ajout: Any) -> Any:
    """Les listes de l'ajout passent devant ; les dictionnaires sont fusionnés clé par clé."""
    if isinstance(base, dict) and isinstance(ajout, dict):
        resultat = dict(base)
        for cle, valeur in ajout.items():
            resultat[cle] = _fusionner(base[cle], valeur) if cle in base else valeur
        return resultat
    if isinstance(base, list) and isinstance(ajout, list):
        return list(ajout) + list(base)
    return ajout


def _condition_valeur(attendu: Any, reel: Any) -> bool:
    """attendu : valeur exacte, liste de valeurs possibles, « !valeur » (différent de), « !null » (présent) ou « >N » (nombre plus grand que N)."""
    if isinstance(attendu, list):
        return any(_condition_valeur(a, reel) for a in attendu)
    if attendu is None:
        return reel is None or reel == ""
    if isinstance(attendu, str) and attendu.startswith(">"):
        try:
            return reel is not None and float(reel) > float(attendu[1:])
        except (TypeError, ValueError):
            return False
    if isinstance(attendu, str) and attendu.startswith("!"):
        contraire = attendu[1:]
        if contraire == "null":
            return reel is not None
        return reel is None or str(reel) != contraire
    if isinstance(attendu, bool):
        return reel is attendu or str(reel).lower() == str(attendu).lower()
    return reel is not None and str(reel) == str(attendu)


def conditions_remplies(conditions: Optional[dict], lecteur) -> bool:
    """« lecteur(clé) » renvoie la valeur réelle de la clé dans l'objet examiné."""
    if not conditions:
        return True
    return all(_condition_valeur(attendu, lecteur(cle)) for cle, attendu in conditions.items())


class Catalogue:
    """Accès aux catalogues. Une instance = un jeu de catalogues fusionnés et vérifiés."""

    def __init__(self, donnees: dict[str, Any]):
        self.d = donnees
        self._index()

    # -- chargement --------------------------------------------------------
    @classmethod
    def charger(cls, complements: Optional[Iterable[str | Path]] = None) -> "Catalogue":
        donnees = {nom: _lire_json(DOSSIER_CATALOGUES / f"{nom}.json") for nom in FICHIERS}
        for dossier in complements or []:
            dossier = Path(dossier)
            for nom in FICHIERS:
                chemin = dossier / f"{nom}.json"
                if chemin.exists():
                    donnees[nom] = _fusionner(donnees[nom], _lire_json(chemin))
        catalogue = cls(donnees)
        erreurs = catalogue.verifier()
        if erreurs:
            raise ErreurCatalogue("Catalogues invalides :\n- " + "\n- ".join(erreurs))
        return catalogue

    def _index(self) -> None:
        self.genres = self.d["symboles"]["genres"]
        self.couches = self.d["symboles"]["couches"]
        self.decompositions = self.d["symboles"].get("decompositions_qgis", {}).get("liste", [])
        self.placements = self.d["placements"]["placements"]
        self.listes = {k: v for k, v in self.d["listes"].items() if not k.startswith("_")}
        self.etiquettes = self.d["etiquettes"]
        self.formes = self.d["formes"]
        self.polices = self.d["polices"]
        self.unites = self.d["unites"]
        self.couleurs = self.d["couleurs"]
        self.sources = self.d["sources"]
        self.expressions = self.d["expressions"]
        self.formats = self.d["formats"]
        self.rendus = self.d["rendus"]
        self._ignorer = {k: v for k, v in self.d["ignorer"].items() if not k.startswith("_")}

    # -- vérification ------------------------------------------------------
    def verifier(self) -> list[str]:
        """Contrôle la cohérence des catalogues ; renvoie la liste des problèmes (vide si tout va bien)."""
        erreurs: list[str] = []

        def verifier_proprietes(ou: str, proprietes: list) -> None:
            for p in proprietes:
                if "nom" not in p or "type" not in p:
                    erreurs.append(f"{ou} : propriété sans « nom » ou sans « type » : {p}")
                    continue
                if p["type"] not in TYPES_PROPRIETES:
                    erreurs.append(f"{ou}.{p['nom']} : type inconnu « {p['type']} » (types possibles : {', '.join(sorted(TYPES_PROPRIETES))})")
                if p["type"] in ("liste", "tirets_qt") and p.get("liste") not in self.listes:
                    erreurs.append(f"{ou}.{p['nom']} : liste « {p.get('liste')} » absente de listes.json")
                if not p.get("lyrx") and not p.get("qgis"):
                    erreurs.append(f"{ou}.{p['nom']} : ni chemin « lyrx » ni clé « qgis »")

        genres = {g["pivot"] for g in self.genres}
        for i, c in enumerate(self.couches):
            ou = f"symboles.couches[{i}] ({c.get('pivot')})"
            if "lyrx" not in c and "qgis" not in c:
                erreurs.append(f"{ou} : ni « lyrx » ni « qgis »")
            if c.get("sens") not in (None, "lecture_qgis", "lecture_lyrx"):
                erreurs.append(f"{ou} : « sens » doit être lecture_qgis ou lecture_lyrx")
            if c.get("sous_symbole") and c["sous_symbole"].get("genre") not in genres:
                erreurs.append(f"{ou} : genre de sous-symbole inconnu")
            verifier_proprietes(ou, c.get("proprietes", []))
        for i, p in enumerate(self.placements):
            verifier_proprietes(f"placements[{i}] ({p.get('pivot')})", p.get("proprietes", []))
        verifier_proprietes("etiquettes", self.etiquettes.get("proprietes", []))
        for nom, liste in self.listes.items():
            if "valeurs" not in liste:
                erreurs.append(f"listes.{nom} : clé « valeurs » manquante")
            if liste.get("inconnu", "signaler") not in ("garder", "signaler"):
                erreurs.append(f"listes.{nom} : « inconnu » doit valoir garder ou signaler")
        noms_formes = {f["qgis"] for f in self.formes["formes"]}
        for s in self.polices.get("substitutions", []):
            if s.get("forme") not in noms_formes:
                erreurs.append(f"polices : forme « {s.get('forme')} » absente de formes.json")
            if s.get("rendu", "plein") not in ("plein", "creux", "trait"):
                erreurs.append(f"polices : rendu « {s.get('rendu')} » inconnu (plein, creux ou trait)")
            if s.get("rendu", "plein") != "plein" and not s.get("epaisseur"):
                erreurs.append(f"polices : caractère {s.get('caractere')} de « {s.get('police')} » : « epaisseur » manquante")
        formules = {"rgb", "hsv", "hsl", "cmyk", "gris", "lab"}
        for m in self.couleurs["modeles"]:
            if m.get("formule") not in formules:
                erreurs.append(f"couleurs : formule inconnue « {m.get('formule')} »")
        if self.unites.get("qgis_sortie") not in self.unites["vers_points"]:
            erreurs.append("unites : « qgis_sortie » absente de « vers_points »")
        for moteur, regles in self.expressions["vers_qgis"].items():
            for r in regles.get("regles", []):
                try:
                    re.compile(r["motif"])
                except re.error as e:
                    erreurs.append(f"expressions.vers_qgis.{moteur} : motif invalide {r['motif']!r} ({e})")
        return erreurs

    # -- recherches --------------------------------------------------------
    def genre_par_lyrx(self, type_cim: str) -> Optional[str]:
        return next((g["pivot"] for g in self.genres if g["lyrx"] == type_cim), None)

    def genre_par_qgis(self, type_qgis: str) -> Optional[str]:
        return next((g["pivot"] for g in self.genres if g["qgis"] == type_qgis), None)

    def genre(self, pivot: str) -> dict:
        return next(g for g in self.genres if g["pivot"] == pivot)

    def couche_par_lyrx(self, objet: dict) -> Optional[dict]:
        from .chemins import lire
        for c in self.couches:
            if c.get("sens") == "lecture_qgis" or "lyrx" not in c:
                continue
            if c["lyrx"]["type"] == objet.get("type") and conditions_remplies(c["lyrx"].get("si"), lambda k: lire(objet, k)):
                return c
        return None

    def couche_par_qgis(self, classe: str, props: dict) -> Optional[dict]:
        for c in self.couches:
            if c.get("sens") == "lecture_lyrx" or "qgis" not in c:
                continue
            q = c["qgis"]
            if q["classe"] != classe:
                continue
            if conditions_remplies(q.get("si"), props.get) and (
                    not q.get("si_ou") or any(conditions_remplies(s, props.get) for s in q["si_ou"])):
                return c
        return None

    def couche_pour_ecriture(self, pivot: str, format_: str) -> Optional[dict]:
        interdit = "lecture_qgis" if format_ == "lyrx" else "lecture_lyrx"
        return next((c for c in self.couches if c.get("pivot") == pivot and c.get("sens") != interdit and format_ in c), None)

    def placement_par_lyrx(self, objet: dict) -> Optional[dict]:
        for p in self.placements:
            if p["lyrx"]["type"] == objet.get("type") and conditions_remplies(p["lyrx"].get("si"), objet.get):
                return p
        return None

    def placement_par_qgis(self, classe: str, props: dict) -> Optional[dict]:
        for p in self.placements:
            q = p["qgis"]
            if q["classe"] != classe:
                continue
            if conditions_remplies(q.get("si"), props.get) and (
                    not q.get("si_ou") or any(conditions_remplies(s, props.get) for s in q["si_ou"])):
                return p
        return None

    def placement(self, pivot: str) -> Optional[dict]:
        return next((p for p in self.placements if p["pivot"] == pivot), None)

    def classes_enveloppes_qgis(self) -> set[str]:
        return {p["qgis"]["classe"] for p in self.placements}

    def liste(self, nom: str) -> dict:
        return self.listes[nom]

    def rendu_par(self, format_: str, type_: str) -> Optional[str]:
        return next((r["pivot"] for r in self.rendus["rendus"] if r[format_] == type_), None)

    def rendu(self, pivot: str) -> dict:
        return next(r for r in self.rendus["rendus"] if r["pivot"] == pivot)

    @staticmethod
    def _correspond(cle: str, classe: Optional[str], motifs: list) -> bool:
        """Un motif « clé » vaut pour toutes les classes ; « Classe.clé » pour une seule."""
        noms = [cle] + ([f"{classe}.{cle}"] if classe else [])
        return any(fnmatch.fnmatchcase(n, m) for m in motifs for n in noms if ("." in m) == (n != cle))

    def ignore(self, format_: str, cle: str, valeur: Any = None, classe: Optional[str] = None) -> bool:
        """Propriété sans intérêt : listée dans ignorer.json, ou égale à sa valeur neutre (« <format>_neutres »)."""
        if valeur is not None and str(valeur) in self._ignorer.get(f"{format_}_neutres", {}).get(cle, []):
            return True
        return self._correspond(cle, classe, self._ignorer.get(format_, []))

    def visible(self, format_: str, cle: str, classe: Optional[str] = None) -> bool:
        """Propriété non convertie qui change le dessin (« <format>_visibles ») : signalée « à vérifier »."""
        return self._correspond(cle, classe, self._ignorer.get(f"{format_}_visibles", []))

    def modele(self, nom: str) -> Any:
        """Modèle de fichier (gabarit) livré dans le dossier « modeles/ »."""
        return _lire_json(DOSSIER_MODELES / nom)


_DEFAUT: Optional[Catalogue] = None


def catalogue_defaut() -> Catalogue:
    global _DEFAUT
    if _DEFAUT is None:
        _DEFAUT = Catalogue.charger()
    return _DEFAUT
