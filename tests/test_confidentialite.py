"""Nettoyage avant envoi et colis de contribution (outil « Contribuer » de la page web).

Toutes les valeurs ci-dessous sont inventées."""
import io
import json
import zipfile
from pathlib import Path

import pytest

from lyrx2qlr.confidentialite import nettoyer, reste_sensible
from lyrx2qlr.contribution import ErreurColis, preparer
from conftest import avec_exemples_reels

EXEMPLES = Path(__file__).resolve().parent.parent / "exemples"


def test_chaine_arcgis():
    texte = ('"workspaceConnectionString" : "ENCRYPTED_PASSWORD=00022e684d4b;SERVER=geo-srv;INSTANCE=sde:oracle:geo-srv;'
             'DBCLIENT=oracle;DATABASE=Database Connections\\\\geo.sde;USER=jdupont;VERSION=sde.DEFAULT"')
    propre, retraits = nettoyer(texte)
    for secret in ("00022e684d4b", "geo-srv", "jdupont"):
        assert secret not in propre
    assert "DBCLIENT=oracle" in propre and "VERSION=sde.DEFAULT" in propre
    assert retraits == {"mot de passe, jeton ou clé": 1, "nom de serveur": 2, "nom d'utilisateur": 1}
    json.loads("{" + propre + "}")  # reste un JSON valide
    assert "DATABASE=base-anonyme" in nettoyer("DATABASE=GEODWH;USER=x")[0]


@pytest.mark.parametrize("source", ["DATABASE=.", "DATABASE=.\\\\", "DATABASE=D:\\\\donnees\\\\vd.gdb",
                                    "dbname='./couches.gpkg'", "DATABASE=Database Connections\\\\geo.sde"])
def test_chemins_de_donnees_gardes(source):
    """Une base « fichier » est un chemin utile à la conversion : on la garde."""
    assert nettoyer(source) == (source, {})


def test_adresse_qgis():
    texte = ("<datasource>dbname='cadastre' host=10.0.0.9 port=5432 user='marie' password='s3cr€t word' "
             "sslmode=disable key='gid' table=\"public\".\"parcelles\" (geom)</datasource>")
    propre, retraits = nettoyer(texte)
    assert "s3cr" not in propre and "marie" not in propre and "10.0.0.9" not in propre and "cadastre" not in propre
    assert "password='RETIRE'" in propre and "port=5432" in propre and '"public"."parcelles"' in propre
    assert retraits["mot de passe, jeton ou clé"] == 1


def test_echappements_xml_et_url():
    propre, retraits = nettoyer('<Option value="user=&apos;bob&apos; password=&apos;x1&apos;"/>'
                                '<a href="https://anna:pw@tuiles.exemple.ch/wms?TOKEN=abc123&amp;LAYERS=x"/>')
    assert "bob" not in propre and "x1" not in propre and "anna" not in propre and "pw@" not in propre
    assert "abc123" not in propre and "LAYERS=x" in propre


def test_email_dossiers_et_reseau():
    texte = ('"C:\\\\Users\\\\jean.martin\\\\Documents\\\\carte.png" contact: jean.martin@exemple.ch '
             'C:\\Users\\Paul\\x.svg /home/lea/ico.svg \\\\\\\\nas-01\\\\partage\\\\a.png \\\\nas-02\\b.png "C:\\\\data\\\\x"')
    propre, retraits = nettoyer(texte)
    for perso in ("jean.martin", "Paul", "lea", "nas-01", "nas-02"):
        assert perso not in propre
    assert "C:\\\\data\\\\x" in propre  # un chemin ordinaire ne bouge pas
    assert retraits == {"adresse e-mail": 1, "dossier personnel": 3, "serveur d'un chemin réseau": 2}


def test_rien_a_retirer_et_idempotent():
    texte = '{"type": "CIMSolidFill", "color": {"values": [255, 0, 0, 100]}, "host": "rien"}'
    assert nettoyer(texte) == (texte, {})
    une_fois = nettoyer("PASSWORD=abc;USER=x;SERVER=y")[0]
    assert nettoyer(une_fois) == (une_fois, {})
    assert reste_sensible(une_fois) == []


@pytest.mark.parametrize("fichier", sorted((EXEMPLES / "lyrx").glob("*.lyrx"))[:15] + sorted((EXEMPLES / "qlr").glob("*.qlr"))[:15],
                         ids=lambda p: p.name)
