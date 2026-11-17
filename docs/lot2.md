# Lot 2 : faire juger nos conversions par ArcGIS Pro

Démarré le **15 novembre 2026**, sur ce poste (ArcGIS Pro 3.7, licence d'association de Yoann,
niveau Advanced). C'est l'étape 1 de la [feuille de route](feuille_de_route.md) et les étapes 5–6
de l'[étude de cas](etude_entrainement_iteratif.md).

Jusqu'ici, tout ce qui touche au .lyrx était vérifié **sans ArcGIS** : selon la spécification CIM et
de vrais exemples. Le lot 2 fait d'ArcGIS Pro l'arbitre, de quatre façons.

## Les quatre contrôles

| | Contrôle | Ce qu'on vérifie | Fichiers prévus |
|---|---|---|---|
| A | **Ouverture et relecture** | ArcGIS ouvre notre .lyrx, le réenregistre ; on compare ce qu'il garde à ce qu'on a écrit | ≈ 1 500 |
| B | **Dessin croisé** | le même jeu de données dessiné « avant » par le logiciel d'origine et « après » par l'autre, avec notre fichier | ≈ 490 planches |
| C | **Vérité du côté ArcGIS** | ArcPy fabrique des symbologies justes par construction ; on les convertit vers QGIS et retour | 400 par tirage |
| D | **Polices ESRI** | chaque caractère de `polices.json` dessiné par ArcGIS, comparé au marqueur QGIS de remplacement | 75 polices installées, 10 suivies |

### A. Ouverture et relecture (sans dessin, rapide)

| Source | Sens | Fichiers | Aller-retour |
|---|---|---|---|
| `exemples/qlr` | QGIS → .lyrx | 42 | QGIS → ArcGIS → QGIS |
| corpus QGIS (204 .qml, 5 .qlr) | QGIS → .lyrx | 209 | QGIS → ArcGIS → QGIS |
| `exemples/lyrx` | .lyrx → .qlr → .lyrx | 33 | ArcGIS → QGIS → ArcGIS |
| corpus ArcGIS | .lyrx → .qlr → .lyrx | 205 | ArcGIS → QGIS → ArcGIS |
| boucle d'entraînement | cas inventés | 400 × 3 tirages | les deux sens |

