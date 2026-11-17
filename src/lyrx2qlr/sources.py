"""Sources de données : lecture et écriture des deux côtés, d'après catalogues/sources.json.

Fichiers (shapefile, géodatabase fichier, GeoPackage) : un dossier et un nom de jeu.
Bases de données (Oracle, PostgreSQL, SQL Server, derrière une connexion ArcGIS « SDE ») : la
chaîne de connexion ArcGIS et l'adresse QGIS passent par des clés neutres (Source.connexion).

Le mot de passe n'est jamais recopié, dans aucun sens (règle du projet, CLAUDE.md).
"""
from __future__ import annotations

import re
from typing import Optional

from .catalogue import Catalogue
from .modele import Couche, Source
from .rapport import Rapport


# == outils =====================================================================
def lire_chaine_arcgis(texte: str) -> dict[str, str]:
    """« CLE=valeur;CLE2=valeur2 » → dictionnaire (clés en majuscules)."""
    d: dict[str, str] = {}
    for morceau in (texte or "").split(";"):
        if "=" in morceau:
            cle, valeur = morceau.split("=", 1)
            d[cle.strip().upper()] = valeur.strip()
    return d


def ecrire_chaine_arcgis(d: dict[str, str]) -> str:
    return ";".join(f"{k}={d[k]}" for k in sorted(d) if d[k] not in (None, ""))


_JETON = re.compile(r"""\s*([A-Za-z_]+)\s*=\s*(?:'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)"|(\S*))""")
_TABLE = re.compile(r"""\s*table\s*=\s*(?:"((?:[^"]|"")*)"\s*\.\s*)?"((?:[^"]|"")*)"(?:\s*\(\s*([^)]*?)\s*\))?""")


