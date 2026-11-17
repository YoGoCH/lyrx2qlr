#!/usr/bin/env bash
# Lot 2 : dessin croisé, fichier par fichier, pour qu'un fichier trop lourd ne bloque pas les autres.
#
#   bash outils/lot2/lancer.sh qgis   SERIE [FICHIERS.qlr...]   QGIS dessine l'original, ArcGIS notre .lyrx
#   bash outils/lot2/lancer.sh arcgis SERIE [FICHIERS.lyrx...]  ArcGIS dessine l'original, QGIS notre .qlr
#
# Par défaut : exemples/qlr/*.qlr ou exemples/lyrx/*.lyrx. Résultats dans comparaisons_lot2/SERIE/
# (dossier ignoré par git). Voir docs/lot2.md.
cd "$(dirname "$0")/../.." || exit 1
ARCPY="/c/Program Files/ArcGIS/Pro/bin/Python/envs/arcgispro-py3/python.exe"
SENS="${1:?sens manquant : qgis ou arcgis}"
SORTIE="comparaisons_lot2/${2:?nom de série manquant}"
shift 2
LIMITE=150
DONNEES="${DONNEES:-donnees_locales}"  # lot 2.1 : DONNEES=comparaisons_lot2/corpus/donnees
mkdir -p "$SORTIE"

qgis() {  # $1 = rôle, $2 = fichier
  timeout -k 5 $LIMITE powershell -NoProfile -File outils/py.ps1 outils/lot2/dessin_qgis.py "$2" \
    --role "$1" --donnees "$DONNEES" --sortie "$SORTIE" 2>&1 | grep -v "^$" \
    || echo "$(basename "$2") : QGIS n'a pas fini en $LIMITE s"
}

arcgis() {  # $1 = rôle, $2 = fichier ; ArcGIS peut aussi rester bloqué sur un dessin lourd
  timeout -k 5 $((LIMITE + 90)) "$ARCPY" outils/lot2/dessin_arcgis.py "$2"     --role "$1" --donnees "$DONNEES" --sortie "$SORTIE" 2>&1 | grep -v "^$"
  [ "${PIPESTATUS[0]}" = 124 ] && echo "ArcGIS n'a pas fini en $((LIMITE + 90)) s" | tee "$SORTIE/$(basename "${2%.*}").$1.erreur.txt"
}

if [ "$SENS" = qgis ]; then
  [ $# -eq 0 ] && set -- exemples/qlr/*.qlr
  for f in "$@"; do qgis avant "$f"; done
  for f in "$@"; do arcgis apres "$f"; done
else
  [ $# -eq 0 ] && set -- exemples/lyrx/*.lyrx
  for f in "$@"; do arcgis avant "$f"; done
  for f in "$@"; do qgis apres "$f"; done
fi
"$ARCPY" outils/lot2/comparer.py "$SORTIE" --donnees "$DONNEES"
