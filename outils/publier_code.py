"""Tient à jour la copie publique du code : le dépôt GitHub « lyrx2qlr_code_public ».

    python outils/publier_code.py                 # prépare et enregistre la copie (sans l'envoyer)
    python outils/publier_code.py --pousser       # … et l'envoie sur GitHub

Le dépôt de travail (lyrx_2_qlr) reste privé : il garde son historique, les symbologies réelles
de travail et d'entraînement, et les notes pour Claude. La copie publique reçoit, à chaque
lancement, l'état **enregistré** (dernier commit) du dépôt de travail, **sans** :

- les symbologies réelles (`exemples/lyrx`, `exemples/qlr`) et le corpus (`corpus/`) ;
- les fichiers de travail pour Claude (`CLAUDE.md`, `.claude/`) ;
- l'historique : un commit par copie, « Copie de lyrx_2_qlr vX.Y.Z (abc1234) ».

Les symbologies inventées (`exemples/fabriques`, `exemples/invalides`) y vont : les tests
automatiques de GitHub s'en servent. Les tests qui demandent les symbologies réelles sont sautés.

Avant d'enregistrer, la copie est contrôlée ; le script s'arrête au moindre doute :
- aucun fichier de symbologie ou de connexion hors des dossiers permis ;
- aucune adresse e-mail hors des domaines d'exemple ;
- aucun des mots de `donnees_locales/mots_interdits.txt` (un par ligne : vrais noms de bases,
  de serveurs, d'utilisateurs… ; ce fichier n'est jamais dans un dépôt).

Le dossier de la copie est `../lyrx2qlr_code_public` (à côté du dépôt de travail), ou `--cible`.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nouveautes import GIT  # noqa: E402  (git trouvé même hors du PATH)

RACINE = Path(__file__).resolve().parent.parent
CIBLE = RACINE.parent / "lyrx2qlr_code_public"
ADRESSE = "https://github.com/YoGoCH/lyrx2qlr_code_public.git"

EXCLUS = ("exemples/lyrx/", "exemples/qlr/", "corpus/", "CLAUDE.md", ".claude/", "comparaisons_lot2/",
          "donnees_locales/", "sorties/", "web/_")
SYMBOLOGIES = re.compile(r"\.(lyrx|lyr|qlr|qml|sde|odc|gdb|gpkg|mxd|aprx|mapx|shp|dbf)$", re.I)
SYMBOLOGIES_PERMISES = ("exemples/fabriques/", "exemples/invalides/")
EMAIL = re.compile(r"[\w.+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})")
DOMAINES_PERMIS = {"example.invalid", "example.org", "example.com", "exemple.ch", "exemple.org",
                   "anthropic.com", "users.noreply.github.com"}
MOTS_INTERDITS = RACINE / "donnees_locales" / "mots_interdits.txt"


def git(*args: str, cwd: Path = RACINE, octets: bool = False):
    r = subprocess.run([GIT, *args], cwd=cwd, capture_output=True)
    if r.returncode:
        sys.exit(f"git {' '.join(args)} : {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout if octets else r.stdout.decode("utf-8")


def fichiers_publics() -> list[str]:
    tous = git("ls-tree", "-r", "-z", "--name-only", "HEAD").split("\0")
    return [f for f in tous if f and not f.startswith(EXCLUS)]


def controler(contenus: dict[str, bytes]) -> list[str]:
    """Problèmes qui empêchent la publication (liste vide : tout va bien)."""
    mots = []
    if MOTS_INTERDITS.is_file():
        mots = [m.strip().lower() for m in MOTS_INTERDITS.read_text(encoding="utf-8").splitlines()
                if m.strip() and not m.startswith("#")]
    problemes = []
    for chemin, donnees in contenus.items():
        if SYMBOLOGIES.search(chemin) and not chemin.startswith(SYMBOLOGIES_PERMISES):
            problemes.append(f"{chemin} : fichier de symbologie ou de données hors des dossiers permis")
        texte = donnees.decode("utf-8", "replace")
        for m in EMAIL.finditer(texte):
            domaine = m.group(1).lower()
            if not any(domaine == d or domaine.endswith("." + d) for d in DOMAINES_PERMIS):
                problemes.append(f"{chemin} : adresse e-mail « …@{m.group(1)} »")
        bas = texte.lower()
        problemes += [f"{chemin} : mot interdit n° {i + 1} de mots_interdits.txt" for i, mot in enumerate(mots) if mot in bas]
    return problemes


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--cible", type=Path, default=CIBLE, help="dossier de la copie publique (un dépôt git)")
    p.add_argument("--pousser", action="store_true", help="envoyer la copie sur GitHub après l'avoir enregistrée")
    a = p.parse_args()

    if git("status", "--porcelain", "--untracked-files=no").strip():
        print("Attention : des changements ne sont pas enregistrés ; seul le dernier commit est copié.")
    version = re.search(r'__version__ = "([^"]+)"', git("show", "HEAD:src/lyrx2qlr/__init__.py")).group(1)
    sha = git("rev-parse", "--short", "HEAD").strip()

    publics = fichiers_publics()
    contenus = {f: git("show", f"HEAD:{f}", octets=True) for f in publics}
    problemes = controler(contenus)
    if problemes:
        print("Copie publique refusée :")
        print("\n".join("  - " + x for x in problemes))
        return 1

    cible = a.cible.resolve()
    if not (cible / ".git").is_dir():
        cible.mkdir(parents=True, exist_ok=True)
        git("init", "-q", "-b", "main", cwd=cible)
        git("remote", "add", "origin", ADRESSE, cwd=cible)
        print(f"Nouveau dépôt local : {cible} (origine {ADRESSE})")
    # On repart d'un dossier vide (hors .git) : un fichier retiré du dépôt de travail disparaît aussi ici
    for element in cible.iterdir():
        if element.name != ".git":
            shutil.rmtree(element) if element.is_dir() else element.unlink()
    for chemin, donnees in contenus.items():
        f = cible / chemin
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(donnees)

    git("add", "-A", cwd=cible)
    if not git("status", "--porcelain", cwd=cible).strip():
        print(f"Copie publique déjà à jour (v{version}, {sha}).")
    else:
        message = (f"Copie de lyrx_2_qlr v{version} ({sha})\n\n"
                   "Copie publique du code, sans historique ni symbologies de travail.\n")
        git("-c", "user.name=YoGoCH", "-c", "user.email=YoGoCH@users.noreply.github.com",
            "commit", "-q", "-m", message, cwd=cible)
        print(f"Copie enregistrée : v{version} ({sha}), {len(contenus)} fichiers, dans {cible}")
    if a.pousser:
        git("push", "-q", "origin", "main", cwd=cible)
        print(f"Envoyée sur {ADRESSE}")
    else:
        print("Pas encore envoyée : relancer avec --pousser.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
