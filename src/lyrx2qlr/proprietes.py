"""Lecture et écriture des propriétés décrites dans les catalogues.

Une « propriété » de catalogue dit où trouver une valeur dans chaque format et
de quel type elle est. Ce module sait, pour chaque type, passer de la valeur
d'un format à la valeur neutre, et inversement. C'est le seul endroit où vivent
les formules (couleurs, unités, angles…) : les catalogues ne font que les citer.
"""
from __future__ import annotations

import colorsys
import math
import re
from typing import Any, Callable, Optional

from . import chemins, images
from .catalogue import Catalogue, conditions_remplies
from .expressions import Traducteur
from .rapport import Rapport

Lecteur = Callable[[str], Any]


def _arrondi(x: float, decimales: int) -> float:
    r = round(float(x), decimales)
    return 0.0 if r == 0 else r


def _texte_nombre(x: float, decimales: int = 6) -> str:
    r = _arrondi(x, decimales)
    if r == int(r):
        return str(int(r))
    return f"{r:.{decimales}f}".rstrip("0").rstrip(".")


def est_trivial(valeur: Any) -> bool:
    """Valeur sans effet visible : 0, faux, vide… (pas la peine de la signaler)."""
    if valeur in (None, "", 0, 0.0, False, [], {}):
        return True
    if isinstance(valeur, str) and valeur.strip() in ("0", "0,0", "false", "3x:0,0,0,0,0,0"):
        return True
    return False


