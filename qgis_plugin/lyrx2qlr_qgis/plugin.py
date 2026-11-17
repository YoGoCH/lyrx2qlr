"""Menu « Extensions › lyrx2qlr » : importer un .lyrx, exporter la couche active en .lyrx, convertir un dossier.

Le cœur de conversion est une copie de src/lyrx2qlr placée dans coeur/ par « python outils/construire.py extension ».
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path

from qgis.core import (Qgis, QgsApplication, QgsDataSourceUri, QgsLayerDefinition, QgsPathResolver, QgsProject,
                       QgsProviderRegistry, QgsReadWriteContext, QgsSettings)
from qgis.PyQt.QtCore import QSettings, Qt
from qgis.PyQt.QtWidgets import (QAction, QApplication, QDialog, QDialogButtonBox, QFileDialog, QLabel, QMessageBox,
                                 QPlainTextEdit, QProgressDialog, QVBoxLayout)
from qgis.PyQt.QtXml import QDomDocument

from .coeur.lyrx2qlr import __version__, api
from .coeur.lyrx2qlr.catalogue import Catalogue
from .coeur.lyrx2qlr.rapport import Rapport
from .coeur.lyrx2qlr.sources import anonymiser

MENU = "&lyrx2qlr"
CLE = "lyrx2qlr/"
_GROUPES_CONNEXIONS = {"oracle": "Oracle/connections", "postgres": "PostgreSQL/connections", "mssql": "MSSQL/connections"}


class FenetreRapport(QDialog):
    """Affiche le rapport de conversion, avec un bouton pour l'enregistrer."""

    def __init__(self, parent, titre: str, resume: str, texte: str):
        super().__init__(parent)
        self.setWindowTitle(titre)
        self.resize(760, 480)
        self.texte = texte
        disposition = QVBoxLayout(self)
        etiquette = QLabel(resume)
        etiquette.setWordWrap(True)
        disposition.addWidget(etiquette)
        zone = QPlainTextEdit(texte)
        zone.setReadOnly(True)
        zone.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        disposition.addWidget(zone)
        boutons = QDialogButtonBox(QDialogButtonBox.Close)
        enregistrer = boutons.addButton("Enregistrer le rapport…", QDialogButtonBox.ActionRole)
        enregistrer.clicked.connect(self.enregistrer)
        boutons.rejected.connect(self.reject)
        disposition.addWidget(boutons)

    def enregistrer(self):
        chemin, _ = QFileDialog.getSaveFileName(self, "Enregistrer le rapport", "rapport_lyrx2qlr.txt", "Texte (*.txt)")
        if chemin:
            Path(chemin).write_text(self.texte, encoding="utf-8")


