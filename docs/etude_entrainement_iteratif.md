# Étude de cas : améliorer les conversions par itérations automatiques

Question posée (13 novembre 2026) : sans ArcGIS Pro, mais avec QGIS et la documentation des deux
formats, peut-on inventer des jeux de données et des symbologies, les convertir, comparer, et
affiner les catalogues encore et encore ? Une licence ArcPy aiderait-elle ?

## Réponse courte

**Oui, en grande partie, et une licence ArcGIS Pro comblerait le reste.**

- **Sans ArcGIS Pro**, une boucle automatique peut trouver et corriger tout ce que QGIS sait
  vérifier : les propriétés QGIS oubliées par les catalogues, les pertes à l'aller-retour, les
  plantages et les cas limites. Elle ne peut pas prouver qu'**ArcGIS** comprend nos .lyrx comme
  nous le croyons.
- **Avec ArcGIS Pro et ArcPy sur le même poste**, ArcGIS devient l'arbitre : il relit nos .lyrx,
  les réécrit et les dessine. On compare alors deux images, celle d'ArcGIS et celle de QGIS. C'est
  le seul moyen de corriger les erreurs que la boucle sans ArcGIS ne voit pas.
- Le mot « entraîner » doit être pris au sens large. Il n'y a pas de réseau de neurones : la boucle
  produit des **corrections de catalogues JSON**, chacune protégée par un nouveau test. Le résultat
  reste lisible et maintenable par Yoann, comme le veut le projet.

## 1. Le problème de fond : qui dit la vérité ?

Pour comparer, il faut un **arbitre**, c'est-à-dire une référence extérieure au convertisseur.

| Ce qu'on veut vérifier | Arbitre disponible aujourd'hui | Fiabilité |
|---|---|---|
| QGIS comprend le .qlr produit | **QGIS lui-même** : chargement, réenregistrement, dessin | totale |
| Le .lyrx garde toute l'information du .qlr | aller-retour .qlr → .lyrx → .qlr, puis **dessin par QGIS** des deux .qlr | bonne |
| ArcGIS comprend le .lyrx produit | aucun sans ArcGIS Pro | — |
| Notre lecture d'un .lyrx est juste | les 33 .lyrx réels (produits par ArcGIS), la spécification CIM d'Esri | partielle |

Le point faible est connu : une **erreur symétrique**, où le lecteur et l'écrivain du .lyrx se
trompent de la même façon, passe tous les allers-retours. Un exemple réel : la règle « un vrai/faux
absent vaut faux » était mal comprise des deux côtés. Les tests aller-retour passaient ; c'est un
aperçu dessiné (des étiquettes affichées en trop) qui l'a révélée. La documentation Esri le dit
pourtant clairement : le CIM « only persists nondefault properties »
([accès au CIM depuis Python](https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/python-cim-access.htm)).

**Conclusion** : sans ArcGIS, on peut rendre le convertisseur cohérent et complet du côté QGIS, mais
la justesse du côté ArcGIS ne repose que sur la lecture de la spécification et sur les vrais .lyrx.

## 2. La boucle sans ArcGIS Pro (faisable tout de suite)

```
 ┌─► 1. Générer   données inventées + symbologie QGIS crédible (API PyQGIS)
 │   2. Convertir .qlr → .lyrx → .qlr
 │   3. Comparer  modèle neutre, puis images QGIS de l'original et du retour
 │   4. Classer   écart nouveau ? → fiche d'écart (propriété, valeurs, image)
 │   5. Corriger  ligne de catalogue (ou code si c'est une notion nouvelle)
 │   6. Figer     le cas devient un test dans exemples/fabriques/
 └── 7. Recommencer, en visant les zones encore peu couvertes
```

### 2.1 Générer des données inventées

C'est facile et sans risque. Avec QGIS ou GDAL, on produit des GeoPackages synthétiques :

- une grille de surfaces avec des trous, des surfaces en plusieurs parties et de toutes petites
  surfaces ;
- des lignes courbes, fermées, très courtes ;
- des points, y compris superposés ;
- des champs texte, entier et décimal, avec des valeurs NULL, des accents, des valeurs vides et des
  valeurs très longues.

