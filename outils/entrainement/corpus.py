"""Lot 1.5 : un corpus de vrais fichiers de symbologie trouvés sur internet, convertis et analysés.

    .\\outils\\py.ps1 outils\\entrainement\\corpus.py telecharger
    .\\outils\\py.ps1 outils\\entrainement\\corpus.py analyser [--sens lyrx|qgis] [--local DOSSIER ...]
    .\\outils\\py.ps1 outils\\entrainement\\corpus.py paires

telecharger : lit corpus/sources.json (une entrée par fichier : adresse, page d'origine, licence) et
    télécharge dans corpus/fichiers/ les fichiers absents. Note dans sources.json la taille, l'empreinte
    SHA-256 et la date. Une archive ZIP est ouverte : seuls les fichiers de symbologie en sont extraits.
    Les fichiers téléchargés sont des données : ils sont lus, jamais exécutés.
analyser : passe chaque fichier du corpus (et des dossiers --local) par l'aller-retour
    .lyrx → .qlr → .lyrx (--sens lyrx, par défaut) ou .qml/.qlr → .lyrx → .qlr (--sens qgis), et compte :
      - les fichiers illisibles et les erreurs internes ;
      - les messages du rapport, regroupés (ce qui manque le plus souvent passe en premier) ;
      - les types CIM rencontrés que les catalogues ne connaissent pas ;
      - les écarts de l'aller-retour (le modèle neutre doit revenir identique).
    Résultats : sorties/corpus/rapport_<sens>.md et resultats_<sens>.json ; résumé dans docs/corpus.md.
paires : compare classe par classe notre conversion d'un .lyrx et la version QGIS publiée par le même
    producteur (corpus/paires.json) → sorties/corpus/paires.md.
"""
from __future__ import annotations

import argparse
import ast
import datetime
import hashlib
import json
import re
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "src"))
sys.path.insert(0, str(RACINE / "tests"))

from conftest import comparer_documents  # noqa: E402
from lyrx2qlr import api  # noqa: E402
from lyrx2qlr.catalogue import DOSSIER_CATALOGUES, Catalogue  # noqa: E402
from lyrx2qlr.rapport import Rapport  # noqa: E402

# Écarts d'aller-retour connus, voulus et annoncés dans le rapport (motif → raison).
ECARTS_CONNUS = [
    (r"etiquettes\[\d+\]\.props\.placement : 'courbe' avant, 'libre' après",
     "placement « courbe dans la surface » sans équivalent QGIS (avertissement)"),
    (r"\.placement : None avant, \{'type': 'sommets'",
     "marqueur sans placement dans une ligne : placé sur les sommets (avertissement)"),
    (r"rendu\.classes\[0\]\.etiquette : .* avant, '' après",
     "libellé de légende d'un symbole unique : QGIS n'en a pas (info)"),
    (r"props\.expression : .*\+.* avant, .*\|\|.* après",
     "concaténation VBScript « + » réécrite « || » (même résultat)"),
    (r"symbole\.opacite : [\d.]+ avant, 1\.0 après",
     "opacité d'un symbole entier : pas d'équivalent ArcGIS (avertissement)"),
    (r"\.geometrie : 'inconnu' avant",
     "type de géométrie absent du .qml et sans symbole pour le deviner"),
    (r"etiquettes\[\d+\]\.props\.casse : '(casse_titre|majuscule_initiale)' avant, 'normale' après",
     "casse « titre » ou « majuscule initiale » sans équivalent ArcGIS (avertissement)"),
    (r"\.geometrie : '\w+' avant, '\w+' après",
     "géométrie déclarée contredite par les symboles ; ArcGIS la déduit des symboles (avertissement)"),
    (r"\.symbole : None avant, \{'genre': '\w+', 'couches': \[\], 'opacite': 1\.0\} après",
     "classe sans symbole : QGIS en exige un, un symbole invisible est écrit (même dessin)"),
    (r"etiquettes\[\d+\]\.props\.placement : absent avant",
     "placement d'étiquettes illisible faute de type de géométrie"),
    (r"etiquettes\[\d+\]\.props\.placement : '(autour|toujours_horizontal)' avant, 'horizontal' après",
     "placement QGIS autour ou décalé du centroïde : pas d'équivalent ArcGIS (avertissement, lot 2)"),
    (r"sous_symbole\.couches\[\d+\]\.props\.decalage : -?[\d.]+ avant, -?[\d.]+ après",
     "décalage du trait d'une hachure ramené dans l'écartement : même dessin, QGIS n'affiche rien au-delà (info, lot 2)"),
    (r"rendu\.(etiquette_defaut : '' avant|symbole_defaut : None avant)",
     "classe NULL sans « autres valeurs » : QGIS dessine aussi les valeurs non listées avec elle (avertissement, lot 2.1)"),
]