def test_exemples_restent_lisibles(fichier):
    """Les exemples (déjà anonymisés) passent le nettoyage sans perdre leur validité."""
    propre, _ = nettoyer(fichier.read_text(encoding="utf-8-sig"))
    if fichier.suffix == ".lyrx":
        json.loads(propre)
    else:
        import xml.etree.ElementTree as ET
        ET.fromstring(propre)


def _lire(colis: bytes) -> tuple[dict, dict]:
    with zipfile.ZipFile(io.BytesIO(colis)) as z:
        return json.loads(z.read("contribution.json")), {n: z.read(n) for n in z.namelist()}


@avec_exemples_reels
def test_colis_a_corriger():
    lyrx = next(iter(sorted((EXEMPLES / "lyrx").glob("*.lyrx"))))
    donnees = lyrx.read_bytes().replace(b'"name"', b'"description" : "PASSWORD=pw123;USER=yo",\n  "name"', 1)
    colis, apercu = preparer({"type": "a_corriger", "problemes": ["couleurs", "inconnu"],
                              "commentaire": "Les couleurs sont fausses, écrivez-moi à moi@exemple.ch",
                              "licence": "corpus", "contact": "moi@exemple.ch", "logiciels": {"qgis": "3.40"}},
                             [("C:\\Users\\moi\\" + lyrx.name, donnees)])
    infos, contenu = _lire(colis)
    assert infos["type"] == "a_corriger" and infos["problemes"] == ["couleurs"] and infos["licence"] == "corpus"
    assert "moi@exemple.ch" not in infos["commentaire"] and infos["contact"] == "moi@exemple.ch"
    assert infos["fichiers"][0]["nom"] == lyrx.name and infos["fichiers"][0]["role"] == "depart"
    assert b"pw123" not in contenu[f"fichiers/{lyrx.name}"]
    assert infos["conversion"]["reussi"] and any(n.startswith("notre_resultat/") for n in contenu)
    assert f"rapports/{lyrx.name}.txt" in contenu
    assert apercu["fichiers"][0]["retraits"]["mot de passe, jeton ou clé"] == 1
    assert apercu["retraits_commentaire"] == {"adresse e-mail": 1}


@avec_exemples_reels
def test_colis_paire_depart_choisi():
    lyrx = sorted((EXEMPLES / "lyrx").glob("*.lyrx"))[0]
    qlr = sorted((EXEMPLES / "qlr").glob("*.qlr"))[0]
    colis, _ = preparer({"type": "paire", "depart": qlr.name},
                        [(lyrx.name, lyrx.read_bytes()), (qlr.name, qlr.read_bytes())])
    infos, _ = _lire(colis)
    assert {f["nom"]: f["role"] for f in infos["fichiers"]} == {lyrx.name: "attendu", qlr.name: "depart"}
    assert infos["conversion"]["entree"] == qlr.name


@pytest.mark.parametrize("infos, fichiers", [
    ({"type": "?"}, []),
    ({"type": "bon"}, []),
    ({"type": "paire"}, [("a.lyrx", b"{}")]),
    ({"type": "remarque"}, []),
    ({"type": "a_corriger"}, [("a.lyrx", b"{}")]),
    ({"type": "bon"}, [("a.zip", b"PK")]),
    ({"type": "bon"}, [("a.lyrx", b"\xff\xfe\x00")]),
    ({"type": "remarque", "commentaire": "x", "contact": "pas une adresse"}, []),
])
def test_colis_refuse(infos, fichiers):
    with pytest.raises(ErreurColis):
        preparer(infos, fichiers)


def test_colis_fichier_illisible_ne_plante_pas():
    colis, apercu = preparer({"type": "a_corriger", "commentaire": "ne s'ouvre pas"}, [("casse.lyrx", b"{ pas du json")])
    infos, _ = _lire(colis)
    assert infos["conversion"]["reussi"] is False and apercu["conversion"]["erreur"]


def test_expressions_intactes():
    """Les barres obliques inverses des expressions (\b, \n…) ne sont pas des chemins réseau."""
    for texte in (r'{"motif": "\bvbNewLine\b|\bvbCrLf\b", "remplace": "\n"}',
                  '<rule filter="regexp_match(&quot;NOM&quot;, \'\\d+\\s\')"/>'):
        assert nettoyer(texte) == (texte, {})