Total : environ **1 500 ouvertures** dans ArcGIS, **490 allers-retours sur des fichiers réels** et
1 200 sur des cas inventés. On compte : les fichiers refusés, les propriétés qu'ArcGIS efface ou
corrige en réenregistrant (signe d'une valeur mal écrite), et les allers-retours qui ne reviennent
pas identiques.

### B. Dessin croisé (le test qui manquait)

| Source | Avant | Après | Planches |
|---|---|---|---|
| `exemples/qlr` avec leurs shapefiles | QGIS, fichier d'origine | ArcGIS, notre .lyrx | 41 |
| `exemples/lyrx` avec leurs shapefiles | ArcGIS, fichier d'origine | QGIS, notre .qlr | 33 |
| corpus (sans données) | logiciel d'origine | l'autre logiciel | 414, sur des données inventées |

Chaque planche montre trois vues côte à côte : **avant | après | différences**. Les deux dessins
utilisent la même emprise, la même taille et aucun fond de plan. Seuls les pixels dessinés
comptent. Une planche est « concordante » sous 10 % de pixels différents. Ce seuil sera ajusté
après les premières séries : les deux moteurs ne lissent pas les bords de la même façon.

### C et D

Ces deux contrôles viennent **après** A et B. C demande d'écrire un générateur ArcPy, le pendant
de celui de la boucle. D demande un petit script qui dessine les caractères un par un.

## Bilan (16 novembre 2026, v1.3.0)

**Lot 2 terminé.** Plus de 1 000 fichiers produits par lyrx2qlr ont été relus par ArcGIS Pro 3.7,
173 planches de dessin croisé ont été regardées, et **onze défauts réels ont été trouvés et
corrigés**. Aucun n'était visible avec les seuls allers-retours.

### Les chiffres

| Contrôle | Fichiers | Résultat |
|---|---|---|
| A. relecture, fichiers réels (exemples + corpus) | 489 | 483 identiques après réenregistrement par ArcGIS ; 5 couches raster refusées proprement ; 1 .qml sans type de géométrie, qu'ArcGIS déduit (connu) |
| A. .lyrx d'origine ouverts par ArcGIS | 238 | 238 |
| A. relecture, cas de la boucle d'entraînement | 425 | 0 changement de sens ; ArcGIS efface seulement un bloc d'étiquettes sans effet (126 fichiers) |
| A'. valeurs comparées à la spécification CIM d'Esri | tous | 0 valeur inconnue après correction |
| B. dessin croisé QGIS → ArcGIS (exemples) | 41 planches | 27 concordantes ; 8 à examiner, toutes expliquées ; 6 douteuses (données presque vides à cette échelle) |
| B. dessin croisé ArcGIS → QGIS (exemples) | 32 planches | 24 concordantes ; 4 à examiner, toutes expliquées ; 3 douteuses ; 1 dessin trop long |
| C. symbologies fabriquées par ArcPy (2 tirages) | 100 | 100 allers-retours identiques ; dessin : 73 concordantes, 6 à examiner (expliquées), 21 douteuses (lignes trop courtes du premier tirage) |
| D. polices ESRI remplacées | 29 caractères | formes pleines : 86 à 100 % de recouvrement ; croix 81 à 90 % ; formes creuses 18 à 100 % (trait un peu plus fin) |

Contrôles du modèle après les corrections : 214 tests ; boucle d'entraînement (graines 12 et 13,
800 cas) : 0 écart silencieux, 0 erreur ; corpus réel dans les deux sens : 0 erreur interne,
0 aller-retour instable.

### Les onze défauts corrigés

| # | Défaut | Trouvé par | Effet avant correction |
|---|---|---|---|
| 1 | Placements d'étiquettes de surfaces « autour » et « périmètre » écrits avec des valeurs qui n'existent pas dans ArcGIS | relecture | ArcGIS les remplaçait en silence |
| 2 | Découpage des grilles de marqueurs (« entiers dedans », « centre dedans ») | relecture | idem |
| 3 | Contour de marqueur écrit sans épaisseur | relecture | ArcGIS lui donnait 4 pt |
| 4 | Décalage d'étiquette absent | relecture | ArcGIS mettait 1 pt |
| 5 | Poids des étiquettes (`barrierWeight`) | relecture | valeur modifiée par ArcGIS |
| 6 | Table des polices ESRI approximative | contrôle D | formes, tailles et pleins / creux faux |
| 7 | Hexagone dans le mauvais sens, octogone absent | contrôle D | forme tournée de 30° |
| 8 | Hachures dont le trait est décalé d'une période | dessin croisé (C) | rien de dessiné dans QGIS |
| 9 | Anciens noms d'options QGIS (`outline_color` d'un trait) | dessin croisé (B) | traits noirs de 1 pt dans ArcGIS (29 fichiers de test) |
| 10 | Contours de marqueurs agrandis par ArcGIS (`scaleSymbolsProportionally`) | dessin croisé (B) | contour jusqu'à 4,5 fois trop épais |
| 11 | Valeur de classe contenant « � » (shapefile sans `.cpg`) | dessin croisé (B) | aucune classe ne correspondait dans ArcGIS ; désormais signalé |

### Qualité supposée du modèle de correspondance

- **Ce que le .lyrx produit contient est juste pour ArcGIS** : il le relit à l'identique dans
  99 % des cas réels, et le reste est expliqué.
- **Le dessin est fidèle pour les cas courants** (aplats, traits, tirets, hachures, marqueurs
  simples, catégories, classes) : quand une planche diffère, c'est le banc d'essai (étiquettes,
  données presque vides) ou le lissage, pas la conversion.
