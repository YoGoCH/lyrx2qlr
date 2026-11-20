"""Textes de l'extension, en français et en anglais, selon la langue de QGIS.

QGIS en français → français ; toute autre langue → anglais. Le rapport de conversion suit la même langue
(le cœur le traduit avec catalogues/traduction_en.json).
"""
from __future__ import annotations

TEXTES = {
    "fr": {
        "importer": "Importer un fichier ArcGIS Pro (.lyrx)…",
        "exporter": "Exporter la couche active en .lyrx…",
        "dossier": "Convertir un dossier (.lyrx ⇄ .qlr)…",
        "garder": "Garder la source de données",
        "garder-aide": "Cochée : le fichier produit pointe sur les mêmes données (dossier, GeoPackage, base Oracle…, "
                       "sans mot de passe). Décochée : seul le nom du jeu de données est gardé, à reconnecter.",
        "a-propos": "À propos de lyrx2qlr {version}",
        "a-propos-texte": "<b>lyrx2qlr {version}</b><br>Conversion de symbologies ArcGIS Pro (.lyrx) ⇄ QGIS (.qlr)."
                          "<br>Même cœur que l'application web et la ligne de commande.",
        "enregistrer-rapport": "Enregistrer le rapport…",
        "enregistrer-titre": "Enregistrer le rapport",
        "nom-rapport": "rapport_lyrx2qlr.txt",
        "filtre-texte": "Texte (*.txt)",
        "importer-titre": "Importer un fichier ArcGIS Pro",
        "filtre-lyrx": "Couches ArcGIS Pro (*.lyrx)",
        "conversion-impossible": "Conversion impossible :\n{erreur}",
        "choisir-couche": "Sélectionnez d'abord une couche vectorielle.",
        "nom-couche": "couche",
        "exporter-titre": "Exporter en .lyrx",
        "description-impossible": "QGIS n'a pas pu décrire la couche :\n{erreur}",
        "dossier-entree": "Dossier à convertir (.lyrx, .qlr, .qml)",
        "dossier-sortie": "Dossier où écrire les résultats",
        "aucun-fichier": "Aucun fichier .lyrx, .qlr ou .qml dans ce dossier.",
        "conversion": "Conversion…",
        "arreter": "Arrêter",
        "bilan-dossier": "{reussis} fichier(s) converti(s) sur {n}, {echecs} échec(s) ; {pertes} fichier(s) avec des "
                         "éléments non convertis. Rapport enregistré dans « {nom} » du dossier de sortie.",
        "titre-dossier": "Conversion du dossier",
        "deux-points": " : ",
        # messages ajoutés au rapport par l'extension elle-même
        "connexion-utilisee": "Connexion QGIS « {nom} » utilisée pour l'authentification de la base « {base} ».",
        "windows-refuse": " Windows refuse de charger {fichier} : {erreur}.",
        "dll-absente": " {fichier} n'est pas installé avec ce QGIS.",
        "conseil-oracle": " Le fournisseur Oracle de QGIS a besoin du client Oracle (oci.dll) : QGIS installé par le"
                          " programme officiel l'apporte dans son dossier bin ; avec OSGeo4W, installer le paquet"
                          " « qgis-oracle-provider » (ou « qgis-full »). Un autre client Oracle placé avant dans le PATH"
                          " (installé pour ArcGIS ou un autre logiciel) peut aussi le bloquer.",
        "fournisseur-absent": "Ce QGIS ne charge pas le fournisseur « {nom} » : la couche ne pourra pas s'ouvrir"
                              " (« Fournisseur de données invalide »).{raison}{conseil}",
        "piste-st-geometry": " Si la table est stockée en ST_GEOMETRY (type Esri), QGIS ne peut pas la lire : il lui faut"
                             " SDO_GEOMETRY, ou une vue qui convertit la géométrie dans la base.",
        "couche-invalide": "Couche « {nom} » chargée mais invalide (source injoignable ?).{detail}{piste}",
        "chargement-impossible": "QGIS n'a pas pu charger la couche convertie : {erreur}",
    },
    "en": {
        "importer": "Import an ArcGIS Pro file (.lyrx)…",
        "exporter": "Export the active layer to .lyrx…",
        "dossier": "Convert a folder (.lyrx ⇄ .qlr)…",
        "garder": "Keep the data source",
        "garder-aide": "Checked: the output file points to the same data (folder, GeoPackage, Oracle database…, "
                       "without password). Unchecked: only the dataset name is kept, to be reconnected.",
        "a-propos": "About lyrx2qlr {version}",
        "a-propos-texte": "<b>lyrx2qlr {version}</b><br>Converts ArcGIS Pro (.lyrx) ⇄ QGIS (.qlr) symbology."
                          "<br>Same engine as the web app and the command line.",
        "enregistrer-rapport": "Save the report…",
        "enregistrer-titre": "Save the report",
        "nom-rapport": "lyrx2qlr_report.txt",
        "filtre-texte": "Text (*.txt)",
        "importer-titre": "Import an ArcGIS Pro file",
        "filtre-lyrx": "ArcGIS Pro layers (*.lyrx)",
        "conversion-impossible": "Conversion failed:\n{erreur}",
        "choisir-couche": "Select a vector layer first.",
        "nom-couche": "layer",
        "exporter-titre": "Export to .lyrx",
        "description-impossible": "QGIS could not describe the layer:\n{erreur}",
        "dossier-entree": "Folder to convert (.lyrx, .qlr, .qml)",
        "dossier-sortie": "Folder for the results",
        "aucun-fichier": "No .lyrx, .qlr or .qml file in this folder.",
        "conversion": "Converting…",
        "arreter": "Stop",
        "bilan-dossier": "{reussis} of {n} file(s) converted, {echecs} failure(s); {pertes} file(s) with items not "
                         "converted. Report saved as “{nom}” in the output folder.",
        "titre-dossier": "Folder conversion",
        "deux-points": ": ",
        "connexion-utilisee": "QGIS connection “{nom}” used to authenticate to the database “{base}”.",
        "windows-refuse": " Windows refuses to load {fichier}: {erreur}.",
        "dll-absente": " {fichier} is not installed with this QGIS.",
        "conseil-oracle": " The QGIS Oracle provider needs the Oracle client (oci.dll): QGIS installed with the"
                          " official installer brings it in its bin folder; with OSGeo4W, install the"
                          " “qgis-oracle-provider” package (or “qgis-full”). Another Oracle client earlier in the PATH"
                          " (installed for ArcGIS or other software) can also block it.",
        "fournisseur-absent": "This QGIS does not load the “{nom}” provider: the layer will not open"
                              " (“Invalid data provider”).{raison}{conseil}",
        "piste-st-geometry": " If the table is stored as ST_GEOMETRY (Esri type), QGIS cannot read it: it needs"
                             " SDO_GEOMETRY, or a view that converts the geometry in the database.",
        "couche-invalide": "Layer “{nom}” loaded but invalid (source unreachable?).{detail}{piste}",
        "chargement-impossible": "QGIS could not load the converted layer: {erreur}",
    },
}


def langue_qgis() -> str:
    """« fr » si QGIS est en français, sinon « en »."""
    try:
        from qgis.core import QgsApplication
        nom = QgsApplication.locale() or ""
    except Exception:  # hors de QGIS (tests) : langue du système
        nom = ""
    if not nom:
        from qgis.PyQt.QtCore import QLocale
        nom = QLocale().name()
    return "fr" if nom.lower().startswith("fr") else "en"


class Textes:
    """t("cle", valeur=…) dans la langue choisie."""

    def __init__(self, langue: str | None = None):
        self.langue = langue if langue in TEXTES else langue_qgis()

    def __call__(self, cle: str, **valeurs) -> str:
        texte = TEXTES[self.langue].get(cle) or TEXTES["fr"][cle]
        return texte.format(**valeurs) if valeurs else texte