class Lyrx2QlrPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.actions: list[QAction] = []
        self._catalogue = None

    # --- cycle de vie imposé par QGIS ---------------------------------------------------------
    def initGui(self):  # noqa: N802
        self._ajouter("Importer un fichier ArcGIS Pro (.lyrx)…", self.importer_lyrx)
        self._ajouter("Exporter la couche active en .lyrx…", self.exporter_lyrx)
        self._ajouter("Convertir un dossier (.lyrx ⇄ .qlr)…", self.convertir_dossier)
        coche = self._ajouter("Garder la source de données", self._changer_garder_source)
        coche.setCheckable(True)
        coche.setChecked(self.garder_source)
        coche.setToolTip("Cochée : le fichier produit pointe sur les mêmes données (dossier, GeoPackage, base Oracle…, "
                         "sans mot de passe). Décochée : seul le nom du jeu de données est gardé, à reconnecter.")
        self._ajouter(f"À propos de lyrx2qlr {__version__}", self.a_propos)

    def unload(self):
        for a in self.actions:
            self.iface.removePluginMenu(MENU, a)
        self.actions.clear()

    def _ajouter(self, texte, fonction):
        a = QAction(texte, self.iface.mainWindow())
        a.triggered.connect(fonction)
        self.iface.addPluginToMenu(MENU, a)
        self.actions.append(a)
        return a

    # --- outils --------------------------------------------------------------------------------
    @property
    def catalogue(self) -> Catalogue:
        if self._catalogue is None:
            self._catalogue = Catalogue.charger()
        return self._catalogue

    @property
    def garder_source(self) -> bool:
        return QSettings().value(CLE + "garder_source", True, type=bool)

    def _changer_garder_source(self, coche: bool):
        QSettings().setValue(CLE + "garder_source", bool(coche))

    def _authentification(self, document: QDomDocument, rapport: Rapport):
        """Base de données : si une connexion QGIS enregistrée vise la même base avec le même utilisateur
        et une configuration d'authentification, la couche l'utilise (pas de mot de passe à saisir)."""
        sources = document.elementsByTagName("datasource")
        fournisseurs = document.elementsByTagName("provider")
        for i in range(sources.count()):
            fournisseur = fournisseurs.at(i).toElement().text() if i < fournisseurs.count() else ""
            if fournisseur not in ("oracle", "postgres", "mssql"):
                continue
            noeud = sources.at(i).toElement()
            uri = QgsDataSourceUri(noeud.text())
            # Connexions enregistrées par QGIS : « Oracle/connections/NOM/database », « …/authcfg »…
            reglages = QgsSettings()
            reglages.beginGroup(_GROUPES_CONNEXIONS[fournisseur])
            for nom in reglages.childGroups():
                def lu(cle):
                    return str(reglages.value(f"{nom}/{cle}", "") or "")
                if (lu("database").lower() == uri.database().lower() and lu("host").lower() == uri.host().lower()
                        and (not uri.username() or lu("username").lower() == uri.username().lower()) and lu("authcfg")):
                    uri.setAuthConfigId(lu("authcfg"))
                    noeud.firstChild().setNodeValue(uri.uri(False))
                    rapport.info("fichier", f"Connexion QGIS « {nom} » utilisée pour l'authentification de la base « {uri.database()} ».")
                    break
            reglages.endGroup()

    @staticmethod
    def _verifier_fournisseurs(document: QDomDocument, rapport: Rapport):
        """Un fournisseur de base absent donne seulement « Fournisseur de données invalide » dans le journal de
        QGIS : le rapport dit pourquoi (souvent le client Oracle, oci.dll, que QGIS ne trouve pas ou pas le bon)."""
        disponibles = set(QgsProviderRegistry.instance().providerList())
        fournisseurs = document.elementsByTagName("provider")
        for nom in sorted({fournisseurs.at(i).toElement().text() for i in range(fournisseurs.count())}):
            if nom not in _GROUPES_CONNEXIONS or nom in disponibles:
                continue
            raison = ""
            bibliotheque = Path(QgsApplication.pluginPath()) / f"provider_{nom}.dll"
            if os.name == "nt" and bibliotheque.exists():
                try:
                    ctypes.WinDLL(str(bibliotheque))
                except OSError as e:  # ex. « [WinError 126] Le module spécifié est introuvable »
                    raison = f" Windows refuse de charger {bibliotheque.name} : {e}."
            elif not bibliotheque.exists() and os.name == "nt":
                raison = f" {bibliotheque.name} n'est pas installé avec ce QGIS."
            conseil = (" Le fournisseur Oracle de QGIS a besoin du client Oracle (oci.dll) : QGIS installé par le"
                       " programme officiel l'apporte dans son dossier bin ; avec OSGeo4W, installer le paquet"
                       " « qgis-oracle-provider » (ou « qgis-full »). Un autre client Oracle placé avant dans le PATH"
                       " (installé pour ArcGIS ou un autre logiciel) peut aussi le bloquer.") if nom == "oracle" else ""
            rapport.avertir("fichier", f"Ce QGIS ne charge pas le fournisseur « {nom} » : la couche ne pourra pas s'ouvrir"
                                       f" (« Fournisseur de données invalide »).{raison}{conseil}")

    @staticmethod
    def _verifier_couches(nouvelles, rapport: Rapport):
        disponibles = set(QgsProviderRegistry.instance().providerList())
        for couche in nouvelles:
            if couche.isValid() or couche.providerType() not in disponibles:  # fournisseur absent : déjà expliqué
                continue
            detail = couche.error().summary() if couche.error() and not couche.error().isEmpty() else ""
            piste = (" Si la table est stockée en ST_GEOMETRY (type Esri), QGIS ne peut pas la lire : il lui faut"
                     " SDO_GEOMETRY, ou une vue qui convertit la géométrie dans la base.") if couche.providerType() == "oracle" else ""
            rapport.avertir("fichier", f"Couche « {couche.name()} » chargée mais invalide (source injoignable ?)."
                                       f"{(' QGIS : ' + detail) if detail else ''}{piste}")

    def _dossier(self, cle: str) -> str:
        return QSettings().value(CLE + cle, str(Path.home()))

    def _retenir(self, cle: str, chemin: str):
        QSettings().setValue(CLE + cle, str(Path(chemin).parent if Path(chemin).is_file() else chemin))

    def _rapport(self, titre: str, rapport: Rapport):
        if rapport.compter("perte") or rapport.compter("avertissement"):
            FenetreRapport(self.iface.mainWindow(), titre, rapport.resume, rapport.en_texte()).exec_()
        else:
            self.iface.messageBar().pushMessage("lyrx2qlr", f"{titre} : {rapport.resume}", Qgis.Success, 5)

    # --- actions ---------------------------------------------------------------------------------
    def importer_lyrx(self):
        chemin, _ = QFileDialog.getOpenFileName(self.iface.mainWindow(), "Importer un fichier ArcGIS Pro",
                                                self._dossier("import"), "Couches ArcGIS Pro (*.lyrx)")
        if not chemin:
            return
        self._retenir("import", chemin)
        chemin = Path(chemin)
        rapport = Rapport(fichier=chemin.name, sens=".lyrx → .qlr")
        try:
            doc = api.lire(chemin.read_bytes(), chemin.name, self.catalogue, rapport)
            if not self.garder_source:
                for c in doc.couches:
                    anonymiser(c)
            for c in doc.couches:  # un dossier relatif se lit depuis l'emplacement du .lyrx
                if c.source.dossier and not os.path.isabs(c.source.dossier):
                    c.source.dossier = str((chemin.parent / c.source.dossier).resolve())
            donnees = api.ecrire(doc, ".qlr", self.catalogue, rapport)
        except Exception as e:  # le cœur signale déjà ce qu'il peut ; ceci couvre un fichier illisible
            QMessageBox.critical(self.iface.mainWindow(), "lyrx2qlr", f"Conversion impossible :\n{e}")
            return
        # Chargement en mémoire : pas de fichier intermédiaire ; un chemin relatif part du dossier du .lyrx.
        document = QDomDocument()
        document.setContent(donnees)
        if self.garder_source:
            self._authentification(document, rapport)
            self._verifier_fournisseurs(document, rapport)
        contexte = QgsReadWriteContext()
        contexte.setPathResolver(QgsPathResolver(str(chemin)))
        projet = QgsProject.instance()
        avant = set(projet.mapLayers())
        ok, erreur = QgsLayerDefinition.loadLayerDefinition(document, projet, projet.layerTreeRoot(), contexte)
        if not ok:
            rapport.perte("fichier", f"QGIS n'a pas pu charger la couche convertie : {erreur}")
        if self.garder_source:
            self._verifier_couches([c for i, c in projet.mapLayers().items() if i not in avant], rapport)
        self._rapport(chemin.name, rapport)

    def exporter_lyrx(self):
        couche = self.iface.activeLayer()
        noeud = QgsProject.instance().layerTreeRoot().findLayer(couche.id()) if couche else None
        if noeud is None:
            QMessageBox.information(self.iface.mainWindow(), "lyrx2qlr", "Sélectionnez d'abord une couche vectorielle.")
            return
        nom = "".join(ch if ch.isalnum() or ch in "._- " else "_" for ch in couche.name()) or "couche"
        chemin, _ = QFileDialog.getSaveFileName(self.iface.mainWindow(), "Exporter en .lyrx",
                                                str(Path(self._dossier("export")) / f"{nom}.lyrx"),
                                                "Couches ArcGIS Pro (*.lyrx)")
        if not chemin:
            return
        self._retenir("export", chemin)
        # Définition de couche QGIS en mémoire, avec des chemins absolus (pas de fichier intermédiaire).
        document = QDomDocument("qgis-layer-definition")
        contexte = QgsReadWriteContext()
        contexte.setPathResolver(QgsPathResolver())
        ok, erreur = QgsLayerDefinition.exportLayerDefinition(document, [noeud], contexte)
        if not ok:
            QMessageBox.critical(self.iface.mainWindow(), "lyrx2qlr", f"QGIS n'a pas pu décrire la couche :\n{erreur}")
            return
        resultat = api.convertir(bytes(document.toByteArray()), f"{nom}.qlr", self.catalogue, self.garder_source)
        if resultat.reussi:
            Path(chemin).write_bytes(resultat.donnees)
            resultat.rapport.sens = ".qlr → .lyrx"
        self._rapport(Path(chemin).name, resultat.rapport)

    def convertir_dossier(self):
        fenetre = self.iface.mainWindow()
        entree = QFileDialog.getExistingDirectory(fenetre, "Dossier à convertir (.lyrx, .qlr, .qml)",
                                                  self._dossier("lot_entree"))
        if not entree:
            return
        self._retenir("lot_entree", entree)
        sortie = QFileDialog.getExistingDirectory(fenetre, "Dossier où écrire les résultats", self._dossier("lot_sortie"))
        if not sortie:
            return
        QSettings().setValue(CLE + "lot_sortie", sortie)
        fichiers = api.lister_fichiers([entree])
        if not fichiers:
            QMessageBox.information(fenetre, "lyrx2qlr", "Aucun fichier .lyrx, .qlr ou .qml dans ce dossier.")
            return
        progres = QProgressDialog("Conversion…", "Arrêter", 0, len(fichiers), fenetre)
        progres.setWindowModality(Qt.WindowModal)
        textes, echecs, pertes = [], 0, 0
        for i, f in enumerate(fichiers):
            if progres.wasCanceled():
                break
            progres.setValue(i)
            progres.setLabelText(f.name)
            QApplication.processEvents()
            cible = Path(sortie) / f.parent.relative_to(entree)
            r = api.convertir_fichier(f, cible, self.catalogue, self.garder_source)
            echecs += 0 if r.reussi else 1
            pertes += 1 if r.rapport.compter("perte") else 0
            textes.append(r.rapport.en_texte())
        progres.setValue(len(fichiers))
        texte = ("\n\n" + "-" * 72 + "\n\n").join(textes)
        (Path(sortie) / "rapport_lyrx2qlr.txt").write_text(texte + "\n", encoding="utf-8")
        resume = (f"{len(textes) - echecs} fichier(s) converti(s) sur {len(fichiers)}, {echecs} échec(s) ; "
                  f"{pertes} fichier(s) avec des éléments non convertis. Rapport enregistré dans "
                  f"« rapport_lyrx2qlr.txt » du dossier de sortie.")
        FenetreRapport(fenetre, "Conversion du dossier", resume, texte).exec_()

    def a_propos(self):
        QMessageBox.about(self.iface.mainWindow(), "lyrx2qlr",
                          f"<b>lyrx2qlr {__version__}</b><br>Conversion de symbologies ArcGIS Pro (.lyrx) ⇄ QGIS (.qlr)."
                          "<br>Même cœur que l'application web et la ligne de commande."
                          "<br><a href='https://github.com/YoGoCH/lyrx2qlr_code_public'>github.com/YoGoCH/lyrx2qlr_code_public</a>")
