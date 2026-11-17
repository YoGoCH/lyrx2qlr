"""Rapport de conversion : ce qui a été converti, approximé ou perdu.

Trois niveaux :
- « perte »          : un élément n'a pas pu être converti (il manque dans le résultat) ;
- « avertissement »  : converti de façon approchée, ou à vérifier ;
- « info »           : remarque sans effet sur le rendu (ex. propriété sans équivalent connue).
Chaque entrée dit où (chemin lisible) et, si possible, quoi faire (souvent : compléter un catalogue).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Optional

NIVEAUX = ("perte", "avertissement", "info")


@dataclass
class Entree:
    niveau: str
    ou: str
    message: str
    conseil: Optional[str] = None
    nombre: int = 1


@dataclass
class Rapport:
    fichier: str = ""
    sens: str = ""
    entrees: list[Entree] = field(default_factory=list)
    _index: dict = field(default_factory=dict, repr=False)

    def ajouter(self, niveau: str, ou: str, message: str, conseil: Optional[str] = None) -> None:
        """Ajoute une entrée ; les doublons (même niveau, même message) sont comptés et non répétés."""
        if niveau not in NIVEAUX:
            raise ValueError(f"niveau inconnu : {niveau}")
        cle = (niveau, message, conseil)
        if cle in self._index:
            self._index[cle].nombre += 1
            return
        entree = Entree(niveau, ou, message, conseil)
        self._index[cle] = entree
        self.entrees.append(entree)

    def perte(self, ou: str, message: str, conseil: Optional[str] = None) -> None:
        self.ajouter("perte", ou, message, conseil)

    def avertir(self, ou: str, message: str, conseil: Optional[str] = None) -> None:
        self.ajouter("avertissement", ou, message, conseil)

    def info(self, ou: str, message: str, conseil: Optional[str] = None) -> None:
        self.ajouter("info", ou, message, conseil)

    def compter(self, niveau: str) -> int:
        return sum(1 for e in self.entrees if e.niveau == niveau)

    @property
    def resume(self) -> str:
        p, a, i = (self.compter(n) for n in NIVEAUX)
        if not (p or a):
            return "Conversion complète."
        return f"{p} perte(s), {a} avertissement(s), {i} info(s)."

    def en_dict(self) -> dict:
        return {
            "fichier": self.fichier,
            "sens": self.sens,
            "resume": self.resume,
            "entrees": [asdict(e) for e in self.entrees],
        }

    def en_json(self) -> str:
        return json.dumps(self.en_dict(), ensure_ascii=False, indent=2)

    def en_texte(self) -> str:
        titres = {"perte": "NON CONVERTI", "avertissement": "À VÉRIFIER", "info": "INFO"}
        lignes = [f"Rapport de conversion — {self.fichier} ({self.sens})", self.resume]
        for niveau in NIVEAUX:
            choix = [e for e in self.entrees if e.niveau == niveau]
            if not choix:
                continue
            lignes.append("")
            lignes.append(f"{titres[niveau]} ({len(choix)})")
            for e in choix:
                fois = f" (×{e.nombre})" if e.nombre > 1 else ""
                lignes.append(f"  - {e.ou} : {e.message}{fois}")
                if e.conseil:
                    lignes.append(f"      → {e.conseil}")
        return "\n".join(lignes)
