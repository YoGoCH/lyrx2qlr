"""Traduction du rapport de conversion (le cœur écrit en français ; l'anglais est fait à l'affichage).

Les phrases sont dans catalogues/traduction_<langue>.json : modèle français → modèle traduit, les parties
variables notées {0}, {1}… Une partie variable est elle-même traduite si elle est connue (« mots », ou une
phrase entière). Une phrase inconnue reste en français : rien n'est perdu.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

LANGUES = ("fr", "en")
_DOSSIER = Path(__file__).parent / "catalogues"
_TROU = re.compile(r"\{(\d+)\}")


def _motif(modele: str) -> tuple[re.Pattern, set[int]]:
    """« Classe « {0} » ignorée. » → expression qui retrouve les parties variables, et les numéros des parties
    entre guillemets (noms choisis par l'utilisateur : jamais traduits)."""
    morceaux, fin, cites = [], 0, set()
    for m in _TROU.finditer(modele):
        if modele[:m.start()].endswith("« "):
            cites.add(int(m.group(1)))
        morceaux.append(re.escape(modele[fin:m.start()]))
        morceaux.append(f"(?P<t{m.group(1)}>.*?)")
        fin = m.end()
    morceaux.append(re.escape(modele[fin:]))
    return re.compile("".join(morceaux), re.DOTALL), cites


class _Table:
    def __init__(self, donnees: dict):
        def preparer(paires: dict) -> list:
            # les modèles au texte fixe le plus long d'abord : « {0} : non converti. » ne doit pas tout prendre
            liste = [(*_motif(fr), autre, len(_TROU.sub("", fr))) for fr, autre in paires.items()]
            return sorted(liste, key=lambda x: -x[3])
        self.exacts = {fr: autre for fr, autre in donnees.get("messages", {}).items() if not _TROU.search(fr)}
        self.messages = preparer({fr: a for fr, a in donnees.get("messages", {}).items() if _TROU.search(fr)})
        self.lieux = preparer(donnees.get("lieux", {}))
        self.mots = donnees.get("mots", {})

    def phrase(self, texte: str, liste: list) -> str | None:
        if texte in self.exacts:
            return self.exacts[texte]
        for motif, cites, autre, _ in liste:
            m = motif.fullmatch(texte)
            if m:
                valeurs = {}
                for k, v in m.groupdict().items():
                    n = int(k[1:])
                    if n not in cites:
                        valeurs[n] = self.partie(v)
                    elif liste is self.messages:  # entre guillemets : seulement les mots du logiciel (« ligne », « Carte de chaleur »)
                        valeurs[n] = self.mots.get(v, v)
                    else:  # nom donné par l'utilisateur dans le chemin « où » : jamais traduit
                        valeurs[n] = v
                return _TROU.sub(lambda t: valeurs.get(int(t.group(1)), t.group(0)), autre)
        return None

    def partie(self, texte: str) -> str:
        """Partie variable : traduite si c'est un mot ou une phrase connue, sinon gardée telle quelle."""
        coeur = texte.strip()
        if not coeur:
            return texte
        traduit = self.mots.get(coeur) or self.phrase(coeur, self.messages)
        return texte.replace(coeur, traduit, 1) if traduit else texte


@lru_cache(maxsize=None)
def _table(langue: str) -> _Table | None:
    chemin = _DOSSIER / f"traduction_{langue}.json"
    if langue == "fr" or not chemin.exists():
        return None
    with open(chemin, encoding="utf-8") as f:
        return _Table(json.load(f))


def langue_connue(langue: str | None) -> str:
    langue = (langue or "fr").lower()[:2]
    return langue if langue in LANGUES else "en"


def traduire(texte: str | None, langue: str = "fr") -> str | None:
    """Traduit une phrase du rapport (message ou conseil) ; inchangée si la langue est le français ou si elle est inconnue."""
    table = _table(langue_connue(langue))
    if table is None or not texte:
        return texte
    return table.phrase(texte, table.messages) or texte


def traduire_lieu(ou: str, langue: str = "fr") -> str:
    """Traduit le chemin « où » (« Couche « A » > classe « B » »), morceau par morceau."""
    table = _table(langue_connue(langue))
    if table is None or not ou:
        return ou
    return " > ".join(table.phrase(morceau, table.lieux) or morceau for morceau in ou.split(" > "))
