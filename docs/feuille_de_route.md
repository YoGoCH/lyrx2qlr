# Feuille de route : faire connaître lyrx2qlr

Décidée le **15 novembre 2026**. C'est la liste de travail principale du projet. Les raisons sont
dans [positionnement.md](positionnement.md). L'outil collaboratif
([collaboratif.md](collaboratif.md)) est lancé depuis la v1.7.0 (17 novembre 2026) : étapes 0 et 1, le panneau
« Contribuer » de la page. L'atelier de règles (étape 2) reste pour plus tard.

| # | Étape | État | Dépend de |
|---|---|---|---|
| 1 | Valider les .lyrx dans ArcGIS Pro (lot 2) | **fait** (v1.3.0) : voir [lot2.md](lot2.md) | rien |
| 2 | Publier l'extension sur plugins.qgis.org | ZIP prêt (v1.7.0 : anglais, icône, licence) ; reste l'envoi par Yoann (compte OSGeo, vraie adresse e-mail) | rien |
| 3 | Proposer la page en anglais | **fait** (v1.2.2), sauf les messages du rapport | rien |
| 4 | Rendre le code public | **fait** (17 novembre 2026) : dépôt de travail public, https://github.com/YoGoCH/lyrx2qlr_code_public | rien |

Ordre conseillé : **3 et 4** tout de suite (aucune dépendance), **2** juste après, **1** en
parallèle (ArcGIS Pro est installé depuis le 15 novembre 2026). On ne fait connaître l'outil **côté ArcGIS** qu'après l'étape 1.

## 1. Valider les .lyrx dans ArcGIS Pro (lot 2)

**15 novembre 2026 : ArcGIS Pro 3.7 est installé sur le poste de travail**, avec la licence
d'association de Yoann (ArcPy indique le niveau « ArcInfo », c'est-à-dire Advanced). Le Python
d'ArcGIS se trouve dans `C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe` ;
il charge le cœur de lyrx2qlr sans installation.

Premier essai le même jour : les **42 exemples QGIS** (`exemples/qlr`) ont été convertis en .lyrx
et **tous s'ouvrent dans ArcGIS sans erreur** (`arcpy.mp.LayerFile`). ArcGIS y reconnaît bien les
valeurs uniques, les symboles uniques et les classes graduées. S'ouvrir ne veut pas encore dire
« bien dessiné » : c'est la suite.

**16 novembre 2026 : lot 2 terminé (v1.3.0).** Bilan complet dans [lot2.md](lot2.md) :
relecture par ArcGIS de plus de 1 000 fichiers produits, dessin croisé avant / après des exemples
et de 100 symbologies fabriquées par ArcGIS, vérification des polices ESRI. Onze défauts réels
trouvés et corrigés ; aucun ne se voyait sans ArcGIS.

**16 novembre 2026 : lot 2.1.** Le corpus réel (403 fichiers) est dessiné à son tour, sur des
GeoPackage fabriqués à partir des symbologies. Six défauts de plus corrigés (unités de carte,
décalages de contours et de hachures, catégorie NULL, courbes de Bézier, images repeintes).
Principale différence restante : les formes de marqueur ArcGIS libres (flèches, pictogrammes),
qui deviennent un carré dans QGIS ; piste, les écrire en SVG intégré.

**16 novembre 2026 : sources de données gardées** (prochaine version). Coche « Garder la source
de données », cochée par défaut : un .qlr sur un GeoPackage ou une base Oracle, PostgreSQL ou
SQL Server s'ouvre directement après conversion, et inversement, sans mot de passe (voir
[limites.md](limites.md), « Sources de données »). Vérifié avec ArcGIS Pro et QGIS pour les
GeoPackage et pour la lecture des connexions Oracle ; l'ouverture réelle d'une couche Oracle est
**à vérifier au travail**.

Reste ouvert :

- essayer au travail une couche Oracle convertie dans les deux sens (ouverture, demande du mot
  de passe, géométrie `SDO_GEOMETRY` côté QGIS). **En attente depuis le 16 novembre 2026** : le
  QGIS du travail n'a pas le fournisseur Oracle (`provider_oracle.dll` absent, diagnostic de
  l'extension 1.5.1), et Yoann ne peut pas l'installer. La conversion elle-même est correcte
  (connexion gardée, lue par QGIS) ;
