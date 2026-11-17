# Corpus de symbologies réelles (lot 1.5)

La boucle d'entraînement (`docs/entrainement.md`) invente des symbologies. Le corpus fait l'inverse :
il rassemble des fichiers **réels**, faits par des producteurs de données, et les fait passer par
l'aller-retour. Il trouve ainsi ce que personne n'aurait pensé à inventer.

## Ce qu'il contient

Tout est dans `corpus/` :

- `corpus/fichiers/` : les fichiers de symbologie, rangés par provenance
  (`github/<propriétaire>__<dépôt>/…`, `defra/<jeu de données>/…`, `quebec/…`). **Ce dossier reste
  sur le poste de travail et n'est jamais mis dans le dépôt** (décision du 15 novembre 2026 : les
  droits de beaucoup de fichiers ne sont pas clairs). On le reconstitue avec
  `corpus.py telecharger`, qui vérifie chaque empreinte ;
- `corpus/sources.json` : **une ligne par fichier**, avec son adresse de téléchargement exacte
  (épinglée sur une version précise pour GitHub), sa provenance, sa licence quand elle est connue,
  le jeu de données, sa taille, son empreinte `sha256` et la date de téléchargement ;
- `corpus/paires.json` : les paires « même symbologie faite à la main dans les deux logiciels ».

419 fichiers (97 Mo) : 205 .lyrx, 204 .qml, 5 .qlr et les archives d'où certains sont extraits.

| Provenance | Fichiers | Licence |
|---|---|---|
| Ordnance Survey, `OSMM-Topography-Layer-stylesheets` et `OS-NGD-Stylesheets` (GitHub) | 222 | voir le dépôt |
| Portail des données ouvertes du Royaume-Uni (Defra, Environment Agency, Natural England) | 118 | non indiquée dans le fichier ; licence du jeu de données sur sa page |
| `arc2qgis/lyrxtoqml` (GitHub) | 34 | GPL-2.0 |
| `geostyler/geostyler-lyrx-parser` (GitHub) | 26 | BSD-2-Clause |
| Données Québec | 12 | CC-BY 4.0 |
| `Esri/arcgis-pro-sdk-community-samples` (GitHub) | 5 | Apache-2.0 |
| `camptocamp/lyrx2sld` (GitHub) | 2 | MIT |

Aucun fichier .aprx ni .stylx n'a été trouvé en accès libre.

**Secrets** : un seul fichier contenait un mot de passe chiffré dans une chaîne de connexion
(`arc2qgis__lyrxtoqml/lyrx samples/migrashim.lyrx`). Il a été retiré (remplacé par `<retiré>`) ;
sa ligne dans `sources.json` le dit (`"modifie"`), et son `sha256` reste celui du fichier d'origine.
Tout nouveau téléchargement passe par le même nettoyage.

Les fichiers de Yoann (le dossier de départ) ne sont **pas** dans `corpus/` : on les ajoute à
l'analyse avec `--local`.

## Commandes

```powershell
# Télécharger (poliment : une pause entre deux demandes, reprises si le serveur dit « trop vite »)
.\outils\py.ps1 outils\entrainement\corpus.py telecharger

# Aller-retour .lyrx → .qlr → .lyrx (sorties\corpus\rapport_lyrx.md)
.\outils\py.ps1 outils\entrainement\corpus.py analyser --local C:\chemin\vers\mes\fichiers

# Aller-retour QGIS → .lyrx → .qlr (sorties\corpus\rapport_qgis.md)
.\outils\py.ps1 outils\entrainement\corpus.py analyser --sens qgis --local C:\chemin\vers\mes\fichiers

# Comparer notre conversion aux paires faites à la main (sorties\corpus\paires.md)
.\outils\py.ps1 outils\entrainement\corpus.py paires
```

Chaque rapport donne : le nombre de fichiers convertis, sans perte, illisibles, les **erreurs
internes** (doivent rester à 0), les **allers-retours instables** (le modèle ne revient pas
identique sans raison connue : doivent rester à 0) et le classement de ce qui manque le plus.

