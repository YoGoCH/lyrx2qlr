# Limites connues (version 1)

Tout ce qui n'est pas converti est **écrit dans le rapport** de chaque fichier, rubrique
« NON CONVERTI », avec l'endroit concerné. Cette page résume les cas connus.

## Pris en charge

- Couches d'entités vectorielles (points, lignes, surfaces).
- Méthodes de rendu : symbole unique, valeurs uniques (catégories, y compris sur plusieurs
  champs et avec groupes), classes (couleurs graduées).
- Symboles : aplat, trait (avec tirets), hachures, marqueurs simples, marqueurs de police,
  marqueurs image, remplissage image, et leurs placements (grille, grille aléatoire,
  centre, le long d'une ligne, sommets, extrémités).
- Étiquettes : texte ou expression, police, taille, couleur, casse, halo, échelles de
  visibilité, placement de base ; plusieurs classes d'étiquettes (règles dans QGIS).
- Couche : nom, visibilité, transparence, échelles de visibilité, filtre de définition,
  alias des champs, champ d'affichage.
- Sources : shapefile, géodatabase fichier, GeoPackage, et bases **Oracle**, **PostgreSQL**
  et **SQL Server** (connexions SDE d'ArcGIS ⇄ fournisseurs `oracle`, `postgres`, `mssql` de
  QGIS). Avec la coche « Garder la source de données » (cochée par défaut ; `--sans-source`
  en ligne de commande), le fichier produit pointe sur les mêmes données et s'ouvre
  directement : serveur, base, utilisateur, schéma, table, colonne de géométrie, clé et filtre
  sont recopiés. Décochée, seul le nom du jeu de données reste, « à reconnecter ».

### Sources de données : ce qu'il faut savoir

- **Le mot de passe n'est jamais recopié**, dans aucun sens : ArcGIS Pro ou QGIS le demande à
  l'ouverture. Dans l'extension QGIS, si une connexion enregistrée (« Gestionnaire des sources
  de données ») vise la même base avec le même utilisateur et une configuration
  d'authentification, la couche importée l'utilise et ne demande rien.
- **Oracle** : QGIS ne lit que la géométrie Oracle Spatial (`SDO_GEOMETRY`), pas le type Esri
  `ST_GEOMETRY`. Une table stockée en `ST_GEOMETRY` s'ouvre dans ArcGIS mais pas dans QGIS.
- La connexion par fichier `.sde` d'ArcGIS est remplacée par la chaîne de connexion
  équivalente (alias de base, utilisateur) : le fichier `.sde` lui-même n'est pas nécessaire.
  QGIS ne sait pas lire un fichier `.sde`, et aucun pilote libre (GDAL) non plus : c'est un
  format Esri, avec un mot de passe chiffré pour le poste. Le .lyrx contient déjà tout le
  reste (serveur, base, utilisateur), c'est ce que lyrx2qlr recopie.
- **« Fournisseur de données invalide oracle »** dans le journal de QGIS : ce QGIS ne charge pas
  son fournisseur Oracle, et la couche ne peut pas s'ouvrir, quelle que soit la conversion. Le
  fournisseur a besoin du client Oracle (`oci.dll`). Le QGIS du programme d'installation
  officiel l'apporte dans son dossier `bin`. Avec OSGeo4W, il faut le paquet
  `qgis-oracle-provider` (ou `qgis-full`). Un autre client Oracle placé avant dans le `PATH`
  (installé pour ArcGIS par exemple) peut aussi le bloquer. L'extension le détecte à l'import et
  met dans le rapport la raison donnée par Windows. Pour vérifier à la main, dans la console
  Python de QGIS : `'oracle' in QgsProviderRegistry.instance().providerList()`.
- Les autres bases (SAP HANA, Db2, Teradata…) restent « à reconnecter ».
- **À vérifier au travail** (pas d'accès à une base Oracle sur le poste de développement) :
  l'ouverture réelle d'une couche Oracle convertie, dans les deux logiciels, et la demande du
  mot de passe par ArcGIS Pro.

## Non pris en charge

**Méthodes de rendu ArcGIS** : symboles proportionnels, densité de points, carte de
chaleur, diagrammes, dictionnaire, variables visuelles (taille, couleur, rotation ou
transparence selon un champ), normalisation.

**Méthodes de rendu QGIS** : ensemble de règles complexes (seul le premier symbole est repris ;
les règles simples, une valeur par règle sur un même champ, deviennent des valeurs uniques),
« Aucun symbole »,
carte de chaleur, déplacement et agrégation de points, polygones inversés, 2,5 D,
entités fusionnées.

**Symboles** :

- Effets géométriques convertis : décalage d'un trait, « Couper », « Déplacer » sur un aplat,
  décalage du motif de tirets. Les autres effets ne le sont pas (vague, flèche…).
- Couches de symbole QGIS sans équivalent : marqueurs et remplissages SVG, dégradés, flèches,
  marqueurs aléatoires, remplissage par forme, interpolation… La liste complète est dans
  [couverture_qgis.md](couverture_qgis.md).
- Rotation selon un champ, et opacité propre à un symbole (vers ArcGIS).
- Un trait déplacé par l'effet « Déplacer » d'ArcGIS : QGIS ne sait pas déplacer un trait seul,
  il reste à sa place (annoncé).
- Options QGIS « dessiner seulement à l'intérieur du polygone » (`draw_inside_polygon`) et
  « anneaux » (`ring_filter`) : signalées « à vérifier ».

**Étiquettes** : cadre de fond, ombre, règles de placement fines Maplex (seule la méthode
principale est reprise), symboles d'appel (bulles), échelles fixées sur une règle
d'étiquettes QGIS.

**Couche** : jointures et relations de tables, filtres d'affichage, réduction d'entités,
niveaux de symboles, requêtes de page, couches raster, couches de groupe avec effets.

## À savoir

- **Polices ESRI** : 29 caractères de « ESRI Default Marker » (les plus courants : ronds,
  carrés, triangles, polygones pleins ou creux, croix, étoiles) sont remplacés par des formes
  simples, mesurées sur la police elle-même (lot 2). Les autres caractères, et les 74 autres
  polices ESRI, restent des marqueurs de police, avec un avertissement : la police doit être
  installée sur le poste QGIS (elle l'est sur un poste qui a ArcGIS Pro).
- **Placements d'étiquettes de surfaces QGIS** « autour du centroïde » et « décalé du
  centroïde » : ArcGIS n'a pas d'équivalent ; étiquettes horizontales dans la surface
  (avertissement). « Périmètre » devient « le long de la limite » (à vérifier).
- **Hexagones venant d'ArcGIS** : QGIS ne connaît que l'hexagone pointe en haut. Un hexagone
  ArcGIS côté plat en haut est donc tourné de 30°.
- **Fichiers sans couche vectorielle** (raster seul) : aucun fichier n'est produit, le rapport
  l'explique.
- **Grilles de points** : ArcGIS ne décale les lignes impaires que d'un demi-pas. Un autre
  décalage QGIS est remplacé par le demi-pas, avec un avertissement.
- **Marqueurs le long d'une ligne** : les fins ArcGIS « WithHalfGap » et « WithFullGap »
  deviennent un décalage du premier marqueur dans QGIS. « WithMarkers » n'a pas d'équivalent
  (avertissement).
- **Classes non contiguës** (QGIS) : ArcGIS n'accepte que des classes qui se suivent ;
  la borne basse est ajustée et le rapport le dit.
- **Symbole « autres valeurs » des classes ArcGIS** : sans équivalent dans QGIS.
- **Catégorie NULL de QGIS** : QGIS lui donne aussi toutes les valeurs non listées. Lue depuis
  QGIS, elle devient donc aussi le symbole « autres valeurs » d'ArcGIS. Vers QGIS, une classe
  NULL sans « autres valeurs » (ou avec un autre symbole) ne peut pas être reproduite par des
  catégories : le rapport le signale (passer à un ensemble de règles « "champ" IS NULL »).
- **Tailles QGIS en unités de carte** (mètres) : ArcGIS n'a pas cette unité pour les symboles.
  Elles sont converties en points à l'**échelle de référence** de la couche, tirée de sa plage
  de visibilité (ou gardées telles quelles s'il n'y en a pas), avec un avertissement : le
  symbole ne grandira plus en zoomant.
- **Formes de marqueur ArcGIS libres** (flèches, pictogrammes, formes en courbes de Bézier) :
  QGIS ne connaît que ses formes simples ; elles deviennent un carré ou un cercle, avec un
  avertissement.
- **Substitutions de couleurs d'une image ArcGIS** (motifs BMP repeints) : l'image est repeinte
  et écrite en PNG pour QGIS. Pour une image d'un autre format, les substitutions sont
  perdues (avertissement).
- **Motifs de brosse QGIS** (« b_diagonal », « cross »…) : remplacés par un aplat dans ArcGIS
  (avertissement) ; préférer « Remplissage par motif de lignes » dans QGIS.
- **Shapefile sans fichier .cpg** : QGIS peut lire les accents avec le mauvais encodage ; une
  valeur de classe contient alors « � » et ne correspond plus à rien dans ArcGIS. Le rapport le
  signale : ajouter un .cpg (UTF-8 ou latin-1) au shapefile et refaire la symbologie dans QGIS.
- **Expressions** : les plus simples (champs, concaténations, majuscules…) sont traduites
  par les règles de `expressions.json`. Les autres sont recopiées et marquées « à vérifier ».
- **Vérification dans ArcGIS Pro** (lot 2, ArcGIS Pro 3.7, novembre 2026) : les .lyrx produits
  à partir de tous les fichiers de test sont ouverts et réenregistrés par ArcGIS, et dessinés à
  côté de l'original. Voir [lot2.md](lot2.md). Les dessins ne seront jamais identiques au
  pixel près : lissage des bords, origine des hachures et position des glyphes de police
  diffèrent légèrement d'un logiciel à l'autre. Un trait plus fin qu'un pixel est dessiné plein
  par QGIS et pâli par ArcGIS. Le lot 2.1 a dessiné de même tout le corpus réel, sur des
  données fabriquées.
- **Polices** : un symbole de police ne se dessine bien que si la police est installée sur le
  poste (« OSMasterMap » d'Ordnance Survey, polices ESRI dans QGIS…). Sinon chaque logiciel
  dessine des carrés vides ou une police de remplacement.

Pour ajouter un cas, voir [catalogues.md](catalogues.md).