- **Points encore approximatifs**, connus et annoncés : origine des hachures et des grilles
  (décalage de phase), position verticale des glyphes de police (1 à 2 pixels), formes creuses
  des polices ESRI (trait un peu fin), et tout ce que liste [limites.md](limites.md).
- **Limite du lot 2 lui-même** : les exemples dessinés sont surtout suisses et
  « administratifs ». Le lot 2.1 (ci-dessous) a levé cette limite en fabriquant des données
  pour tout le corpus.

## Lot 2.1 : dessiner le corpus sans données (16 novembre 2026)

Le lot 2 n'avait dessiné que nos exemples suisses : le **corpus réel** (414 fichiers du
Royaume-Uni, du Québec, d'Israël, d'Esri, de GeoStyler…) n'avait été que relu, faute de
données. Le lot 2.1 **fabrique ces données** à partir des symbologies elles-mêmes.

### La méthode

`outils/lot2/fabriquer_donnees.py` lit chaque fichier et produit un **GeoPackage** :

- une table par couche, avec les champs utilisés par la symbologie (valeurs uniques, classes,
  filtres de règles) ;
- **une case par classe** : un carré pour une surface, un zigzag pour une ligne, un point au
  centre pour un point. Chaque entité porte les valeurs qui la font tomber dans sa classe ; une
  case « autres valeurs » reçoit une valeur absente de toutes les classes ;
- les filtres de règles (`=`, `<>`, `<`, `>`, `IN`, `LIKE`, `IS NULL`, `AND`, `OR`) sont
  résolus pour trouver une valeur qui les satisfait : **0 filtre non satisfait** sur le corpus ;
- le système de coordonnées suit la provenance (MN95 par défaut, Lambert du Québec, British
  National Grid) ; la taille des cases suit l'échelle de la couche (visibilité, ou 1:5 000) ;
- un plan (`.plan.json`) décrit les cases : le comparateur sait ainsi **quelle classe** diffère,
  et l'encadre en rose sur la planche.

Les deux logiciels dessinent ensuite le même GeoPackage : chaque source est rebranchée dessus
(`gpkg|layername=…` dans QGIS, connexion « Sql » dans ArcGIS), et les filtres de couche sont
retirés pour que toutes les cases soient visibles.

### Les chiffres

| Série | Fichiers | Concordantes | À examiner | Douteuses | Échecs |
|---|---|---|---|---|---|
| ArcGIS → QGIS (.lyrx du corpus) | 200 | 147 | 42 | 11 | 0 |
| QGIS → ArcGIS (.qml et .qlr du corpus) | 203 | 56 | 100 | 47 | 0 |

403 des 414 fichiers ont reçu des données (les autres : raster seul ou sans couche vectorielle).
Côté QGIS, **200 des 203 fichiers viennent d'Ordnance Survey** : leurs symboles utilisent la
police « OSMasterMap », absente de ce poste, que QGIS dessine lui-même en carrés vides dans
l'image **d'origine**. Ces planches mesurent le banc d'essai, pas la conversion.

### Les six défauts corrigés

| # | Défaut | Effet avant correction |
|---|---|---|
| 12 | Tailles QGIS en unités de carte (mètres) gardées telles quelles | un trait de 2 m devenait 2 pt ; désormais converti à l'échelle de référence de la couche (avertissement « 1:2 000 ») |
| 13 | Décalage du contour d'une surface : ArcGIS compte le négatif vers l'intérieur, QGIS vers l'extérieur | contour dessiné du mauvais côté (fichier AGR.CADASTRE_VITICOLE du lot 2) |
| 14 | Catégorie NULL de QGIS : elle dessine aussi toutes les valeurs non listées | lue comme « autres valeurs » ; vers QGIS, l'écart est annoncé (3 fichiers WFD) |
| 15 | Formes de marqueur en courbes de Bézier prises pour des cercles | dessinées en cercle sans rien dire ; désormais annoncées |
| 16 | Décalage des hachures : `offsetX` / `offsetY` sont dans le repère de la carte (ArcGIS), et le sens du décalage QGIS dépend du quadrant de l'angle | hachures intercalées superposées ou décalées (13 fichiers) |
| 17 | Remplissages par image BMP avec substitutions de couleurs (`colorSubstitutions`) | motif noir sur fond blanc opaque au lieu de vert sur fond transparent (8 fichiers, 33 remplissages) ; l'image est désormais repeinte en PNG |

