"""Le dépôt est public : rien de privé ne doit y être suivi par git (outils/verifier_depot.py)."""
import shutil
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "outils"))


@pytest.mark.skipif(not (RACINE / ".git").exists() or not (shutil.which("git") or Path("C:/Program Files/Git/cmd/git.exe").is_file()),
                    reason="pas de dépôt git")
def test_rien_de_prive_dans_le_depot():
    import verifier_depot
    assert verifier_depot.controler(verifier_depot.contenus(index=True)) == []


def test_le_controle_refuse_ce_qui_est_prive():
    import verifier_depot
    problemes = verifier_depot.controler({
        "corpus/fichiers/vrai.lyrx": b"{}",
        "CLAUDE.md": b"notes",
        "docs/x.md": ("écrire à jean" + "@" + "entreprise.ch").encode(),  # écrite en morceaux : le contrôle lit aussi ce fichier
        "outils/y.gpkg": b"",
        "exemples/fabriques/q.qlr": b"<qgis/>",
        "tests/z.py": b"anna@tuiles.exemple.ch",
    })
    assert len(problemes) == 4
    assert not any("fabriques" in p or "tests/z.py" in p for p in problemes)
