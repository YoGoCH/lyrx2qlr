# Contribuer à lyrx2qlr / Contributing

> **English:** the easiest way to help is the **“Contribute”** tab on
> https://lyrx2qlr.papetche.ch/?lang=en : send a badly (or well) converted file, cleaned in your
> browser before it leaves your computer. On GitHub, open an issue with the “Badly converted
> file” form, or a pull request on the JSON catalogues. Rules below: a test file for every
> change, and never a password, key, real e-mail address or connection string.

## Trois façons d'aider

1. **Envoyer un exemple** depuis la page web, onglet « Contribuer » : une conversion à corriger,
   une bonne conversion, ou une paire de référence (le même rendu fait à la main dans ArcGIS Pro et
   dans QGIS). Le navigateur retire les mots de passe, utilisateurs, serveurs, adresses e-mail et
   dossiers personnels avant l'envoi, et montre ce qu'il a retiré.
2. **Ouvrir un ticket** (« Issues » › « Fichier mal converti ») : joindre un fichier **nettoyé**,
   dire ce qui ne va pas, avec une capture si possible.
3. **Proposer une règle** par une demande de fusion (« pull request »).

## Proposer une règle

La connaissance est rangée dans les catalogues JSON de `src/lyrx2qlr/catalogues/`, pas dans le
code. Une nouvelle correspondance, c'est en général **une ligne** de catalogue. Le mode d'emploi
est dans [docs/catalogues.md](docs/catalogues.md).

- Joindre un **fichier d'essai** qui montre le cas, nettoyé (onglet « Contribuer » de la page, ou
  `python outils/preparer_exemples.py`, qui refuse les fichiers sensibles). Les nouveaux
  exemples vont dans `exemples/lyrx` ou `exemples/qlr` ; le corpus de fichiers téléchargés reste
  sur le poste du mainteneur.
- Lancer les tests : `pytest` (et `lyrx2qlr --verifier-catalogues`). Ils doivent passer.
- Ne pas modifier `expressions.json` (expressions régulières) sans explication détaillée :
  ces règles sont relues avec un soin particulier.
- Tout ce qui n'est pas converti doit aller dans le rapport (`rapport.perte` / `rapport.avertir`),
  jamais en silence.
- Le cœur (`src/lyrx2qlr`) n'utilise que la bibliothèque standard de Python : il doit tourner dans
  QGIS et dans le navigateur.

## Jamais de secret

Aucun mot de passe, aucune clé, aucune adresse e-mail réelle, aucune chaîne de connexion ni aucun
nom de serveur interne dans un fichier, un ticket ou une demande de fusion. Les tests n'utilisent
que des serveurs et des utilisateurs inventés. En cas de doute, passer le fichier dans l'onglet
« Contribuer » de la page et utiliser « Télécharger le colis » : le fichier dans `fichiers/` est
nettoyé.

## Licence

En contribuant, vous acceptez que votre contribution soit publiée sous la licence du projet,
GNU GPL version 3 ou plus récente (voir [LICENSE](LICENSE)).
