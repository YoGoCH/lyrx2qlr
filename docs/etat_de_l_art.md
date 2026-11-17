# État de l'art : existe-t-il déjà un convertisseur .lyrx ↔ .qlr gratuit ?

Vérifié le **13 novembre 2026**, sur les pages officielles des outils. Les dates
indiquées sont celles de la dernière version publiée ou de la dernière modification du code.

## Réponse nette

**Non.** Aucun outil gratuit et entretenu ne convertit les couches dans **les deux sens**
entre ArcGIS Pro (.lyrx) et QGIS (.qlr / .qml).

- De **ArcGIS Pro vers QGIS**, il existe des solutions gratuites, mais partielles
  (ArcToQ, qlyrx), ou qui ne produisent pas un fichier QGIS (GeoStyler).
- De **QGIS vers ArcGIS Pro**, la seule voie gratuite est une bibliothèque de
  développement (bridge-style) qui écrit des symboles CIM sans couche complète.
- La seule solution complète dans les deux sens, **SLYR**, est **payante** pour ces
  fonctions (licence d'environ 1500 €). Sa version gratuite ne lit ni n'écrit les .lyrx.
- Ni QGIS ni ArcGIS Pro ne savent lire le format de l'autre sans extension.

Le projet lyrx2qlr comble donc un vrai manque.

## Détail par outil

| Outil | lyrx → QGIS | QGIS → lyrx | Gratuit | Dernière version |
|---|---|---|---|---|
| SLYR, version gratuite « Community Edition » (North Road) | non | non | oui | 7.2.0, 4 août 2026 |
| SLYR, version sous licence (North Road) | oui (.qlr, .qml) | oui | non (environ 1500 €, une fois) | non indiquée |
| ArcToQ Converter (extension QGIS) | oui, vers .qlr | non | oui | 1.4.3, 16 mai 2026 |
| qlyrx (arc2qgis) | partiel : valeurs uniques et symbole unique, sans étiquettes ni classes | non | oui (GPL-2.0) | v0.3.5, 21 novembre 2024 (plus modifié depuis) |
| geostyler-lyrx-parser | lecture seule, vers le format GeoStyler (pas un fichier QGIS) | non (« it can not write Lyrx files ») | oui (BSD) | v2.2.0, 20 octobre 2026 |
| bridge-style (GeoCat) | vers SLD, MapLibre, Mapfile, mais **pas vers QGIS** | écrit des symboles CIM depuis un .qml, pas un .lyrx complet ; demande QGIS | oui (MIT) | 0.1.9, 22 juin 2026, entretien lent |
| QGIS seul | non | non | — | — |
| ArcGIS Pro seul | non | non (pas d'import .qml ni SLD) | — | — |

Remarques :

- **SLYR** : le tableau des fonctions sur le site de North Road coche « Convert LYRX to
  QLR » et « Convert layers to LYRX » pour la licence seulement. Le sous-titre de
  l'extension gratuite cite « lyrx », mais sa description et le tableau montrent qu'elle
  se limite aux anciens formats ArcMap (.lyr, .mxd, .style).
- **ArcToQ** convertit dans un seul sens. Il ne fournit pas de rapport ni de catalogue
  de correspondances modifiable.
- **qlyrx** n'est plus modifié depuis deux ans.
- **bridge-style** sert de base à geostyler-lyrx-parser. Son but annoncé est de
  convertir les .lyrx vers tous les formats « sauf QGIS ».

## Sources

- SLYR, extension gratuite : https://plugins.qgis.org/plugins/slyr_community/
- SLYR, site et tableau des fonctions : https://north-road.com/slyr/
- SLYR, outils de conversion : https://slyr.north-road.com/user_guide/tools.html
- Extensions QGIS portant l'étiquette lyrx : https://plugins.qgis.org/plugins/tags/lyrx/
- ArcToQ Converter : https://plugins.qgis.org/plugins/ArcToQ/
- qlyrx : https://github.com/arc2qgis/qlyrx
- geostyler-lyrx-parser : https://github.com/geostyler/geostyler-lyrx-parser
- bridge-style : https://github.com/GeoCat/bridge-style
- Esri, demande d'import SLD toujours ouverte :
  https://community.esri.com/t5/arcgis-pro-ideas/arcgis-pro-online-support-sld-layer-style-import/idi-p/922867

À revoir de temps en temps : une nouvelle version de SLYR gratuit ou d'ArcToQ pourrait
changer la réponse.