def _equivalent(ecart: str) -> bool:
    """Deux expressions égales aux guillemets des noms de champs et aux espaces près."""
    m = re.fullmatch(r"\S*(?:filtre|expression) : (.*) avant, (.*) après", ecart, re.S)
    if not m:
        return False
    def norme(t: str) -> str:
        try:
            t = str(ast.literal_eval(t))  # les écarts écrivent les valeurs avec repr()
        except (ValueError, SyntaxError):
            return t
        return re.sub(r"\s+", " ", re.sub(r'"([A-Za-z_][A-Za-z0-9_]*)"', r"\1", t)).strip()
    return norme(m.group(1)) == norme(m.group(2))


CORPUS = RACINE / "corpus"
SOURCES = CORPUS / "sources.json"
FICHIERS = CORPUS / "fichiers"
EXTENSIONS = (".lyrx", ".qml", ".qlr", ".aprx", ".stylx", ".mapx")
TAILLE_MAX = 50 * 1024 * 1024
# Types CIM qui concernent le dessin (les autres : métadonnées, temps, fenêtres contextuelles, 3D…).
SYMBOLOGIE = r"Renderer|Symbol(?!Reference|LayerIdentifier|LayerDrawing)|Fill|Stroke|Marker|Effect|Placement|Callout|Halo|LabelClass|Layer$"


# == téléchargement ======================================================================
def _telecharger(url: str) -> bytes:
    """Téléchargement poli : une pause entre deux requêtes, et des reprises si le serveur demande d'attendre."""
    url = urllib.parse.quote(url, safe=":/?&=%#+,;@")
    requete = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (corpus de symbologies)"})
    for essai in range(5):
        time.sleep(1.5)
        try:
            with urllib.request.urlopen(requete, timeout=120) as r:
                donnees = r.read(TAILLE_MAX + 1)
            break
        except urllib.error.HTTPError as ex:
            if ex.code not in (429, 503) or essai == 4:
                raise
            time.sleep(int(ex.headers.get("Retry-After") or 0) or 20 * (essai + 1))
    if len(donnees) > TAILLE_MAX:
        raise ValueError("fichier trop gros")
    return donnees


SECRETS = re.compile(r"((?:ENCRYPTED_)?PASSWORD(?:_UTF8)?|PWD|TOKEN|API_?KEY)=(?!<retiré>)[^;\"'<>]*", re.I)


def nettoyer(chemin: Path) -> bool:
    """Retire mots de passe (même chiffrés), jetons et clés d'un fichier : jamais de secret dans le dépôt."""
    try:
        texte = chemin.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return False
    propre = SECRETS.sub(lambda m: m.group(1) + "=<retiré>", texte)
    if propre == texte:
        return False
    chemin.write_text(propre, encoding="utf-8")
    return True


def _extraire_zip(chemin: Path) -> list[str]:
    """Extrait les fichiers de symbologie d'une archive, sans jamais écrire hors de son dossier."""
    dossier = chemin.with_suffix("")
    extraits = []
    with zipfile.ZipFile(chemin) as z:
        for info in z.infolist():
            nom = Path(info.filename)
            if info.is_dir() or nom.suffix.lower() not in EXTENSIONS or nom.is_absolute() or ".." in nom.parts:
                continue
            cible = dossier / nom
            cible.parent.mkdir(parents=True, exist_ok=True)
            cible.write_bytes(z.read(info))
            nettoyer(cible)
            extraits.append(cible.relative_to(FICHIERS).as_posix())
    return extraits


