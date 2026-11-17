# Positionnement : y a-t-il un besoin, et lyrx2qlr peut-il réussir ?

Rapport du **15 novembre 2026**. Il complète l'[état de l'art](etat_de_l_art.md) (liste des outils,
vérifiée le 13 novembre 2026) avec la question du besoin et des chances de succès.

## En bref

- **Le besoin existe et grandit.** ArcMap est retiré depuis le 1er mars 2026. Chaque bureau doit
  choisir entre payer ArcGIS Pro ou passer à QGIS. Beaucoup gardent les deux, et les échanges de
  fichiers entre organisations équipées différemment deviennent quotidiens.
- **La place est libre pour un outil gratuit dans les deux sens.** Le seul outil complet, SLYR, est
  payant (1500 € par site) et ne s'utilise que dans QGIS. Les outils gratuits ne vont que dans un
  sens, ou sont à l'abandon.
- **lyrx2qlr a trois atouts uniques** : il marche sans rien installer (navigateur), il sert aussi
  aux utilisateurs ArcGIS qui n'ont pas QGIS, et il dit ce qu'il n'a pas converti.
- **Ses chances sont bonnes comme outil de référence dans une niche** (quelques milliers
  d'utilisateurs, d'abord en Suisse et dans la francophonie), pas comme produit à vendre.
  Trois conditions : validation dans ArcGIS Pro (lot 2), extension publiée dans le dépôt officiel
  de QGIS, page en anglais.

## 1. Le besoin

### Ce qui pousse les gens à convertir

- **Fin d'ArcMap.** Esri a retiré ArcGIS Desktop (ArcMap, ArcCatalog…) le 1er mars 2026 : plus de
  mises à jour ni d'assistance. De plus, les versions d'ArcGIS Pro sorties depuis mars 2026 ne
  prennent plus en charge les licences flottantes (« Concurrent Use »). Pour beaucoup de bureaux,
  c'est une hausse de coût et le moment de se poser la question de QGIS.
- **Migrations en Suisse, dans nos métiers.** À la conférence des utilisateurs QGIS 2026,
  Geotest AG, bureau suisse d'ingénierie et d'environnement de plus de 200 personnes, a présenté
  son passage complet d'ArcMap à QGIS. Ramboll y a parlé de faire vivre QGIS et ArcGIS côte à côte.
  Les cantons suisses entretiennent ensemble des extensions QGIS depuis dix ans (Model Baker).
- **Environnements mixtes.** Un canton sous ArcGIS, un bureau mandataire sous QGIS, une commune
  qui a les deux : la symbologie (couleurs officielles, légendes normées) doit passer de l'un à
  l'autre. Refaire une légende de 50 classes à la main prend des heures et introduit des erreurs.
- **Demandes visibles.** Les listes de discussion QGIS reçoivent régulièrement la question
  « comment importer une carte ArcGIS Pro dans QGIS ? ». Côté Esri, la demande d'import SLD dans
  ArcGIS Pro reste ouverte : ArcGIS Pro ne sait toujours rien lire de QGIS.

### Ce qu'on ne sait pas chiffrer

Aucune source publique ne donne le nombre d'utilisateurs de QGIS ni sa part face à ArcGIS. Ordres
de grandeur connus : environ 30 000 téléchargements de QGIS par jour sur qgis.org et près de
2 millions de téléchargements d'extensions par mois (chiffres annoncés à la conférence 2026).
Le nombre de personnes qui convertissent des symbologies est donc une petite fraction de cela,
probablement **quelques milliers par an dans le monde**.

## 2. La concurrence

| | lyrx2qlr | SLYR (sous licence) | ArcToQ | qlyrx | geostyler-lyrx-parser |
|---|---|---|---|---|---|
| ArcGIS → QGIS | oui | oui, très complet | oui | partiel | lecture seule, pas de fichier QGIS |
| QGIS → ArcGIS | **oui** | oui | non | non | non |
| Prix | **gratuit** | 1500 € (10 postes, un site) | gratuit | gratuit | gratuit |
| Sans installation | **oui (navigateur)** | non (extension QGIS) | non | non | non (bibliothèque) |
| Utilisable sans QGIS | **oui** | non | non | non | — |
| Rapport de ce qui manque | **oui, détaillé** | partiel | non | non | non |
| Règles modifiables par l'utilisateur | **oui (catalogues JSON)** | non | non | non | non |
| Projets entiers (.aprx, .mxd) | non | oui | non | non | non |
| Entretenu | oui | oui | oui | non (depuis 2024) | oui |

**SLYR** est le vrai concurrent : des années de travail, des projets entiers, des effets
graphiques avancés. On ne le dépassera pas en couverture à court terme. Mais il vise les
organisations qui migrent tout vers QGIS et peuvent payer. lyrx2qlr vise le **quotidien des
échanges** : un fichier, tout de suite, gratuit, dans les deux sens, y compris pour la personne
qui n'a qu'ArcGIS Pro.