class Convertisseur:
    def __init__(self, catalogue: Catalogue, rapport: Rapport):
        self.cat = catalogue
        self.rapport = rapport
        self.expr = Traducteur(catalogue, rapport)
        self.decimales = catalogue.unites.get("decimales", 4)
        self.echelle_reference: Optional[float] = None  # couche en cours de lecture (tailles en unités de carte)
        self.genre_symbole: Optional[str] = None  # symbole en cours de lecture ou d'écriture (« qgis_facteur_selon_genre »)

    # == couleurs ============================================================
    def couleur_lyrx_vers_pivot(self, c: Any, ou: str) -> Optional[list[int]]:
        if not isinstance(c, dict):
            return None
        modele = next((m["formule"] for m in self.cat.couleurs["modeles"] if m["lyrx"] == c.get("type")), None)
        v = c.get("values") or []
        amax = self.cat.couleurs.get("alpha_lyrx_max", 100)
        if modele is None:
            self.rapport.avertir(ou, f"Modèle de couleur « {c.get('type')} » inconnu : gris moyen utilisé.",
                                 "Ajouter le modèle dans catalogues/couleurs.json (et sa formule dans le code s'il est nouveau).")
            return [128, 128, 128, 255]
        n = {"rgb": 3, "hsv": 3, "hsl": 3, "cmyk": 4, "gris": 1, "lab": 3}[modele]
        alpha = v[n] if len(v) > n else amax
        a = round(float(alpha) / amax * 255)
        if modele == "rgb":
            r, g, b = (float(x) for x in v[:3])
        elif modele == "hsv":
            r, g, b = (x * 255 for x in colorsys.hsv_to_rgb(float(v[0]) / 360, float(v[1]) / 100, float(v[2]) / 100))
        elif modele == "hsl":
            r, g, b = (x * 255 for x in colorsys.hls_to_rgb(float(v[0]) / 360, float(v[2]) / 100, float(v[1]) / 100))
        elif modele == "cmyk":
            cc, m, y, k = (float(x) / 100 for x in v[:4])
            r, g, b = (255 * (1 - cc) * (1 - k), 255 * (1 - m) * (1 - k), 255 * (1 - y) * (1 - k))
        elif modele == "gris":
            r = g = b = float(v[0])
        else:  # lab (D65)
            r, g, b = _lab_vers_rgb(float(v[0]), float(v[1]), float(v[2]))
        return [max(0, min(255, round(x))) for x in (r, g, b)] + [max(0, min(255, a))]

    def couleur_pivot_vers_lyrx(self, c: list[int]) -> dict:
        amax = self.cat.couleurs.get("alpha_lyrx_max", 100)
        a = _arrondi(c[3] / 255 * amax, 2)
        a = int(a) if a == int(a) else a
        return {"type": self.cat.couleurs.get("ecriture_lyrx", "CIMRGBColor"), "values": [int(c[0]), int(c[1]), int(c[2]), a]}

    @staticmethod
    def couleur_qgis_vers_pivot(texte: Optional[str]) -> Optional[list[int]]:
        if texte is None or texte == "":
            return None
        texte = texte.strip()
        if texte.startswith("#"):
            h = texte[1:]
            if len(h) in (6, 8):
                vals = [int(h[i:i + 2], 16) for i in range(0, len(h), 2)]
                if len(vals) == 4:  # #AARRGGBB (Qt)
                    vals = vals[1:] + vals[:1]
                return vals + [255] * (4 - len(vals))
            return None
        morceaux = texte.split(",")
        try:
            vals = [int(float(x)) for x in morceaux[:4] if not x.startswith("rgb:")]
        except ValueError:
            return None
        if len(vals) < 3:
            return None
        vals = [max(0, min(255, v)) for v in vals]
        return vals[:3] + [vals[3] if len(vals) > 3 else 255]

    @staticmethod
    def couleur_pivot_vers_qgis(c: list[int]) -> str:
        return ",".join(str(int(x)) for x in c[:4])

    # == longueurs ===========================================================
    def vers_points(self, valeur: float, unite: Optional[str], ou: str) -> float:
        facteurs = self.cat.unites["vers_points"]
        unite = unite or self.cat.unites.get("qgis_defaut_si_absente", "MM")
        if unite not in facteurs:
            self.rapport.avertir(ou, f"Unité QGIS « {unite} » inconnue : valeur prise en millimètres.",
                                 "Ajouter l'unité dans catalogues/unites.json.")
            unite = "MM"
        f = facteurs[unite]
        if f is None and self.echelle_reference:
            e = self.echelle_reference
            self.rapport.avertir(ou, f"Taille exprimée en unités de carte ({unite}) : convertie en points pour l'échelle "
                                 f"1:{e:,.0f} (milieu de la plage de visibilité de la couche, en supposant des mètres). "
                                 "À cette échelle, ArcGIS Pro dessine la même taille ; plus zoomé ou plus dézoomé, le symbole "
                                 "ne grandit ni ne rapetisse avec la carte.".replace(",", " "),
                                 "Pour que les symboles suivent le zoom, régler une échelle de référence sur la carte ArcGIS Pro.")
            return float(valeur) * self.cat.unites["metre_carte_vers_points"] / e
        if f is None:
            self.rapport.avertir(ou, f"Taille exprimée en unités de carte ({unite}) : ArcGIS Pro ne connaît pas cette unité pour les symboles ; la valeur est gardée telle quelle, en points.")
            return float(valeur)
        return float(valeur) * f

    def depuis_points(self, pt: float) -> tuple[str, str]:
        unite = self.cat.unites["qgis_sortie"]
        return _texte_nombre(pt / self.cat.unites["vers_points"][unite], self.decimales), unite

    # == listes ==============================================================
    def liste_vers_pivot(self, nom: str, cote: str, brut: Any, ou: str, defaut: Any = None,
                         lecteur: Optional[Callable[[str], Any]] = None) -> Any:
        """Plusieurs lignes peuvent avoir la même valeur : on préfère alors celle dont les options
        complémentaires (« <côté>_extra ») correspondent à ce qui est lu."""
        table = self.cat.liste(nom)
        candidates = [ligne for ligne in table["valeurs"]
                      if cote in ligne and (ligne[cote] == brut or (brut is not None and ligne[cote] is not None and str(ligne[cote]) == str(brut)))]
        if candidates:
            if lecteur is not None:
                for ligne in candidates:
                    extra = ligne.get(f"{cote}_extra")
                    if extra and all(str(lecteur(k)) == str(v) for k, v in extra.items()):
                        return ligne["pivot"]
            return candidates[0]["pivot"]
        if brut is None or brut == "":
            return defaut
        if table.get("inconnu", "signaler") == "garder":
            return brut
        self.rapport.avertir(ou, f"Valeur « {brut} » absente de la liste « {nom} » : valeur par défaut utilisée.",
                             f"Ajouter la valeur dans catalogues/listes.json, liste « {nom} ».")
        return defaut

    def liste_depuis_pivot(self, nom: str, cote: str, valeur: Any, ou: str) -> tuple[Any, dict]:
        table = self.cat.liste(nom)
        for ligne in table["valeurs"]:
            if ligne.get("pivot") == valeur and ligne.get(cote) is None and ligne.get(f"avertissement_{cote}"):
                self.rapport.avertir(ou, ligne[f"avertissement_{cote}"])  # valeur sans équivalent, annoncée
                return None, {}
            if ligne.get("pivot") == valeur and cote in ligne and ligne[cote] is not None:
                if ligne.get(f"avertissement_{cote}"):
                    self.rapport.avertir(ou, ligne[f"avertissement_{cote}"])
                return ligne[cote], ligne.get(f"{cote}_extra", {})
        if table.get("inconnu", "signaler") == "garder":
            return valeur, {}
        self.rapport.avertir(ou, f"Valeur « {valeur} » sans équivalent {cote.upper()} dans la liste « {nom} ».",
                             f"Ajouter la valeur dans catalogues/listes.json, liste « {nom} ».")
        return None, {}

    # == formes de marqueurs ================================================
    def forme_depuis_graphique(self, graphique: Any, ou: str) -> Optional[str]:
        if not isinstance(graphique, dict):
            return None
        sig = _signature(graphique.get("geometry") or {})
        if sig is None:
            self.rapport.avertir(ou, "Géométrie de marqueur illisible : cercle utilisé.")
            return self.cat.formes.get("defaut", "circle")
        for f in self.cat.formes["formes"]:
            attendu = f.get("signature")
            if f.get("lecture_seule") == "qgis" or not attendu:
                continue
            if all(sig.get(k) == v for k, v in attendu.items()):
                return f["qgis"]
        self.rapport.avertir(ou, f"Forme de marqueur non reconnue ({sig}) : cercle utilisé.",
                             "Ajouter la forme et sa signature dans catalogues/formes.json.")
        return self.cat.formes.get("defaut", "circle")

    def forme(self, nom: str) -> Optional[dict]:
        return next((f for f in self.cat.formes["formes"] if f["qgis"] == nom), None)


