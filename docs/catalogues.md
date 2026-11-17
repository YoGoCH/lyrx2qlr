# Les catalogues : ajouter une correspondance sans toucher au code

Toute la connaissance « ArcGIS ↔ QGIS » vit dans des fichiers JSON, dans
`src/lyrx2qlr/catalogues/`. Le code Python ne fait que lire ces tables. Pour qu'un
nouveau cas soit converti, on ajoute une ligne dans le bon catalogue.

Chaque fichier commence par une rubrique `_doc` qui explique ses champs.

## Le principe : une valeur neutre au milieu

Chaque notion a un nom **neutre** (`pivot`), qui ne dépend d'aucun des deux logiciels.
La conversion passe toujours par ce nom neutre :

```
.lyrx  →  modèle neutre  →  .qlr
.qlr   →  modèle neutre  →  .lyrx
```

Les unités neutres sont :

| Notion | Unité neutre |
|---|---|
| longueur (épaisseur, taille, décalage) | point typographique (pt) |
| couleur | `[rouge, vert, bleu, opacité]`, chacun de 0 à 255 |
| angle | degrés, sens inverse des aiguilles d'une montre |
| échelle | dénominateur (25000 pour 1:25 000) |

## Quel fichier pour quoi ?

| Fichier | Contenu |
|---|---|
| `symboles.json` | Types de couches de symboles (aplat, trait, hachures, marqueurs…) et leurs propriétés |
| `placements.json` | Placement des marqueurs (grille, le long d'une ligne, sommets, centre…) |
| `listes.json` | Tables de valeurs : extrémités de ligne, jointures, styles de police, placements d'étiquettes, méthodes de classement… |
| `etiquettes.json` | Propriétés des étiquettes |
| `formes.json` | Formes de marqueurs simples (cercle, carré, étoile…) |
| `polices.json` | Polices de symboles ESRI et leur remplacement dans QGIS |
| `unites.json` | Unités de longueur et leur facteur vers le point |
| `couleurs.json` | Modèles de couleur ArcGIS (RGB, HSV, CMYK, Lab…) |
| `sources.json` | Types de sources de données (shapefile, géodatabase fichier, GeoPackage, base d'entreprise) |
| `expressions.json` | Règles de traduction des expressions (Arcade, VBScript, Python, SQL ↔ QGIS) |
| `formats.json` | Versions de fichiers lues et écrites |
| `rendus.json` | Méthodes de rendu (symbole unique, catégories, classes) et celles non prises en charge |
| `ignorer.json` | Propriétés qu'on sait ne pas convertir et qu'il est inutile de signaler |

## Exemples

### Ajouter une valeur dans une liste

Une nouvelle extrémité de ligne, dans `listes.json`, rubrique `extremites_ligne` :

```json
{"pivot": "triangle", "lyrx": "Triangle", "qgis": "triangle"}
```

La **première** ligne qui correspond gagne, dans les deux sens. Pour qu'une valeur ne
soit lue que d'un côté, ne remplissez que ce côté (`"lyrx": null`).

Autres réglages d'une ligne de liste :

- `qgis_extra` : options QGIS écrites en plus (par exemple `"placement@placementFlags": "10"`).
  À la lecture, quand plusieurs lignes ont la même valeur QGIS, celle dont les `qgis_extra`
  correspondent au fichier est choisie : c'est ainsi que « ligne décalée » et « ligne centrée »
  sont distinguées.
- `avertissement_lyrx` / `avertissement_qgis` : message émis quand la valeur est écrite de ce
  côté. Avec `"lyrx": null`, la valeur n'a pas d'équivalent ArcGIS : le message l'annonce (par
  exemple la casse « Titre » de QGIS).

### Ajouter une propriété à une couche de symbole

Dans `symboles.json`, dans la couche concernée, rubrique `proprietes` :

```json
{"nom": "decalage", "type": "longueur", "lyrx": "offset", "qgis": "offset", "qgis_unite": "offset_unit"}
```

- `lyrx` est le chemin dans l'objet ArcGIS. Il accepte des points et des filtres :
  `symbol.symbolLayers[type=CIMSolidFill].color`.
- `qgis` est le nom de l'option QGIS. Pour les étiquettes, c'est
  `élément/sous-élément@attribut`.

Types possibles :

| Type | Sens |
|---|---|
| `couleur` | couleur, convertie selon le modèle de couleur |
| `longueur`, `longueurs` | une ou plusieurs longueurs, converties en points |
| `angle` | angle (le sens est corrigé si besoin) |
| `nombre`, `entier` | nombre sans unité |
| `texte` | texte recopié |
| `booleen` | vrai / faux |
| `liste` | valeur passée par une table de `listes.json` (champ `liste`) |
| `caractere` | numéro de caractère d'une police |
| `image` | image intégrée (base64) |
| `forme` | forme de marqueur (voir `formes.json`) |
| `expression` | expression traduite par `expressions.json` |
| `tirets_qt` | motif de tirets QGIS |
| `decalage_impair` | décalage des lignes impaires d'une grille |

Champs facultatifs utiles :

| Champ | Effet |
|---|---|
| `defaut` | valeur neutre quand la propriété manque |
| `qgis_si`, `lyrx_si` | lire seulement si une autre propriété a telle valeur (`"!null"` = présente, `">0"` = nombre positif) |
| `qgis_si_present`, `qgis_si_absent` | options QGIS ajoutées à l'écriture selon la présence de la valeur |
| `lecture_seule` | `"qgis"` ou `"lyrx"` : la propriété n'est jamais écrite dans ce format |
| `geometrie` | `point`, `ligne` ou `surface` : ne s'applique qu'à ce type de couche |
| `zero_est_absent` | un zéro veut dire « pas de valeur » |
| `qgis_composante`, `qgis_facteur` | une partie d'une option QGIS à plusieurs nombres (`offset` = « x,y ») et un facteur (−1 pour les y, comptés vers le bas dans QGIS) |
| `sens` | `"vers_lyrx"` : lue dans QGIS et écrite dans ArcGIS seulement ; vers QGIS, un avertissement (`avertissement_qgis`) remplace l'écriture |
| `qgis_facteur_selon_genre` | facteur supplémentaire selon le genre du symbole (`{"surface": -1}` : le décalage d'un contour de surface change de sens) |
| `qgis_signe_selon_angle` | signe du décalage QGIS selon l'angle (hachures) : valeurs pour les axes 0, 90, 180, 270, puis pour chaque quadrant |
| `lyrx_perpendiculaire` | décalage CIM donné en x / y dans le repère de la carte : seule la composante perpendiculaire aux traits est gardée |
| `lyrx_substitutions` | (image) clé CIM des substitutions de couleurs, appliquées à l'image elle-même (BMP → PNG) |

Autres réglages :

- **Placements** (`placements.json`) : `lyrx_fins` convertit les fins de ligne d'ArcGIS
  (`endings`) en décalage du premier marqueur. Chaque valeur a un facteur de l'intervalle :
  `WithHalfGap` vaut 0,5. Une valeur sans équivalent (`null`) donne un avertissement.
- **Décompositions** (`symboles.json`, `decompositions_qgis`) : une couche QGIS qui devient
  plusieurs couches ArcGIS. Par exemple, le contour d'un aplat devient un trait. `renommer` dit
  quelles options passent à la couche ajoutée.
- **Genres** (`symboles.json`, `genres`) : `qgis_vide` est la couche invisible écrite quand un
  symbole n'a aucune couche. Sinon, QGIS mettrait un symbole par défaut.
- **Formes** (`formes.json`) : la `signature` reconnaît une forme ArcGIS par sa géométrie
  (genre, nombre de sommets, proportion hauteur/largeur).
- **Options QGIS ignorées** (`ignorer.json`) :
  - `qgis` : options sans intérêt, ignorées sans rien dire ;
  - `qgis_neutres` : ignorées seulement si elles ont leur valeur neutre (par exemple
    `alpha` = 1) ;
  - `qgis_visibles` : options qui changent le dessin, signalées « à vérifier » quand elles ne
    sont pas converties ;
  - un motif « Classe.option » ne vaut que pour cette classe QGIS (par exemple
    `SimpleLine.outline_width`, option héritée sans effet sur un trait, alors que
    `SimpleFill.outline_width` est l'épaisseur du contour).
- **Règles QGIS simples** (`rendus.json`, `regles_qgis_simples`) : les deux formes de filtre
  (`"champ" = 'valeur'` et `"champ" IN (…)`) qui permettent de lire un ensemble de règles comme
  des valeurs uniques. Une règle `ELSE` devient « toutes les autres valeurs ».

### Ajouter un type de couche de symbole

Copier une entrée de `symboles.json`, changer `pivot`, `lyrx.type`, `qgis.classe`,
le `modele` (l'objet ArcGIS de départ) et les `proprietes`. Avec `"sens": "lecture_qgis"`,
l'entrée ne sert qu'à lire les .qlr (utile pour une variante QGIS sans équivalent exact).
Un `avertissement` est recopié dans le rapport chaque fois que l'entrée sert.

### Remplacer un caractère de police ESRI

Dans `polices.json`, rubrique `substitutions` :

```json
{"police": "ESRI Default Marker", "caractere": 40, "forme": "circle", "facteur_taille": 0.7,
 "rendu": "creux", "epaisseur": 0.03}
```

- `forme` : un nom de `formes.json` ;
- `facteur_taille` : taille de la forme QGIS = taille de la police × facteur. Un glyphe n'occupe
  qu'une partie de la hauteur de la police (environ 0,7 pour « ESRI Default Marker ») ;
- `rendu` : `plein` (forme remplie, sans contour visible), `creux` (contour seul) ou `trait`
  (croix : dessinée par le contour). Pour `creux` et `trait`, `epaisseur` est l'épaisseur du trait
  du glyphe, en fraction de la taille de la police ;
- `angle` (facultatif) : rotation ajoutée quand la forme QGIS n'a pas la même orientation que le
  glyphe (hexagone : 30°).

Ne pas deviner ces valeurs : les mesurer. `outils/lot2/polices_esri.py` (dans QGIS, avec les
polices installées par ArcGIS Pro) dessine le vrai glyphe sous le remplacement et donne leur
recouvrement et le rapport de taille ; corriger `facteur_taille` en le divisant par ce rapport.
Les formes pleines doivent dépasser 85 % de recouvrement.

### Ajouter un type de base de données (`sources.json`)

Une base d'entreprise a une entrée avec un bloc `base`, qui décrit comment passer de la chaîne
de connexion d'ArcGIS (`CLE=valeur;…`) à l'adresse QGIS (`cle='valeur' … table="S"."T" (geom)`) :

- `lyrx.workspaceFactory` (`SDE`) et `base.si` (par exemple `{"DBCLIENT": "oracle"}`) :
  reconnaître la base dans un .lyrx ; `qgis.fournisseur` (`oracle`, `postgres`, `mssql`) : dans
  un .qlr ;
- `base.serveur` : forme du serveur, `oracle` (alias ou `hôte:port/service`) ou `virgule`
  (`hôte,port`) ;
- `base.cles_lyrx` et `base.cles_qgis` : clé de chaque côté → nom neutre (`base`, `hote`, `port`,
  `utilisateur`, `authentification`, `version`, `cle`, `srid`) ;
- `base.fixe_lyrx` et `base.fixe_qgis` : valeurs toujours écrites, avec `{serveur}` remplacé ;
- `base.jeu_lyrx` : forme du nom du jeu ArcGIS (`{schema}.{table}` ou `{base}.{schema}.{table}`) ;
- `base.defauts` : colonne de géométrie et clé quand le fichier n'en dit rien ;
- `base.remarque_qgis` (facultatif) : recopiée dans le rapport.

Le mot de passe (`ENCRYPTED_PASSWORD`, `password=`) n'est jamais lu ni écrit, quel que soit le
catalogue. Une base sans entrée reste « à reconnecter » (entrée de repli `sde`).

### Vérifier qu'une valeur ArcGIS existe

Une valeur écrite dans un .lyrx qui n'existe pas dans le format CIM est **remplacée en silence**
par ArcGIS (relecture du lot 2). Avant d'ajouter une valeur `lyrx` dans `listes.json`, la chercher
dans la spécification publiée par Esri ([github.com/Esri/cim-spec](https://github.com/Esri/cim-spec),
rubriques « Enumeration »), ou lancer `outils/lot2/verifier_cim.py`.

## Vos propres catalogues, sans modifier ceux du projet

Placez dans un dossier des fichiers de même nom ne contenant que vos ajouts, puis :

```bash
lyrx2qlr mes_couches/ -o sorties/ -c mon_dossier_de_catalogues
```

Vos lignes passent **devant** celles du projet : elles gagnent en cas de doublon.

## Vérifier après une modification

```bash
lyrx2qlr --verifier-catalogues
```

puis lancer les tests (voir le README). Le contrôle signale les chemins mal formés, les
listes inconnues, les doublons et les types de propriété inconnus.
