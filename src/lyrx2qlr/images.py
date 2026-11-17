"""Images intégrées (adresses « data: ») : substitutions de couleurs ArcGIS.

ArcGIS peut repeindre une image de remplissage ou de marqueur (« colorSubstitutions » : telle
couleur de l'image devient telle autre, éventuellement transparente). QGIS n'a pas cette notion :
on applique donc les substitutions à l'image elle-même, qui devient un PNG. Seuls les BMP non
compressés sont traités (ce sont ceux que le corpus contient, souvent en 1 bit) ; pour un autre
format, la fonction renvoie None et l'appelant prévient dans le rapport.

Bibliothèque standard uniquement (Pyodide, QGIS).
"""
from __future__ import annotations

import base64
import struct
import zlib
from typing import Optional

Couleur = list  # [R, V, B, A] 0–255


def recolorer(url: str, substitutions: list[tuple[Couleur, Couleur]]) -> Optional[str]:
    """Renvoie l'image avec les substitutions appliquées (adresse « data:image/png;base64,… »),
    l'image d'origine si aucune substitution ne la change, ou None si le format n'est pas pris en charge."""
    if not url.startswith("data:image/bmp;base64,"):
        return None
    try:
        donnees = base64.b64decode(url.split(",", 1)[1])
        png = _bmp_vers_png(donnees, substitutions)
    except (ValueError, struct.error, IndexError, zlib.error):
        return None
    if png is False:
        return url
    if png is None:
        return None
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def _remplacer(rgb: tuple, substitutions: list[tuple[Couleur, Couleur]]) -> tuple:
    """(R, V, B, A) après substitution ; une couleur absente des substitutions reste opaque."""
    for avant, apres in substitutions:
        if tuple(avant[:3]) == rgb:
            return tuple(apres[:4])
    return rgb + (255,)


def _bmp_vers_png(d: bytes, substitutions: list) -> "bytes | bool | None":
    if d[:2] != b"BM":
        return None
    debut_pixels = struct.unpack_from("<I", d, 10)[0]
    taille_entete = struct.unpack_from("<I", d, 14)[0]
    if taille_entete < 40:
        return None
    largeur, hauteur, _, bits, compression = struct.unpack_from("<iiHHI", d, 18)
    if compression != 0 or largeur <= 0 or hauteur == 0 or bits not in (1, 4, 8, 24, 32):
        return None
    bas_en_haut = hauteur > 0
    hauteur = abs(hauteur)
    pas = ((bits * largeur + 31) // 32) * 4
    lignes = [d[debut_pixels + i * pas: debut_pixels + (i + 1) * pas] for i in range(hauteur)]
    if any(len(ligne) < pas for ligne in lignes):
        return None
    if bas_en_haut:
        lignes.reverse()
    if bits <= 8:
        nombre = struct.unpack_from("<I", d, 46)[0] or (1 << bits)
        debut_palette = 14 + taille_entete
        palette = [tuple(d[debut_palette + 4 * i + 2 - k] for k in range(3)) for i in range(nombre)]
        nouvelle = [_remplacer(c, substitutions) for c in palette]
        if all(n == c + (255,) for n, c in zip(nouvelle, palette)):
            return False
        utiles = (bits * largeur + 7) // 8
        brut = b"".join(b"\0" + ligne[:utiles] for ligne in lignes)
        morceaux = [_morceau(b"IHDR", struct.pack(">IIBBBBB", largeur, hauteur, bits, 3, 0, 0, 0)),
                    _morceau(b"PLTE", bytes(v for c in nouvelle for v in c[:3]))]
        if any(c[3] < 255 for c in nouvelle):
            morceaux.append(_morceau(b"tRNS", bytes(c[3] for c in nouvelle)))
    else:
        octets = bits // 8
        change = False
        sortie = bytearray()
        for ligne in lignes:
            sortie.append(0)
            for x in range(largeur):
                b, v, r = ligne[x * octets: x * octets + 3]
                n = _remplacer((r, v, b), substitutions)
                change = change or n != (r, v, b, 255)
                sortie.extend(n)
        if not change:
            return False
        brut = bytes(sortie)
        morceaux = [_morceau(b"IHDR", struct.pack(">IIBBBBB", largeur, hauteur, 8, 6, 0, 0, 0))]
    morceaux.append(_morceau(b"IDAT", zlib.compress(brut, 9)))
    morceaux.append(_morceau(b"IEND", b""))
    return b"\x89PNG\r\n\x1a\n" + b"".join(morceaux)


def _morceau(nom: bytes, contenu: bytes) -> bytes:
    return struct.pack(">I", len(contenu)) + nom + contenu + struct.pack(">I", zlib.crc32(nom + contenu) & 0xFFFFFFFF)