def _signature(geom: dict) -> Optional[dict]:
    if "curveRings" in geom or "curvePaths" in geom:
        # Cercle : uniquement des arcs (« a », « c ») ; une forme en courbes de Bézier (« b »), une
        # épingle par exemple, n'est pas un cercle (lot 2.1 : elle devenait un rond sans le dire).
        segments = [s for anneau in (geom.get("curveRings") or geom.get("curvePaths") or []) for s in anneau
                    if isinstance(s, dict)]
        return {"genre": "courbe", "arcs_seuls": bool(segments) and all(set(s) <= {"a", "c"} for s in segments)}
    if "rings" in geom and geom["rings"]:
        anneau = geom["rings"][0]
        sommets = anneau[:-1] if len(anneau) > 1 and anneau[0] == anneau[-1] else anneau
        aligne = all(any(abs(float(p[i]) - float(q[i])) < 1e-6 for i in (0, 1))
                     for p, q in zip(sommets, sommets[1:] + sommets[:1]))
        xs = [float(p[0]) for p in sommets]
        ys = [float(p[1]) for p in sommets]
        largeur = max(xs) - min(xs)
        proportion = round((max(ys) - min(ys)) / largeur, 1) if largeur else None
        return {"genre": "anneau", "sommets": len(sommets), "aligne": aligne, "proportion": proportion}
    if "paths" in geom and geom["paths"]:
        chemins_ = geom["paths"]
        aligne = all(any(abs(float(c[0][i]) - float(c[-1][i])) < 1e-6 for i in (0, 1)) for c in chemins_)
        return {"genre": "chemin", "sommets": len(chemins_), "aligne": aligne}
    return None


