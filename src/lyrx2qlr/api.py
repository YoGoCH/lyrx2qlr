"""Fonctions d'usage : ce que l'application web, l'extension QGIS et la ligne de commande appellent.

Le sens de conversion se déduit de l'extension : .lyrx → .qlr ; .qlr (ou .qml) → .lyrx.
Aucune de ces fonctions n'a besoin de QGIS ni d'ArcGIS : seulement Python.
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from .catalogue import Catalogue, catalogue_defaut
from .ecriture_lyrx import EcrivainLyrx
from .ecriture_qlr import EcrivainQlr
from .lecture_lyrx import LecteurLyrx
from .lecture_qlr import LecteurQlr
from .modele import Document
from .sources import anonymiser
from .rapport import Rapport

EXTENSIONS_ENTREE = {".lyrx": ".qlr", ".qlr": ".lyrx", ".qml": ".lyrx"}


@dataclass
class Resultat:
    nom_entree: str
    nom_sortie: Optional[str]
    donnees: Optional[bytes]
    rapport: Rapport
    erreur: Optional[str] = None

    @property
    def reussi(self) -> bool:
        return self.erreur is None and self.donnees is not None


def sens_conversion(nom_fichier: str) -> tuple[str, str]:
    ext = Path(nom_fichier).suffix.lower()
    if ext not in EXTENSIONS_ENTREE:
        raise ValueError(f"Extension « {ext} » non prise en charge (attendu : .lyrx, .qlr ou .qml).")
    return ext, EXTENSIONS_ENTREE[ext]


def lire(donnees: bytes, nom_fichier: str, catalogue: Optional[Catalogue] = None,
         rapport: Optional[Rapport] = None) -> Document:
    """Lit un fichier (.lyrx, .qlr, .qml) vers le modèle neutre."""
    cat = catalogue or catalogue_defaut()
    rapport = rapport if rapport is not None else Rapport(fichier=nom_fichier)
    ext, _ = sens_conversion(nom_fichier)
    lecteur = LecteurLyrx(cat, rapport) if ext == ".lyrx" else LecteurQlr(cat, rapport)
    return lecteur.lire(donnees)


def ecrire(doc: Document, extension: str, catalogue: Optional[Catalogue] = None,
           rapport: Optional[Rapport] = None) -> bytes:
    cat = catalogue or catalogue_defaut()
    rapport = rapport if rapport is not None else Rapport()
    ecrivain = EcrivainQlr(cat, rapport) if extension == ".qlr" else EcrivainLyrx(cat, rapport)
    return ecrivain.ecrire(doc)


def convertir(donnees: bytes, nom_fichier: str, catalogue: Optional[Catalogue] = None,
              garder_source: bool = True) -> Resultat:
    """Convertit le contenu d'un fichier. Ne lève pas d'exception : l'erreur éventuelle est dans le résultat.

    garder_source : coche « Garder la source de données ». Vraie, le fichier produit pointe sur les
    mêmes données (dossier, GeoPackage, base Oracle…, sans mot de passe). Fausse, la source se
    réduit au nom du jeu de données, à reconnecter."""
    rapport = Rapport(fichier=nom_fichier)
    try:
        ext, ext_sortie = sens_conversion(nom_fichier)
        rapport.sens = f"{ext} → {ext_sortie}"
        doc = lire(donnees, nom_fichier, catalogue, rapport)
        if not doc.couches:
            # Un fichier sans couche ne s'ouvre pas dans ArcGIS (relecture du lot 2) : on n'en produit pas.
            erreur = "aucune couche d'entités vectorielles à convertir (couches raster ou autres non prises en charge)"
            return Resultat(nom_fichier, None, None, rapport, erreur=erreur)
        if not garder_source:
            for couche in doc.couches:
                anonymiser(couche)
            rapport.info("fichier", "Source de données non gardée (coche « Garder la source de données » décochée) : à reconnecter.")
        sortie = ecrire(doc, ext_sortie, catalogue, rapport)
        return Resultat(nom_fichier, str(Path(nom_fichier).with_suffix(ext_sortie).name), sortie, rapport)
    except Exception as e:  # le rapport doit toujours revenir à l'utilisateur
        rapport.perte("fichier", f"Conversion impossible : {e}")
        return Resultat(nom_fichier, None, None, rapport, erreur=str(e))


def convertir_fichier(chemin: str | Path, dossier_sortie: Optional[str | Path] = None,
                      catalogue: Optional[Catalogue] = None, garder_source: bool = True) -> Resultat:
    """Convertit un fichier sur le disque ; écrit le résultat à côté (ou dans dossier_sortie)."""
    chemin = Path(chemin)
    resultat = convertir(chemin.read_bytes(), chemin.name, catalogue, garder_source)
    if resultat.reussi:
        dossier = Path(dossier_sortie) if dossier_sortie else chemin.parent
        dossier.mkdir(parents=True, exist_ok=True)
        (dossier / resultat.nom_sortie).write_bytes(resultat.donnees)
    return resultat


def lister_fichiers(entrees: Iterable[str | Path]) -> list[Path]:
    """Fichiers convertibles parmi des fichiers et des dossiers (parcourus avec leurs sous-dossiers)."""
    fichiers: list[Path] = []
    for e in entrees:
        e = Path(e)
        if e.is_dir():
            fichiers += sorted(p for p in e.rglob("*") if p.suffix.lower() in EXTENSIONS_ENTREE)
        elif e.suffix.lower() in EXTENSIONS_ENTREE:
            fichiers.append(e)
    return fichiers


def convertir_lot(fichiers: Iterable[tuple[str, bytes]], catalogue: Optional[Catalogue] = None,
                  garder_source: bool = True, langue: str = "fr") -> tuple[bytes, list[Resultat]]:
    """Convertit plusieurs fichiers (nom, contenu) ; renvoie une archive ZIP avec les résultats et les rapports.

    langue : langue des rapports de l'archive (« fr » ou « en »)."""
    resultats = [convertir(donnees, nom, catalogue, garder_source) for nom, donnees in fichiers]
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        resume = []
        for r in resultats:
            if r.reussi:
                z.writestr(r.nom_sortie, r.donnees)
            base = Path(r.nom_entree).stem
            z.writestr(f"rapports/{base}.txt", r.rapport.en_texte(langue))
            echec = "FAILED" if langue == "en" else "ÉCHEC"
            resume.append(f"{r.nom_entree} → {r.nom_sortie or echec} : {r.rapport.resume_en(langue)}")
        z.writestr("rapports/_resume.txt", "\n".join(resume) + "\n")
    return tampon.getvalue(), resultats
