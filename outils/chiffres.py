"""Calcule les compteurs affichés sur la page web (web/chiffres.json).

    .\\outils\\py.ps1 outils\\chiffres.py

À relancer avant chaque version, après `corpus.py analyser` dans les deux sens :
- tests : nombre de tests automatiques (pytest --collect-only) ;
- lyrx / qgis : fichiers différents passés par l'aller-retour, d'après les derniers rapports du
  corpus (sorties/corpus/resultats_*.json, qui comptent aussi les fichiers locaux), sinon les
  fichiers du dépôt ;
- regles : entrées des catalogues JSON (correspondances, motifs, formes, règles d'expression…) ;
- arcgis : fichiers produits relus par ArcGIS Pro, d'après `docs/lot2_chiffres.json` (tenu à jour à
  la main après chaque passage du lot 2, car ArcGIS n'est pas sur tous les postes).

Lance aussi `outils/nouveautes.py` (section « Nouveautés » de la page, web/nouveautes.json).
"""
from __future__ import annotations

import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
CATALOGUES = RACINE / "src" / "lyrx2qlr" / "catalogues"
CIBLE = RACINE / "web" / "chiffres.json"
LOT2 = RACINE / "docs" / "lot2_chiffres.json"


def compter_tests() -> int | None:
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=RACINE,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"(\d+) tests? collected", r.stdout)
    return int(m.group(1)) if m else None


def _entrees(x, cle: str = "", dans_liste: bool = False) -> int:
    """Un objet dans une liste = une règle ; un texte dans une liste = un motif ; « _doc » ne compte pas."""
    if cle.startswith("_"):
        return 0
    if isinstance(x, dict):
        return (1 if dans_liste else 0) + sum(_entrees(v, k) for k, v in x.items())
    if isinstance(x, list):
        if all(isinstance(i, (int, float)) for i in x):
            return 0  # liste de nombres = une valeur (ex. motif de tirets), pas des règles
        return sum(_entrees(i, "", True) if isinstance(i, dict) else 1 if isinstance(i, str) else _entrees(i) for i in x)
    return 0


def compter_regles() -> tuple[int, int]:
    fichiers = sorted(CATALOGUES.glob("*.json"))
    return sum(_entrees(json.loads(f.read_text(encoding="utf-8"))) for f in fichiers), len(fichiers)


def compter_fichiers(sens: str, extensions: tuple[str, ...]) -> int:
    resultats = RACINE / "sorties" / "corpus" / f"resultats_{sens}.json"
    if resultats.exists():
        return len(json.loads(resultats.read_text(encoding="utf-8"))["fichiers"])
    dossiers = [RACINE / "corpus" / "fichiers", RACINE / "exemples"]
    return sum(1 for d in dossiers for f in d.rglob("*") if f.suffix.lower() in extensions)


def main() -> int:
    ancien = json.loads(CIBLE.read_text(encoding="utf-8")) if CIBLE.exists() else {}
    regles, catalogues = compter_regles()
    chiffres = {
        "tests": compter_tests() or ancien.get("tests"),
        "lyrx": compter_fichiers("lyrx", (".lyrx",)),
        "qgis": compter_fichiers("qgis", (".qlr", ".qml")),
        "regles": regles,
        "arcgis": json.loads(LOT2.read_text(encoding="utf-8"))["relus_arcgis"] if LOT2.exists() else ancien.get("arcgis"),
        "catalogues": catalogues,
        "date": datetime.date.today().isoformat(),
    }
    CIBLE.write_text(json.dumps(chiffres, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{CIBLE.relative_to(RACINE)} : {chiffres}")
    ecrire_dans_la_page(chiffres)
    import nouveautes  # ajouts au modèle et aux catalogues, version par version (web/nouveautes.json)
    nouveautes.main()
    return 0


def ecrire_dans_la_page(chiffres: dict) -> None:
    """Recopie les nombres dans web/index.html (data-chiffre="…") : les moteurs de recherche et les
    visiteurs sans JavaScript lisent ces nombres-là ; schema.js ne les remplace qu'à l'animation."""
    page = RACINE / "web" / "index.html"
    texte = page.read_text(encoding="utf-8")

    def remplacer(m: re.Match) -> str:
        valeur = chiffres.get(m.group(2))
        return f"{m.group(1)}{valeur}<" if valeur is not None else m.group(0)

    nouveau = re.sub(r'(<[^>]*\bdata-chiffre="(\w+)"[^>]*>)[^<]*<', remplacer, texte)
    if nouveau != texte:
        page.write_bytes(nouveau.encode("utf-8"))
        print(f"{page.relative_to(RACINE)} : nombres mis à jour")


if __name__ == "__main__":
    sys.exit(main())
