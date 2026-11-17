"""Outils communs aux tests."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "src"))

from lyrx2qlr.catalogue import Catalogue  # noqa: E402
from lyrx2qlr.modele import en_dict  # noqa: E402

EXEMPLES = RACINE / "exemples"
EXEMPLES_LYRX = sorted((EXEMPLES / "lyrx").glob("*.lyrx")) + sorted((EXEMPLES / "fabriques").glob("*.lyrx"))
EXEMPLES_QLR = sorted((EXEMPLES / "qlr").glob("*.qlr")) + sorted((EXEMPLES / "fabriques").glob("*.qlr"))

# La copie publique du code (outils/publier_code.py) n'a pas les symbologies réelles de exemples/lyrx et
# exemples/qlr : les tests qui en ont besoin sont alors sautés.
EXEMPLES_REELS = bool(sorted((EXEMPLES / "lyrx").glob("*.lyrx")))
avec_exemples_reels = pytest.mark.skipif(not EXEMPLES_REELS, reason="symbologies réelles absentes (copie publique du code)")


@pytest.fixture(scope="session")
def catalogue() -> Catalogue:
    return Catalogue.charger()


@pytest.fixture(scope="session")
def catalogue_sans_substitution() -> Catalogue:
    """Catalogue sans remplacement des polices ESRI : l'aller-retour doit alors être exact."""
    cat = Catalogue.charger()
    d = copy.deepcopy(cat.d)
    d["polices"]["substitutions"] = []
    return Catalogue(d)


def _normaliser(x, cle=None):
    if isinstance(x, float):
        return round(x, 2)
    if isinstance(x, dict):
        return {k: _normaliser(v, k) for k, v in x.items() if k not in ("chemin_qgis", "fournisseur_qgis")}
    if isinstance(x, list):
        return [_normaliser(v) for v in x]
    return x


def differences(a, b, chemin="") -> list[str]:
    """Différences lisibles entre deux structures (modèle neutre en dictionnaires)."""
    if isinstance(a, dict) and isinstance(b, dict):
        diffs = []
        for k in sorted(set(a) | set(b)):
            if k not in a:
                diffs.append(f"{chemin}.{k} : absent avant, {b[k]!r} après")
            elif k not in b:
                diffs.append(f"{chemin}.{k} : {a[k]!r} avant, absent après")
            else:
                diffs += differences(a[k], b[k], f"{chemin}.{k}")
        return diffs
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{chemin} : {len(a)} éléments avant, {len(b)} après"]
        diffs = []
        for i, (x, y) in enumerate(zip(a, b)):
            diffs += differences(x, y, f"{chemin}[{i}]")
        return diffs
    if isinstance(a, float) or isinstance(b, float):
        try:
            if abs(float(a) - float(b)) <= max(0.02, abs(float(a)) * 1e-3):
                return []
        except (TypeError, ValueError):
            pass
    return [] if a == b else [f"{chemin} : {a!r} avant, {b!r} après"]


def _preparer(doc) -> dict:
    d = _normaliser(en_dict(doc))
    d.pop("format_source", None)
    d.pop("version_source", None)
    for c in d["couches"]:
        if len(c["etiquettes"]) == 1 and not c["etiquettes"][0]["filtre"]:
            c["etiquettes"][0]["nom"] = ""  # l'étiquetage « simple » de QGIS n'a pas de nom de classe
    return d


def comparer_documents(doc_a, doc_b) -> list[str]:
    return differences(_preparer(doc_a), _preparer(doc_b))


_RESULTAT = {}


def pytest_sessionfinish(session, exitstatus):
    _RESULTAT["code"] = int(exitstatus)


def pytest_unconfigure(config):
    """Sur GitHub (variable CI), QGIS plante souvent quand Python s'arrête dans un conteneur (code 139),
    après des tests réussis. Une fois QGIS chargé, on sort donc directement avec le vrai résultat des
    tests, après le résumé de pytest."""
    import os
    if os.environ.get("CI") and "qgis.core" in sys.modules and "code" in _RESULTAT:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(_RESULTAT["code"])
