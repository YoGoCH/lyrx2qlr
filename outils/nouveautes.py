"""Calcule, pour chaque version, ce qui a été ajouté au modèle neutre et aux catalogues de règles,
et l'écrit dans web/nouveautes.json (section « Nouveautés » de la page web).

    .\\outils\\py.ps1 outils\\nouveautes.py

Lancé aussi par `outils/chiffres.py`, avant chaque version.

web/nouveautes.json contient une entrée par version : « version », « date », et les textes courts
« fr » et « en », écrits à la main (ajouter l'entrée de la nouvelle version en tête). Ce script ne
remplit que « ajouts », calculé avec git entre l'étiquette de la version précédente et celle de la
version (ou les fichiers du poste si l'étiquette n'existe pas encore). Seules les versions
présentes dans le fichier sont affichées (depuis la 1.4.0) :
- modele : lignes ajoutées à src/lyrx2qlr/modele.py ;
- catalogues : lignes ajoutées aux catalogues JSON ;
- regles : règles en plus dans les catalogues (même compte que les chiffres de la page).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chiffres import _entrees  # noqa: E402  (même façon de compter les règles)

RACINE = Path(__file__).resolve().parent.parent
CIBLE = RACINE / "web" / "nouveautes.json"
MODELE = "src/lyrx2qlr/modele.py"
CATALOGUES = "src/lyrx2qlr/catalogues"
ARBRE_VIDE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"  # « rien », pour la première version


def _trouver_git() -> str:
    """Le Python de QGIS ne voit pas toujours git dans le PATH : on regarde aussi les dossiers usuels."""
    for chemin in (shutil.which("git"), "C:/Program Files/Git/cmd/git.exe", "C:/Program Files/Git/ucrt64/bin/git.exe"):
        if chemin and Path(chemin).is_file():
            return chemin
    sys.exit("git est introuvable : il faut git pour calculer les nouveautés.")


GIT = _trouver_git()


def _git(*args: str) -> str:
    r = subprocess.run([GIT, *args], cwd=RACINE, capture_output=True, text=True, encoding="utf-8")
    return r.stdout if r.returncode == 0 else ""


def _etiquette_existe(version: str) -> bool:
    return bool(_git("rev-parse", "-q", "--verify", f"refs/tags/v{version}").strip())


def _numero(version: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", version))


def _etiquette_precedente(version: str) -> str | None:
    """Dernière étiquette vX.Y.Z plus ancienne que cette version (None pour la toute première)."""
    anciennes = [e for e in _git("tag", "--list", "v*").split() if _numero(e) < _numero(version)]
    return max(anciennes, key=_numero) if anciennes else None


def _lignes_ajoutees(avant: str, apres: str | None, chemin: str) -> int:
    args = ["diff", "--numstat", avant] + ([apres] if apres else []) + ["--", chemin]
    total = 0
    for ligne in _git(*args).splitlines():
        ajout = ligne.split("\t")[0]
        total += int(ajout) if ajout.isdigit() else 0
    return total


def _regles(ref: str | None) -> int:
    """Règles des catalogues à une étiquette donnée (None = fichiers du poste)."""
    if ref is None:
        return sum(_entrees(json.loads(f.read_text(encoding="utf-8")))
                   for f in sorted((RACINE / CATALOGUES).glob("*.json")))
    if ref == ARBRE_VIDE:
        return 0
    total = 0
    for chemin in _git("ls-tree", "--name-only", f"{ref}:{CATALOGUES}").split():
        if chemin.endswith(".json"):
            total += _entrees(json.loads(_git("show", f"{ref}:{CATALOGUES}/{chemin}")))
    return total


def main() -> int:
    donnees = json.loads(CIBLE.read_text(encoding="utf-8"))
    versions = donnees["versions"]  # la plus récente en tête
    for i, v in enumerate(versions):
        # Le dépôt public (depuis la v1.7.0) n'a pas l'historique des versions plus anciennes : leurs
        # chiffres, calculés avant la migration, sont gardés tels quels. Seule la version en cours
        # (la première, sans étiquette) est comparée aux fichiers du poste.
        if not _etiquette_existe(v["version"]) and i > 0 and "ajouts" in v:
            continue
        if _etiquette_existe(v["version"]) and _etiquette_precedente(v["version"]) is None and "ajouts" in v:
            continue
        # Comparaison avec l'étiquette git qui précède, même si sa version n'est pas affichée
        avant = _etiquette_precedente(v["version"]) or ARBRE_VIDE
        apres = f"v{v['version']}" if _etiquette_existe(v["version"]) else None
        v["ajouts"] = {
            "modele": _lignes_ajoutees(avant, apres, MODELE),
            "catalogues": _lignes_ajoutees(avant, apres, CATALOGUES),
            "regles": _regles(apres) - _regles(avant),
        }
    CIBLE.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for v in versions:
        print(f"v{v['version']:<7} {v['ajouts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