def _lab_vers_rgb(L: float, a: float, b: float) -> tuple[float, float, float]:
    fy = (L + 16) / 116
    fx, fz = fy + a / 500, fy - b / 200

    def finv(t: float) -> float:
        return t ** 3 if t ** 3 > 0.008856 else (t - 16 / 116) / 7.787

    x, y, z = 0.95047 * finv(fx), 1.0 * finv(fy), 1.08883 * finv(fz)
    rl = 3.2406 * x - 1.5372 * y - 0.4986 * z
    gl = -0.9689 * x + 1.8758 * y + 0.0415 * z
    bl = 0.0557 * x - 0.2040 * y + 1.0570 * z

    def gamma(c: float) -> float:
        c = max(0.0, min(1.0, c))
        return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055

    return gamma(rl) * 255, gamma(gl) * 255, gamma(bl) * 255


# ============================================================================
# Lecture / écriture d'un ensemble de propriétés
# ============================================================================

def _sans_zero(p: dict, valeur: Any) -> Any:
    """Un zéro sans valeur par défaut au catalogue vaut « absent » (ex. décalage nul) : les deux formats l'écrivent ou non."""
    if (valeur in (0, 0.0) and not isinstance(valeur, bool) and p["type"] in ("longueur", "nombre")
            and (p.get("defaut") is None or p.get("zero_est_absent"))):
        return None
    return valeur


def _applicable(p: dict, geometrie: Optional[str]) -> bool:
    return p.get("geometrie") in (None, geometrie)


def lire_lyrx(conv: Convertisseur, proprietes: list[dict], objet: dict, ou: str,
              geometrie: Optional[str] = None) -> tuple[dict, set[str]]:
    """Lit les propriétés d'un objet CIM. Renvoie (valeurs neutres, clés de premier niveau utilisées)."""
    props: dict[str, Any] = {}
    utilisees: set[str] = set()
    for p in proprietes:
        if not _applicable(p, geometrie) or not p.get("lyrx") or p.get("lecture_seule") == "qgis":
            continue
        chemin = p["lyrx"]
        utilisees.add(chemins.decouper(chemin)[0][1])
        if p.get("lyrx_perpendiculaire"):
            utilisees.add(p["lyrx_perpendiculaire"]["x"])
        if p.get("lyrx_moteur"):
            utilisees.add(p["lyrx_moteur"])
        if p.get("lyrx_substitutions"):
            utilisees.add(p["lyrx_substitutions"])
        if p["nom"] in props and props[p["nom"]] is not None:
            continue
        if not conditions_remplies(p.get("lyrx_si"), lambda k: chemins.lire(objet, k)):
            continue
        brut = chemins.lire(objet, chemin)
        if p.get("lyrx_perpendiculaire"):
            brut = _perpendiculaire_lyrx(p["lyrx_perpendiculaire"], objet, brut)
        if p.get("zero_est_absent") and isinstance(brut, (int, float)) and abs(brut) < 1e-3:
            brut = None
        if isinstance(brut, str) and brut in ("NaN", "Infinity", "-Infinity"):
            brut = None  # ArcGIS écrit parfois « NaN » (en texte) pour une valeur non définie
        if brut is None and p["type"] == "booleen":
            # ArcGIS n'écrit pas les valeurs fausses dans le .lyrx : un vrai/faux absent vaut « faux ».
            brut = p.get("defaut_lyrx", False)
        if p.get("lyrx_proportionnel") and isinstance(brut, (int, float)):
            brut = brut * _echelle_proportionnelle(objet)
        valeur = _sans_zero(p, _lyrx_vers_pivot(conv, p, brut, objet, ou))
        if valeur is None:
            valeur = p.get("defaut")
        if valeur is not None:
            props[p["nom"]] = valeur
    return props, utilisees


