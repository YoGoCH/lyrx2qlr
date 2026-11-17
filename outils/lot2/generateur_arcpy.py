"""Lot 2, contrôle C : ArcGIS Pro fabrique des symbologies justes par construction.

    & "C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe" outils\\lot2\\generateur_arcpy.py ^
        --cas 60 --graine 1 --donnees donnees_locales --sortie comparaisons_lot2\\arcpy_g1

Chaque cas tire au hasard un symbole ArcGIS (surface, ligne ou point) parmi des briques fréquentes :
traits pleins ou tiretés, décalés ; remplissages pleins ou hachurés ; grilles de marqueurs ;
marqueurs de police ESRI le long des lignes ou sur les points. Le .lyrx brut est **ouvert puis
réenregistré par ArcGIS** (`saveACopy`) : ArcGIS le valide et le complète. C'est ce fichier, écrit
par ArcGIS lui-même, qui sert d'original.

Pour chaque cas, on vérifie ensuite l'aller-retour .lyrx → .qlr → .lyrx dans le modèle neutre (sans les
remplacements de polices ESRI, voulus et annoncés : le dessin croisé les juge).
Les fichiers vont dans `<sortie>/fichiers/` ; le dessin croisé se lance ensuite avec
`bash outils/lot2/lancer.sh arcgis arcpy_g1 comparaisons_lot2/arcpy_g1/fichiers/*.lyrx`.
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "src"))
sys.path.insert(0, str(RACINE / "tests"))
from conftest import comparer_documents  # noqa: E402
from lyrx2qlr import api  # noqa: E402
from lyrx2qlr.catalogue import Catalogue  # noqa: E402
from lyrx2qlr.rapport import Rapport  # noqa: E402

import arcpy  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Couches modèles (exemples du dépôt) et leurs shapefiles dans donnees_locales/.
MODELES = {
    "surface": RACINE / "exemples/lyrx/DGE.MN95_DGE_TPR_EOLIEN_PLANIF.lyrx",
    "ligne": RACINE / "exemples/lyrx/DGMR.MN95_DGMR_TPR_ITIN_CONV_EXCEPT.lyrx",  # lignes longues : marqueurs visibles
    "point": RACINE / "exemples/lyrx/DGTL.MN95_DGTL_CONTENU_SUPERPOSE_P.lyrx",
}
CARACTERES = [33, 34, 35, 36, 37, 40, 41, 42, 68, 69, 94, 172, 183]  # ESRI Default Marker


def couleur(h: random.Random) -> dict:
    return {"type": "CIMRGBColor", "values": [h.randrange(0, 256), h.randrange(0, 256), h.randrange(0, 256), 100]}


def trait(h: random.Random, largeur=None) -> dict:
    t = {"type": "CIMSolidStroke", "enable": True, "capStyle": h.choice(["Round", "Butt", "Square"]),
         "joinStyle": h.choice(["Round", "Miter", "Bevel"]), "lineStyle3D": "Strip", "miterLimit": 10,
         "width": largeur if largeur is not None else h.choice([0.4, 1, 1.5, 2, 3, 4]), "color": couleur(h)}
    effets = []
    if h.random() < 0.35:
        effets.append({"type": "CIMGeometricEffectDashes", "dashTemplate": h.choice([[4, 2], [6, 3], [2, 2], [8, 2, 2, 2]]),
                       "lineDashEnding": "NoConstraint"})
    if h.random() < 0.15:
        effets.append({"type": "CIMGeometricEffectOffset", "method": "Square", "offset": h.choice([-3, -1.5, 1.5, 3]), "option": "Fast"})
    if effets:
        t["effects"] = effets
    return t


def marqueur_police(h: random.Random, taille=None) -> dict:
    return {"type": "CIMCharacterMarker", "enable": True, "anchorPointUnits": "Relative", "dominantSizeAxis3D": "Y",
            "size": taille or h.choice([6, 8, 10, 14, 18]), "billboardMode3D": "FaceNearPlane",
            "characterIndex": h.choice(CARACTERES), "fontFamilyName": "ESRI Default Marker", "fontStyleName": "Regular",
            "fontType": "Unspecified", "scaleX": 1, "rotation": h.choice([0, 0, 0, 30, 45]),
            "symbol": {"type": "CIMPolygonSymbol", "symbolLayers": [{"type": "CIMSolidFill", "enable": True, "color": couleur(h)}]},
            "scaleSymbolsProportionally": True, "respectFrame": True}


def symbole(geometrie: str, h: random.Random) -> tuple[dict, str]:
    if geometrie == "surface":
        couches, quoi = [trait(h, h.choice([0.4, 1, 2]))], []
        choix = h.choice(["plein", "hachures", "hachures", "grille", "plein+hachures"])
        if "hachures" in choix:
            couches.append({"type": "CIMHatchFill", "enable": True, "rotation": h.choice([0, 45, 90, 135, 30]),
                            "separation": h.choice([3, 5, 8, 12]),
                            "lineSymbol": {"type": "CIMLineSymbol", "symbolLayers": [trait(h, h.choice([0.5, 1, 2]))]}})
            quoi.append("hachures")
        if choix == "grille":
            m = marqueur_police(h, h.choice([6, 8, 10]))
            pas = h.choice([10, 14, 20])
            m["markerPlacement"] = {"type": "CIMMarkerPlacementInsidePolygon", "gridType": "Fixed", "stepX": pas, "stepY": pas,
                                    "clipping": "ClipAtBoundary"}
            couches.append(m)
            quoi.append(f"grille de marqueurs {m['characterIndex']}")
        if "plein" in choix:
            couches.append({"type": "CIMSolidFill", "enable": True, "color": couleur(h)})
            quoi.append("plein")
        return {"type": "CIMPolygonSymbol", "symbolLayers": couches}, "surface : " + ", ".join(quoi)
    if geometrie == "ligne":
        couches = [trait(h)]
        quoi = ["trait" + (" tireté" if "effects" in couches[0] else "")]
        if h.random() < 0.4:
            m = marqueur_police(h, h.choice([6, 8, 10]))
            m["markerPlacement"] = {"type": "CIMMarkerPlacementAlongLineSameSize", "angleToLine": True,
                                    "placementTemplate": [h.choice([10, 20, 30])]}
            couches.insert(0, m)
            quoi.append(f"marqueurs {m['characterIndex']} le long")
        if h.random() < 0.3:
            couches.append(trait(h, couches[-1]["width"] + 2))  # trait de fond plus large, dessiné dessous
            quoi.append("double trait")
        return {"type": "CIMLineSymbol", "symbolLayers": couches}, "ligne : " + ", ".join(quoi)
    m = marqueur_police(h)
    couches = [m]
    if h.random() < 0.3:
        couches.append(dict(marqueur_police(h, m["size"] * 1.6), characterIndex=33))  # rond de fond
    return ({"type": "CIMPointSymbol", "symbolLayers": couches, "haloSize": 1, "scaleX": 1, "angleAlignment": "Display"},
            f"point : marqueur {m['characterIndex']} taille {m['size']}")


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--cas", type=int, default=60)
    a.add_argument("--graine", type=int, default=1)
    a.add_argument("--donnees", required=True)
    a.add_argument("--sortie", required=True)
    args = a.parse_args()
    h = random.Random(args.graine)
    donnees = Path(args.donnees).resolve()
    sortie = Path(args.sortie).resolve()
    (sortie / "fichiers").mkdir(parents=True, exist_ok=True)
    cat = Catalogue.charger()
    # aller-retour exact : sans les remplacements de polices ESRI (voulus et annoncés, jugés par le dessin croisé)
    exact = Catalogue(json.loads(json.dumps(cat.d)))
    exact.d["polices"]["substitutions"] = []
    modeles = {g: json.loads(p.read_text(encoding="utf-8-sig")) for g, p in MODELES.items()}
    lignes = ["# Contrôle C : symbologies fabriquées par ArcGIS Pro", "",
              f"Graine {args.graine}, {args.cas} cas. Aller-retour .lyrx → .qlr → .lyrx dans le modèle neutre.", "",
              "| Cas | Symbole | Aller-retour | Rapport |", "|---|---|---|---|"]
    stables = 0
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        for i in range(args.cas):
            geometrie = h.choice(["surface", "surface", "ligne", "ligne", "point"])
            doc = copy.deepcopy(modeles[geometrie])
            couche = doc["layerDefinitions"][0]
            sym, quoi = symbole(geometrie, h)
            couche["renderer"] = {"type": "CIMSimpleRenderer", "patch": "Default",
                                  "symbol": {"type": "CIMSymbolReference", "symbol": sym}}
            couche["labelVisibility"] = False
            couche["visibility"] = True  # le modèle de lignes est enregistré masqué : ArcGIS ne le dessinerait pas
            conn = couche["featureTable"]["dataConnection"]
            conn["workspaceConnectionString"] = f"DATABASE={donnees}"
            nom = f"c{args.graine}_{i:03d}_{geometrie}"
            brut = Path(tmp) / f"{nom}.lyrx"
            brut.write_text(json.dumps(doc), encoding="utf-8")
            final = sortie / "fichiers" / f"{nom}.lyrx"
            if final.exists():
                final.unlink()
            try:
                arcpy.mp.LayerFile(str(brut)).saveACopy(str(final))  # ArcGIS valide et complète
            except Exception as e:  # noqa: BLE001
                lignes.append(f"| {nom} | {quoi} | refusé par ArcGIS : {str(e).splitlines()[-1][:80]} | |")
                continue
            r1 = Rapport(fichier=nom)
            d1 = api.lire(final.read_bytes(), final.name, cat, r1)
            api.ecrire(d1, ".qlr", cat, r1)  # rapport de la vraie conversion (avec remplacements)
            qlr = api.ecrire(d1, ".qlr", exact, Rapport())
            d2 = api.lire(qlr, "x.qlr", exact, Rapport())
            lyrx = api.ecrire(d2, ".lyrx", exact, Rapport())
            d3 = api.lire(lyrx, "x.lyrx", exact, Rapport())
            ecarts = comparer_documents(d1, d3)
            stables += not ecarts
            etat = "identique" if not ecarts else f"{len(ecarts)} écart(s) : `{ecarts[0][:90]}`"
            lignes.append(f"| {nom} | {quoi} | {etat} | {r1.resume} |")
            print(f"{nom:24} {quoi:45} {etat[:60]}", flush=True)
    lignes[2] += f" **{stables} identiques sur {args.cas}.**"
    (sortie / "resume.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
