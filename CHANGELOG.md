# Journal des versions

## v1.7.1 — 17 novembre 2026

Le code est public : https://github.com/YoGoCH/lyrx2qlr_code_public (licence GPL-3.0). La
conversion ne change pas.

- Le dépôt de travail est désormais public. Son historique commence à la v1.7.0 ; l'historique
  plus ancien (qui contenait le corpus de fichiers réels) reste archivé à part.
- Restent sur le poste du mainteneur, ignorés par git : les symbologies réelles de test
  (`exemples/lyrx`, `exemples/qlr`), le corpus et les notes de travail. Les tests qui en ont besoin
  sont sautés sur GitHub.
- Nouveau contrôle `outils/verifier_depot.py` (avant chaque envoi et dans les tests) : aucun fichier
  privé, aucune adresse e-mail réelle, aucun mot interdit dans le dépôt.
- Extension QGIS : `metadata.txt` en anglais, icône, liens vers le dépôt public (pour
  plugins.qgis.org). `CONTRIBUTING.md` et modèle de ticket « Fichier mal converti ».
- Tests GitHub : image QGIS `qgis/qgis:3.40` (l'ancienne étiquette n'existe plus), et sortie
  directe après les tests dans QGIS (plantage connu de QGIS à l'arrêt dans un conteneur).
- Page web : lien « code ouvert sur GitHub » en bas de page.
- Outil « Contribuer » : les dossiers de shapefiles et les expressions ne sont plus abîmés par le
  nettoyage ; un refus du serveur est affiché tel quel.

## v1.7.0 — 17 novembre 2026

Outil collaboratif « Contribuer » : les utilisateurs peuvent envoyer des exemples pour entraîner
lyrx2qlr. La conversion elle-même ne change pas.

- Page web : onglet « Contribuer » sur le bord droit, panneau latéral avec formulaire : sorte de
  contribution (« Conversion à corriger », « Bonne conversion », « Paire de référence », « Idée ou
  remarque »), fichiers .lyrx et .qlr/.qml, ce qui ne va pas, commentaire, versions des logiciels,
  usage (tests seulement ou corpus public CC-BY 4.0), e-mail facultatif. Bouton « Contribuer » sur
  chaque résultat de conversion. Français et anglais, styles papetche et sobre, modes clair et sombre.
- Rien ne part sans aperçu ni accord : le navigateur nettoie les fichiers et le commentaire
  (nouveau module du cœur `confidentialite.py` : mots de passe, jetons, utilisateurs, serveurs,
  bases, e-mails, dossiers personnels) et montre ce qui a été retiré.
- Nouveau module du cœur `contribution.py` (colis ZIP : fichiers nettoyés, notre conversion et son
  rapport, `contribution.json`) et outil de tri `outils/contributions.py`.
- Les textes de la page sur la confidentialité disent que seul le bouton « Envoyer » transmet des
  fichiers.

## v1.6.0 — 17 novembre 2026

Page web : apparence au choix et section « Nouveautés ». Le cœur de conversion ne change pas.

- Section « Nouveautés » : un court texte par version (français et anglais, écrit à la main dans
  `web/nouveautes.json`) et ce qui a été ajouté au modèle neutre (lignes de `modele.py`) et aux
  catalogues (lignes et règles de correspondance), calculé avec git par `outils/nouveautes.py`
  (lancé aussi par `outils/chiffres.py`, avant chaque version).
- Mot d'avertissement sous la zone de dépôt : selon la complexité de la symbologie, le résultat
  peut demander une retouche ; l'outil s'améliore à chaque version. Annonce de l'extension QGIS
  bientôt dans le gestionnaire d'extensions.
- `outils/construire.py web` ajoute une empreinte (`?v=…`) aux adresses des styles et scripts de
  la page : un navigateur ne garde plus un ancien `style.css` avec une nouvelle page.
- Page web : bouton « Style » pour passer du style papetche (couleurs, ombres, quadrillage) à un
  style sobre (coins carrés, traits fins, accent bleu), comme sur INTERLIS web tools ; bouton
  « ☾ Sombre / ☀ Clair » pour le mode sombre, dans les deux styles. Sans choix, le mode suit
  l'ordinateur. Les deux choix sont gardés dans le navigateur (`localStorage`), rien n'est envoyé.
- Extension QGIS : la piste `ST_GEOMETRY` n'est plus proposée quand le fournisseur de la base
  manque (l'avertissement sur le fournisseur suffit).

## v1.5.1 — 16 novembre 2026

- Extension QGIS : à l'import, si ce QGIS ne charge pas le fournisseur de la base (« Fournisseur
  de données invalide oracle »), le rapport le dit, avec la raison donnée par Windows et la marche
  à suivre (client Oracle `oci.dll`, paquet OSGeo4W `qgis-oracle-provider`). Une couche chargée
  mais invalide est aussi signalée, avec la piste `ST_GEOMETRY` pour Oracle.
- Anciens .lyrx sans `DBCLIENT` : le moteur et le serveur sont lus dans `INSTANCE`
  (`sde:sqlserver:serveur`, `sde:oracle11g:alias`, `sde:oracle$alias`) ; la connexion est
  gardée au lieu de devenir « à reconnecter » (catalogue `sources.json`, « moteurs_instance »).

## v1.5.0 — 16 novembre 2026

**Sources de données** : un fichier converti pointe sur les mêmes données et s'ouvre directement,
sans « Changer la source de données… ».

- Nouvelle coche « Garder la source de données », cochée par défaut, dans la page web et
  l'extension QGIS ; `--sans-source` en ligne de commande. Décochée, la source est réduite au nom
  du jeu, « à reconnecter » (comportement d'avant pour les bases).
- Correspondance des connexions de base de données entre les deux logiciels (catalogue
  `sources.json`, module `sources.py`) : **Oracle**, **PostgreSQL** et **SQL Server** (connexion
  SDE d'ArcGIS ⇄ fournisseurs `oracle`, `postgres`, `mssql` de QGIS) : serveur, base,
  utilisateur, schéma, table, colonne de géométrie, clé, système de coordonnées, filtre.
- **Le mot de passe n'est jamais recopié**, dans aucun sens. L'extension QGIS reprend la
  configuration d'authentification d'une connexion enregistrée sur la même base.
- GeoPackage : le préfixe `main.` qu'ArcGIS ajoute au nom de la table est retiré vers QGIS.
- Règle du projet (CLAUDE.md) : les fichiers convertis sur le poste peuvent garder leur
  connexion ; le dépôt, le corpus et les fichiers envoyés par d'autres restent anonymisés.

## v1.4.0 — 16 novembre 2026

Lot 2.1 : le **corpus réel** est dessiné par les deux logiciels, sur des données fabriquées à
partir des symbologies elles-mêmes (voir `docs/lot2.md`, section « Lot 2.1 »).

- Nouvel outil `outils/lot2/fabriquer_donnees.py` : un GeoPackage par fichier, une case par
  classe ; 403 fichiers du corpus dessinés dans les deux sens, sans échec.
- Corrigé grâce à ce dessin :
  - tailles QGIS en unités de carte (mètres) : converties à l'échelle de référence de la couche
    au lieu d'être gardées telles quelles ;
  - décalage du contour d'une surface : ArcGIS et QGIS le comptent en sens inverse ;
  - décalage des hachures : ArcGIS l'exprime dans le repère de la carte, QGIS selon l'angle ;
  - catégorie NULL de QGIS : elle dessine aussi les valeurs non listées (lue comme « autres
    valeurs » ; l'écart inverse est annoncé) ;
  - formes de marqueur en courbes de Bézier : annoncées au lieu de devenir un cercle en silence ;
  - remplissages et marqueurs par image BMP avec substitutions de couleurs : l'image est
    repeinte (PNG à fond transparent) au lieu de rester noire sur blanc.
- Le comparateur de dessins nomme et encadre les classes qui diffèrent.

## v1.3.0 — 16 novembre 2026

Lot 2 : les conversions sont jugées par **ArcGIS Pro 3.7** lui-même (voir `docs/lot2.md`).

- ArcGIS ouvre et réenregistre plus de 1 000 fichiers produits par lyrx2qlr ; les 238 .lyrx
  d'origine de nos tests s'ouvrent tous.
- Corrigé grâce à ArcGIS :
  - placements d'étiquettes de surfaces « autour » et « périmètre » : valeurs inexistantes dans
    ArcGIS, remplacées par des valeurs valides (avec avertissement) ;
  - découpage des grilles de marqueurs (« entiers dedans », « centre dedans ») ;
  - contour de marqueur sans épaisseur : ArcGIS lui donnait 4 pt ; décalage d'étiquette absent :
    ArcGIS mettait 1 pt ;
  - poids des étiquettes de classes (`barrierWeight`).
- Corrigé grâce au dessin croisé (le même jeu de données dessiné par QGIS et par ArcGIS) :
  - contour des marqueurs : ArcGIS l'agrandit avec la taille du marqueur
    (`scaleSymbolsProportionally`), QGIS non ; un cercle de 18 pt avait un contour 4,5 fois trop
    épais ;
  - anciens noms d'options QGIS (`outline_color`, `outline_width` d'un trait) : lus comme absents,
    les traits devenaient noirs de 1 pt (29 fichiers de test concernés) ;
  - hachures dont le trait est décalé d'une période entière : rien n'était dessiné dans QGIS ;
  - une valeur de classe QGIS contenant « � » (shapefile sans `.cpg` lu avec le mauvais encodage)
    est signalée : ArcGIS lira le bon caractère et la classe ne correspondra à rien.
- Polices ESRI : 29 caractères de « ESRI Default Marker » remplacés par des formes QGIS
  **mesurées** sur la vraie police (plein, creux ou trait, épaisseur, rotation), au lieu de
  l'ancienne table approximative.
- Hexagone dans le bon sens (pointe en haut) ; octogone ajouté.
- Un fichier sans couche vectorielle (raster seul) donne un message clair, sans fichier vide.
- Nouveaux outils `outils/lot2/` : relecture par ArcGIS, dessin croisé avant / après,
  vérification selon la spécification CIM d'Esri, symbologies fabriquées par ArcPy, contrôle des
  polices ESRI.
- Page web : compteur des fichiers relus par ArcGIS Pro.

## v1.2.3 — 15 novembre 2026

- Page anglaise mieux référencée : sur `?lang=en`, l'adresse de référence (`canonical`), la
  description et les balises de partage sont en anglais.
- Une adresse = une langue : « / » est toujours en français (sauf si le visiteur a choisi
  l'anglais la dernière fois, et l'adresse devient alors `?lang=en`). Un navigateur non
  francophone voit une invitation « This page is also available in English », au lieu d'un
  changement automatique que les moteurs de recherche comprendraient mal.

## v1.2.2 — 15 novembre 2026

- Page web en anglais : bouton « English / Français », langue du navigateur par défaut, adresse
  `?lang=en` à partager. Le rapport est mis en forme dans la langue de la page ; ses messages
  détaillés restent en français pour l'instant.
- Licence : GNU GPL version 3 ou plus récente (fichier `LICENSE`, aussi dans l'extension QGIS).
- Les fichiers du corpus restent sur le poste de travail et sortent du dépôt
  (`corpus.py telecharger` les reconstitue). `corpus/sources.json` reste dans le dépôt.

## v1.2.1 — 14 novembre 2026

Nouvelle page web, dans le style de papetche.ch. Le cœur de conversion ne change pas.

- Logo : deux demi-cercles fléchés, de « lyrx » vers « qlr » et retour (aussi en icône d'onglet).
- Courte préface sur l'interopérabilité dans les métiers de la géomatique et de l'environnement.
- Schéma interactif « Comment ça marche » : lecture, modèle neutre, écriture, catalogues de
  règles et rapport, dans les deux sens, le tout sur l'ordinateur de l'utilisateur.
- Compteurs (tests, fichiers .lyrx et QGIS réels, règles des catalogues) lus dans
  `web/chiffres.json`, produit par `outils/chiffres.py`.

## v1.2.0 — 14 novembre 2026

Corpus de symbologies réelles (lot 1.5) et corrections qu'il a permises.

- `corpus/` : 419 fichiers trouvés sur internet (Ordnance Survey, portail des données ouvertes du
  Royaume-Uni, Données Québec, dépôts GitHub), chacun avec son adresse, sa licence et son
  empreinte dans `corpus/sources.json`. Un mot de passe chiffré trouvé dans un fichier a été retiré.
- `outils/entrainement/corpus.py` : téléchargement poli, aller-retour dans les deux sens,
  comparaison aux paires faites à la main par Ordnance Survey. Mode d'emploi : `docs/corpus.md`.
- Ensembles de règles QGIS simples (une valeur par règle) convertis en valeurs uniques.
- Corrige : « NaN » dans un .lyrx ; classe sans borne supérieure ; format des images intégrées
  (BMP, JPEG, GIF) ; diagrammes désactivés signalés à tort ; contour des marqueurs de police sans
  épaisseur ; décalage quasi nul.
- Ajoute : marqueurs à des positions relatives (milieu, extrémités) ; grille aléatoire ; positions
  des étiquettes de points (nord, nord-est…) ; étiquettes de lignes centrées ou décalées ; forme
  `cross_fill` ; `$feature['champ']` en Arcade.
- Annonce : casse « Titre » et « Majuscule initiale » sans équivalent ArcGIS.
- Catalogues : condition `">0"`, `qgis_extra` utilisé à la lecture, `avertissement_<côté>`,
  motifs « Classe.option » dans `ignorer.json`, `regles_qgis_simples` (voir `docs/catalogues.md`).
- Corpus : 0 erreur interne et 0 aller-retour instable dans les deux sens ; fichiers QGIS sans
  aucune perte : 84 → 185 sur 248.

## v1.1.0 — 13 novembre 2026

Boucle d'entraînement sans ArcGIS Pro (étapes 1 à 4 de l'étude) et corrections qu'elle a permises.

- `outils/entrainement/` : génération de symbologies QGIS inventées, aller-retour, comparaison du
  modèle et des images, fiches d'écart, diagnostic, rapport de couverture
  (`docs/couverture_qgis.md`). Mode d'emploi et résultats : `docs/entrainement.md`.
- 7 cas inventés figés dans `exemples/fabriques/` comme tests permanents.
- Corrige : formes de marqueurs QGIS relues comme des cercles ; triangle isocèle relu en
  équilatéral ; extrémités `LastVertex|FirstVertex` ; symbole sans couche remplacé dans QGIS par
  un symbole par défaut ; contour d'un aplat décalé non décalé côté ArcGIS.
- Ajoute les effets ArcGIS « Couper », « Déplacer » (aplat) et le décalage des tirets ; le
  décalage du premier marqueur le long d'une ligne et les fins « WithHalfGap » / « WithFullGap » ;
  le contour des marqueurs de police vers ArcGIS.
- Annonce désormais : remplacement des polices ESRI, décalage des lignes impaires d'une grille
  ramené au demi-pas, options QGIS visibles mais non converties (`qgis_visibles`).
- Catalogues : nouveaux réglages `lyrx_fins`, `qgis_neutres`, `qgis_visibles`, `qgis_vide`,
  `sens: vers_lyrx`, proportion dans les signatures de formes (voir `docs/catalogues.md`).
- Boucle, graine 4 (cas jamais vus) : 333 cas, 0 écart silencieux.

## v1.0.0 — 13 novembre 2026

Première version prête à tester.

- Cœur de conversion en Python (bibliothèque standard seulement) : .lyrx → .qlr, .qlr ou .qml → .lyrx.
- Correspondances décrites dans des catalogues JSON (`src/lyrx2qlr/catalogues/`), modifiables sans
  toucher au code ; catalogues complémentaires possibles (`-c`).
- Rapport de conversion : « NON CONVERTI », « À VÉRIFIER », « INFO ».
- Application web statique : Python dans le navigateur (Pyodide 0.29.4), plusieurs fichiers à la
  fois, archive ZIP avec les rapports.
- Extension QGIS (3.40 et plus) : importer un .lyrx, exporter la couche active en .lyrx, convertir
  un dossier.
- Ligne de commande `lyrx2qlr`.
- 33 .lyrx et 42 .qlr réels comme exemples ; tests aller-retour, tests dans QGIS 3.44, tests de
  l'extension.
- État de l'art des outils existants (`docs/etat_de_l_art.md`).