- vérifier que les conditions de la licence d'association autorisent cet usage de test ;
- relancer le lot 2 à chaque changement de catalogue qui touche l'écriture des .lyrx
  (commandes dans [lot2.md](lot2.md)) ;
- les remplacements creux des polices ESRI (cercle, triangle, étoile creux) gardent un trait un
  peu plus fin que le glyphe d'origine.

## 2. Publier l'extension sur plugins.qgis.org

C'est là que les utilisateurs de QGIS cherchent leurs extensions ; ArcToQ et SLYR y sont.

Ce que le dépôt officiel exige, et ce qui manque aujourd'hui :

- **une licence compatible avec la GPL**, avec un fichier `LICENSE` dans le ZIP de l'extension :
  il n'y en a pas encore (à choisir à l'étape 4) ;
- **un dépôt de code et un suivi des problèmes publics** : `metadata.txt` pointe déjà vers
  GitHub, mais le dépôt est privé (étape 4) ;
- **une vraie adresse e-mail** dans `metadata.txt` : il y a `contact@example.invalid`. L'adresse
  n'est vue que par les gestionnaires du dépôt QGIS. Yoann la saisit lui-même au moment de
  l'envoi ; elle ne doit pas être commitée (règle du projet) ;
- **une description en anglais** (`description`, `about`, journal des versions) ;
- un compte OSGeo pour envoyer le ZIP produit par `outils/construire.py tout`.

L'extension est marquée `experimental=True` : à garder tant que l'étape 1 n'est pas faite. Le
passage en version stable sera la vraie annonce.

Terminé quand : l'extension s'installe depuis le gestionnaire d'extensions de QGIS.

## 3. Proposer la page en anglais

- page en français par défaut, bouton « English » ; langue choisie selon le navigateur ;
- traduire : la préface, les principes, le schéma (`web/schema.js`), les compteurs, le pied de
  page, les balises de partage ;
- **le rapport aussi** : les messages viennent du cœur (`rapport.perte` / `rapport.avertir`).
  Deux options : traduire les messages dans le cœur, avec une langue choisie à l'appel, ou garder
  le rapport en français dans un premier temps. À décider ;
- `README.md` en anglais (ou une section anglaise), utile aussi pour les étapes 2 et 4 ;
- `web/sitemap.xml` et les balises `hreflang` si la version anglaise a sa propre adresse.

Terminé quand : un visiteur anglophone peut convertir un fichier et comprendre le rapport.

**Fait le 15 novembre 2026 (v1.2.2)** :

- `web/langue.js` contient tous les textes de la page, en français et en anglais ;
- bouton « English / Français » ; une adresse par langue : « / » en français, `?lang=en` en
  anglais, avec leur propre adresse de référence (`canonical`), description et balises de
  partage (v1.2.3). La langue du navigateur ne change pas la page : elle affiche seulement une
  invitation vers la version anglaise (les moteurs de recherche lisent la page avec un
  navigateur réglé en anglais) ;
- balises `hreflang` dans `web/index.html`, adresse anglaise dans `web/sitemap.xml` ;
- le rapport est mis en forme dans la langue de la page (titres « NOT CONVERTED / TO CHECK /
  NOTE », résumé), avec une note : les messages détaillés viennent du cœur et restent en
  français. **Reste à faire** : traduire ces messages (environ 80 appels à `rapport.perte`,
  `rapport.avertir` et `rapport.info`, plus les avertissements des catalogues), avec une langue
  choisie à l'appel ;
- le README commence par un paragraphe en anglais.

## 4. Rendre le code public

**Fait le 17 novembre 2026 : le dépôt de travail est public**, https://github.com/YoGoCH/lyrx2qlr_code_public.
Le même jour, une copie publique à part avait d'abord été essayée ; Yoann a préféré travailler
directement en public, par transparence. L'historique public commence à la v1.7.0 : l'ancien
historique (qui contenait le corpus) reste dans l'ancien dépôt privé `YoGoCH/lyrx_2_qlr`, gardé comme
archive. Restent sur le poste, ignorés par git : les symbologies réelles (`exemples/lyrx`,
`exemples/qlr`), le corpus (`corpus/`), les notes pour Claude (`CLAUDE.md`, `.claude/`).
`outils/verifier_depot.py` le contrôle avant chaque `git push` (crochet) et dans les tests. Les
tests qui demandent les symbologies réelles sont sautés sur GitHub et tournent sur le poste.
Le texte ci-dessous est l'étude d'avant cette décision.

