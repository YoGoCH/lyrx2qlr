"""Copie des fichiers .lyrx / .qlr d'un dossier de travail vers exemples/, en refusant tout fichier sensible.

    python outils/preparer_exemples.py DOSSIER_SOURCE [--dossier-cible exemples]

Un fichier est REFUSÉ s'il contient une chaîne de connexion à une base de données
(serveur, utilisateur, mot de passe chiffré), une adresse e-mail ou un chemin réseau.
Les doublons (même contenu) ne sont copiés qu'une fois. Rien n'est modifié dans la source.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
from pathlib import Path

MOTIFS_SENSIBLES = {
    "mot de passe": re.compile(r"PASSWORD|password=|pwd=", re.I),
    "serveur": re.compile(r"SERVER=|INSTANCE=|host=|dbname=", re.I),
    "utilisateur": re.compile(r"\bUSER=|user=", re.I),
    "base d'entreprise (SDE)": re.compile(r'"workspaceFactory"\s*:\s*"SDE"|providerKey="(postgres|oracle|mssql)"'),
    "adresse e-mail": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "chemin réseau": re.compile(r"\\\\\\\\[A-Za-z0-9_.-]+\\\\|\\\\\\\\[A-Za-z0-9_.-]+\\\\|(?<![:/])//[A-Za-z0-9_-]+/[A-Za-z]"),
    "dossier personnel": re.compile(r"[A-Za-z]:(\\\\+|/)Users(\\\\+|/)|/home/", re.I),
}


def sensible(texte: str) -> list[str]:
    return [nom for nom, motif in MOTIFS_SENSIBLES.items() if motif.search(texte)]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("source")
    p.add_argument("--dossier-cible", default=str(Path(__file__).resolve().parent.parent / "exemples"))
    a = p.parse_args()
    cible = Path(a.dossier_cible)
    vus: set[str] = set()
    copies = refus = doublons = 0
    for f in sorted(Path(a.source).rglob("*")):
        if f.suffix.lower() not in (".lyrx", ".qlr"):
            continue
        brut = f.read_bytes()
        empreinte = hashlib.sha256(brut).hexdigest()
        if empreinte in vus:
            doublons += 1
            continue
        vus.add(empreinte)
        texte = brut.decode("utf-8", errors="replace")
        raisons = sensible(texte)
        if raisons:
            refus += 1
            print(f"REFUSÉ ({', '.join(raisons)}) : {f.name}")
            continue
        dossier = cible / f.suffix.lower().lstrip(".")
        dossier.mkdir(parents=True, exist_ok=True)
        nom = f.name
        if (dossier / nom).exists():
            nom = f"{f.stem}_{empreinte[:6]}{f.suffix}"
        shutil.copyfile(f, dossier / nom)
        copies += 1
    print(f"{copies} copié(s), {refus} refusé(s), {doublons} doublon(s) ignoré(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
