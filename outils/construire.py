"""Prépare le cœur pour l'application web et pour l'extension QGIS.

    python outils/construire.py web        → web/lyrx2qlr.zip (le cœur, chargé par Pyodide dans le navigateur)
    python outils/construire.py extension  → copie du cœur dans qgis_plugin/lyrx2qlr_qgis/coeur/
                                             + dist/lyrx2qlr_qgis-<version>.zip (à installer dans QGIS)
    python outils/construire.py tout       → les deux

Le cœur (src/lyrx2qlr) reste la seule source : ces copies sont produites, jamais modifiées à la main
(elles sont ignorées par git).
"""
from __future__ import annotations

import hashlib
import re
import shutil
import sys
import zipfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
COEUR = RACINE / "src" / "lyrx2qlr"
EXTENSION = RACINE / "qgis_plugin" / "lyrx2qlr_qgis"


def _fichiers_coeur():
    for f in sorted(COEUR.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts and f.suffix not in (".pyc",):
            yield f


def version() -> str:
    texte = (COEUR / "__init__.py").read_text(encoding="utf-8")
    return re.search(r'__version__\s*=\s*"([^"]+)"', texte).group(1)


def construire_web() -> Path:
    cible = RACINE / "web" / "lyrx2qlr.zip"
    with zipfile.ZipFile(cible, "w", zipfile.ZIP_DEFLATED) as z:
        for f in _fichiers_coeur():
            z.write(f, Path("lyrx2qlr") / f.relative_to(COEUR))
    print(f"Application web : {cible.relative_to(RACINE)} ({cible.stat().st_size // 1024} Ko, version {version()})")
    estampiller_page()
    estampiller_hors_ligne()
    return cible


def estampiller_hors_ligne() -> None:
    """Version dans web/sw.js : une nouvelle version remplace la copie hors ligne gardée par les navigateurs."""
    sw = RACINE / "web" / "sw.js"
    texte = sw.read_text(encoding="utf-8")
    nouveau = re.sub(r'const VERSION = "[^"]*";', f'const VERSION = "{version()}";', texte, count=1)
    if nouveau != texte:
        sw.write_text(nouveau, encoding="utf-8", newline="\n")
        print(f"Usage hors ligne : web/sw.js passe en version {version()}")


def estampiller_page() -> None:
    """Ajoute à chaque feuille de style et script local de web/index.html une empreinte de son contenu
    (« style.css?v=1a2b3c4d »). Le serveur n'envoie pas de consigne de cache : sans cela, un navigateur
    peut garder un ancien style.css avec la nouvelle page, et un bouton semble ne rien faire."""
    page = RACINE / "web" / "index.html"
    texte = page.read_text(encoding="utf-8")

    def empreinte(m: re.Match) -> str:
        fichier = RACINE / "web" / m.group(2)
        if not fichier.is_file():
            return m.group(0)
        v = hashlib.sha256(fichier.read_bytes()).hexdigest()[:8]
        return f'{m.group(1)}="{m.group(2)}?v={v}"'

    nouveau = re.sub(r'\b(href|src)="([\w.-]+\.(?:css|js))(?:\?v=\w+)?"', empreinte, texte)
    if nouveau != texte:
        page.write_text(nouveau, encoding="utf-8", newline="\n")
        print("Page web : empreintes des fichiers mises à jour dans web/index.html")


def construire_extension() -> Path:
    coeur = EXTENSION / "coeur"
    if coeur.exists():
        shutil.rmtree(coeur)
    (coeur / "lyrx2qlr").mkdir(parents=True)
    (coeur / "__init__.py").write_text("# Copie du cœur produite par outils/construire.py : ne pas modifier.\n", encoding="utf-8")
    for f in _fichiers_coeur():
        dest = coeur / "lyrx2qlr" / f.relative_to(COEUR)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest)
    # La version de l'extension suit celle du cœur.
    meta = EXTENSION / "metadata.txt"
    meta.write_text(re.sub(r"(?m)^version=.*$", f"version={version()}", meta.read_text(encoding="utf-8")), encoding="utf-8")
    dist = RACINE / "dist"
    dist.mkdir(exist_ok=True)
    cible = dist / f"lyrx2qlr_qgis-{version()}.zip"
    with zipfile.ZipFile(cible, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(EXTENSION.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts:
                z.write(f, Path(EXTENSION.name) / f.relative_to(EXTENSION))
        z.write(RACINE / "LICENSE", Path(EXTENSION.name) / "LICENSE")  # exigé par plugins.qgis.org
    print(f"Extension QGIS : {cible.relative_to(RACINE)} (version {version()})")
    return cible


def main(args: list[str]) -> int:
    quoi = args[0] if args else "tout"
    if quoi not in ("web", "extension", "tout"):
        print(__doc__)
        return 2
    if quoi in ("web", "tout"):
        construire_web()
    if quoi in ("extension", "tout"):
        construire_extension()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