def _perpendiculaire_lyrx(regle: dict, objet: dict, oy: Any) -> Optional[float]:
    """Hachures CIM : offsetX / offsetY sont dans le repère de la carte (lot 2.1, mesuré dans ArcGIS
    Pro 3.7). Seule compte la composante perpendiculaire aux traits, le long de la normale
    (sin a, cos a) à l'écran : offsetX · sin a − offsetY · cos a."""
    ox = chemins.lire(objet, regle["x"])
    if ox is None and oy is None:
        return None
    try:
        a = math.radians(float(chemins.lire(objet, regle["angle"]) or 0))
        return float(ox or 0) * math.sin(a) - float(oy or 0) * math.cos(a)
    except (TypeError, ValueError):
        return None


def _signe_selon_angle(regle: Optional[dict], props: dict) -> int:
    """Signe à appliquer au décalage QGIS d'une hachure selon son angle (table du catalogue)."""
    if not regle:
        return 1
    a = float(props.get(regle["angle"]) or 0) % 360
    for axe, signe in regle.get("axes", {}).items():
        if abs(a - float(axe)) < 1e-6:
            return int(signe)
    return int(regle["quadrants"][int(a // 90) % 4])


def _image_lyrx(conv: Convertisseur, url: str, substitutions: Any, ou: str) -> str:
    """Image CIM avec « colorSubstitutions » : les couleurs sont repeintes dans l'image (images.py)."""
    if not isinstance(substitutions, list) or not substitutions:
        return url
    paires = []
    for s in substitutions:
        if isinstance(s, dict):
            avant = conv.couleur_lyrx_vers_pivot(s.get("oldColor"), ou)
            apres = conv.couleur_lyrx_vers_pivot(s.get("newColor"), ou)
            if avant and apres:
                paires.append((avant, apres))
    nouvelle = images.recolorer(url, paires) if paires else url
    if nouvelle is None:
        conv.rapport.avertir(ou, "Image : les substitutions de couleurs ArcGIS ne sont pas reprises "
                                 "(seules les images BMP intégrées sont repeintes).")
        return url
    return nouvelle


def _echelle_proportionnelle(objet: dict) -> float:
    """Marqueur CIM avec « scaleSymbolsProportionally » : ArcGIS agrandit ses traits avec le marqueur,
    dans le rapport taille / hauteur du cadre (lot 2 : contour de 1 pt dessiné à 4,5 pt sur un cercle
    de 18 pt au cadre de 4). QGIS garde l'épaisseur telle quelle."""
    if not objet.get("scaleSymbolsProportionally"):
        return 1.0
    cadre = objet.get("frame") or {}
    try:
        hauteur = float(cadre.get("ymax", 0)) - float(cadre.get("ymin", 0))
        taille = float(objet.get("size", 0))
    except (TypeError, ValueError):
        return 1.0
    return taille / hauteur if hauteur > 0 and taille > 0 else 1.0


def _lyrx_vers_pivot(conv: Convertisseur, p: dict, brut: Any, objet: dict, ou: str) -> Any:
    t = p["type"]
    if t == "forme":
        return conv.forme_depuis_graphique(brut, ou)
    if t == "expression":
        if brut is None:
            return None
        return conv.expr.vers_qgis(str(brut), chemins.lire(objet, p["lyrx_moteur"]) or "VBScript", ou)
    if brut is None:
        return None
    if t == "couleur":
        return conv.couleur_lyrx_vers_pivot(brut, ou)
    if t in ("longueur", "nombre"):
        return _arrondi(float(brut), 6)
    if t == "angle":
        return _arrondi(float(brut) % 360, 6)
    if t == "entier":
        return int(brut)
    if t == "texte":
        return str(brut)
    if t == "booleen":
        return bool(brut)
    if t == "longueurs":
        return [_arrondi(float(x), 6) for x in brut] if isinstance(brut, list) and brut else None
    if t == "caractere":
        return int(brut)
    if t == "image":
        return _image_lyrx(conv, str(brut), objet.get(p.get("lyrx_substitutions") or ""), ou)
    if t == "liste":
        return conv.liste_vers_pivot(p["liste"], "lyrx", brut, ou, p.get("defaut"))
    if t == "decalage_impair":
        return True if brut else None
    return None


def ecrire_lyrx(conv: Convertisseur, proprietes: list[dict], props: dict, objet: dict, ou: str,
                geometrie: Optional[str] = None) -> None:
    deja: set[str] = set()
    for p in proprietes:
        if not _applicable(p, geometrie) or not p.get("lyrx") or p.get("lecture_seule"):
            continue
        if p["lyrx"] in deja:
            continue
        valeur = props.get(p["nom"])
        if valeur is None:
            continue
        deja.add(p["lyrx"])
        t = p["type"]
        if p.get("lyrx_perpendiculaire"):
            regle = p["lyrx_perpendiculaire"]
            a = math.radians(float(props.get(regle.get("angle_pivot", "angle")) or 0))
            for cle, x in ((regle["x"], valeur * math.sin(a)), (p["lyrx"], -valeur * math.cos(a))):
                if abs(x) > 1e-6:
                    chemins.ecrire(objet, cle, _arrondi(x, 6))
            continue
        if t == "forme":
            forme = conv.forme(valeur) or conv.forme(conv.cat.formes.get("defaut", "circle"))
            if forme["qgis"] != valeur:
                conv.rapport.avertir(ou, f"Forme de marqueur QGIS « {valeur} » inconnue : cercle utilisé.",
                                     "Ajouter la forme dans catalogues/formes.json.")
            graphique = chemins.lire(objet, p["lyrx"])
            if graphique is None:
                chemins.ecrire(objet, p["lyrx"] + ".geometry", {})
                graphique = chemins.lire(objet, p["lyrx"])
            graphique["geometry"] = forme["cim_geometrie"]
            graphique.setdefault("symbol", {"symbolLayers": []})["type"] = forme.get("cim_symbole", "CIMPolygonSymbol")
            continue
        if t == "expression":
            texte, moteur = conv.expr.depuis_qgis(valeur, "Arcade", ou)
            chemins.ecrire(objet, p["lyrx"], texte)
            chemins.ecrire(objet, p["lyrx_moteur"], moteur)
            continue
        if t == "couleur":
            brut: Any = conv.couleur_pivot_vers_lyrx(valeur)
        elif t in ("longueur", "nombre", "angle"):
            brut = _arrondi(valeur, 6)
            brut = int(brut) if brut == int(brut) else brut
        elif t in ("entier", "caractere"):
            brut = int(valeur)
        elif t == "longueurs":
            brut = [int(x) if float(x) == int(x) else _arrondi(x, 6) for x in valeur]
        elif t == "liste":
            brut, _ = conv.liste_depuis_pivot(p["liste"], "lyrx", valeur, ou)
            if brut is None:
                continue
        elif t in ("booleen", "decalage_impair"):
            brut = bool(valeur)
        else:
            brut = valeur
        chemins.ecrire(objet, p["lyrx"], brut)


def lire_qgis(conv: Convertisseur, proprietes: list[dict], lecteur: Lecteur, ou: str,
              geometrie: Optional[str] = None) -> tuple[dict, set[str]]:
    """Lit des propriétés QGIS. « lecteur(clé) » renvoie le texte de la propriété ou None."""
    props: dict[str, Any] = {}
    utilisees: set[str] = set()
    for p in proprietes:
        if not _applicable(p, geometrie) or not p.get("qgis") or p.get("lecture_seule") == "lyrx":
            continue
        utilisees.add(p["qgis"])
        if p.get("qgis_unite"):
            utilisees.add(p["qgis_unite"])
        if p["nom"] in props and props[p["nom"]] is not None:
            continue
        if not conditions_remplies(p.get("qgis_si"), lecteur):
            continue
        valeur = _sans_zero(p, _qgis_vers_pivot(conv, p, lecteur, props, ou))
        if valeur is None:
            valeur = p.get("defaut_qgis", p.get("defaut"))
        if valeur is not None:
            props[p["nom"]] = valeur
    return props, utilisees


def _nombre(texte: Any) -> Optional[float]:
    if texte is None or texte == "":
        return None
    try:
        return float(texte)
    except (TypeError, ValueError):
        return None


def _qgis_vers_pivot(conv: Convertisseur, p: dict, lire: Lecteur, deja: dict, ou: str) -> Any:
    t = p["type"]
    brut = lire(p["qgis"])
    if t == "expression":
        if brut is None or brut == "":
            return None
        est_expr = str(lire(p["qgis_drapeau"]) or "0") in ("1", "true")
        return brut if est_expr else '"' + brut.replace('"', '""') + '"'
    if brut is None:
        return None
    if "qgis_composante" in p:
        morceaux = str(brut).split(",")
        brut = morceaux[p["qgis_composante"]] if len(morceaux) > p["qgis_composante"] else None
        if brut is None:
            return None
    facteur = p.get("qgis_facteur", 1) * p.get("qgis_facteur_selon_genre", {}).get(conv.genre_symbole, 1)
    facteur *= _signe_selon_angle(p.get("qgis_signe_selon_angle"), deja)
    if t == "couleur":
        return conv.couleur_qgis_vers_pivot(brut)
    if t == "longueur":
        x = _nombre(brut)
        if x is None:
            return None
        return _arrondi(conv.vers_points(x * facteur, lire(p["qgis_unite"]) if p.get("qgis_unite") else "Point", ou), 6)
    if t == "longueurs":
        try:
            valeurs = [float(x) for x in re.split(r"[;,]", str(brut)) if x.strip()]
        except ValueError:
            return None
        unite = lire(p["qgis_unite"]) if p.get("qgis_unite") else "Point"
        return [_arrondi(conv.vers_points(x, unite, ou), 6) for x in valeurs] or None
    if t == "angle":
        x = _nombre(brut)
        if x is None:
            return None
        if p.get("qgis_sens") == "horaire":
            x = -x
        return _arrondi(x % 360, 6)
    if t == "nombre":
        x = _nombre(brut)
        return None if x is None else _arrondi(x * facteur, 6)
    if t == "entier":
        x = _nombre(brut)
        return None if x is None else int(x)
    if t == "texte":
        return str(brut)
    if t == "booleen":
        return str(brut).lower() in ("1", "true")
    if t == "caractere":
        return ord(brut[0]) if brut else None
    if t == "forme":
        # Nom de forme QGIS gardé tel quel ; une forme inconnue est signalée à l'écriture du .lyrx.
        return str(brut) or None
    if t == "image":
        if not brut.startswith("base64:"):
            return brut
        donnees = brut[len("base64:"):]
        # QGIS ne note pas le format de l'image : on le reconnaît à ses premiers octets (en base64).
        debuts = {"Qk": "bmp", "iVBOR": "png", "/9j/": "jpeg", "R0lG": "gif", "PHN2": "svg+xml", "PD94": "svg+xml"}
        format_ = next((f for d, f in debuts.items() if donnees.startswith(d)), "png")
        return f"data:image/{format_};base64," + donnees
    if t == "liste":
        return conv.liste_vers_pivot(p["liste"], "qgis", brut, ou, p.get("defaut"), lire)
    if t == "tirets_qt":
        motif = conv.liste_vers_pivot(p["liste"], "qgis", brut, ou, None)
        if not motif:
            return None
        largeur = max(float(deja.get("largeur") or 1), 0.5)
        return [_arrondi(x * largeur, 6) for x in motif]
    if t == "decalage_impair":
        x = _nombre(brut)
        if not x:
            return None
        pas = deja.get(p.get("pas", "pas_x"))
        valeur = conv.vers_points(x, lire(p["qgis_unite"]) if p.get("qgis_unite") else "Point", ou)
        if pas and abs(valeur - pas / 2) > 0.05 * pas:
            conv.rapport.avertir(ou, f"Décalage des lignes impaires de la grille ({valeur:.2f} pt) remplacé par un "
                                     f"demi-pas ({pas / 2:.2f} pt) : ArcGIS Pro ne connaît que ce décalage.")
        return True
    return None


class ProprietesXml:
    """Présente un élément XML comme un dictionnaire de propriétés à chemins (« a/b@attr »)."""

    def __init__(self, element):
        self.element = element

    def get(self, cle: str, defaut: Any = None) -> Any:
        v = chemins.xml_lire(self.element, cle)
        return defaut if v is None else v

    def __setitem__(self, cle: str, valeur: str) -> None:
        chemins.xml_ecrire(self.element, cle, valeur)


def ecrire_qgis(conv: Convertisseur, proprietes: list[dict], props: dict, sortie, ou: str,
                geometrie: Optional[str] = None) -> None:
    """Écrit les valeurs neutres dans « sortie » (dictionnaire ou ProprietesXml)."""
    deja: set[str] = set()
    for p in proprietes:
        if not _applicable(p, geometrie) or not p.get("qgis") or p.get("lecture_seule"):
            continue
        if p.get("sens") == "vers_lyrx":
            if props.get(p["nom"]):
                conv.rapport.avertir(ou, p.get("avertissement_qgis") or f"Propriété « {p['nom']} » sans équivalent QGIS : non convertie.")
            continue
        valeur = props.get(p["nom"])
        cle = p["qgis"] + (f"#{p['qgis_composante']}" if "qgis_composante" in p else "")
        if cle in deja:
            continue
        if valeur is None:
            for k, v in (p.get("qgis_si_absent") or {}).items():
                sortie[k] = v
            continue
        deja.add(cle)
        t = p["type"]
        facteur = p.get("qgis_facteur", 1) * p.get("qgis_facteur_selon_genre", {}).get(conv.genre_symbole, 1)
        facteur *= _signe_selon_angle(p.get("qgis_signe_selon_angle"), props)
        unite = None
        if t == "couleur":
            texte = conv.couleur_pivot_vers_qgis(valeur)
        elif t == "longueur":
            texte, unite = conv.depuis_points(float(valeur) * facteur)
        elif t == "longueurs":
            unite = conv.cat.unites["qgis_sortie"]
            texte = ";".join(conv.depuis_points(float(x))[0] for x in valeur)
        elif t == "angle":
            x = -float(valeur) if p.get("qgis_sens") == "horaire" else float(valeur)
            texte = _texte_nombre(x % 360 if x >= 0 else x, 6)
        elif t in ("nombre", "entier"):
            texte = _texte_nombre(float(valeur) * facteur, 6)
        elif t == "booleen":
            texte = "1" if valeur else "0"
        elif t == "caractere":
            texte = chr(int(valeur))
        elif t == "image":
            m = re.match(r"data:image/[a-z+]+;base64,(.*)", str(valeur), re.S)
            texte = "base64:" + m.group(1) if m else str(valeur)
        elif t == "liste":
            texte, extra = conv.liste_depuis_pivot(p["liste"], "qgis", valeur, ou)
            if texte is None:
                continue
            for k, v in extra.items():
                sortie[k] = v
        elif t == "expression":
            m = re.fullmatch(r'"((?:[^"]|"")+)"', str(valeur).strip())
            if m:
                texte = m.group(1).replace('""', '"')
                sortie[p["qgis_drapeau"]] = "0"
            else:
                texte = str(valeur)
                sortie[p["qgis_drapeau"]] = "1"
        elif t == "decalage_impair":
            if not valeur:
                continue
            pas = props.get("pas_x") or 0
            texte, unite = conv.depuis_points(float(pas) / 2)
        else:
            texte = str(valeur)
        if "qgis_composante" in p:
            actuel = (sortie.get(p["qgis"]) or "0,0").split(",")
            while len(actuel) < 2:
                actuel.append("0")
            actuel[p["qgis_composante"]] = texte
            texte = ",".join(actuel)
        sortie[p["qgis"]] = texte
        if unite and p.get("qgis_unite"):
            sortie[p["qgis_unite"]] = unite
        for k, v in (p.get("qgis_si_present") or {}).items():
            sortie[k] = v
