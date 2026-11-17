"""Chemins vers une valeur, utilisés par les catalogues.

Dans un objet JSON (.lyrx) :  « a.b[0].c[type=CIMSolidFill].color »
  - « .clé »          : entrer dans une clé ;
  - « [0] »           : prendre l'élément numéro 0 d'une liste ;
  - « [type=X] »      : prendre le premier élément de la liste dont « type » vaut X.

Dans un élément XML (.qlr) :  « text-style/text-buffer@bufferSize »
  - « / » descend dans un sous-élément, « @ » désigne un attribut.

À l'écriture, les étapes manquantes sont créées. Un dictionnaire portant la clé
« _facultatif » dans un modèle est supprimé s'il n'a reçu aucune valeur.
"""
from __future__ import annotations

import re
# Contrôle de sécurité (B405) : éléments seulement ; la lecture passe par xml_sur.lire
import xml.etree.ElementTree as ET  # nosec B405
from typing import Any, Optional

_ETAPE = re.compile(r"([^.\[\]]+)|\[(\d+)\]|\[([A-Za-z_]+)=([^\]]*)\]")


def decouper(chemin: str) -> list[tuple]:
    etapes: list[tuple] = []
    for m in _ETAPE.finditer(chemin):
        if m.group(1) is not None:
            etapes.append(("cle", m.group(1)))
        elif m.group(2) is not None:
            etapes.append(("index", int(m.group(2))))
        else:
            etapes.append(("filtre", m.group(3), m.group(4)))
    return etapes


def lire(objet: Any, chemin: str) -> Any:
    """Valeur au bout du chemin, ou None si une étape manque."""
    courant = objet
    for etape in decouper(chemin):
        if courant is None:
            return None
        if etape[0] == "cle":
            if not isinstance(courant, dict):
                return None
            courant = courant.get(etape[1])
        elif etape[0] == "index":
            if not isinstance(courant, list) or etape[1] >= len(courant):
                return None
            courant = courant[etape[1]]
        else:
            if not isinstance(courant, list):
                return None
            courant = next((e for e in courant if isinstance(e, dict) and str(e.get(etape[1])) == etape[2]), None)
    return courant


def ecrire(objet: dict, chemin: str, valeur: Any) -> None:
    """Écrit la valeur au bout du chemin en créant ce qui manque."""
    etapes = decouper(chemin)
    courant: Any = objet
    for i, etape in enumerate(etapes):
        dernier = i == len(etapes) - 1
        suivante = None if dernier else etapes[i + 1]
        if isinstance(courant, dict):
            courant.pop("_facultatif", None)
        if etape[0] == "cle":
            if dernier:
                courant[etape[1]] = valeur
                return
            if courant.get(etape[1]) is None:
                courant[etape[1]] = [] if suivante[0] in ("index", "filtre") else {}
            courant = courant[etape[1]]
        elif etape[0] == "index":
            while len(courant) <= etape[1]:
                courant.append({})
            if dernier:
                courant[etape[1]] = valeur
                return
            courant = courant[etape[1]]
        else:
            trouve = next((e for e in courant if isinstance(e, dict) and str(e.get(etape[1])) == etape[2]), None)
            if trouve is None:
                trouve = {etape[1]: etape[2]}
                courant.append(trouve)
            if dernier:
                raise ValueError(f"chemin terminé par un filtre : {chemin}")
            courant = trouve
    if isinstance(courant, dict):
        courant.pop("_facultatif", None)


def nettoyer_facultatifs(objet: Any) -> Any:
    """Retire les dictionnaires de modèle restés « _facultatif » (sans valeur reçue)."""
    if isinstance(objet, dict):
        for cle in list(objet):
            v = objet[cle]
            if isinstance(v, dict) and v.get("_facultatif"):
                del objet[cle]
            else:
                nettoyer_facultatifs(v)
    elif isinstance(objet, list):
        objet[:] = [e for e in objet if not (isinstance(e, dict) and e.get("_facultatif"))]
        for e in objet:
            nettoyer_facultatifs(e)
    return objet


# --- XML ---------------------------------------------------------------------

def _xml_separer(chemin: str) -> tuple[list[str], Optional[str]]:
    if "@" in chemin:
        elements, attribut = chemin.split("@", 1)
    else:
        elements, attribut = chemin, None
    noms = [n for n in elements.split("/") if n]
    return noms, attribut


def xml_lire(element: ET.Element, chemin: str) -> Optional[str]:
    noms, attribut = _xml_separer(chemin)
    courant: Optional[ET.Element] = element
    for nom in noms:
        courant = courant.find(nom) if courant is not None else None
    if courant is None:
        return None
    if attribut is None:
        return courant.text
    return courant.get(attribut)


def xml_ecrire(element: ET.Element, chemin: str, valeur: str) -> None:
    noms, attribut = _xml_separer(chemin)
    courant = element
    for nom in noms:
        enfant = courant.find(nom)
        if enfant is None:
            enfant = ET.SubElement(courant, nom)
        courant = enfant
    if attribut is None:
        courant.text = valeur
    else:
        courant.set(attribut, valeur)
