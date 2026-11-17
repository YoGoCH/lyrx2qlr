# Boucle d'entraînement (lot 1, sans ArcGIS Pro)

Mise en œuvre des étapes 1 à 4 de l'[étude de cas](etude_entrainement_iteratif.md). Le principe :
inventer beaucoup de symbologies QGIS valides, les faire passer par la conversion aller-retour
(.qlr → .lyrx → .qlr), comparer avant/après, et corriger les catalogues là où un écart n'est pas
signalé dans le rapport.

## Les outils (`outils/entrainement/`)

| Outil | Rôle |
|---|---|
| `boucle.py` | génère les données et les symbologies, convertit, compare, écrit le rapport |
| `diagnostic.py` | compare, couche par couche, les options QGIS d'un cas avant et après |
| `couverture.py` | liste les options QGIS connues et dit si les catalogues les convertissent |

Commandes (Windows, Python de QGIS) :

```powershell
.\outils\py.ps1 outils\entrainement\boucle.py --cas 400 --graine 3 --mutations 1
.\outils\py.ps1 outils\entrainement\diagnostic.py sorties\entrainement\cas\q3_0124.qlr 0
.\outils\py.ps1 outils\entrainement\couverture.py
.\outils\py.ps1 outils\entrainement\boucle.py --figer q3_0001 q3_0005
```

- `--cas` : nombre de symbologies inventées ; `--graine` : tirage reproductible ;
  `--mutations` : variantes inventées à partir des vrais .lyrx d'exemple (valeurs changées au hasard).
- Résultats dans `sorties/entrainement/` (jamais publié) : `rapport.md` (écarts regroupés par
  nature), `fiches.json` (une fiche par cas), `cas/` (les fichiers et les images des symboles).
- `--figer` copie des cas dans `exemples/fabriques/`, avec un chemin de données relatif. Ils
  deviennent alors des tests permanents : allers-retours et passage par QGIS.

## Ce que fait la boucle

1. **Données inventées** : un GeoPackage avec des surfaces, des lignes et des points, et des
   champs `classe`, `valeur` et `code`. Il contient des valeurs pièges (vides, accents, très
   grands nombres).
2. **Symbologies** : tirées au hasard avec l'interface Python de QGIS, donc valides par
   construction :
   - couches de symbole : aplat, trait (tirets, décalage, raccourcissement), marqueurs simples
     et de police, lignes de marqueurs, hachures, grilles de points, marqueur au centre ;
   - rendus : symbole unique, catégories, classes ;
   - étiquettes.
3. **Comparaison à deux niveaux** :
   - **modèle neutre** : chaque propriété avant et après ;
   - **image** : chaque symbole est dessiné par QGIS sur une géométrie type. L'écart compte les
     pixels qui diffèrent de plus de 48 sur un canal, à un pixel près. Au-delà de 1,5 %, l'écart
     est retenu.
4. **Classement** : un écart est **annoncé** si le rapport de conversion en parle, sinon il est
   **silencieux**. Les silencieux passent en premier : ce sont des pertes dont l'utilisateur
   n'est pas prévenu.

## Résultats

| Passage | Cas | Identiques | Silencieux |
|---|---|---|---|
| Graine 1, avant corrections | 366 | 297 | 55 |
| Graine 2 | 466 | 430 | 10 |
| Graine 3 | 433 | 413 | 11 |
| Graine 3, après les dernières corrections | 433 | 397 | 1 |
| Graine 4 (cas jamais vus) | 333 | 308 | **0** |

Entre les deux passages de la graine 3, le nombre d'identiques baisse : des écarts autrefois
silencieux sont maintenant annoncés dans le rapport. C'est voulu.

Le dernier écart silencieux de la graine 3 (q3_0124, deux hachures, 2,2 %) vient de l'arrondi
des unités : 5,25 pt donnent 1,852083 mm, écrits 1,8521 mm. Les hachures glissent d'un pixel.
Ce n'est pas une erreur de conversion.

### Erreurs trouvées et corrigées

- Toute forme de marqueur QGIS était relue comme un **cercle**.
- Le **triangle** isocèle de QGIS revenait en triangle équilatéral : les formes sont maintenant
  reconnues aussi par leur proportion hauteur/largeur.
- Le **remplacement des polices ESRI** par une forme simple n'était pas signalé.
- Le **décalage des lignes impaires** d'une grille de points était perdu sans avertissement.
  ArcGIS ne connaît que le demi-pas : c'est maintenant annoncé quand la valeur diffère.
- Les extrémités `LastVertex|FirstVertex` (ordre inverse) n'étaient pas reconnues.
- Les booléens QGIS 3.44 écrits `true` / `false` n'étaient pas comparés à leur valeur neutre.
- **Effets ArcGIS** maintenant convertis :
  - « Couper » (raccourcissement du début et de la fin d'un trait) ;
  - décalage du motif de tirets ;
  - « Déplacer » sur un aplat ;
  - décalage du premier marqueur le long d'une ligne, y compris les fins « WithHalfGap » et
    « WithFullGap ».
- Le **contour d'un aplat QGIS décalé** n'était pas décalé du côté ArcGIS : il reçoit
  maintenant le même effet « Déplacer ». Au retour vers QGIS, un trait ne peut pas être déplacé
  seul : c'est annoncé.
- Un **symbole sans aucune couche** devenait dans QGIS un symbole par défaut, de couleur au
  hasard. Il devient maintenant une couche invisible.
- Les options QGIS qui changent le dessin mais n'ont pas d'équivalent (`qgis_visibles`) sont
  maintenant signalées « à vérifier » au lieu d'être ignorées. Exemples : `draw_inside_polygon`,
  `ring_filter`, `alpha`.

### Couverture des options QGIS

Voir [couverture_qgis.md](couverture_qgis.md), produit par `couverture.py`. 18 types de couche
QGIS restent sans équivalent : SVG, dégradés, flèches, marqueurs aléatoires, etc.

## À trancher avec ArcGIS Pro (lot 2)

La boucle sans ArcGIS vérifie que la conversion est **cohérente**, pas qu'elle est **juste**.
Ces points demandent ArcGIS Pro pour trancher :

1. **Fins « WithHalfGap » / « WithFullGap »** : notre équivalence (premier marqueur à un demi ou
   un intervalle entier) vient de la spécification CIM. Il faut la vérifier sur une image
   ArcGIS.
2. **Décalages des grilles de points** : sens des y et demi-pas des lignes impaires.
3. **Polices ESRI** : la table de remplacement de `polices.json` (forme, taille relative).
4. **Triangles et autres formes** : leur proportion exacte dans ArcGIS.
5. **Effet « Déplacer » sur un trait** : vérifier le sens des y.
6. Convertir en .lyrx les .qlr de `exemples/fabriques/`, les ouvrir dans ArcGIS Pro, et
   comparer les images produites par ArcPy avec celles de QGIS.