Décidé le 15 novembre 2026 :

- **licence du code : GNU GPL version 3 ou plus récente.** Fichier `LICENSE` à la racine, copié
  dans le ZIP de l'extension par `outils/construire.py` ; déclarée dans `pyproject.toml` ;
- **aucun fichier de symbologie d'essai dans les dépôts.** Le corpus reste sur ce poste
  (`corpus/fichiers/` est ignoré par git). On cite le nombre de fichiers testés sur la page, sans
  les publier. `corpus/sources.json` (adresses, licences, empreintes) reste dans le dépôt.

Reste à trancher ou à faire :

- **les exemples** (`exemples/lyrx`, `exemples/qlr`) : 75 symbologies réelles, vaudoises pour la
  plupart. **Décision du 15 novembre 2026 : on les garde dans le dépôt tant qu'elles restent
  anonymisées** (les tests et GitHub Actions s'en servent). Contrôle du même jour : aucun mot de
  passe, aucune adresse e-mail, aucun nom de serveur ou d'utilisateur, aucun chemin personnel ;
  toutes les sources sont des chemins relatifs (`./COUCHE.shp`, `DATABASE=.`). Il reste les noms
  des couches cantonales, qui sont publics. Tout nouvel exemple passe par
  `outils/preparer_exemples.py`. À revoir avant la publication du dépôt ;
- **l'historique git** : il contient encore le corpus (et les exemples). Il faudra donc publier un
  **dépôt neuf, sans historique**, plutôt que de rendre public le dépôt actuel ;
- **un dernier contrôle des secrets** sur tout l'historique : mots de passe, chaînes de connexion,
  adresses e-mail réelles, chemins personnels ;
- ajouter `CONTRIBUTING.md` (règles : fichier d'essai obligatoire, aucun secret) et les
  modèles de demande GitHub (« Fichier mal converti »).

Terminé quand : le dépôt est public, sous licence libre, et les tests automatiques de GitHub
passent.

## Ensuite : faire connaître

Une fois les étapes 2 à 4 faites (et l'étape 1 pour le public ArcGIS) :

- annonce sur planet.qgis.org, GeoRezo, au groupe suisse des utilisateurs QGIS ;
- associations professionnelles (géomatique suisse, ingénieurs en environnement) ;
- proposer une présentation à une conférence QGIS.

## Mesurer : qui utilise lyrx2qlr ?

Situation au 15 novembre 2026 : **aucun suivi**. La page ne contient aucun outil de mesure et
aucun cookie. Les conversions se font dans le navigateur ; elles ne laissent aucune trace sur le
serveur. Les seules traces qui existent sans rien ajouter :

- le **journal du serveur papetche** (nombre de chargements de la page et de `lyrx2qlr.zip`, donc
  de personnes qui ont ouvert l'outil) : à demander à la session qui gère papetche.ch ;
- les **téléchargements de l'extension**, affichés par plugins.qgis.org après l'étape 2 ;
- les **visites et les « étoiles » de GitHub**, après l'étape 4.

Pour compter les conversions, il faudrait ajouter quelque chose. Ces options sont à décider ;
rien n'est fait :

| Option | Ce qu'on apprend | Effet sur la promesse « rien ne sort d'ici » |
|---|---|---|
| Statistiques de visite sans cookie, hébergées par papetche (GoatCounter, Umami, Plausible) | visites, pays, sites d'où viennent les visiteurs | aucun fichier envoyé ; à mentionner en bas de page |
| Petit compteur anonyme : à chaque conversion, la page envoie « 1 conversion, sens, nombre de pertes » | nombre de fichiers convertis, sens, qualité | aucun contenu de fichier, mais une information sort : à écrire clairement sur la page |
| Rien de plus | journal du serveur et chiffres des dépôts | promesse intacte |

Dans tous les cas : jamais le nom ni le contenu d'un fichier, jamais d'identifiant de personne, et
le compteur se coupe si le navigateur demande de ne pas être suivi.
