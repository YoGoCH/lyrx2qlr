"""Modèle neutre (« pivot ») d'une couche et de sa symbologie.

Les lecteurs (.lyrx, .qlr) remplissent ce modèle ; les écrivains le relisent.
Ainsi, chaque format n'a qu'un lecteur et qu'un écrivain, et les deux sens de
conversion partagent la même représentation.

Unités neutres :
- longueurs en points typographiques (pt), comme ArcGIS Pro ;
- couleurs [R, V, B, A] entières de 0 à 255 ;
- angles en degrés, sens antihoraire ;
- échelles en dénominateur (50000 pour 1:50 000), None = pas de limite.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class Placement:
    """Placement d'un marqueur dans une ligne ou une surface (grille, le long de la ligne…)."""
    type: str
    props: dict[str, Any] = field(default_factory=dict)


@dataclass
class CoucheSymbole:
    """Une couche de symbole (aplat, trait, hachure, marqueur…)."""
    type: str
    props: dict[str, Any] = field(default_factory=dict)
    actif: bool = True
    sous_symbole: Optional["Symbole"] = None
    placement: Optional[Placement] = None


@dataclass
class Symbole:
    """Un symbole : une pile de couches, de la plus basse (dessinée en premier) à la plus haute."""
    genre: str  # surface, ligne, point
    couches: list[CoucheSymbole] = field(default_factory=list)
    opacite: float = 1.0


@dataclass
class Classe:
    """Une classe de rendu : une catégorie (valeurs) ou une classe de valeurs (bornes)."""
    symbole: Optional[Symbole]
    etiquette: str = ""
    valeurs: list[list[Optional[str]]] = field(default_factory=list)
    min: Optional[float] = None
    max: Optional[float] = None
    visible: bool = True


@dataclass
class Rendu:
    """Méthode de rendu : unique, categories ou classes."""
    type: str
    champs: list[str] = field(default_factory=list)
    expression: Optional[str] = None
    classes: list[Classe] = field(default_factory=list)
    symbole_defaut: Optional[Symbole] = None
    etiquette_defaut: str = ""
    methode: Optional[str] = None


@dataclass
class ClasseEtiquette:
    """Une classe d'étiquettes (texte, police, halo, placement, filtre, échelles)."""
    nom: str = ""
    filtre: Optional[str] = None
    props: dict[str, Any] = field(default_factory=dict)


@dataclass
class Source:
    """Source de données. Ne contient jamais de mot de passe (sources.py le retire à la lecture)."""
    type: str = "inconnu"
    dossier: Optional[str] = None
    jeu: Optional[str] = None
    chemin_qgis: Optional[str] = None
    fournisseur_qgis: Optional[str] = None
    a_reconnecter: bool = False
    # Base de données : clés neutres de catalogues/sources.json (hote, port, base, utilisateur,
    # authentification, schema, table, colonne_geometrie, cle, srid).
    connexion: dict[str, str] = field(default_factory=dict)


@dataclass
class Couche:
    """Une couche vectorielle et tout ce qui la rend lisible."""
    nom: str
    geometrie: str = "inconnu"  # point, ligne, surface, inconnu
    source: Source = field(default_factory=Source)
    visible: bool = True
    opacite: float = 1.0
    echelle_min: Optional[float] = None  # au-delà (plus dézoomé), la couche est masquée
    echelle_max: Optional[float] = None  # en deçà (plus zoomé), la couche est masquée
    filtre: Optional[str] = None  # requête de définition, en langage QGIS
    alias: dict[str, str] = field(default_factory=dict)
    champ_affichage: Optional[str] = None
    rendu: Optional[Rendu] = None
    etiquettes_actives: bool = False
    etiquettes: list[ClasseEtiquette] = field(default_factory=list)

    def echelle_de_reference(self) -> Optional[float]:
        """Échelle (dénominateur) au milieu de la plage de visibilité, ou None sans plage.

        Sert à traduire en points les tailles QGIS en unités de carte. Une limite « la plus zoomée »
        de 50 ou moins (QGIS écrit souvent 1) compte comme absente."""
        zoome = self.echelle_max if self.echelle_max and self.echelle_max > 50 else None
        dezoome = self.echelle_min
        if zoome and dezoome:
            return (zoome * dezoome) ** 0.5
        if dezoome:
            return dezoome / 2
        if zoome:
            return zoome * 2
        return None


@dataclass
class Document:
    """Un fichier : une ou plusieurs couches."""
    couches: list[Couche] = field(default_factory=list)
    format_source: str = ""
    version_source: str = ""


def en_dict(objet: Any) -> Any:
    """Transforme le modèle en dictionnaire (pour les tests, le débogage, les exports JSON)."""
    return asdict(objet)