def lire_adresse_qgis(texte: str) -> tuple[dict[str, str], Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Adresse QGIS d'une base (« dbname='x' host=h … table="schéma"."table" (géométrie) sql=… »).
    Renvoie (clés, schéma, table, colonne géométrique, filtre sql)."""
    sql = None
    m = re.search(r"\ssql=(.*)$", " " + texte, re.S)
    if m:
        sql = m.group(1).strip() or None
        texte = (" " + texte)[: m.start()]
    schema = table = geom = None
    t = _TABLE.search(texte)
    if t:
        schema = t.group(1).replace('""', '"') if t.group(1) is not None else None
        table = t.group(2).replace('""', '"')
        geom = t.group(3) or None
        texte = texte[: t.start()] + " " + texte[t.end():]
    cles: dict[str, str] = {}
    for j in _JETON.finditer(texte):
        valeur = next((v for v in j.groups()[1:] if v is not None), "")
        cles[j.group(1)] = re.sub(r"\\(.)", r"\1", valeur)
    return cles, schema, table, geom, sql


class _Valeurs(dict):
    """Pour str.format_map : une clé absente vaut une chaîne vide."""
    def __init__(self, c: dict, **autres):
        super().__init__(c, **autres)

    def __missing__(self, cle):
        return ""


def _guillemets(valeur: str) -> str:
    return "'" + str(valeur).replace("\\", "\\\\").replace("'", "\\'") + "'"


def _entree(cat: Catalogue, pivot: str) -> Optional[dict]:
    return next((e for e in cat.sources["sources"] if e["pivot"] == pivot), None)


def _srid_defaut(cat: Catalogue) -> Optional[str]:
    m = re.search(r"(\d+)$", cat.formats["qgis"].get("srs_defaut") or "")
    return m.group(1) if m else None


# == serveur (DB_CONNECTION_PROPERTIES d'ArcGIS) ================================
def _serveur_vers_neutre(forme: str, texte: str) -> dict[str, str]:
    texte = (texte or "").strip()
    if forme == "oracle":
        # alias TNS (« ma_base ») ou connexion directe (« hote:port/service », « //hote/service »)
        m = re.fullmatch(r"/*([^/:]+)(?::(\d+))?/(.+)", texte)
        if m:
            return {k: v for k, v in (("hote", m.group(1)), ("port", m.group(2)), ("base", m.group(3))) if v}
        return {"base": texte} if texte else {}
    m = re.fullmatch(r"([^,]+?)(?:,(\d+))?", texte)  # « hote » ou « hote,port »
    return {k: v for k, v in (("hote", m.group(1)), ("port", m.group(2))) if v} if m else {}


def _serveur_depuis_neutre(forme: str, c: dict) -> str:
    if forme == "oracle":
        if c.get("hote"):
            return c["hote"] + (f":{c['port']}" if c.get("port") else "") + "/" + (c.get("base") or "")
        return c.get("base") or ""
    return (c.get("hote") or "") + (f",{c['port']}" if c.get("port") else "")


def _decouper_jeu(forme: str, jeu: str) -> dict[str, str]:
    """« {schema}.{table} » ou « {base}.{schema}.{table} » : le nom du jeu ArcGIS en clés neutres."""
    noms = re.findall(r"\{(\w+)\}", forme)
    parties = jeu.split(".", len(noms) - 1)
    return dict(zip(noms[len(noms) - len(parties):], parties))


# == lecture ====================================================================
def _completer_ancienne_chaine(cat: Catalogue, chaine: dict[str, str]) -> dict[str, str]:
    """Anciens .lyrx : pas de DBCLIENT ni de DB_CONNECTION_PROPERTIES, le moteur et le serveur sont dans
    INSTANCE (« sde:sqlserver:serveur », « sde:oracle11g:alias », « sde:oracle$alias »)."""
    instance = chaine.get("INSTANCE", "")
    if chaine.get("DBCLIENT") or not instance:
        return chaine
    moteurs = {k: v for k, v in cat.sources.get("moteurs_instance", {}).items() if not k.startswith("_")}
    moteur = next((v for k, v in moteurs.items() if instance.lower().startswith(k)), None)
    if moteur is None:
        return chaine
    chaine = dict(chaine, DBCLIENT=moteur)
    if not chaine.get("DB_CONNECTION_PROPERTIES"):
        m = re.match(r"sde:[^:$]*[:$](.+)", instance, re.I)
        serveur = m.group(1) if m else chaine.get("SERVER", "")
        if serveur:
            chaine["DB_CONNECTION_PROPERTIES"] = serveur
    return chaine


def lire_lyrx(cat: Catalogue, rapport: Rapport, dc: dict, ou: str) -> Source:
    source = Source()
    fabrique = dc.get("workspaceFactory")
    if dc.get("type") not in (None, "CIMStandardDataConnection", "CIMFeatureDatasetDataConnection"):
        rapport.perte(ou + " > source", f"Connexion de données « {dc.get('type')} » non prise en charge : source à reconnecter dans QGIS.")
        source.a_reconnecter = True
        return source
    source.jeu = dc.get("dataset")
    chaine = _completer_ancienne_chaine(cat, lire_chaine_arcgis(dc.get("workspaceConnectionString") or ""))
    candidates = [s for s in cat.sources["sources"] if s["lyrx"].get("workspaceFactory") == fabrique]
    entree = next((s for s in candidates if all(chaine.get(k, "").lower() == v.lower()
                                                for k, v in (s.get("base") or {}).get("si", {}).items())), None)
    if entree is None:
        rapport.perte(ou + " > source", f"Type de source ArcGIS « {fabrique} » inconnu : source à reconnecter.",
                      "Ajouter la source dans catalogues/sources.json.")
        source.a_reconnecter = True
        return source
    source.type = entree["pivot"]
    if entree.get("secrete"):
        source.a_reconnecter = True
        rapport.avertir(ou + " > source", f"Base de données « {chaine.get('DBCLIENT', '?')} » non prise en charge : "
                                          f"source à reconnecter dans le logiciel cible. Jeu de données : « {source.jeu} ».",
                        "Ajouter le moteur dans catalogues/sources.json (« base »).")
        return source
    if entree.get("base"):
        return _lire_base_lyrx(cat, rapport, entree, chaine, source, ou)
    dossier = (chaine.get("DATABASE") or cat.sources.get("dossier_defaut", ".")).replace("\\", "/").rstrip("/")
    source.dossier = dossier or "."
    if source.jeu and entree.get("extension_jeu") and source.jeu.lower().endswith(entree["extension_jeu"]):
        source.jeu = source.jeu[: -len(entree["extension_jeu"])]
    prefixe = entree.get("prefixe_jeu_lyrx")
    if source.jeu and prefixe and source.jeu.lower().startswith(prefixe.lower()):
        source.jeu = source.jeu[len(prefixe):]
    return source


def _lire_base_lyrx(cat: Catalogue, rapport: Rapport, entree: dict, chaine: dict, source: Source, ou: str) -> Source:
    b = entree["base"]
    c: dict[str, str] = dict(b.get("defauts", {}))
    if _srid_defaut(cat):
        c["srid"] = _srid_defaut(cat)
    c.update(_serveur_vers_neutre(b["serveur"], chaine.get("DB_CONNECTION_PROPERTIES", "")))
    for cle_arcgis, cle in b.get("cles_lyrx", {}).items():
        if chaine.get(cle_arcgis):
            c[cle] = chaine[cle_arcgis]
    c["authentification"] = cat.sources.get("authentification", {}).get(c.get("authentification", "DBMS").upper(), "base")
    if c["authentification"] == "systeme":
        c.pop("utilisateur", None)
    version = c.pop("version", None)
    if version and version.lower() not in ("sde.default", "dbo.default", "default"):
        rapport.avertir(ou + " > source", f"Version de géodatabase « {version} » : QGIS lit la version par défaut.")
    c.update(_decouper_jeu(b["jeu_lyrx"], source.jeu or ""))
    source.connexion = {k: v for k, v in c.items() if v not in (None, "")}
    source.jeu = ".".join(x for x in (c.get("schema"), c.get("table")) if x)
    return source  # ENCRYPTED_PASSWORD n'est jamais lu


def lire_qgis(cat: Catalogue, rapport: Rapport, datasource: str, fournisseur: str, ou: str) -> tuple[Source, Optional[str]]:
    # Le mot de passe éventuel ne reste pas dans l'adresse gardée telle quelle.
    sans_mot_de_passe = re.sub(r"\s*\bpassword\s*=\s*(?:'(?:[^'\\]|\\.)*'|\S*)", "", datasource)
    source = Source(fournisseur_qgis=fournisseur, chemin_qgis=sans_mot_de_passe)
    for entree in cat.sources["sources"]:
        q = entree.get("qgis")
        if q and q["fournisseur"] == fournisseur and entree.get("base"):
            return _lire_base_qgis(cat, rapport, entree, datasource, source, ou)
    filtre = None
    m = re.search(r"\|subset=(.*)$", datasource, re.S)
    if m:
        filtre = m.group(1)
        datasource = datasource[: m.start()]
    for entree in cat.sources["sources"]:
        q = entree.get("qgis")
        if not q or q["fournisseur"] != fournisseur or not q.get("motif"):
            continue
        motif = re.escape(q["motif"]).replace(r"\{dossier\}", r"(?P<dossier>[^|]*?)").replace(r"\{jeu\}", r"(?P<jeu>[^|/\\]+?)")
        m = re.fullmatch(motif, datasource.replace("\\", "/"))
        if m and (not entree.get("si_dossier") or m.group("dossier").lower().endswith(entree["si_dossier"])):
            source.type = entree["pivot"]
            source.dossier = m.group("dossier") or "."
            source.jeu = m.group("jeu")
            return source, filtre
    source.a_reconnecter = True
    rapport.avertir(ou + " > source", f"Source QGIS « {fournisseur} » non reconnue ({datasource[:60]}) : à reconnecter dans ArcGIS Pro.",
                    "Ajouter le cas dans catalogues/sources.json.")
    return source, filtre


def _lire_base_qgis(cat: Catalogue, rapport: Rapport, entree: dict, datasource: str, source: Source, ou: str):
    b = entree["base"]
    cles, schema, table, geom, sql = lire_adresse_qgis(datasource)
    source.type = entree["pivot"]
    if not table:
        source.a_reconnecter = True
        rapport.avertir(ou + " > source", f"Adresse QGIS « {entree['qgis']['fournisseur']} » sans table : à reconnecter dans ArcGIS Pro.")
        return source, sql
    c: dict[str, str] = {}
    for cle_qgis, cle in b.get("cles_qgis", {}).items():
        if cles.get(cle_qgis):
            c[cle] = cles[cle_qgis]
    c.update({k: v for k, v in (("schema", schema), ("table", table), ("colonne_geometrie", geom)) if v})
    c["authentification"] = "base" if c.get("utilisateur") else "systeme"
    source.connexion = c
    source.jeu = ".".join(x for x in (schema, table) if x)
    if cles.get("authcfg"):
        rapport.info(ou + " > source", "Configuration d'authentification QGIS (« authcfg ») propre à ce poste : "
                                       "ArcGIS demandera l'utilisateur et le mot de passe.")
    return source, sql


# == écriture ===================================================================
def ecrire_lyrx(cat: Catalogue, rapport: Rapport, couche: Couche, ou: str) -> dict:
    s = couche.source
    entree = _entree(cat, s.type)
    if entree is None or entree.get("secrete") or s.a_reconnecter or not s.jeu:
        rapport.avertir(ou + " > source", f"Source de données à reconnecter dans ArcGIS Pro (« Définir la source de données »). Jeu : « {s.jeu or couche.nom} ».")
        return {"type": "CIMStandardDataConnection", "workspaceConnectionString": "DATABASE=.",
                "workspaceFactory": "Shapefile", "dataset": f"{s.jeu or couche.nom}.shp", "datasetType": "esriDTFeatureClass"}
    if entree.get("base"):
        b = entree["base"]
        c = dict(s.connexion)
        serveur = _serveur_depuis_neutre(b["serveur"], c)
        valeurs = _Valeurs(c, serveur=serveur)
        chaine = {k: v.format_map(valeurs) for k, v in b.get("fixe_lyrx", {}).items()}
        chaine["DB_CONNECTION_PROPERTIES"] = serveur
        for cle_arcgis, cle in b.get("cles_lyrx", {}).items():
            if cle == "authentification":
                inverse = {v: k for k, v in cat.sources.get("authentification", {}).items() if not k.startswith("_")}
                chaine[cle_arcgis] = inverse.get(c.get("authentification", "base"), "DBMS")
            elif c.get(cle):
                chaine[cle_arcgis] = c[cle]
        if c.get("authentification") == "base":
            rapport.info(ou + " > source", f"Connexion gardée ({entree['pivot']}, « {serveur} », table « {s.jeu} ») ; "
                                           "le mot de passe n'est pas recopié : ArcGIS Pro le demandera.")
        jeu = b["jeu_lyrx"].format(**{k: c.get(k, "") for k in ("base", "schema", "table")}).strip(".")
        return {"type": "CIMStandardDataConnection", "workspaceConnectionString": ecrire_chaine_arcgis(chaine),
                "workspaceFactory": entree["lyrx"]["workspaceFactory"], "dataset": jeu, "datasetType": "esriDTFeatureClass"}
    dossier = (s.dossier or ".").replace("/", "\\")
    jeu = s.jeu + (entree.get("extension_jeu") or "")
    return {"type": "CIMStandardDataConnection", "workspaceConnectionString": f"DATABASE={dossier}",
            "workspaceFactory": entree["lyrx"]["workspaceFactory"], "dataset": jeu, "datasetType": "esriDTFeatureClass"}


def ecrire_qgis(cat: Catalogue, rapport: Rapport, couche: Couche, ou: str) -> tuple[str, str]:
    s = couche.source
    if s.chemin_qgis and s.fournisseur_qgis:
        chemin, fournisseur = s.chemin_qgis, s.fournisseur_qgis
        entree = next((e for e in cat.sources["sources"] if (e.get("qgis") or {}).get("fournisseur") == fournisseur and e.get("base")), None)
        if entree is None and couche.filtre:
            chemin += "|subset=" + couche.filtre
        return fournisseur, chemin  # adresse QGIS d'origine, filtre « sql= » compris pour une base
    entree = _entree(cat, s.type)
    if entree is None or not entree.get("qgis") or s.a_reconnecter or not s.jeu:
        rapport.avertir(ou + " > source", f"Source de données à reconnecter dans QGIS (clic droit sur la couche, « Changer la source de données… »). Jeu : « {s.jeu or '?'} ».")
        chemin, fournisseur = (s.jeu or couche.nom), "ogr"
    elif entree.get("base"):
        return entree["qgis"]["fournisseur"], _adresse_base(cat, rapport, entree, couche, ou)
    else:
        fournisseur = entree["qgis"]["fournisseur"]
        chemin = entree["qgis"]["motif"].format(dossier=s.dossier or ".", jeu=s.jeu)
    if couche.filtre:
        chemin += "|subset=" + couche.filtre
    return fournisseur, chemin


def _adresse_base(cat: Catalogue, rapport: Rapport, entree: dict, couche: Couche, ou: str) -> str:
    b = entree["base"]
    c = {**b.get("defauts", {}), **couche.source.connexion}
    morceaux = []
    for cle_qgis, cle in b.get("cles_qgis", {}).items():
        if c.get(cle):
            morceaux.append(f"{cle_qgis}={_guillemets(c[cle])}" if cle_qgis in ("dbname", "user", "key") else f"{cle_qgis}={c[cle]}")
    morceaux += [f"{k}={v}" for k, v in b.get("fixe_qgis", {}).items()]
    table = '"%s"' % c["table"].replace('"', '""')
    if c.get("schema"):
        table = '"%s".' % c["schema"].replace('"', '""') + table
    if c.get("colonne_geometrie"):
        table += f" ({c['colonne_geometrie']})"
    morceaux.append(f"table={table}")
    morceaux.append("sql=" + (couche.filtre or ""))
    if c.get("authentification") == "base":
        rapport.info(ou + " > source", f"Connexion gardée ({entree['pivot']}, base « {c.get('base', '?')} », table « {couche.source.jeu} ») ; "
                                       "le mot de passe n'est pas recopié : QGIS le demandera."
                     + (" " + b["remarque_qgis"] if b.get("remarque_qgis") else ""))
    return " ".join(morceaux)


# == coche « Garder la source de données » =====================================
def anonymiser(couche: Couche) -> None:
    """Coche décochée : la source se réduit au nom du jeu de données, à reconnecter."""
    s = couche.source
    jeu = s.jeu or couche.nom
    couche.source = Source(jeu=jeu, a_reconnecter=True)