def telecharger() -> int:
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    nouveaux = erreurs = 0
    for e in sources:
        cible = FICHIERS / e["fichier"]
        if cible.exists() and e.get("sha256"):
            continue
        try:
            donnees = _telecharger(e["url"])
        except Exception as ex:  # noqa: BLE001 — on note l'échec et on continue
            e["erreur"] = str(ex)[:200]
            erreurs += 1
            print(f"échec : {e['fichier']} ({ex})")
            continue
        cible.parent.mkdir(parents=True, exist_ok=True)
        cible.write_bytes(donnees)
        e.pop("erreur", None)
        e.update(taille=len(donnees), sha256=hashlib.sha256(donnees).hexdigest(),
                 telecharge_le=datetime.date.today().isoformat())
        if cible.suffix.lower() != ".zip" and nettoyer(cible):
            e["modifie"] = "secret retiré (mot de passe, jeton ou clé) ; sha256 = fichier d'origine"
        if cible.suffix.lower() == ".zip":
            try:
                e["contenu"] = _extraire_zip(cible)
            except zipfile.BadZipFile:
                e["erreur"] = "archive illisible"
            cible.unlink()  # on ne garde que les fichiers de symbologie extraits
        nouveaux += 1
    SOURCES.write_text(json.dumps(sources, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{nouveaux} fichier(s) téléchargé(s), {erreurs} échec(s), {len(sources)} source(s) en tout.")
    return 0


# == analyse =============================================================================
def _types_connus() -> set[str]:
    connus: set[str] = set()
    for f in DOSSIER_CATALOGUES.glob("*.json"):
        connus |= set(re.findall(r"CIM[A-Za-z0-9]+", f.read_text(encoding="utf-8")))
    return connus


def _types_cim(objet, compteur: Counter) -> None:
    if isinstance(objet, dict):
        t = objet.get("type")
        if isinstance(t, str) and t.startswith("CIM"):
            compteur[t] += 1
        for v in objet.values():
            _types_cim(v, compteur)
    elif isinstance(objet, list):
        for v in objet:
            _types_cim(v, compteur)


def _famille_message(message: str) -> str:
    """Regroupe les messages semblables : valeurs entre parenthèses et nombres retirés."""
    m = re.sub(r"\([^()]*\)", "(…)", message)
    m = re.sub(r"(?<![A-Za-z])-?\d+(?:[.,]\d+)?", "N", m)
    m = re.sub(r"« [^»]*\$feature[^»]* »|'[^']{25,}'", "«…»", m)
    return m


def _origine(chemin: Path, index: dict) -> str:
    try:
        rel = chemin.relative_to(FICHIERS).as_posix()
    except ValueError:
        return "local"
    return index.get(rel, rel.split("/")[0])


def analyser(locaux: list[str], sens: str = "lyrx") -> int:
    """sens « lyrx » : .lyrx → .qlr → .lyrx ; sens « qgis » : .qml/.qlr → .lyrx → .qlr."""
    cat = Catalogue.charger()
    # Pour l'aller-retour, comme dans les tests : sans remplacement des polices ESRI (voulu et annoncé).
    cat_exact = Catalogue({**cat.d, "polices": {**cat.d["polices"], "substitutions": []}})
    connus = _types_connus()
    sources = json.loads(SOURCES.read_text(encoding="utf-8")) if SOURCES.exists() else []
    index = {}
    for e in sources:
        for f in [e["fichier"]] + e.get("contenu", []):
            index[f] = e["origine"]
    motifs = ("*.lyrx",) if sens == "lyrx" else ("*.qml", "*.qlr")
    autre = ".qlr" if sens == "lyrx" else ".lyrx"
    fichiers = [f for m in motifs for f in sorted(FICHIERS.rglob(m))]
    for d in locaux:
        fichiers += [f for m in motifs for f in sorted(Path(d).rglob(m))]
    vus: set[str] = set()
    resultats = []
    messages: dict[tuple, dict] = {}
    types_total: Counter = Counter()
    types_fichiers: dict[str, set] = defaultdict(set)
    for chemin in fichiers:
        donnees = chemin.read_bytes()
        empreinte = hashlib.sha256(donnees).hexdigest()
        if empreinte in vus:  # même fichier publié deux fois
            continue
        vus.add(empreinte)
        nom = chemin.relative_to(FICHIERS).as_posix() if FICHIERS in chemin.parents else f"local/{chemin.name}"
        fiche = {"fichier": nom, "origine": _origine(chemin, index)}
        try:
            if sens == "lyrx":
                cim = json.loads(donnees.decode("utf-8-sig"), parse_constant=lambda _: None)
            else:
                cim = {}
                import xml.etree.ElementTree as ET
                ET.fromstring(donnees)
        except Exception as ex:  # noqa: BLE001
            fiche["etat"] = f"illisible : {ex}"[:150]
            resultats.append(fiche)
            continue
        fiche["version"] = cim.get("version") if isinstance(cim, dict) else None
        compte: Counter = Counter()
        _types_cim(cim, compte)
        types_total.update(compte)
        for t in compte:
            types_fichiers[t].add(nom)
        fiche["types_inconnus"] = sorted(t for t in compte if t not in connus)
        r1 = Rapport(fichier=nom)
        try:
            doc1 = api.lire(donnees, chemin.name, cat, r1)
            api.ecrire(doc1, autre, cat, r1)  # pour le rapport complet (avec remplacement des polices)
            doc1 = api.lire(donnees, chemin.name, cat_exact, Rapport())
            sortie1 = api.ecrire(doc1, autre, cat_exact, Rapport())
            doc2 = api.lire(sortie1, "x" + autre, cat_exact, Rapport())
            retour = ".lyrx" if sens == "lyrx" else ".qlr"
            doc3 = api.lire(api.ecrire(doc2, retour, cat_exact, Rapport()), "x" + retour, cat_exact, Rapport())
        except Exception:  # noqa: BLE001 — une erreur interne est justement ce qu'on cherche
            fiche["etat"] = "erreur interne"
            fiche["trace"] = traceback.format_exc()[-1500:]
            resultats.append(fiche)
            continue
        fiche["couches"] = len(doc1.couches)
        fiche["rendus"] = sorted({c.rendu.type for c in doc1.couches if c.rendu})
        fiche["pertes"] = r1.compter("perte")
        fiche["avertissements"] = r1.compter("avertissement")
        # Une source à reconnecter (base d'entreprise…) est annoncée : son nom de jeu peut se perdre.
        a_reconnecter = "reconnecter" in r1.en_texte()
        def ecarts(a, b):
            return [d for d in comparer_documents(a, b) if not (a_reconnecter and ".source." in d)][:20]
        fiche["ecarts_aller_retour"] = ecarts(doc1, doc2)
        fiche["ecarts_retour_lyrx"] = ecarts(doc1, doc3)
        fiche["etat"] = "ok"
        for e in r1.entrees:
            cle = (e.niveau, _famille_message(e.message))
            m = messages.setdefault(cle, {"niveau": e.niveau, "message": cle[1], "fichiers": set(), "fois": 0, "exemple": e.message})
            m["fichiers"].add(nom)
            m["fois"] += e.nombre
        resultats.append(fiche)
    return _ecrire(resultats, messages, types_total, types_fichiers, connus, sens)


def _ecrire(resultats, messages, types_total, types_fichiers, connus, sens="lyrx") -> int:
    nom_format = ".lyrx" if sens == "lyrx" else "QGIS (.qml / .qlr)"
    parcours = ".lyrx → .qlr → .lyrx" if sens == "lyrx" else "QGIS → .lyrx → .qlr"
    sortie = RACINE / "sorties" / "corpus"
    sortie.mkdir(parents=True, exist_ok=True)
    ok = [r for r in resultats if r["etat"] == "ok"]
    erreurs = [r for r in resultats if r["etat"] == "erreur interne"]
    illisibles = [r for r in resultats if r["etat"].startswith("illisible")]
    for r in ok:
        tous = r["ecarts_aller_retour"] + r["ecarts_retour_lyrx"]
        r["ecarts_connus"] = sorted({raison for d in tous for motif, raison in ECARTS_CONNUS if re.search(motif, d)})
        if any(_equivalent(d) for d in tous):
            r["ecarts_connus"].append("expression ou filtre équivalent (guillemets, espaces)")
        r["ecarts_inattendus"] = [d for d in tous if not any(re.search(m, d) for m, _ in ECARTS_CONNUS) and not _equivalent(d)]
    instables = [r for r in ok if r["ecarts_inattendus"]]
    connus_seuls = [r for r in ok if r["ecarts_connus"] and not r["ecarts_inattendus"]]
    sans_perte = [r for r in ok if not r["pertes"]]
    par_origine = Counter(r["origine"] for r in resultats)
    lignes = [
        f"# Corpus de symbologies réelles : fichiers {nom_format}",
        "",
        f"- {len(resultats)} fichiers {nom_format} différents ; origines : "
        + ", ".join(f"{o} ({n})" for o, n in par_origine.most_common()) + ".",
        f"- {len(ok)} convertis ; {len(sans_perte)} sans aucune perte ; {len(illisibles)} illisible(s) ;"
        f" **{len(erreurs)} erreur(s) interne(s)**.",
        f"- Aller-retour {parcours} : **{len(instables)} fichier(s) instable(s)** (le modèle ne revient pas"
        f" identique, sans raison connue) ; {len(connus_seuls)} avec seulement des écarts connus et annoncés.",
        "",
        "## Ce qui manque le plus souvent (pertes et avertissements)",
        "",
        "| Fichiers | Fois | Niveau | Message |",
        "|---|---|---|---|",
    ]
    tries = sorted(messages.values(), key=lambda m: (-len(m["fichiers"]), -m["fois"]))
    for m in tries:
        if m["niveau"] == "info" and len(m["fichiers"]) < 3:
            continue
        lignes.append(f"| {len(m['fichiers'])} | {m['fois']} | {m['niveau']} | {m['message'].replace('|', '/')} |")
    if sens == "lyrx":
        lignes += ["", "## Types CIM inconnus des catalogues", "", "| Fichiers | Fois | Type |", "|---|---|---|"]
    for t, n in sorted(types_total.items(), key=lambda x: (-len(types_fichiers[x[0]]), -x[1])):
        if t not in connus and re.search(SYMBOLOGIE, t):
            lignes.append(f"| {len(types_fichiers[t])} | {n} | `{t}` |")
    lignes += ["", "## Erreurs internes", ""]
    lignes += [f"- `{r['fichier']}` : {r['trace'].strip().splitlines()[-1]}" for r in erreurs] or ["Aucune."]
    lignes += ["", "## Allers-retours instables", ""]
    for r in instables:
        lignes.append(f"- `{r['fichier']}` : " + " ; ".join(r["ecarts_inattendus"][:3])[:400])
    if not instables:
        lignes.append("Aucun.")
    lignes += ["", "## Écarts connus et annoncés", "", "| Fichiers | Raison |", "|---|---|"]
    for raison, n in Counter(x for r in ok for x in r["ecarts_connus"]).most_common():
        lignes.append(f"| {n} | {raison} |")
    (sortie / f"rapport_{sens}.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    pour_json = [{**m, "fichiers": sorted(m["fichiers"])} for m in tries]
    (sortie / f"resultats_{sens}.json").write_text(json.dumps({"fichiers": resultats, "messages": pour_json},
                                                      ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(lignes[2:6]))
    print(f"→ {sortie / f'rapport_{sens}.md'}")
    return 0


def _resume_symbole(sym) -> list:
    """Ce qui se voit d'un symbole : type, couleur (avec opacité), épaisseur et taille de chaque couche active."""
    if sym is None:
        return []
    return [(c.type, tuple(c.props["couleur"]) if c.props.get("couleur") else None,
             round(c.props["largeur"], 1) if c.props.get("largeur") else None,
             round(c.props["taille"], 1) if c.props.get("taille") else None)
            for c in sym.couches if c.actif]


def paires() -> int:
    """Compare, classe par classe, notre conversion d'un .lyrx avec la version QGIS faite à la main
    par le même producteur (corpus/paires.json)."""
    cat = Catalogue.charger()
    liste = json.loads((CORPUS / "paires.json").read_text(encoding="utf-8"))["paires"]
    lignes = ["# Paires officielles .lyrx / QGIS : notre conversion contre la version faite à la main", "",
              "| Paire | Classes comparées | Identiques | Couches différentes | Couleurs | Épaisseurs | Tailles |",
              "|---|---|---|---|---|---|---|"]
    exemples: dict[str, list] = defaultdict(list)
    for paire in liste:
        a = api.lire((FICHIERS / paire["lyrx"]).read_bytes(), "a.lyrx", cat, Rapport())
        b = api.lire((FICHIERS / paire["qgis"]).read_bytes(), Path(paire["qgis"]).name, cat, Rapport())
        par_nom = {c.nom: c for c in b.couches}
        n = Counter()
        for ca in a.couches:
            cq = par_nom.get(ca.nom)
            if cq is None or ca.rendu is None or cq.rendu is None:
                continue
            cles = lambda r: {tuple(map(tuple, k.valeurs)) if k.valeurs else ("*",): k for k in r.classes}
            qa, qq = cles(ca.rendu), cles(cq.rendu)
            for v, ka in qa.items():
                if v not in qq:
                    continue
                ra, rq = _resume_symbole(ka.symbole), _resume_symbole(qq[v].symbole)
                n["comparees"] += 1
                if ra == rq:
                    n["identiques"] += 1
                    continue
                if [x[0] for x in ra] != [x[0] for x in rq]:
                    genre = "couches"
                elif [x[1] for x in ra] != [x[1] for x in rq]:
                    genre = "couleurs"
                elif [x[2] for x in ra] != [x[2] for x in rq]:
                    genre = "epaisseurs"
                else:
                    genre = "tailles"
                n[genre] += 1
                exemples[genre].append(f"{ca.nom} « {v[0][0] if v[0] else v} » : {ra} ↔ {rq}")
        nom = Path(paire["lyrx"]).name + " / " + Path(paire["qgis"]).name
        lignes.append(f"| {nom} | {n['comparees']} | {n['identiques']} | {n['couches']} | {n['couleurs']} | {n['epaisseurs']} | {n['tailles']} |")
    lignes += ["", "Chaque ligne d'exemple : type, couleur [R, V, B, A], épaisseur (pt), taille (pt) ; à gauche notre",
               "conversion du .lyrx, à droite la version QGIS du producteur.", ""]
    for genre, l in exemples.items():
        lignes += [f"## Exemples : {genre} différent(e)s", ""] + [f"- {e[:300]}" for e in l[:8]] + [""]
    sortie = RACINE / "sorties" / "corpus"
    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / "paires.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes[2:3 + len(liste) + 1]))
    print(f"→ {sortie / 'paires.md'}")
    return 0


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = a.add_subparsers(dest="action", required=True)
    s.add_parser("telecharger")
    an = s.add_parser("analyser")
    an.add_argument("--local", nargs="*", default=[], help="dossiers locaux à ajouter")
    an.add_argument("--sens", choices=("lyrx", "qgis"), default="lyrx",
                    help="lyrx : .lyrx → .qlr → .lyrx ; qgis : .qml/.qlr → .lyrx → .qlr")
    s.add_parser("paires")
    args = a.parse_args()
    if args.action == "telecharger":
        return telecharger()
    if args.action == "paires":
        return paires()
    return analyser(args.local, args.sens)


if __name__ == "__main__":
    sys.exit(main())