Chaque sens et chaque angle ont été **mesurés** dans les deux logiciels avant d'écrire la règle
(catalogue `symboles.json`, clés `qgis_facteur_selon_genre` et `qgis_signe_selon_angle`).

### Ce qui reste, et pourquoi

| Cause | Fichiers | Statut |
|---|---|---|
| Formes de marqueur CIM libres (flèches, pictogrammes, épingles) remplacées par un carré | ≈ 10 (≈ 280 marqueurs) | annoncé ; **piste : les écrire en SVG intégré dans QGIS** |
| Police OSMasterMap absente du poste (Ordnance Survey) | ≈ 200 | banc d'essai : QGIS dessine des carrés vides dans l'original |
| Polices ESRI dans QGIS (caractères non remplacés) | 4 | annoncé (installer la police) |
| Classe NULL sans « autres valeurs » vers QGIS | 3 | annoncé ; seul un ensemble de règles le permettrait |
| Motifs de brosse QGIS (`b_diagonal`, `cross`…) remplacés par un aplat | 1 | annoncé |
| Origine des hachures et des grilles (décalage de phase) | quelques-uns | même dessin, simple décalage du motif |
| Traits plus fins qu'un pixel : QGIS les dessine pleins, ArcGIS les pâlit | Ordnance Survey | différence des moteurs de dessin |

Contrôles après les corrections : 223 tests ; corpus réel dans les deux sens : 0 erreur interne,
0 aller-retour instable ; boucle d'entraînement (graines 14 à 17) : 0 écart silencieux.

## Où sont les résultats

Dossier **`comparaisons_lot2/`** à la racine du dépôt. Il reste sur ce poste : il est ignoré par
git, car les images montrent les données locales. Un sous-dossier par série :

- `concordantes/` : planches où les deux logiciels dessinent pareil ;
- `a_examiner/` : planches avec des différences, à regarder une par une ;
- `douteuses/` : image vide ou fond non blanc (problème de dessin, pas de conversion) ;
- `lyrx/` : les .lyrx produits, à ouvrir à la main dans ArcGIS Pro si besoin ;
- `resume.md` : tableau de toutes les planches, de la plus différente à la plus proche.

Chaque planche a deux rangées : la vue d'ensemble, puis une **vue rapprochée** sur la zone la plus
dense (1/6 de la largeur), où les symboles se voient vraiment.

### Comment une planche est jugée

1. Les images sont posées sur du blanc (ArcGIS exporte un fond transparent, qui deviendrait noir).
   L'histogramme vérifie ensuite que le fond est bien blanc et que l'image n'est pas vide.
2. **Formes** : la vue rapprochée est réduite 8 fois avant comparaison. Une hachure ou une grille de
   marqueurs devient une teinte : leur origine (le point de départ du motif) diffère d'un logiciel à
   l'autre sans que le dessin soit faux.
3. **Couleurs** : on compare les **teintes dominantes** de la vue rapprochée (18 teintes, plus les
   gris). Un trait fin lissé se mêle au blanc, ce qui change sa clarté mais pas sa teinte.
4. Concordante : moins de 10 % de pixels différents **et** moins de 10 % d'écart de teintes.

Limites connues de la mesure : deux couleurs qui se mêlent (hachure rose sur fond bleu) donnent une
teinte intermédiaire, et une grille de marqueurs au pas large garde un écart d'origine. Ces planches
restent « à examiner » et sont jugées à l'œil.

## Commandes

