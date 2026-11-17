"""Lot 2 : compare les images « avant » et « après » et fait les planches côte à côte.

    & "C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe" outils\\lot2\\comparer.py DOSSIER_SERIE

(Il faut Pillow et numpy : le Python d'ArcGIS les a.)
Lot 2.1 : ajouter `--donnees comparaisons_lot2/corpus/donnees` pour juger aussi case par case.

Pour chaque `<nom>.avant.png` + `<nom>.apres.png` du dossier :

1. chaque image est posée sur un **fond blanc** (ArcGIS exporte un fond transparent, qui deviendrait
   noir) ;
2. **contrôle de l'histogramme** : la part de blanc pur, de noir pur et de pixels dessinés de chaque
   image. Une image presque vide, ou au fond qui n'est pas blanc, est classée « image douteuse »
   au lieu de fausser la note ;
3. **deux notes** :
   - *pixels* : part des pixels dessinés (d'un côté ou de l'autre) dont la couleur diffère
     nettement, sur des images réduites de moitié (le lissage des bords ne compte pas). Elle est
     calculée sur la vue d'ensemble et sur la **vue rapprochée** (1/6 de la largeur, sur la zone la
     plus dessinée), où l'on voit le détail des symboles ;
   - *couleurs* : écart entre les histogrammes de couleurs des pixels dessinés (0 % = mêmes couleurs
     dans les mêmes proportions), insensible à la position ;
4. **classement** : « concordante » si la vue rapprochée diffère de moins de 10 % et les couleurs de
   moins de 10 % ; sinon « à examiner » ;
5. **lot 2.1, case par case** : avec `--donnees DOSSIER` (données fabriquées par
   `fabriquer_donnees.py`), chaque case de la grille (une catégorie ou une classe) est comparée
   seule. Une case vide d'un côté et dessinée de l'autre, ou qui diffère nettement, est encadrée en
   rose sur la planche et nommée dans `resume.md` ; la planche passe alors « à examiner » ;
6. **planche** sur deux rangées (ensemble, rapprochée) « avant | après | différences », rangée dans
   `concordantes/`, `a_examiner/` ou `douteuses/`, et tableau `resume.md`.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SEUIL = 0.10        # vue rapprochée : part des pixels dessinés qui diffèrent ; en dessous, « concordante »
SEUIL_COULEURS = 0.10  # écart entre histogrammes de couleurs
ECART_COULEUR = 48  # différence de couleur (0–255, sur la composante la plus différente) jugée nette
BLANC = 245         # au-dessus, un pixel compte comme du fond


def charger(chemin: Path) -> Image.Image:
    """Image posée sur un fond blanc (la transparence ne doit jamais devenir du noir)."""
    img = Image.open(chemin).convert("RGBA")
    fond = Image.new("RGBA", img.size, (255, 255, 255, 255))
    return Image.alpha_composite(fond, img).convert("RGB")


def histogramme(img: Image.Image) -> dict:
    p = np.asarray(img).astype(int)
    n = p.shape[0] * p.shape[1]
    blanc = (p.min(axis=2) >= BLANC).sum() / n
    noir = (p.max(axis=2) <= 10).sum() / n
    # couleur de fond = couleur la plus fréquente sur le bord de l'image
    bord = np.concatenate([p[0], p[-1], p[:, 0], p[:, -1]])
    valeurs, nombres = np.unique(bord, axis=0, return_counts=True)
    fond = tuple(int(x) for x in valeurs[nombres.argmax()])
    return {"blanc": round(float(blanc), 4), "noir": round(float(noir), 4), "dessine": round(float(1 - blanc), 4), "fond": fond}


def douteuse(h: dict) -> str | None:
    if min(h["fond"]) < BLANC:
        return f"fond {h['fond']} au lieu de blanc"
    if h["dessine"] < 0.0005:
        return "image presque vide"
    return None


def comparer(a: Image.Image, b: Image.Image, reduction: int = 2) -> tuple[float, Image.Image]:
    """reduction 2 : bords lissés ignorés ; 8 : motifs (hachures, points) comparés comme des teintes,
    leur origine (phase) diffère d'un logiciel à l'autre sans que le dessin soit faux."""
    b = b.resize(a.size)
    demi = (a.width // reduction, a.height // reduction)
    pa = np.asarray(a.resize(demi, Image.BOX)).astype(int)
    pb = np.asarray(b.resize(demi, Image.BOX)).astype(int)
    dessine = (pa.min(axis=2) < BLANC) | (pb.min(axis=2) < BLANC)
    ecart = (np.abs(pa - pb).max(axis=2) > ECART_COULEUR) & dessine
    part = float(ecart.sum() / max(1, dessine.sum()))
    fond = (np.asarray(a.resize(demi)) * 0.25 + 191).astype(np.uint8)  # avant pâli
    fond[ecart] = (31, 21, 48)                                            # écarts en violet foncé
    return part, Image.fromarray(fond).resize(a.size, Image.NEAREST)


PART_DOMINANTE = 0.03  # une couleur pèse au moins 3 % des pixels dessinés pour compter


def ecart_couleurs(images_a: list[Image.Image], images_b: list[Image.Image]) -> float:
    """Distance (0–1) entre les **teintes dominantes** dessinées : 18 teintes de 20°, plus une case
    pour les gris (noir compris).

    On compare la teinte, pas la couleur exacte : un trait fin lissé se mêle au blanc, ce qui change
    sa clarté et sa saturation mais pas sa teinte. ArcGIS étale ainsi un trait de 1 pt sur deux pixels
    pâlis là où QGIS le dessine franc. Les teintes qui pèsent moins de 3 % sont écartées."""
    def histo(images):
        h = np.zeros(19)
        for img in images:
            rgb = np.asarray(img).reshape(-1, 3).astype(int)
            hsv = np.asarray(img.convert("HSV")).reshape(-1, 3).astype(int)
            dessine = rgb.min(axis=1) < BLANC
            # gris : écart faible entre composantes (pas la saturation, qui est basse aussi pour une
            # teinte vive pâlie par le lissage)
            gris = dessine & (rgb.max(axis=1) - rgb.min(axis=1) < 12)
            teinte = dessine & ~gris
            h[18] += gris.sum()
            np.add.at(h, hsv[teinte, 0] * 18 // 256, 1)
        return h / max(1, h.sum())
    ha, hb = histo(images_a), histo(images_b)
    garde = np.maximum(ha, hb) >= PART_DOMINANTE
    ha, hb = ha * garde, hb * garde
    ha, hb = ha / max(1e-9, ha.sum()), hb / max(1e-9, hb.sum())
    return float(np.abs(ha - hb).sum() / 2)


SEUIL_CASE = 0.50           # case nommée si ses pixels diffèrent à ce point et que ses couleurs s'écartent aussi
SEUIL_CASE_COULEURS = 0.30  # ou si ses teintes s'écartent à ce point


def cases(plan: dict, e: dict, a: Image.Image, b: Image.Image) -> tuple[list[dict], list[tuple]]:
    """Compare chaque case de la grille fabriquée ; renvoie les cases qui diffèrent et leurs cadres (pixels)."""
    b = b.resize(a.size)
    lx, ly = a.width / (e["xmax"] - e["xmin"]), a.height / (e["ymax"] - e["ymin"])
    ecarts, cadres = [], []
    for couche in plan["couches"]:
        for k in couche["cases"]:
            x0, x1 = (k["xmin"] - e["xmin"]) * lx, (k["xmax"] - e["xmin"]) * lx
            y0, y1 = (e["ymax"] - k["ymax"]) * ly, (e["ymax"] - k["ymin"]) * ly
            boite = tuple(int(round(v)) for v in (max(0, x0), max(0, y0), min(a.width, x1), min(a.height, y1)))
            if boite[2] - boite[0] < 4 or boite[3] - boite[1] < 4:
                continue
            ca, cb = a.crop(boite), b.crop(boite)
            da = (np.asarray(ca).min(axis=2) < BLANC).mean()
            db = (np.asarray(cb).min(axis=2) < BLANC).mean()
            if da < 0.002 and db < 0.002:
                continue  # vide des deux côtés (symbole invisible, classe masquée)
            if min(da, db) < 0.002:
                ecart, quoi, nommer = 1.0, "vide dans " + ("l'original" if da < 0.002 else "la conversion"), True
            else:
                part, _ = comparer(ca, cb, reduction=6)  # motifs comparés comme des teintes
                coul = ecart_couleurs([ca], [cb])
                quoi = f"{part:.0%} de pixels, couleurs {coul:.0%}"
                ecart = max(part, coul)
                # la position des hachures et des grilles (phase) change d'un logiciel à l'autre : des
                # pixels différents ne comptent que si les couleurs s'écartent un peu aussi
                nommer = coul >= SEUIL_CASE_COULEURS or (part >= SEUIL_CASE and coul >= SEUIL_CASE_COULEURS / 2)
                if max(da, db) < 0.01:  # case presque vide (trait de moins d'un pixel) : teintes trop peu sûres
                    nommer = False
            if nommer:
                ecarts.append({"classe": k["classe"], "ecart": round(ecart, 3), "detail": quoi})
                cadres.append(boite)
    return ecarts, cadres


def encadrer(img: Image.Image, cadres: list[tuple]) -> Image.Image:
    img = img.copy()
    d = ImageDraw.Draw(img)
    for c in cadres:
        d.rectangle(c, outline="#ff5fa2", width=3)
    return img


def planche(rangees: list[list[tuple[Image.Image, str]]], titre: str, chemin: Path) -> None:
    l, h = rangees[0][0][0].size
    feuille = Image.new("RGB", (l * len(rangees[0]), 34 + len(rangees) * (h + 30)), "#fff6ec")
    d = ImageDraw.Draw(feuille)
    try:
        gras, normal = ImageFont.truetype("arialbd.ttf", 15), ImageFont.truetype("arial.ttf", 13)
    except OSError:
        gras = normal = ImageFont.load_default()
    d.text((10, 8), titre, fill="#1f1530", font=gras)
    for j, images in enumerate(rangees):
        y = 34 + j * (h + 30)
        d.line([(0, y), (feuille.width, y)], fill="#1f1530", width=3)
        for i, (img, legende) in enumerate(images):
            feuille.paste(img, (i * l, y + 30))
            d.text((i * l + 10, y + 8), legende, fill="#6d5f7a", font=normal)
            d.line([(i * l, y), (i * l, y + h + 30)], fill="#1f1530", width=3)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    feuille.save(chemin)


def pc(v) -> str:
    return "—" if v is None else format(v, ".1%")


def main() -> int:
    serie = Path(sys.argv[1]).resolve()
    donnees = Path(sys.argv[sys.argv.index("--donnees") + 1]).resolve() if "--donnees" in sys.argv else None
    lignes = []
    for avant in sorted(serie.glob("*.avant.png")):
        nom = avant.name[: -len(".avant.png")]
        apres = serie / f"{nom}.apres.png"
        e = json.loads((serie / f"{nom}.emprise.json").read_text(encoding="utf-8"))
        rapport = (serie / f"{nom}.rapport.txt").read_text(encoding="utf-8") if (serie / f"{nom}.rapport.txt").exists() else ""
        if not apres.exists():
            erreur = next(serie.glob(f"{nom}.apres.erreur.txt"), None)
            lignes.append({"nom": nom, "classement": "échec", "note": None,
                           "detail": erreur.read_text(encoding="utf-8")[:200] if erreur else "image « après » manquante", "rapport": rapport})
            continue
        try:
            a, b = charger(avant), charger(apres)
            za, zb = serie / f"{nom}.avant.zoom.png", serie / f"{nom}.apres.zoom.png"
            zoom = (charger(za), charger(zb)) if za.exists() and zb.exists() else None
        except OSError as erreur:  # image tronquée (dessin arrêté en cours d'écriture)
            lignes.append({"nom": nom, "classement": "échec", "note": None,
                           "detail": f"image illisible : {erreur}"[:200], "rapport": rapport})
            continue
        ha, hb = histogramme(a), histogramme(b)
        doute = douteuse(ha) or douteuse(hb)
        part, diff = comparer(a, b)
        part_z, diff_z = comparer(*zoom, reduction=8) if zoom else (part, diff)
        # couleurs jugées sur la vue rapprochée : en vue d'ensemble, les motifs fins se mêlent au fond
        # différemment selon le logiciel (ArcGIS grise des hachures que QGIS garde vives)
        couleurs = ecart_couleurs([zoom[0]], [zoom[1]]) if zoom else ecart_couleurs([a], [b])
        plan_f = donnees / f"{nom}.plan.json" if donnees else None
        ecarts_cases, total_cases = [], 0
        if plan_f and plan_f.exists():
            plan = json.loads(plan_f.read_text(encoding="utf-8"))
            total_cases = sum(len(c["cases"]) for c in plan["couches"])
            ecarts_cases, cadres = cases(plan, e, a, b)
            diff = encadrer(diff, cadres)
        if doute:
            classement = "douteuses"
        else:
            classement = ("concordantes" if part_z < SEUIL and couleurs < SEUIL_COULEURS and not ecarts_cases
                          else "a_examiner")
        la, lb = e.get("logiciel_avant", "?"), e.get("logiciel_apres", "?")
        rangees = [[(a, f"AVANT : {la}, fichier d'origine ({e.get('rendu_avant', '?')})"),
                    (b, f"APRÈS : {lb}, fichier de lyrx2qlr ({e.get('rendu_apres', '?')})"),
                    (diff, f"ENSEMBLE : {part:.1%} de pixels différents · couleurs {couleurs:.1%}"
                     + (f" · {len(ecarts_cases)} case(s) sur {total_cases}" if total_cases else "")
                     + (f" · DOUTE : {doute}" if doute else ""))]]
        if zoom:
            rangees.append([(zoom[0], f"AVANT, vue rapprochée ({la})"), (zoom[1], f"APRÈS, vue rapprochée ({lb})"),
                            (diff_z, f"RAPPROCHÉE : {part_z:.1%} de pixels différents")])
        planche(rangees, f"{nom}   |   {rapport}", serie / classement / f"{nom}.png")
        lignes.append({"nom": nom, "classement": classement, "note": round(part_z, 4), "ensemble": round(part, 4),
                       "couleurs": round(couleurs, 4), "rapport": rapport,
                       "detail": doute or ("; ".join(f"« {k['classe'][:40]} » ({k['detail']})" for k in
                                                     sorted(ecarts_cases, key=lambda k: -k["ecart"])[:4])
                                           + (f" … {len(ecarts_cases)} cases sur {total_cases}" if len(ecarts_cases) > 4 else "")),
                       "cases": total_cases, "cases_differentes": ecarts_cases,
                       "histogramme_avant": ha, "histogramme_apres": hb})
        print(f"{classement:13} rapprochée {part_z:6.1%} · ensemble {part:6.1%} · couleurs {couleurs:6.1%}  {nom}", flush=True)
    (serie / "resultats.json").write_text(json.dumps(lignes, indent=1, ensure_ascii=False), encoding="utf-8")
    notes = [x for x in lignes if x["note"] is not None]
    compte = {k: sum(1 for x in lignes if x["classement"] == k) for k in ("concordantes", "a_examiner", "douteuses", "échec")}
    t = [f"# Dessin croisé : {serie.name}", "",
         f"{time.strftime('%d.%m.%Y %H:%M')} · seuil {SEUIL:.0%} · {len(lignes)} fichiers", "",
         f"- concordantes : **{compte['concordantes']}**", f"- à examiner : **{compte['a_examiner']}**",
         f"- images douteuses (histogramme) : {compte['douteuses']}", f"- échecs de dessin : {compte['échec']}",
         f"- vue rapprochée, médiane des pixels différents : {np.median([x['note'] for x in notes]):.1%}" if notes else "",
         f"- couleurs, écart médian : {np.median([x['couleurs'] for x in notes]):.1%}" if notes else "", "",
         "| Fichier | Vue rapprochée | Ensemble | Couleurs | Classement | Remarque | Rapport de conversion |",
         "|---|---|---|---|---|---|---|"]
    for x in sorted(lignes, key=lambda x: -(x["note"] if x["note"] is not None else 2)):
        t.append(f"| {x['nom']} | {pc(x['note'])} | {pc(x.get('ensemble'))} | {pc(x.get('couleurs'))} | {x['classement']} "
                 f"| {x['detail']} | {x['rapport']} |")
    (serie / "resume.md").write_text("\n".join(t) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