Ces jeux restent petits (quelques centaines d'entités) : dessin rapide, aucune donnée réelle.

### 2.2 Générer des symbologies crédibles

Le point clé est de **générer du côté QGIS**. Une symbologie construite avec l'API PyQGIS est
forcément valide, puisque QGIS la vérifie lui-même. Générer directement des .lyrx produirait des
fichiers qu'ArcGIS pourrait refuser, sans que personne ne le voie.

Trois sources de cas, à mélanger :

1. **Tirage au sort dans l'espace des catalogues** : pour chaque type de couche de symbole
   convertible, on tire des valeurs dans les plages réalistes (épaisseurs de 0,1 à 5 mm, couleurs,
   angles, styles des listes). C'est une méthode de « test par propriétés » : on ne vérifie pas un
   résultat précis, mais une règle (« l'aller-retour ne change rien »).
2. **Mutations de vrais fichiers** : on reprend les 75 exemples et on change une propriété à la
   fois. Les cas restent proches de la réalité de Yoann.
3. **Couverture systématique** : QGIS fournit pour chaque type de couche de symbole la liste de ses
   propriétés (`properties()`). On compare cette liste aux catalogues : chaque propriété absente est
   soit à ajouter, soit à classer dans `ignorer.json`, soit à signaler dans `limites.md`.

### 2.3 Comparer à trois niveaux

| Niveau | Comment | Ce que ça attrape |
|---|---|---|
| Modèle neutre | `comparer_documents` (déjà en place) | toute valeur perdue ou déformée |
| Échantillon de symbole | image d'un seul symbole, 200 × 200 px, original contre retour | erreurs d'unité, d'ordre des couches, de couleur |
| Carte complète | `outils/apercu_qgis.py` sur les données inventées | filtres, échelles, étiquettes, catégories |

Pour les images, on mesure la part de pixels différents au-delà d'une petite tolérance (lissage
des bords). L'échantillon de symbole est le plus utile, car il isole la cause. Les étiquettes se
comparent plutôt par leurs propriétés : le moindre changement de réglage déplace leur placement,
et l'image ne dit pas pourquoi.

### 2.4 Rythme et coût

La suite actuelle (177 tests, dont le passage par QGIS) tourne en une quinzaine de secondes. Une
boucle de **1000 cas générés** se compte donc en minutes, et le dessin des échantillons ajoute peu.
Le coût réel est ailleurs : **décider de chaque correction**. Pour éviter de « coller » aux cas
inventés (sur-apprentissage), trois règles :

- une correction ne va **dans le catalogue** que si elle s'appuie sur la spécification CIM, sur la
  documentation QGIS ou sur un vrai fichier ;
- chaque écart corrigé devient un **test permanent** : la boucle ne peut pas défaire une
  correction précédente ;
- un écart que la spécification ne permet pas de trancher est **mis de côté** pour l'arbitre
  ArcGIS (partie 3), plutôt que deviné.

### 2.5 Ce que cette boucle trouvera (estimation)

- **Probablement** : des propriétés QGIS non lues (décalages, unités rares, options de MarkerLine
  ou de grille), des combinaisons qui font planter ou perdent un sous-symbole, des cas limites de
  catégories (NULL, valeurs vides, plusieurs champs), des expressions mal traduites.
- **Impossible** : savoir si ArcGIS dessine nos tirets, nos décalages de marqueurs, nos hachures ou
  nos substitutions de polices ESRI comme QGIS. C'est là que se cachent la plupart des écarts
  visibles restants.

## 3. Avec ArcGIS Pro et ArcPy : la boucle complète

### 3.1 Ce que dit la documentation Esri

- **ArcPy n'existe pas sans ArcGIS Pro** : le paquet « still requires ArcGIS Pro, which must be
  installed » ([installer ArcPy](https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/installing-arcpy.htm)).
  ArcGIS Pro ne tourne que sous Windows. Pour qu'un script tourne sans l'application ouverte, la
  licence doit être autorisée hors ligne ou « Sign me in automatically » doit être coché.
- **Lire et écrire un .lyrx** : `arcpy.mp.LayerFile` ouvre un .lyrx, liste ses couches et le
  réenregistre (`save()`). Pour chaque couche, `getDefinition("V3")` donne le CIM comme objets
  Python, et `setDefinition()` le remet
  ([LayerFile](https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/layerfile-class.htm)).
- **Dessiner** : une vue de carte s'exporte en PNG, à une taille et une résolution choisies, avec
  l'emprise réglée par la caméra
  ([MapView](https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/mapview-class.htm)).
  `exportToPNG` est remplacé par `export` depuis ArcGIS Pro 3.4. À vérifier sur place : la
  documentation montre ces exemples dans un projet ouvert ; un script indépendant passera peut-être
  par une mise en page ou un projet .aprx modèle.
- **Spécification** : Esri publie la description du CIM, version 3.7.0, sur
  [github.com/Esri/cim-spec](https://github.com/Esri/cim-spec) (fichiers Markdown, pas de schéma
  JSON formel).

### 3.2 Les quatre arbitres qu'ArcGIS apporterait

1. **Relecture** : ArcGIS ouvre notre .lyrx puis le réenregistre. Une propriété que nous écrivons
   et qu'ArcGIS supprime ou modifie signale une valeur mal formée. Cela se vérifie sans rien
   dessiner, des milliers de fois.
2. **Dessin croisé** : ArcGIS dessine le .lyrx, QGIS dessine le .qlr équivalent, sur les mêmes
   données inventées. On compare les échantillons de symboles. C'est **le** test qui manque
   aujourd'hui.
3. **Vérité terrain du côté ArcGIS** : ArcPy fabrique lui-même des symbologies (par le CIM), qu'on
   convertit vers QGIS. Ces cas d'entrée sont garantis justes, comme ceux que PyQGIS fournit pour
   QGIS.
4. **Polices ESRI** : installées avec ArcGIS Pro, elles permettent de dessiner chaque caractère et
   de vérifier ou compléter la table de substitution (`polices.json`) par comparaison d'images.

Avec ces quatre arbitres, la boucle devient symétrique : générer d'un côté, dessiner des deux,
comparer, corriger. Le convertisseur cesse de dépendre de notre seule lecture de la spécification.

### 3.3 Limites à garder en tête

- Les deux moteurs ne dessineront **jamais** au pixel près : lissage, rendu des polices, placement
  des étiquettes. Il faut des tolérances et des échantillons de symboles isolés plutôt que des
  cartes entières.
- Certains écarts n'ont **pas de solution** (une couche de symbole sans équivalent). La boucle doit
  alors s'assurer que le rapport le dit, pas chercher à les supprimer.
- ArcGIS Pro demande un poste Windows assez puissant. Le serveur papetche (2 Go de mémoire) ne
  convient pas.

### 3.4 Quelle licence ?

- **ArcGIS for Personal Use** (abonnement annuel, niveau « Basic » d'ArcGIS Pro, suffisant pour
  `arcpy.mp`) : la licence est réservée à un usage **personnel et non commercial**, ce qui exclut un
  travail fait pour un employeur ou une administration
  ([conditions Esri](https://www.esri.com/en-us/arcgis/products/arcgis-for-personal-use/buy)).
  Prix à vérifier sur la boutique Esri. Elle ne convient que si lyrx2qlr reste un projet
  personnel.
- **Une licence existante chez l'employeur de Yoann** : les exemples viennent d'une administration
  qui utilise ArcGIS Pro. C'est la voie la plus simple, si les règles internes autorisent à faire
  tourner des scripts de test sur un poste équipé.
- Dans les deux cas, les scripts ArcPy et la boucle peuvent s'exécuter dans une session Claude Code
  **sur ce poste équipé**. Il suffit qu'ArcGIS Pro y soit installé et autorisé.

## 4. Une voie intermédiaire peu coûteuse

Sans licence, on peut demander à des collègues qui ont ArcGIS Pro **quelques dizaines de paires
« .lyrx + image PNG exportée par ArcGIS »** sur des données publiques, en couvrant exprès les cas
douteux : hachures, tirets, marqueurs le long des lignes, polices ESRI, décalages. Chaque paire
devient un test de dessin croisé figé. Cela ne remplace pas une boucle automatique, mais cela
apporte de vraies références ArcGIS là où la boucle sans ArcGIS est aveugle.

## 5. Plan proposé

> Les étapes 1 à 4 sont faites (version 1.1.0) : voir [entrainement.md](entrainement.md).

| Étape | Contenu | Besoin |
|---|---|---|
| 1 | Générateur de données inventées et de symbologies QGIS (tirage + mutations), dans `outils/` | rien |
| 2 | Comparaison par échantillons de symboles, fiches d'écart, `exemples/fabriques/` | rien |
| 3 | Rapport de couverture : propriétés QGIS connues contre catalogues | rien |
| 4 | Relecture de la spécification CIM, propriété par propriété des catalogues (valeurs par défaut, unités, sens des angles) | rien |
| 5 | Paires « .lyrx + PNG » fournies par des collègues | collègues équipés |
| 6 | Boucle complète avec ArcPy : relecture, dessin croisé, polices ESRI | poste avec ArcGIS Pro |

Les étapes 1 à 4 sont faisables tout de suite, dans ce dépôt, et corrigeront déjà une bonne partie
des écarts du côté QGIS. L'étape 6 est celle qui transforme « cohérent » en « juste ».