## 3. Nos atouts

1. **Gratuit et dans les deux sens** : aucun autre outil gratuit n'écrit de .lyrx complet.
2. **Aucune installation** : une page web. Dans une administration où l'on ne peut rien
   installer sans le service informatique, c'est décisif.
3. **Confidentialité** : la conversion se fait sur le poste. Les fichiers ne partent sur aucun
   serveur. Pour des données sensibles (réseaux, sites protégés), c'est un argument fort.
4. **Honnêteté** : le rapport « NON CONVERTI / À VÉRIFIER / INFO » dit quoi contrôler. Les autres
   outils se taisent sur ce qu'ils perdent.
5. **Améliorable par des géomaticiens** : les correspondances sont des lignes de JSON, pas du code.
   C'est la base d'un outil collaboratif (voir [collaboratif.md](collaboratif.md)).
6. **Testé sur du concret** : plus de 500 symbologies réelles, 0 aller-retour instable.

## 4. Les faiblesses et les risques

- **Pas encore validé dans ArcGIS Pro.** Tous les tests côté ArcGIS sont faits sans le logiciel.
  Un .lyrx refusé ou mal affiché par ArcGIS Pro ruinerait la confiance. C'est le **lot 2**,
  priorité absolue avant de faire connaître l'outil côté ArcGIS.
- **Couverture plus faible que SLYR** sur les cas avancés : niveaux de symboles, variables
  visuelles, SVG, tailles en unités de carte (voir [corpus.md](corpus.md)).
- **Visibilité nulle aujourd'hui.** L'extension n'est pas dans le dépôt officiel des extensions
  QGIS, la page n'existe qu'en français, et le code n'est pas public.
- **Un seul mainteneur.** Le format CIM d'Esri évolue avec chaque version d'ArcGIS Pro.
- **Pas de modèle économique évident.** Le marché est trop petit pour vendre l'outil seul.

## 5. Peut-il réussir ?

Oui, si « réussir » veut dire **devenir l'outil gratuit de référence pour échanger une symbologie
entre ArcGIS Pro et QGIS**, et une belle vitrine du savoir-faire de Yoann. Non, s'il s'agit d'en
faire un produit rentable : SLYR occupe déjà le haut du marché.

Ce qui ferait la différence, par ordre d'importance :

1. **Lot 2 : valider les .lyrx dans ArcGIS Pro.** Sans cela, pas de bouche-à-oreille côté Esri.
2. **Publier l'extension sur plugins.qgis.org.** C'est le canal où les utilisateurs de QGIS
   cherchent ; ArcToQ et SLYR y sont.
3. **Page et rapport en anglais** (le français reste la langue par défaut pour la Suisse romande).
4. **Rendre le code public** (licence libre). Les géomaticiens font confiance à un outil dont ils
   peuvent lire les règles ; c'est aussi la condition pour recevoir des contributions.
5. **Faire connaître** : planet.qgis.org, GeoRezo, le groupe suisse des utilisateurs QGIS,
   la conférence QGIS, les associations professionnelles (géomatique suisse, ingénieurs
   environnement).
6. **Collaboratif** : laisser les utilisateurs envoyer leurs fichiers difficiles et proposer des
   règles. Chaque fichier reçu améliore l'outil pour tous ([collaboratif.md](collaboratif.md)).

Indicateurs à suivre : visites de la page, téléchargements de l'extension, fichiers reçus,
part de fichiers « sans aucune perte » dans le corpus.

## Sources

- Retrait d'ArcMap le 1er mars 2026 et fin des licences flottantes pour les nouvelles versions de
  Pro : https://esriaustralia.com.au/blog/arcgis-desktop-retirement-next-gen-mapping-now,
  https://resources.esri.ca/arcgis-pro/arcgis-desktop-is-retiring-its-time-to-migrate-to-user-types
- Point de vue d'un bureau QGIS sur ce choix : https://www.lutraconsulting.co.uk/blogs/arcmap-is-dead-great-time-to-switch-to-qgis
- Geotest AG, migration vers QGIS (conférence QGIS 2026) : https://talks.osgeo.org/qgis-uc2026/talk/EP7YH7/
- Model Baker, extension entretenue par les cantons suisses : https://talks.osgeo.org/qgis-uc2026/talk/YDGRGY/
- Chiffres de téléchargement de QGIS (conférence 2026) : https://talks.osgeo.org/qgis-uc2026/talk/BRMCB9/
- Question type sur la liste QGIS : https://lists.osgeo.org/pipermail/qgis-user/2022-March/050903.html
- Demande d'import SLD dans ArcGIS Pro : https://community.esri.com/t5/arcgis-pro-ideas/arcgis-pro-online-support-sld-layer-style-import/idi-p/922867
- Prix de SLYR : https://slyr.north-road.com/user_guide/pricing.html
- Fonctions de SLYR par licence : https://slyr.north-road.com/user_guide/tools.html
