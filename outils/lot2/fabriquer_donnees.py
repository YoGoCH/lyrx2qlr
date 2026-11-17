"""Lot 2.1 : fabrique des données de test pour les fichiers du corpus qui n'en ont pas.

    .\\outils\\py.ps1 outils\\lot2\\fabriquer_donnees.py FICHIERS_OU_DOSSIERS... --sortie comparaisons_lot2\\corpus

Le corpus (`corpus/fichiers/`, voir docs/corpus.md) ne contient que des symbologies : on ne peut pas les
dessiner. Pour chaque fichier, cet outil lit la symbologie avec le cœur et fabrique une **légende
dessinée** : une GeoPackage où chaque catégorie (ou classe) a **un objet** posé dans une case d'une
grille, avec la valeur qui la déclenche, plus une case « autres valeurs ».

- surfaces : un carré par case ; lignes : un zigzag (angles et longueur pour les marqueurs le long
  de la ligne) ; points : un point au centre de la case ;
- catégories : la première valeur de chaque classe ; classes : le milieu de la classe ;
- ensembles de règles QGIS : chaque règle finale donne une case, avec des valeurs qui satisfont son
  filtre quand il est simple (« = », « IN », « LIKE », « < », « > », « IS NULL », reliés par AND) ;
- échelle : prise dans la plage de visibilité de la couche quand elle existe (symboles en unités
  de carte), sinon 1:5 000.

Sorties dans `<sortie>/` (dossier ignoré par git) :

- `fichiers/<nom>.<ext>` : copie du fichier d'origine sous un nom unique et sans point ;
- `donnees/<nom>.gpkg` : les données (une table `couche_<i>` par couche du fichier) ;
- `donnees/<nom>.plan.json` : les cases (coordonnées, classe, valeurs), pour juger case par case ;
- `fabrication.md` : ce qui a été fabriqué ou écarté, et pourquoi.

Le dessin croisé se lance ensuite comme pour les exemples, avec `--donnees <sortie>/donnees`
(`lancer.sh` le fait avec la variable DONNEES).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "src"))
from lyrx2qlr import api  # noqa: E402
from lyrx2qlr.catalogue import Catalogue  # noqa: E402
from lyrx2qlr.rapport import Rapport  # noqa: E402

from osgeo import gdal, ogr, osr  # noqa: E402

gdal.UseExceptions()
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LARGEUR, HAUTEUR, DPI = 800, 620, 96  # comme dessin_qgis / dessin_arcgis
MAX_CASES = 150  # au-delà, les cases deviennent trop petites pour juger : on garde les premières
ECHELLE_DEFAUT = 5000
AUTRE_TEXTE, AUTRE_NOMBRE = "zz_autre_valeur", -987654
EXTENSIONS = (".lyrx", ".qml", ".qlr")


# -- où poser la grille ---------------------------------------------------------
def systeme(chemin: Path) -> tuple[int, float, float]:
    """Système de coordonnées plausible selon la provenance (EPSG, x0, y0)."""
    t = chemin.as_posix().lower()
    if "quebec" in t:
        return 32198, -300000.0, 300000.0
    if "defra" in t or "ordnancesurvey" in t or "os-" in t or "osmm" in t:
        return 27700, 450000.0, 250000.0
    return 2056, 2540000.0, 1160000.0


def echelle(couche) -> float:
    """Échelle dans la plage de visibilité : la même que celle où le cœur traduit les unités de carte."""
    return couche.echelle_de_reference() or ECHELLE_DEFAUT


# -- les cases d'une couche -------------------------------------------------------
def _nombre(v: str):
    if re.fullmatch(r"-?\d{1,15}", v) and str(int(v)) == v:
        return int(v)
    if re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
    return None


def cases_rendu(rendu) -> tuple[list[dict], list[str]]:
    """Cases tirées du modèle neutre : [{"classe", "valeurs": {champ: valeur}}], champs."""
    if rendu is None:
        return [], []
    if rendu.type == "unique":
        return [{"classe": (rendu.classes[0].etiquette if rendu.classes else "") or "symbole unique", "valeurs": {}}], []
    champs = list(rendu.champs)
    cases = []
    for k in rendu.classes:
        if rendu.type == "classes":
            lo = k.min if k.min is not None else (k.max - 1 if k.max is not None else 0)
            hi = k.max if k.max is not None else lo + 1
            cases.append({"classe": k.etiquette, "valeurs": {champs[0]: (lo + hi) / 2} if champs else {}})
            continue
        tup = k.valeurs[0] if k.valeurs else [None] * len(champs)
        cases.append({"classe": k.etiquette or "/".join(str(v) for v in tup),
                      "valeurs": {c: v for c, v in zip(champs, tup)}})
    if rendu.symbole_defaut is not None or rendu.type == "categories":
        cases.append({"classe": rendu.etiquette_defaut or "autres valeurs", "valeurs": {c: "__autre__" for c in champs},
                      "autre": True})
    return cases, champs


_CHAMP = r'(?:"((?:[^"]|"")+)"|([A-Za-z_][A-Za-z0-9_]*))'
_VAL = r"('(?:[^']|'')*'|-?\d+(?:\.\d+)?)"


def _texte(v: str):
    if v.startswith("'"):
        return v[1:-1].replace("''", "'")
    return _nombre(v) if _nombre(v) is not None else float(v)


def _couper(texte: str, mot: str) -> list[str]:
    """Coupe sur « AND » ou « OR » hors des guillemets et des parenthèses."""
    parties, debut, prof, quote, i = [], 0, 0, None, 0
    motif = re.compile(r"\s+" + mot + r"\s+", re.I)
    while i < len(texte):
        ch = texte[i]
        if quote:
            quote = None if ch == quote else quote
        elif ch in "'\"":
            quote = ch
        elif ch == "(":
            prof += 1
        elif ch == ")":
            prof -= 1
        elif prof == 0:
            m = motif.match(texte, i)
            if m:
                parties.append(texte[debut:i])
                debut = i = m.end()
                continue
        i += 1
    return parties + [texte[debut:]]


def _sans_parentheses(f: str) -> str:
    """Retire les parenthèses qui entourent tout le filtre."""
    f = f.strip()
    while f.startswith("(") and f.endswith(")"):
        prof = 0
        for i, ch in enumerate(f):  # la première parenthèse doit se fermer tout à la fin
            prof += (ch == "(") - (ch == ")")
            if prof == 0 and i < len(f) - 1:
                return f
        f = f[1:-1].strip()
    return f


def satisfaire(filtre: str) -> dict | None:
    """Valeurs qui satisfont un filtre QGIS simple (conditions reliées par AND / OR), sinon None."""
    f = _sans_parentheses(filtre)
    ou = _couper(f, "OR")
    if len(ou) > 1:
        return next((v for v in (satisfaire(x) for x in ou) if v is not None), None)
    et = _couper(f, "AND")
    if len(et) > 1:
        valeurs: dict = {}
        for x in et:
            v = satisfaire(x)
            if v is None:
                return None
            valeurs.update(v)
        return valeurs
    valeurs = {}
    for partie in [f]:
        p = partie.strip()
        m = re.fullmatch(_CHAMP + r"\s*(=|==|<>|!=|<=|>=|<|>)\s*" + _VAL, p, re.S)
        if m:
            champ, op, v = m.group(1) or m.group(2), m.group(3), _texte(m.group(4))
            if op in ("=", "=="):
                valeurs[champ] = v
            elif op in ("<>", "!="):
                valeurs[champ] = (v + 1) if isinstance(v, (int, float)) else f"{v}_x"
            elif isinstance(v, (int, float)):
                valeurs[champ] = v + (1 if ">" in op else -1) * (0 if "=" in op else 1)
            else:
                return None
            continue
        m = re.fullmatch(_CHAMP + r"\s+IN\s*\((.*)\)", p, re.S | re.I)
        if m:
            premiere = re.split(r",(?=(?:[^']*'[^']*')*[^']*$)", m.group(3))[0].strip()
            valeurs[m.group(1) or m.group(2)] = _texte(premiere)
            continue
        m = re.fullmatch(_CHAMP + r"\s+(?:I?LIKE)\s+'((?:[^']|'')*)'", p, re.S | re.I)
        if m:
            valeurs[m.group(1) or m.group(2)] = m.group(3).replace("''", "'").replace("%", "").replace("_", " ")
            continue
        m = re.fullmatch(_CHAMP + r"\s+IS\s+NULL", p, re.S | re.I)
        if m:
            valeurs[m.group(1) or m.group(2)] = None
            continue
        m = re.fullmatch(_CHAMP + r"\s+IS\s+NOT\s+NULL", p, re.S | re.I)
        if m:
            valeurs.setdefault(m.group(1) or m.group(2), "x")
            continue
        return None
    return valeurs


def cases_regles(xml: bytes, numero: int) -> tuple[list[dict], list[str], int] | None:
    """Cases d'un ensemble de règles QGIS (couche n° numero du fichier), ou None si ce n'en est pas un."""
    racine = ET.fromstring(xml)
    couches = [ml for ml in racine.iter("maplayer") if ml.get("type") == "vector"] or [racine]
    if numero >= len(couches):
        return None
    r = couches[numero].find("renderer-v2")
    if r is None or r.get("type") != "RuleRenderer":
        return None
    cases, champs, non = [], [], 0

    def parcourir(regle, herite: dict, libelle: str):
        nonlocal non
        filtre = (regle.get("filter") or "").strip()
        vals = dict(herite)
        if filtre and filtre.upper() != "ELSE" and regle.get("else") != "1":
            v = satisfaire(filtre)
            if v is None:
                non += 1
            else:
                vals.update(v)
        nom = regle.get("label") or filtre or libelle
        enfants = regle.findall("rule")
        if regle.get("symbol") is not None:
            cases.append({"classe": nom, "valeurs": vals, "autre": filtre.upper() == "ELSE" or regle.get("else") == "1"})
        for e in enfants:
            parcourir(e, vals, nom)

    for regle in r.findall("rules/rule"):
        parcourir(regle, {}, "")
    for k in cases:
        for c in k["valeurs"]:
            if c not in champs:
                champs.append(c)
    return cases, champs, non


# -- écriture de la GeoPackage -----------------------------------------------------
GEOM = {"surface": ogr.wkbPolygon, "ligne": ogr.wkbLineString, "point": ogr.wkbPoint}


def type_champ(valeurs: list):
    vs = [v for v in valeurs if v is not None and v != "__autre__"]
    nombres = [v if isinstance(v, (int, float)) else _nombre(str(v)) for v in vs]
    if vs and all(n is not None for n in nombres):
        return ogr.OFTReal if any(isinstance(n, float) for n in nombres) else ogr.OFTInteger64
    return ogr.OFTString


def geometrie(genre: str, x: float, y: float, s: float):
    m = 0.08 * s
    if genre == "surface":
        return ogr.CreateGeometryFromWkt(
            f"POLYGON(({x + m} {y + m},{x + s - m} {y + m},{x + s - m} {y + s - m},{x + m} {y + s - m},{x + m} {y + m}))")
    if genre == "ligne":
        pts = [(0.08, 0.25), (0.36, 0.75), (0.64, 0.25), (0.92, 0.75)]
        return ogr.CreateGeometryFromWkt("LINESTRING(" + ",".join(f"{x + a * s} {y + b * s}" for a, b in pts) + ")")
    return ogr.CreateGeometryFromWkt(f"POINT({x + s / 2} {y + s / 2})")


def genre_couche(couche) -> str:
    if couche.geometrie in GEOM:
        return couche.geometrie
    r = couche.rendu
    for s in ([r.symbole_defaut] + [k.symbole for k in r.classes]) if r else []:
        if s is not None and s.genre in GEOM:
            return s.genre
    return "point"


def nom_unique(f: Path, base: Path, pris: set) -> str:
    try:
        rel = f.relative_to(base)
    except ValueError:
        rel = Path(f.name)
    parties = list(rel.with_suffix("").parts)
    tete = parties[1].split("__")[0][:16] if len(parties) > 2 else ""  # provenance : propriétaire GitHub, jeu Defra…
    nom = re.sub(r"[^A-Za-z0-9_-]+", "_", "__".join([tete] + parties[-2:] if tete else parties[-2:]))
    nom = nom.strip("_")[:80] or "fichier"
    n, i = nom, 2
    while n.lower() in pris:
        n, i = f"{nom}_{i}", i + 1
    pris.add(n.lower())
    return n


def fabriquer(f: Path, nom: str, sortie: Path, cat: Catalogue) -> tuple[str, dict | None]:
    brut = f.read_bytes()
    rapport = Rapport(fichier=f.name)
    doc = api.lire(brut, f.name, cat, rapport)
    couches = [c for c in doc.couches if c.rendu is not None or c.geometrie != "inconnu"]
    if not couches:
        return "écarté : aucune couche vectorielle avec un rendu (raster, groupe vide…)", None
    epsg, x0, y0 = systeme(f)
    plan = {"fichier": f.as_posix(), "epsg": epsg, "couches": []}
    specs = []
    for i, c in enumerate(doc.couches):
        if c not in couches:
            continue
        regles = cases_regles(brut, i) if f.suffix.lower() in (".qml", ".qlr") else None
        if regles:
            cases, champs, non = regles
        else:
            cases, champs = cases_rendu(c.rendu)
            non = 0
        tronque = max(0, len(cases) - MAX_CASES)
        if tronque:
            cases = cases[:MAX_CASES - 1] + [k for k in cases if k.get("autre")][:1]
        specs.append((i, c, cases, champs, non, tronque))
    total = sum(len(s[2]) for s in specs) or 1
    colonnes = max(1, math.ceil(math.sqrt(total * LARGEUR / HAUTEUR)))
    rangees = math.ceil(total / colonnes)
    case_px = min(LARGEUR / colonnes, HAUTEUR / rangees) / 1.05
    e = echelle(specs[0][1])
    s = case_px * e * 0.0254 / DPI  # côté d'une case, en mètres
    gpkg = sortie / "donnees" / f"{nom}.gpkg"
    if gpkg.exists():
        gpkg.unlink()
    ds = ogr.GetDriverByName("GPKG").CreateDataSource(str(gpkg))
    sr = osr.SpatialReference()
    sr.ImportFromEPSG(epsg)
    n = 0
    for i, c, cases, champs, non, tronque in specs:
        table = f"couche_{i}"
        genre = genre_couche(c)
        lyr = ds.CreateLayer(table, sr, GEOM[genre], options=["FID=fid"])
        types = {ch: type_champ([k["valeurs"].get(ch) for k in cases]) for ch in champs}
        for ch, t in types.items():
            lyr.CreateField(ogr.FieldDefn(ch, t))
        lyr.CreateField(ogr.FieldDefn("lot2_classe", ogr.OFTString))
        defn = lyr.GetLayerDefn()
        infos = []
        for k in cases:
            col, rang = n % colonnes, n // colonnes
            x, y = x0 + col * s, y0 + (rangees - 1 - rang) * s
            ft = ogr.Feature(defn)
            for ch in champs:
                v = k["valeurs"].get(ch, "__autre__" if k.get("autre") else None)
                if v == "__autre__":
                    v = AUTRE_TEXTE if types[ch] == ogr.OFTString else AUTRE_NOMBRE
                if v is None:
                    ft.SetFieldNull(ch)
                elif types[ch] == ogr.OFTString:
                    ft.SetField(ch, str(v))
                else:
                    ft.SetField(ch, float(v) if types[ch] == ogr.OFTReal else int(float(v)))
            ft.SetField("lot2_classe", str(k["classe"])[:250])
            ft.SetGeometry(geometrie(genre, x, y, s))
            lyr.CreateFeature(ft)
            infos.append({"classe": str(k["classe"]), "xmin": x, "ymin": y, "xmax": x + s, "ymax": y + s})
            n += 1
        plan["couches"].append({"numero": i, "nom": c.nom, "table": table, "geometrie": genre, "champs": champs,
                                "regles_non_satisfaites": non, "cases_retirees": tronque, "cases": infos})
    ds = None
    plan["echelle"], plan["cote_case"] = e, s
    (sortie / "donnees" / f"{nom}.plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    (sortie / "fichiers" / f"{nom}{f.suffix.lower()}").write_bytes(brut)
    detail = ", ".join(f"{len(k[2])} cases" + (f" ({k[4]} règles non satisfaites)" if k[4] else "") +
                       (f" ({k[5]} retirées)" if k[5] else "") for k in specs)
    return f"fabriqué : {genre_couche(specs[0][1])}, {detail}, 1:{e:,.0f}".replace(",", " "), plan


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("entrees", nargs="+", help="fichiers ou dossiers (parcourus récursivement)")
    a.add_argument("--sortie", required=True)
    a.add_argument("--max", type=int, default=0, help="nombre maximal de fichiers (0 = tous)")
    args = a.parse_args()
    sortie = Path(args.sortie).resolve()
    (sortie / "donnees").mkdir(parents=True, exist_ok=True)
    (sortie / "fichiers").mkdir(parents=True, exist_ok=True)
    fichiers = []
    for e in args.entrees:
        p = Path(e).resolve()
        fichiers += sorted(x for x in p.rglob("*") if x.suffix.lower() in EXTENSIONS) if p.is_dir() else [p]
    if args.max:
        fichiers = fichiers[:args.max]
    cat = Catalogue.charger()
    base = (RACINE / "corpus" / "fichiers").resolve()
    pris: set = set()
    lignes = ["# Lot 2.1 : données fabriquées pour le corpus", "", "| Fichier | Nom | Résultat |", "|---|---|---|"]
    faits = 0
    for f in fichiers:
        nom = nom_unique(f, base, pris)
        try:
            etat, plan = fabriquer(f, nom, sortie, cat)
        except Exception as e:  # noqa: BLE001
            etat, plan = f"ÉCHEC : {type(e).__name__} {str(e)[:150]}", None
        faits += plan is not None
        rel = f.relative_to(base).as_posix() if f.is_relative_to(base) else f.name
        lignes.append(f"| {rel} | {nom if plan else ''} | {etat} |")
        print(f"{nom:60} {etat}", flush=True)
    lignes.insert(2, f"**{faits} fichiers sur {len(fichiers)}** ont leurs données.")
    lignes.insert(3, "")
    (sortie / "fabrication.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
