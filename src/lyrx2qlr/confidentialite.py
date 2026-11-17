"""Nettoyage des fichiers avant qu'ils quittent le poste (outil « Contribuer » de la page web).

Retire ce qui ne doit jamais être envoyé ni rangé dans le corpus : mots de passe (même chiffrés),
jetons et clés, noms d'utilisateur, noms de serveurs et de bases, adresses e-mail, dossiers
personnels et serveurs des chemins réseau. Le reste du fichier est laissé tel quel : la symbologie
doit rester exploitable pour l'entraînement.

Les valeurs de remplacement n'ont ni « < » ni « > » ni « @ » : le fichier reste un JSON ou un XML
valide, et une valeur remplacée n'est pas reprise pour une adresse e-mail.
"""
from __future__ import annotations

import re

# Libellés montrés au visiteur dans l'aperçu (« ce qui a été retiré »)
ACCES = "mot de passe, jeton ou clé"
UTILISATEUR = "nom d'utilisateur"
SERVEUR = "nom de serveur"
BASE = "nom de base de données"
EMAIL = "adresse e-mail"
DOSSIER = "dossier personnel"
RESEAU = "serveur d'un chemin réseau"

REMPLACEMENTS = {ACCES: "RETIRE", UTILISATEUR: "utilisateur-anonyme", SERVEUR: "serveur-anonyme",
                 BASE: "base-anonyme"}

_CLES = {
    ACCES: r"ENCRYPTED_PASSWORD(?:_UTF8)?|PASSWORD|PASSWD|PWD|TOKEN|ACCESS_TOKEN|API_?KEY|SECRET",
    UTILISATEUR: r"USER|USERNAME|UID",
    SERVEUR: r"SERVER|INSTANCE|HOST|HOSTADDR|DB_CONNECTION_PROPERTIES",
    BASE: r"DBNAME|DATABASE",
}
# Valeur entre apostrophes ou guillemets (bruts ou écrits en XML), ou nue jusqu'au séparateur suivant
_VALEUR = r"""(?P<val>'(?:[^'\\]|\\.)*'|&apos;.*?&apos;|&quot;.*?&quot;|\\"(?:[^"\\]|\\[^"])*\\"|[^;&\s"'<>,]*)"""
# D'abord la forme ArcGIS (clés en majuscules, valeur jusqu'au « ; », espaces permis :
# « DATABASE=Database Connections\x.sde »), puis la forme QGIS (valeur entre apostrophes, ou nue
# jusqu'à l'espace suivant), quelle que soit la casse.
_ARCGIS = r"(?P<val>[^;&\"<>\r\n]*)"
_CLE_VALEUR = [(nom, True, re.compile(rf"(?<![\w.])(?P<cle>{cles})=" + _ARCGIS)) for nom, cles in _CLES.items()]
_CLE_VALEUR += [(nom, False, re.compile(rf"(?<![\w.])(?P<cle>{cles})\s*=\s*{_VALEUR}", re.I)) for nom, cles in _CLES.items()]

_URL_IDENTIFIANTS = re.compile(r"(?P<debut>\b[a-z][a-z0-9+.-]*://)(?P<qui>[^/@\s\"'<>]+)@", re.I)
_EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
_DOSSIER = re.compile(r"(?P<debut>(?:\b[A-Za-z]:(?:\\\\|\\|/)|(?<![\w.])/)(?:Users|Documents and Settings|home)(?:\\\\|\\|/))"
                      r"(?P<nom>[^\\/\"'<>;\s]+)", re.I)
# Chemin réseau \\serveur\partage : écrit tel quel (XML, texte) ou doublé dans un JSON
# (\\\\serveur\\partage). Les formes doivent être exactes, pour ne pas prendre pour un serveur
# les « \\b » ou « \\n » des expressions écrites dans un JSON.
_UNC = re.compile(r"(?<![\w:.\\$])(?:(?P<debut>\\\\\\\\)(?P<nom>[A-Za-z0-9_.-]+)(?=\\\\(?!\\)[\w$])"
                  r"|(?P<debut2>\\\\)(?!\\)(?P<nom2>[A-Za-z0-9_.-]+)(?=\\(?!\\)[\w$]))")
