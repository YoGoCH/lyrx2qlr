# Rendre lyrx2qlr collaboratif : faisabilité et architecture

Étude du **15 novembre 2026**. **Étapes 0 et 1 lancées en v1.7.0 (17 novembre 2026)**, à la demande
de Yoann. L'atelier de règles (étape 2) et les contributions par GitHub (étape 3) restent pour plus tard.

## Ce qui existe (v1.7.0)

- **Page web** : encadré « Un outil collaboratif » et son bouton « Contribuer un exemple », qui
  ouvre un panneau latéral (l'onglet du bord droit a été retiré en v1.8.4)
  (`web/contribuer.js`). Aussi par le lien `#contribuer` et par le bouton « Contribuer » de chaque
  résultat, qui joint le fichier et propose « Conversion à corriger » s'il y a des pertes, sinon
  « Bonne conversion ». Quatre sortes de contribution :
  - « Conversion à corriger » : résultat faux ou incomplet, pour l'entraînement correctif, avec
    des cases « Ce qui ne va pas » (couleurs, épaisseurs, symboles, étiquettes, échelles…) ;
  - « Bonne conversion » : exemple de référence ;
  - « Paire de référence » : le même rendu fait à la main dans les deux logiciels ;
  - « Idée ou remarque ».
  Un .lyrx et/ou un .qlr/.qml, un commentaire, les versions d'ArcGIS Pro et de QGIS, l'usage
  (« tests seulement », par défaut, ou « corpus public CC-BY 4.0 »), un e-mail facultatif.
- **Nettoyage dans le navigateur** par le cœur (`src/lyrx2qlr/confidentialite.py`) : mots de passe
  même chiffrés, jetons, clés, noms d'utilisateur, de serveurs et de bases, e-mails, dossiers
  personnels, serveurs des chemins réseau. Le commentaire est nettoyé aussi.
- **Colis** (`src/lyrx2qlr/contribution.py`) : `contribution.json`, `fichiers/` (nettoyés),
  `notre_resultat/` et `rapports/` (notre conversion du fichier de départ, refaite sur le fichier
  nettoyé). L'aperçu montre ce qui part et ce qui a été retiré ; « Envoyer » demande la case
  d'accord, et toute modification oblige à refaire l'aperçu. Champ piège contre les robots.
- **Envoi** : `POST https://lyrx2qlr.papetche.ch/api/contribuer`, corps = le ZIP brut
  (`Content-Type: application/zip`, taille obligatoire). En ligne depuis le 17 novembre 2026 ; code
  dans le dépôt papetche (`serveur/lyrx2qlr-contributions/`), géré par la session papetche.
  Réponses JSON : 201 `{"ok": true, "numero": "AAAAMMJJ-HHMMSS-xxxxxx"}` (heure suisse) ; sinon
  `{"ok": false, "erreur": "…"}` : 400 (pas un ZIP, colis incomplet), 411 (taille manquante), 413
  (plus de 5 Mo), 429 (plus de 10 envois par heure depuis la même adresse), 507 (boîte pleine,
  500 Mo), 500. La page affiche ce message tel quel ; sans réponse JSON (service arrêté, panne),
  elle propose de télécharger le colis.
- **Côté serveur** : le colis est rangé tel quel, jamais ouvert, hors du dossier du site.
  L'adresse IP n'est gardée qu'en mémoire, une heure, pour la limite d'envois, et n'est jamais
  écrite (pas de journal d'accès). Le seul journal note « reçu <numéro>.zip (<taille> octets) ».
  Purge automatique après 12 mois ; les colis ne sont pas sauvegardés ; pas d'avis automatique.
- **Récupérer les colis** : dans Git Bash, à la racine du dépôt papetche,
  `bash outils/recuperer-contributions.sh [dossier]` copie les nouveaux colis dans
  `~/lyrx2qlr-contributions` (ou le dossier donné) ; ils restent aussi sur le serveur. Puis
  `outils/contributions.py ~/lyrx2qlr-contributions`. **Ce sont des fichiers d'inconnus** : les
  ouvrir comme non sûrs (pas de double-clic dans ArcGIS ou QGIS avant le tri, qui relit sans rien
  exécuter).
- **Tri** : `outils/contributions.py DOSSIER` relit les colis sans rien exécuter, revérifie les
  secrets, refait la conversion et l'aller-retour avec le cœur du jour, range chaque colis dans
  `donnees_locales/contributions/<numéro>/` (ignoré par git) et écrit la fiche `tri.csv`.
  Un colis retenu rejoint le corpus **sans** l'adresse de contact, et seulement avec la licence
  « corpus » ; sinon il ne sert qu'aux tests locaux.

La suite de ce document est l'étude de départ.

## L'idée

Permettre aux utilisateurs de QGIS et d'ArcGIS de :

1. **envoyer un fichier** qui se convertit mal (ou bien !), pour qu'il rejoigne le corpus de test ;
2. **proposer une règle** pour les catalogues (une correspondance manquante, une valeur fausse),
   en la testant d'abord sur leur propre fichier.

C'est le prolongement naturel du projet : la connaissance est déjà rangée dans des catalogues JSON
lisibles, et le corpus montre que chaque fichier réel fait progresser l'outil.

## Verdict

**Faisable, à coût faible, en trois étapes.** La plus grande partie du travail se fait dans la page
web, avec le cœur Python qui y tourne déjà. Côté serveur, il ne faut qu'un petit point de dépôt
(recevoir un fichier et le ranger), qui dépend de l'hébergement papetche.

Trois points demandent une décision de Yoann :

- **le dépôt de code devient-il public ?** C'est indispensable pour que des développeurs proposent
  des règles par GitHub, et c'est un gage de confiance ; ce n'est pas indispensable pour la page ;
- **qui peut voir les fichiers envoyés ?** Proposition : par défaut, seulement Yoann, pour les
  tests ; publication dans le corpus seulement si le contributeur l'accepte ;
- **le serveur papetche peut-il recevoir des fichiers ?** Question à poser à la session qui le gère
  (liste plus bas).

## Les règles qui ne changent pas

- **La promesse de la page reste vraie** : sans action explicite, aucun fichier ne quitte le poste.
  L'envoi est un bouton séparé, avec un aperçu de ce qui part et une case à cocher.
- **Jamais de secret ni de donnée personnelle** : le fichier est nettoyé **dans le navigateur,
  avant l'envoi** (mots de passe, chaînes de connexion, noms de serveurs, chemins personnels,
  adresses e-mail), avec les motifs déjà utilisés par `outils/preparer_exemples.py` et
  `corpus.py`. Ce qui a été retiré est montré à l'utilisateur.
- **Rien n'entre dans les catalogues sans relecture humaine** et sans que les tests et le corpus
  restent à 0 erreur interne et 0 aller-retour instable.

## Architecture

```
 POSTE DE L'UTILISATEUR (page web, Python dans le navigateur)               SERVEUR papetche
┌──────────────────────────────────────────────────────────────┐        ┌─────────────────────────┐
│ 1. conversion habituelle  ──►  rapport                       │        │ point de dépôt          │
│                                   │                          │        │  /api/contribuer        │
│ 2. « Envoyer ce fichier »  ───────┤                          │        │  • 5 Mo au plus         │
│ 3. « Proposer une règle » ──► atelier de règles              │        │  • .lyrx .qlr .qml .json│
│        (catalogue complémentaire, essai en direct)           │        │  • limite de débit      │
│                                   ▼                          │        │  • rangé hors du site   │
│                 colis de contribution (.zip)                 │ HTTPS  │    en quarantaine       │
│   fichier nettoyé · notre résultat · rapport · version       │ ─────► │  • avis à Yoann         │
│   règle proposée (facultatif) · commentaire · licence choisie │        └───────────┬─────────────┘
│   (aperçu complet avant l'envoi, case « j'accepte »)          │                    │ récupération
└──────────────────────────────────────────────────────────────┘                    ▼
                                                    POSTE DE YOANN (dépôt lyrx2qlr)   
                                          ┌──────────────────────────────────────────────┐
                                          │ outils/contributions.py                      │
                                          │  • relit chaque colis (sans rien exécuter)   │
                                          │  • revérifie l'absence de secret             │
                                          │  • aller-retour, avec et sans la règle       │
                                          │  • fiche de tri : nouveau cas ? règle utile ?│
                                          │ accepté → corpus/fichiers/contributions/     │
                                          │           + corpus/sources.json              │
                                          │ règle   → catalogue, tests, corpus, version  │
                                          └──────────────────────────────────────────────┘
```

### Étape 1 — Envoyer un fichier (le plus utile, le plus simple)

Dans chaque résultat de conversion, un bouton « Envoyer ce fichier pour améliorer lyrx2qlr ».

- Le navigateur prépare un **colis** : le fichier d'origine nettoyé, notre fichier converti, le
  rapport, la version de lyrx2qlr, un commentaire libre (« les étiquettes sont décalées »), et le
  choix de licence :
  - « pour vos tests seulement » (jamais publié) ;
  - « peut rejoindre le corpus public » (licence CC-BY 4.0, comme les données ouvertes).
- Une adresse e-mail est **facultative**, seulement pour être recontacté ; elle n'est jamais
  rangée avec le fichier dans le corpus.
- Le nettoyage réutilise le cœur : on déplace les motifs de `preparer_exemples.py` et `nettoyer()`
  de `corpus.py` dans un module du cœur (`confidentialite.py`), testé, utilisable par la page, la
  ligne de commande et l'extension QGIS.

**Sans serveur, une version de secours est possible tout de suite** : le bouton télécharge le colis,
et l'utilisateur l'envoie lui-même (courriel ou formulaire). Plus lourd pour lui, mais aucune
infrastructure à créer.

### Étape 2 — L'atelier de règles

Quand le rapport dit « Propriété X non convertie » ou « valeur Y inconnue », un lien « Proposer une
correspondance » ouvre un petit formulaire **guidé** (pas un éditeur de JSON brut) :

- l'atelier sait de quel catalogue et de quelle rubrique il s'agit, grâce au message du rapport ;
- l'utilisateur remplit les cases (« dans ArcGIS : `Square`, dans QGIS : `square` ») ;
- la règle est ajoutée comme **catalogue complémentaire** : le mécanisme existe déjà
  (`Catalogue.charger(complements)`, option `-c` de la ligne de commande). La conversion est
  relancée tout de suite ; l'utilisateur voit si le message disparaît du rapport ;
- la règle, le fichier et les deux rapports (avant / après) partent dans le même colis.

Les **expressions régulières** (`expressions.json`) restent hors de l'atelier au début : une
expression mal écrite peut bloquer le programme, elles demandent une relecture d'expert.

### Étape 3 — Contributions par GitHub (si le dépôt devient public)

Pour les développeurs : une « demande de fusion » sur les catalogues JSON. Les tests automatiques
(GitHub Actions, déjà en place) vérifient les catalogues et les allers-retours. Un modèle de
demande rappelle les règles (fichier d'essai obligatoire, aucun secret).

## Sécurité

| Risque | Parade |
|---|---|
| Fichier piégé (XML à entités en cascade, archive qui explose) | refuser tout `<!DOCTYPE` avec entité, taille limitée à 5 Mo, aucun ZIP envoyé par l'utilisateur hors du colis, colis relu sans être décompressé au-delà de 20 Mo |
| Envoi massif, robots | limite par adresse, champ piège invisible, taille plafonnée, quarantaine hors du dossier du site |
| Secret oublié dans un fichier | nettoyage dans le navigateur, revérification à la réception et au tri (`corpus.py` refuse déjà les secrets) |
| Règle malveillante ou fausse | aucune fusion automatique ; tests et corpus obligatoires ; pas d'expressions régulières depuis l'atelier |
| Données personnelles (loi fédérale sur la protection des données) | aucun compte, e-mail facultatif et séparé, finalité écrite sur la page, suppression sur demande, durée de garde limitée (par exemple 12 mois pour les colis non retenus) |

## Ce qu'il faut demander à l'hébergement papetche

1. Le serveur peut-il faire tourner un petit service (quelques dizaines de lignes, Python ou autre)
   derrière une adresse comme `lyrx2qlr.papetche.ch/api/contribuer` ?
2. Où se trouve le serveur (en Suisse ?) et y a-t-il une sauvegarde ?
3. Peut-il envoyer un avis (courriel ou autre) quand un colis arrive ?
4. Quelle place disque accorder à la quarantaine (proposition : 1 Go, purge automatique) ?

## Charge de travail estimée

| Étape | Contenu | Ordre de grandeur |
|---|---|---|
| 0 | `confidentialite.py` dans le cœur + tests ; colis téléchargeable (sans serveur) | 1 à 2 jours |
| 1 | point de dépôt (côté papetche), bouton d'envoi, `outils/contributions.py` | 2 à 3 jours |
| 2 | atelier de règles pour les listes et les propriétés simples | 3 à 5 jours |
| 3 | dépôt public, modèles de contribution, documentation | 1 jour |

Le volume attendu est faible (quelques colis par semaine au début) : le tri reste humain, aidé par
`contributions.py` qui fait l'aller-retour et classe chaque colis.

## Lien avec le lot 2 (ArcGIS Pro)

Les colis venant d'utilisateurs d'ArcGIS (fichiers .lyrx et fichiers .lyrx que nous avons produits)
sont exactement ce qu'il faut pour la boucle d'autoévaluation dans ArcGIS Pro : chaque colis
accepté devient un cas de test du lot 2.

## Proposition d'ordre

1. Étape 0 tout de suite (aucune dépendance) : elle profite aussi à l'outil actuel.
2. Poser les quatre questions à l'hébergement, et décider du dépôt public.
3. Étape 1 dès que le point de dépôt est possible.
4. Étape 2 après le lot 2, pour que les règles proposées vers ArcGIS soient vérifiables dans
   ArcGIS Pro.
