# Journal des versions

## v1.10.1 — 25 novembre 2026

La conversion ne change pas.

- Page web : l'extension QGIS est acceptée sur plugins.qgis.org (extensions expérimentales). Un
  encadré « Aussi dans QGIS » la présente sous la zone de dépôt, avec la marche à suivre pour
  l'installer et un lien vers sa page. « À venir » annonce maintenant son passage en version stable.

## v1.10.0 — 21 novembre 2026

La conversion ne change pas.

- Extension QGIS en anglais : si QGIS n'est pas en français, le menu, les fenêtres, les messages et le
  rapport de conversion sont en anglais (le rapport d'un dossier s'appelle alors `lyrx2qlr_report.txt`).
  QGIS en français garde tout en français. Les textes sont dans `qgis_plugin/lyrx2qlr_qgis/textes.py`.
- Tests : l'extension est essayée dans les deux langues ; les deux listes de textes ont les mêmes clés.

## v1.9.1 — 21 novembre 2026

La conversion ne change pas.

- Page web : dans le schéma « Comment ça marche », l'étape « Rapport » devient « Report » sur la page
  en anglais (le mot n'était pas traduit).

## v1.9.0 — 20 novembre 2026

La conversion ne change pas ; son rapport existe maintenant en anglais.

- Rapport de conversion en anglais : sur la page en anglais (« English »), le rapport détaillé, son
  résumé et les rapports de l'archive ZIP sont en anglais. On peut changer de langue sans reconvertir
  (les entrées arrivent dans les deux langues).
- Ligne de commande : option `--langue en` (ou `-l en`), pour le texte comme pour le JSON.
- Le cœur écrit toujours ses messages en français ; ils sont traduits à l'affichage par
  `traduction.py` et la table `catalogues/traduction_en.json` (phrase française → phrase anglaise,
  parties variables notées {0}, {1}…). Les noms donnés par l'utilisateur (couches, classes) ne sont
  jamais traduits. Une phrase sans traduction reste en français.
- Nouveau test `tests/test_traduction.py` : chaque message du code et des catalogues doit avoir sa
  traduction, et les 75 exemples réels sont entièrement traduits.
- L'extension QGIS garde ses rapports en français (son interface est en français ; anglais en v1.10.0).

## v1.8.5 — 17 novembre 2026

La conversion ne change pas.

- Page web : comptage anonyme de l'usage (`web/compteur.js`). Une « visite » par onglet ouvert,
  et pour chaque conversion le nombre de fichiers et de réussites, envoyés à `/api/compter` du même
  serveur. Ni nom ni contenu de fichier, ni cookie, ni identifiant ; le serveur additionne par jour,
  sans adresse IP, et efface après 100 jours. Rien n'est envoyé en local ni hors ligne.

## v1.8.4 — 17 novembre 2026

La conversion ne change pas.

- Page web : l'onglet « Contribuer » du bord droit est retiré. Le panneau s'ouvre par le bouton
  « Contribuer un exemple » de l'encadré « Un outil collaboratif » (ou par le bouton « Contribuer »
  d'un résultat, ou le lien `#contribuer`) ; à la fermeture, le focus revient sur ce bouton.

## v1.8.3 — 17 novembre 2026

Page web allégée. La conversion ne change pas.

- Style sobre par défaut à la première visite ; le style papetche reste au choix (bouton « Style »)
  et n'est retenu qu'après un clic.
- Plus de rappel « ← papetche.ch » en haut : le pied de page dit « Un outil de papetche.ch ».
- « Comment ça marche » est repliée au départ : ses premières lignes s'estompent, « Lire la suite »
  la déplie (`web/repli.js`).
- Nouvel encadré « Un outil collaboratif », juste au-dessus, avec le bouton « Contribuer un
  exemple » ; l'onglet du bord droit reste.
- « Construit et testé sur du concret » tient en une bande de chiffres ; l'explication passe sous
  « Comment c'est vérifié ».
- « Nouveautés » plus discrètes : sans cadres ni pastilles, deux versions visibles.

## v1.8.2 — 17 novembre 2026

La conversion ne change pas.

- L'extension QGIS est publiée sur https://plugins.qgis.org/plugins/lyrx2qlr_qgis/ : la page web l'annonce (à la place
  de « Bientôt »), avec la marche à suivre dans QGIS ; README et feuille de route à jour.
- `outils/construire.py envoi ADRESSE` : ZIP d'envoi pour plugins.qgis.org avec la vraie adresse
  e-mail, écrite seulement dans `dist/` (ignoré par git).
- Contrôle flake8 de plugins.qgis.org : noms de variable ambigus (`l`) renommés dans `images.py`,
  trois corrections de mise en forme.

## v1.8.1 — 17 novembre 2026

Corrections demandées par le contrôle automatique de plugins.qgis.org. La conversion ne change pas.

- Lecture des .qlr et .qml : nouveau module `xml_sur` (bibliothèque standard seulement). Un fichier
  qui déclare des entités XML (base des attaques « milliard de rires » ou lecture d'un fichier du
  poste) est refusé avec un message clair. Les vrais fichiers QGIS n'en déclarent jamais ; les 75
  exemples réels passent.
- Contrôle de sécurité Bandit et recherche de secrets (detect-secrets) : plus aucune alerte sur
  l'extension. Empreintes MD5 marquées « non sécuritaires » (elles ne servent qu'à fabriquer des
  identifiants stables), attribut QGIS « pass » (ordre de dessin) posé sans ressembler à un mot de
  passe, libellé `SECRET` renommé `ACCES`.
- Extension prête pour Qt6 (QGIS 4) : énumérations écrites en entier, `exec()` au lieu de
  `exec_()`, `supportsQt6=True` dans les métadonnées. Toujours compatible Qt5 (QGIS 3.40 et plus).

## v1.8.0 — 17 novembre 2026

La conversion ne change pas.

- Page web : bouton « Utiliser hors ligne ». Il garde dans le navigateur la page, le cœur Python et
  Pyodide (environ 15 Mo, `web/sw.js`), puis la conversion marche sans internet. Il propose ensuite
  d'installer lyrx2qlr comme une application (`web/manifest.webmanifest`, icônes 192 et 512 px
  faites par `outils/icones_web.py`). Rien n'est gardé sans le clic ; un lien « Retirer la copie hors
  ligne » efface tout. Les fichiers de la page viennent du réseau d'abord : une nouvelle version
  arrive dès qu'on est en ligne.
- Onglet « Contribuer » plus grand et plus lisible.
- Tests GitHub dans QGIS : une seule application QGIS pour toute la session. La fixture de
  `test_qgis` la lâchait en fin de fichier, et `test_extension` plantait ensuite (erreur 139).

## v1.7.2 — 17 novembre 2026

La conversion ne change pas.

- Le dépôt s'appelle maintenant https://github.com/YoGoCH/lyrx2qlr (GitHub redirige l'ancienne
  adresse). Liens mis à jour dans l'extension, la page et la documentation.
- Les 75 symbologies réelles anonymisées de test (`exemples/lyrx`, `exemples/qlr`) sont publiques,
  après un dernier contrôle : les tests d'aller-retour et de QGIS tournent aussi sur GitHub. Le
  corpus de fichiers téléchargés reste sur le poste du mainteneur.
- Tests GitHub : en cas d'échec dans QGIS, la fin du journal est publiée en annotations.

## v1.7.1 — 17 novembre 2026

Le code est public : https://github.com/YoGoCH/lyrx2qlr (licence GPL-3.0). La
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