_UNC_OBLIQUE = re.compile(r"(?<![\w:/.])(?P<debut>//)(?P<nom>[A-Za-z0-9_-][A-Za-z0-9_.-]*)(?=/[A-Za-z0-9$_-])")

_DEJA = {"retire", "utilisateur-anonyme", "serveur-anonyme", "base-anonyme", "utilisateur", "serveur", "adresse-retiree"}


def _sans_guillemets(valeur: str) -> tuple[str, str, str]:
    for g in ("&apos;", "&quot;", '\\"', "'", '"'):
        if len(valeur) >= 2 * len(g) and valeur.startswith(g) and valeur.endswith(g):
            return g, valeur[len(g):-len(g)], g
    return "", valeur, ""


def nettoyer(texte: str) -> tuple[str, dict[str, int]]:
    """Renvoie le texte nettoyé et, pour chaque sorte de chose retirée, combien de fois."""
    retraits: dict[str, int] = {}

    def compter(nom: str) -> None:
        retraits[nom] = retraits.get(nom, 0) + 1

    def cle_valeur(nom: str, arcgis: bool):
        def remplacer(m: re.Match) -> str:
            if not arcgis and m.group("cle").isupper():
                return m.group(0)  # forme ArcGIS, déjà traitée en entier par le premier passage
            debut, contenu, fin = _sans_guillemets(m.group("val"))
            if not contenu.strip() or contenu.lower() in _DEJA:
                return m.group(0)
            # Base « fichier » (dossier de shapefiles, GeoPackage, géodatabase) : c'est un chemin, utile
            # à la conversion ; ses parties personnelles sont retirées plus bas (dossiers, réseau).
            if nom == BASE and (re.search(r"[\\/]", contenu) or contenu.strip() == "."
                                or re.search(r"\.(gdb|gpkg|sqlite|db|sde|mdb)$", contenu.strip(), re.I)):
                return m.group(0)
            compter(nom)
            return m.group(0)[: m.start("val") - m.start()] + debut + REMPLACEMENTS[nom] + fin
        return remplacer

    def url(m: re.Match) -> str:
        compter(ACCES if ":" in m.group("qui") else UTILISATEUR)
        return m.group("debut") + "RETIRE@"

    def dossier(m: re.Match) -> str:
        if m.group("nom").lower() in _DEJA | {"public", "default", "all users", "shared"}:
            return m.group(0)
        compter(DOSSIER)
        return m.group("debut") + "utilisateur"

    def reseau(m: re.Match) -> str:
        debut, nom = (m.group("debut"), m.group("nom")) if m.group("nom") else (m.group("debut2"), m.group("nom2"))
        if nom.lower() in _DEJA | {"localhost"}:
            return m.group(0)
        compter(RESEAU)
        return debut + "serveur"

    def email(m: re.Match) -> str:
        compter(EMAIL)
        return "adresse-retiree"

    texte = _URL_IDENTIFIANTS.sub(url, texte)
    for nom, arcgis, motif in _CLE_VALEUR:
        texte = motif.sub(cle_valeur(nom, arcgis), texte)
    texte = _EMAIL.sub(email, texte)
    texte = _DOSSIER.sub(dossier, texte)
    texte = _UNC.sub(reseau, texte)
    texte = _UNC_OBLIQUE.sub(reseau, texte)
    return texte, retraits


def nettoyer_octets(donnees: bytes) -> tuple[bytes, dict[str, int]]:
    """Comme `nettoyer`, pour le contenu d'un fichier. Un fichier qui n'est pas du texte UTF-8 est refusé."""
    try:
        texte = donnees.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValueError("le fichier n'est pas un texte UTF-8 (.lyrx, .qlr ou .qml attendu)") from e
    propre, retraits = nettoyer(texte)
    return propre.encode("utf-8"), retraits


def reste_sensible(texte: str) -> list[str]:
    """Ce qui ressemble encore à un secret ou à une donnée personnelle (revérification après nettoyage)."""
    return sorted(set(nettoyer(texte)[1]))
