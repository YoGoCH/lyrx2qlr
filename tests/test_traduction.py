"""Rapport en anglais : chaque phrase du code et des catalogues doit avoir sa traduction (catalogues/traduction_en.json)."""
import ast
import json
import re
from pathlib import Path

import pytest

from lyrx2qlr import api
from lyrx2qlr.rapport import Rapport
from lyrx2qlr.traduction import _table, traduire, traduire_lieu

RACINE = Path(__file__).resolve().parent.parent
PAQUET = RACINE / "src" / "lyrx2qlr"
TABLE = _table("en")
TROU = re.compile(r"\{(\d+)\}")


def _modele(noeud):
    """Texte d'un argument littéral, les parties variables d'une f-chaîne remplacées par « x »."""
    if isinstance(noeud, ast.Constant) and isinstance(noeud.value, str):
        return noeud.value
    if isinstance(noeud, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "x" for v in noeud.values)
    return None


def _phrases_du_code():
    for f in sorted(PAQUET.glob("*.py")):
        if f.name in ("rapport.py", "traduction.py", "catalogue.py"):
            continue
        for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("perte", "avertir", "info"):
                for i, arg in enumerate(n.args[:3]):
                    texte = _modele(arg)
                    if texte:
                        yield f"{f.name}:{n.lineno}", ("ou" if i == 0 else "phrase"), texte


def _phrases_des_catalogues():
    def parcourir(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k.startswith(("avertissement", "remarque")) and isinstance(v, str):
                    yield re.sub(r"\{\w+\}", "x", v)
                else:
                    yield from parcourir(v)
        elif isinstance(o, list):
            for v in o:
                yield from parcourir(v)
    for f in sorted((PAQUET / "catalogues").glob("*.json")):
        if not f.name.startswith("traduction"):
            yield from parcourir(json.loads(f.read_text(encoding="utf-8")))


@pytest.mark.parametrize("ou,quoi,texte", list(_phrases_du_code()))
def test_phrase_du_code_traduite(ou, quoi, texte):
    if quoi == "ou":
        assert all(TABLE.phrase(m, TABLE.lieux) or m.startswith("x") for m in texte.split(" > ")), f"{ou} : lieu sans traduction : {texte}"
    else:
        assert TABLE.phrase(texte, TABLE.messages) is not None, f"{ou} : ajouter dans traduction_en.json : {texte}"


def test_phrases_des_catalogues_traduites():
    manque = [t for t in _phrases_des_catalogues() if TABLE.phrase(t, TABLE.messages) is None]
    assert not manque, manque


def test_libelles_des_catalogues_traduits():
    rendus = json.loads((PAQUET / "catalogues" / "rendus.json").read_text(encoding="utf-8"))
    libelles = [v for partie in rendus["signaler_lyrx"].values() if isinstance(partie, dict) for k, v in partie.items() if not k.startswith("_")]
    libelles += [v for logiciel in rendus["non_pris_en_charge"].values() for v in logiciel.values()]
    assert not [x for x in libelles if x not in TABLE.mots]


def test_memes_parties_variables():
    donnees = json.loads((PAQUET / "catalogues" / "traduction_en.json").read_text(encoding="utf-8"))
    for partie in ("messages", "lieux"):
        for fr, en in donnees[partie].items():
            assert set(TROU.findall(fr)) == set(TROU.findall(en)), fr


def test_noms_de_l_utilisateur_gardes():
    assert traduire_lieu("Couche « surface » > classe « ligne » > couche 2", "en") == "Layer “surface” > class “ligne” > layer 2"
    assert traduire("Classe « Forêt » sans borne supérieure : ignorée.", "en") == "Class “Forêt” has no upper bound: ignored."
    assert traduire("{} : non converti.".format("Jointures de tables"), "en") == "Table joins: not converted."


def test_francais_inchange_et_inconnu_garde():
    assert traduire("Classe « A » sans borne supérieure : ignorée.", "fr") == "Classe « A » sans borne supérieure : ignorée."
    assert traduire("Phrase encore inconnue.", "en") == "Phrase encore inconnue."


def test_rapport_en_anglais():
    r = Rapport("a.qlr", "qgis → lyrx")
    r.perte("Couche « A »", "Diagrammes non convertis.")
    r.avertir("Couche « A » > rendu", "Classe « B » sans borne supérieure : ignorée.", "Vérifier la première classe dans QGIS.")
    texte = r.en_texte("en")
    assert "1 loss(es), 1 warning(s), 0 note(s)." in texte
    assert "NOT CONVERTED (1)\n  - Layer “A”: Diagrams not converted." in texte
    assert "→ Check the first class in QGIS." in texte
    assert r.en_texte() == r.en_texte("fr") and "NON CONVERTI" in r.en_texte()


def test_exemples_reels_entierement_traduits():
    manque = set()
    for f in sorted((RACINE / "exemples").rglob("*")):
        if f.suffix.lower() not in api.EXTENSIONS_ENTREE:
            continue
        for e in api.convertir(f.read_bytes(), f.name).rapport.entrees:
            for texte in (e.message, e.conseil):
                if texte and not texte.startswith("Conversion impossible") and TABLE.phrase(texte, TABLE.messages) is None:
                    manque.add(texte)
    assert not manque, sorted(manque)[:10]
