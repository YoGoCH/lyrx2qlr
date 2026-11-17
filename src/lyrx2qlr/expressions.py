"""Traduction des expressions (étiquettes, filtres) à l'aide de catalogues/expressions.json.

Le langage neutre est celui des expressions QGIS : champs entre guillemets doubles
("CHAMP"), textes entre apostrophes ('texte'), concaténation avec ||.
Les textes littéraux sont mis de côté avant d'appliquer les règles, puis remis
avec les guillemets du langage cible : les règles ne les abîment jamais.
"""
from __future__ import annotations

import re
from typing import Optional

from .rapport import Rapport


def _proteger(texte: str, guillemets: str) -> tuple[str, list[str]]:
    """Remplace chaque texte littéral par un repère \x00N\x00 ; renvoie le texte et la liste des littéraux."""
    litteraux: list[str] = []
    resultat = []
    i = 0
    while i < len(texte):
        c = texte[i]
        if c in guillemets:
            j = i + 1
            contenu = []
            while j < len(texte):
                if texte[j] == c:
                    if j + 1 < len(texte) and texte[j + 1] == c:  # guillemet doublé = échappé
                        contenu.append(c)
                        j += 2
                        continue
                    break
                contenu.append(texte[j])
                j += 1
            litteraux.append("".join(contenu))
            resultat.append(f"\x00{len(litteraux) - 1}\x00")
            i = j + 1
        else:
            resultat.append(c)
            i += 1
    return "".join(resultat), litteraux


def _restaurer(texte: str, litteraux: list[str], guillemet: str) -> str:
    def remettre(m: re.Match) -> str:
        contenu = litteraux[int(m.group(1))]
        return guillemet + contenu.replace(guillemet, guillemet * 2) + guillemet
    return re.sub(r"\x00(\d+)\x00", remettre, texte)


class Traducteur:
    def __init__(self, catalogue, rapport: Rapport):
        self.cat = catalogue.expressions
        self.rapport = rapport

    def vers_qgis(self, texte: str, moteur: str, ou: str) -> Optional[str]:
        """Expression ArcGIS (moteur VBScript, Python, Arcade ou SQL) → expression QGIS."""
        if texte is None or texte.strip() == "":
            return None
        regles = self.cat["vers_qgis"].get(moteur)
        if regles is None:
            self.rapport.avertir(ou, f"Langage d'expression « {moteur} » inconnu : expression recopiée telle quelle ({texte!r}).",
                                 "Ajouter le langage dans catalogues/expressions.json.")
            return texte
        if regles.get("simple_champ"):
            m = re.match(regles["simple_champ"], texte)
            if m:
                champ = next(g for g in m.groups() if g)
                return '"' + champ.replace('"', '""') + '"'
        protege, litteraux = _proteger(texte, regles.get("chaines", "\""))
        for r in regles.get("regles", []):
            protege = re.sub(r["motif"], r["remplace"], protege)
        resultat = _restaurer(protege, litteraux, "'").strip()
        douteux = [m for m in regles.get("a_verifier", []) if re.search(m, texte)]
        if douteux:
            self.rapport.avertir(ou, f"Expression {moteur} complexe, traduction à vérifier : {texte!r} → {resultat!r}.",
                                 "Corriger l'expression dans QGIS, ou ajouter une règle dans catalogues/expressions.json.")
        elif moteur != "SQL":
            self.rapport.info(ou, f"Expression {moteur} traduite : {texte!r} → {resultat!r}.")
        return resultat

    def depuis_qgis(self, expression: str, cible: str, ou: str) -> tuple[str, str]:
        """Expression QGIS → (expression dans le langage cible, nom du langage)."""
        regles = self.cat["depuis_qgis"][cible]
        m = re.fullmatch(r'\s*"((?:[^"]|"")+)"\s*', expression)
        if m and "champ_simple" in regles:
            champ = m.group(1).replace('""', '"')
            modele = regles["champ_simple"] if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", champ) else regles["champ_simple_special"]
            return modele.format(champ=champ), cible
        protege, litteraux = _proteger(expression, regles.get("chaines_qgis", "'"))
        # les noms de champs QGIS entre guillemets doubles ne sont pas des textes : on les a laissés dans « protege »
        for r in regles.get("regles", []):
            protege = re.sub(r["motif"], r["remplace"], protege)
        resultat = _restaurer(protege, litteraux, regles.get("chaine_sortie", "'")).strip()
        douteux = [m for m in regles.get("a_verifier", []) if re.search(m, expression)]
        if douteux:
            self.rapport.avertir(ou, f"Expression QGIS complexe, traduction en {cible} à vérifier : {expression!r} → {resultat!r}.",
                                 "Corriger l'expression dans ArcGIS Pro, ou ajouter une règle dans catalogues/expressions.json.")
        elif cible != "SQL":
            self.rapport.info(ou, f"Expression QGIS traduite en {cible} : {expression!r} → {resultat!r}.")
        return resultat, cible
