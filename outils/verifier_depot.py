"""Contrôle avant envoi : rien de privé ne doit partir sur le dépôt public.

    python outils/verifier_depot.py            # contrôle le dernier commit (HEAD)
    python outils/verifier_depot.py --index    # contrôle ce qui est prêt à être enregistré (git add)

Le dépôt est public depuis le 17 novembre 2026. Ce script est lancé automatiquement avant chaque
`git push` (crochet `.git/hooks/pre-push`, installé par `python outils/verifier_depot.py --installer`)
et par les tests (tests/test_depot.py). Il refuse :

- un fichier de symbologie, de données ou de connexion hors des dossiers d'exemples
  (`exemples/lyrx`, `exemples/qlr` : symbologies réelles anonymisées, publiées depuis la v1.7.2 ;
  `exemples/fabriques`, `exemples/invalides` : cas inventés) ; le corpus (`corpus/`) reste sur le
  poste, ignoré par git ;
- les fichiers de travail pour Claude (`CLAUDE.md`, `.claude/`) ;
- une adresse e-mail hors des domaines d'exemple ;
- un des mots de `donnees_locales/mots_interdits.txt` (un par ligne : vrais noms de bases, de
  serveurs, d'utilisateurs… ; ce fichier n'est jamais dans le dépôt).
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nouveautes import GIT  # noqa: E402  (git trouvé même hors du PATH)

RACINE = Path(__file__).resolve().parent.parent
INTERDITS = ("corpus/", "CLAUDE.md", ".claude/", "donnees_locales/",
             "comparaisons_lot2/", "sorties/")
SYMBOLOGIES = re.compile(r"\.(lyrx|lyr|qlr|qml|sde|odc|gdb|gpkg|mxd|aprx|mapx|shp|dbf|sqlite)$", re.I)
SYMBOLOGIES_PERMISES = ("exemples/lyrx/", "exemples/qlr/", "exemples/fabriques/", "exemples/invalides/")
EMAIL = re.compile(r"[\w.+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})")
DOMAINES_PERMIS = {"example.invalid", "example.org", "example.com", "exemple.ch", "exemple.org",
                   "anthropic.com", "users.noreply.github.com"}
MOTS_INTERDITS = RACINE / "donnees_locales" / "mots_interdits.txt"
CROCHET = """#!/bin/sh
# Installé par outils/verifier_depot.py : refuse l'envoi si un fichier privé est dans le dépôt.
racine=$(git rev-parse --show-toplevel)
if [ -f "$racine/outils/py.ps1" ] && command -v powershell >/dev/null 2>&1; then
  py="powershell -NoProfile -File $racine/outils/py.ps1"   # Windows : le Python de QGIS
elif command -v python3 >/dev/null 2>&1; then py="python3"; else py="python"; fi
$py "$racine/outils/verifier_depot.py" || { echo "Envoi annulé : voir ci-dessus."; exit 1; }
"""


def _git(*args: str, octets: bool = False):
    r = subprocess.run([GIT, *args], cwd=RACINE, capture_output=True)
    if r.returncode:
        sys.exit(f"git {' '.join(args)} : {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout if octets else r.stdout.decode("utf-8")


def contenus(index: bool = False) -> dict[str, bytes]:
    if index:
        noms = _git("ls-files", "-z", "--cached").split("\0")
        return {n: _git("show", f":{n}", octets=True) for n in noms if n}
    noms = _git("ls-tree", "-r", "-z", "--name-only", "HEAD").split("\0")
    return {n: _git("show", f"HEAD:{n}", octets=True) for n in noms if n}


def controler(fichiers: dict[str, bytes]) -> list[str]:
    """Problèmes qui empêchent la publication (liste vide : tout va bien)."""
    mots = []
    if MOTS_INTERDITS.is_file():
        mots = [m.strip().lower() for m in MOTS_INTERDITS.read_text(encoding="utf-8").splitlines()
                if m.strip() and not m.startswith("#")]
    problemes = []
    for chemin, donnees in fichiers.items():
        if chemin.startswith(INTERDITS):
            problemes.append(f"{chemin} : fichier qui doit rester sur le poste (voir .gitignore)")
        elif SYMBOLOGIES.search(chemin) and not chemin.startswith(SYMBOLOGIES_PERMISES):
            problemes.append(f"{chemin} : fichier de symbologie ou de données hors des dossiers d'exemples")
        texte = donnees.decode("utf-8", "replace")
        for m in EMAIL.finditer(texte):
            domaine = m.group(1).lower()
            if not any(domaine == d or domaine.endswith("." + d) for d in DOMAINES_PERMIS):
                problemes.append(f"{chemin} : adresse e-mail « …@{m.group(1)} »")
        bas = texte.lower()
        problemes += [f"{chemin} : mot interdit n° {i + 1} de mots_interdits.txt" for i, mot in enumerate(mots) if mot in bas]
    return problemes


def main() -> int:
    if "--installer" in sys.argv:
        crochet = RACINE / ".git" / "hooks" / "pre-push"
        crochet.write_text(CROCHET, encoding="utf-8", newline="\n")
        print(f"Crochet installé : {crochet}")
        return 0
    problemes = controler(contenus(index="--index" in sys.argv))
    if problemes:
        print("Contrôle du dépôt public : refusé")
        print("\n".join("  - " + p for p in problemes))
        return 1
    print("Contrôle du dépôt public : rien de privé.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
