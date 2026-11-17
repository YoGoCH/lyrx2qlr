"""Assemble un favicon.ico à partir d'images PNG carrées (16, 32, 48 px…).

    .\\outils\\py.ps1 outils\\ico.py web\\favicon.ico i16.png i32.png i48.png

Le format .ico accepte des PNG tels quels : un en-tête, une ligne par image, puis les PNG.
Les PNG se fabriquent à partir de web/icon.svg (par exemple avec Edge sans fenêtre, option
--screenshot).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path


def taille_png(donnees: bytes) -> tuple[int, int]:
    if donnees[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("pas une image PNG")
    return struct.unpack(">II", donnees[16:24])


def assembler(sortie: Path, pngs: list[Path]) -> None:
    images = [p.read_bytes() for p in pngs]
    entete = struct.pack("<HHH", 0, 1, len(images))
    lignes, position = b"", 6 + 16 * len(images)
    for donnees in images:
        largeur, hauteur = taille_png(donnees)
        if largeur != hauteur or largeur > 256:
            raise ValueError(f"image {largeur}×{hauteur} : il faut un carré de 256 px au plus")
        lignes += struct.pack("<BBBBHHII", largeur % 256, hauteur % 256, 0, 0, 1, 32, len(donnees), position)
        position += len(donnees)
    sortie.write_bytes(entete + lignes + b"".join(images))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    assembler(Path(sys.argv[1]), [Path(p) for p in sys.argv[2:]])
    print(f"{sys.argv[1]} : {len(sys.argv) - 2} image(s)")