Un écart d'aller-retour attendu et annoncé dans le rapport de conversion (par exemple la casse
« Titre » de QGIS, qu'ArcGIS ne connaît pas) est rangé dans `ECARTS_CONNUS`, en tête de
`corpus.py`, avec sa raison. N'y mettre que des écarts **annoncés** à l'utilisateur.

## Résultats (v1.2.0)

| | Au début du lot | Après corrections |
|---|---|---|
| .lyrx : erreurs internes | 1 | **0** |
| .lyrx : allers-retours instables | 90 | **0** |
| .lyrx : sans aucune perte | — | 230 sur 263 |
| QGIS : sans aucune perte | 84 sur 248 | **185 sur 248** |
| QGIS : allers-retours instables | 79 | **0** |

### Corrections apportées

- Lecture ArcGIS : valeurs « NaN » (écrites telles quelles ou en texte) lues comme absentes ;
  classe sans borne supérieure signalée au lieu de planter ; décalage quasi nul traité comme absent.
- Marqueurs le long d'une ligne : placement ArcGIS « à des positions relatives »
  (`CIMMarkerPlacementAtRatioPositions`) ↔ QGIS « au point central » ou « aux extrémités ».
- Grille de marqueurs QGIS avec écart aléatoire : reconnue comme grille aléatoire.
- Étiquettes de points : positions nord, nord-est… ↔ QGIS « Autour du point » avec quadrant ;
  étiquettes de lignes centrées ou décalées.
- Casse QGIS « Majuscule initiale » et « Titre » : annoncées (pas d'équivalent ArcGIS).
- Ensembles de règles QGIS simples (`"champ" = 'valeur'`, `"champ" IN (…)`, `ELSE`) convertis en
  **valeurs uniques** au lieu de ne garder que le premier symbole (58 fichiers concernés).
- Images intégrées dans un .qml : format (BMP, PNG, JPEG, GIF, SVG) reconnu aux premiers octets.
- Diagrammes QGIS désactivés : plus signalés comme perdus.
- Contour des marqueurs de police : seulement s'il a une épaisseur.
- Arcade : `$feature['champ']` reconnu comme un simple champ.
- Nouvelle forme `cross_fill` ; option `outline_width` héritée et sans effet sur `SimpleLine`
  ignorée.

### Paires faites à la main (Ordnance Survey, NGD)

Ordnance Survey publie la même symbologie en .lyrx et en .qlr (4 styles : noir et blanc, clair,
plein air, routier). Sur 520 à 580 classes par style, 24 à 98 sont identiques après notre
conversion. Les différences viennent surtout de **choix de dessin différents du producteur**, pas
de la conversion : police « OSMasterMap » de taille 50 côté ArcGIS contre simple point côté QGIS,
traits de 0,1 point contre 0,1 millimètre, symboles vides d'un côté et marqueurs transparents de
l'autre. Ces paires ne sont donc pas une référence exacte, mais elles servent à repérer les vrais
écarts (couleur inversée, couche oubliée).

## Ce qui manque encore (par fréquence)

Sens ArcGIS → QGIS :

1. Dessin par niveaux de symboles (20 fichiers).
2. Variables visuelles : taille ou couleur selon un champ (13).
3. ~~Décalage des hachures `offsetX` (13)~~ : converti depuis le lot 2.1 (mesuré dans les deux
   logiciels).
4. Pictogrammes vectoriels complexes des polices ESRI, remplacés par un cercle ou un carré
   (piste : les écrire en SVG intégré) ; découpe `clippingPath` des marqueurs (8).
5. Bulles et ombres des étiquettes (9).

Sens QGIS → ArcGIS :

1. Tailles en unités de carte (80 fichiers) : ArcGIS n'a pas cette unité pour les symboles.
   Depuis le lot 2.1, elles sont converties à l'échelle de référence de la couche.
2. Remplissages et marqueurs SVG (34 et 24).
3. Rendu « Aucun symbole » (10).
4. Ensembles de règles complexes (5) : piste, une expression Arcade `When()`.
5. Décalage vertical des grilles de points `displacement_y` (15).
