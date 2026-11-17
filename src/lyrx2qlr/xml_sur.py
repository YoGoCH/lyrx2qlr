"""Lecture prudente d'un fichier XML venu de l'utilisateur (.qlr, .qml).

Les attaques connues contre les lecteurs XML (« milliard de rires », entités externes qui lisent
un fichier du poste) passent toutes par des déclarations d'entités dans le DOCTYPE. Un vrai .qlr
ou .qml n'en a jamais : son DOCTYPE est une simple ligne (« <!DOCTYPE qgis-layer-definition> »).
On refuse donc tout DOCTYPE qui déclare quelque chose (entre crochets) et toute déclaration
d'entité, avant de lire. Bibliothèque standard seulement : le cœur doit tourner dans Pyodide et
dans QGIS, sans le paquet defusedxml.
"""
from __future__ import annotations

import re
# Contrôle de sécurité (B405) : lecture protégée par lire() ci-dessous
import xml.etree.ElementTree as ET  # nosec B405

# Début du document jusqu'au premier élément : c'est là que se trouve le DOCTYPE
_PREMIER_ELEMENT = re.compile(r"<[A-Za-z_:]")
_DECLARATION = re.compile(r"<!ENTITY|<!DOCTYPE[^>]*\[", re.I)


class XmlRefuse(ValueError):
    """Le fichier contient des déclarations XML qu'un fichier QGIS n'a jamais."""


def _texte(donnees: bytes) -> str:
    if donnees[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return donnees.decode("utf-16", errors="ignore")
    return donnees.decode("utf-8", errors="ignore")


def verifier(donnees: bytes) -> None:
    """Lève XmlRefuse si le début du document déclare des entités ou un DOCTYPE à déclarations."""
    texte = _texte(donnees)
    debut = _PREMIER_ELEMENT.search(texte)
    prologue = texte[:debut.start()] if debut else texte
    if _DECLARATION.search(prologue):
        raise XmlRefuse("fichier XML refusé : il déclare des entités (DOCTYPE avec déclarations), "
                        "ce qu'un fichier QGIS ne fait jamais")


def lire(donnees: bytes | str) -> ET.Element:
    """Élément racine du document, après vérification (voir verifier)."""
    if isinstance(donnees, str):
        donnees = donnees.encode("utf-8")
    verifier(donnees)
    # Contrôle de sécurité (B314) : entités et DOCTYPE à déclarations refusés juste avant
    return ET.fromstring(donnees)  # nosec B314