```bash
# B. dessin croisé : QGIS → ArcGIS (exemples/qlr) puis ArcGIS → QGIS (exemples/lyrx)
bash outils/lot2/lancer.sh qgis   serie1_qgis_vers_arcgis
bash outils/lot2/lancer.sh arcgis serie2_arcgis_vers_qgis
```

```powershell
$arcpy = "C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe"
# A. relecture par ArcGIS (fichiers réels ; même commande sur un dossier de la boucle d'entraînement)
& $arcpy outils\lot2\relecture.py exemples\qlr exemples\lyrx corpus\fichiers --sortie comparaisons_lot2\relecture_v3
# A'. valeurs conformes à la spécification CIM d'Esri (dépôt github.com/Esri/cim-spec cloné à part)
.\outils\py.ps1 outils\lot2\verifier_cim.py --spec CHEMIN\cim-spec\docs\v3 comparaisons_lot2\relecture_v3 --sortie comparaisons_lot2\verification_cim.md
# C. symbologies fabriquées par ArcGIS, puis leur dessin croisé
& $arcpy outils\lot2\generateur_arcpy.py --cas 40 --graine 2 --donnees donnees_locales --sortie comparaisons_lot2\arcpy_g2
bash outils/lot2/lancer.sh arcgis arcpy_g2_dessins comparaisons_lot2/arcpy_g2/fichiers/*.lyrx
# D. polices ESRI (dans QGIS, avec les polices du dossier d'ArcGIS Pro)
.\outils\py.ps1 outils\lot2\polices_esri.py --sortie comparaisons_lot2\polices
```

Lot 2.1 (corpus sans données) : fabriquer les GeoPackage, puis dessiner dans les deux sens.

```powershell
.\outils\py.ps1 outils\lot2\fabriquer_donnees.py corpus\fichiers --sortie comparaisons_lot2\corpus
```

```bash
F=comparaisons_lot2/corpus/fichiers
DONNEES=comparaisons_lot2/corpus/donnees bash outils/lot2/lancer.sh arcgis c21_corpus_arcgis $F/*.lyrx
DONNEES=comparaisons_lot2/corpus/donnees bash outils/lot2/lancer.sh qgis   c21_corpus_qgis   $F/*.qml $F/*.qlr
```

La série complète dure plusieurs heures (un processus par fichier) : la lancer en arrière-plan.

Les dessins se font **un fichier par processus**, avec une limite de temps : un fichier trop lourd
(hachures très denses, par exemple) ne bloque pas toute la série.

## Terminé quand

- A : 0 fichier refusé, 0 propriété effacée par ArcGIS sans raison connue ;
- B : chaque planche « à examiner » est soit corrigée, soit expliquée par un écart annoncé dans
  le rapport de conversion ou dans [limites.md](limites.md) ;
- C et D : faits sur au moins un tirage, avec les polices ESRI de `polices.json` vérifiées.

**État au 16.11.2026 : les trois conditions sont remplies.** A : 0 propriété effacée sans
raison connue (5 rasters refusés proprement, annoncés). B : toutes les planches « à examiner »
sont corrigées ou expliquées (voir le bilan). C : deux tirages (100 cas) ; D : 29 caractères.

## Journal

- **15.11.2026** : ArcGIS Pro 3.7 installé ; les 42 .lyrx produits depuis `exemples/qlr` s'ouvrent
  tous. Premier dessin croisé : outil en place (`outils/lot2/`).
- **16.11.2026** : lot 2 terminé (v1.3.0). Relecture finale, dessin croisé des exemples dans les
  deux sens et de 100 symbologies ArcPy ; onze défauts corrigés (voir le bilan).
- **16.11.2026** : lot 2.1. Données fabriquées (GeoPackage) pour 403 fichiers du corpus, dessin
  croisé dans les deux sens ; six défauts de plus corrigés (unités de carte, décalage des
  contours et des hachures, catégorie NULL, courbes de Bézier, images BMP repeintes).
