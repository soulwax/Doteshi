import json

import numpy as np
import pytest
from PIL import Image

from doteshi.atlas import mellangan

LAYOUT = '''
from dataclasses import dataclass
TILE, CELL = 16, 18

@dataclass(frozen=True)
class Band:
    name: str
    x: int
    y: int
    cols: int
    rows: int

BANDS = (Band("top", 0, 0, 4, 1), Band("side", 36, 20, 2, 2))
'''

SPRITES = '''
from doteshi import mat, sdf, sprite

@sprite("mb_dot", sizes=[16])
def dot(s, rng):
    s.part(sdf.circle(0.6), mat.matte("#c04040"))

@sprite("mb_slab", sizes=[16], aspect=2.0)
def slab(s, rng):
    s.part(sdf.box(1.6, 0.5, 0.1), mat.matte("#4060c0"))
'''


@pytest.fixture
def project(tmp_path):
    (tmp_path / "layout.py").write_text(LAYOUT)
    (tmp_path / "content").mkdir()
    (tmp_path / "content" / "mb.py").write_text(SPRITES)
    return tmp_path


def manifest(project, *sprites):
    lines = ['[atlas]', 'name = "mb"', 'layout = "mellangan"', 'bands = "layout.py"', 'content = "content"']
    for band, index, id in sprites:
        lines += ["[[sprite]]", f'id = "{id}"', f'band = "{band}"', f"index = {index}"]
    path = project / "manifest.toml"
    path.write_text("\n".join(lines) + "\n")
    return path


def test_bake_places_cells_at_band_coordinates(project):
    path = manifest(project, ("top", 2, "mb_dot"), ("side", 2, "mb_slab"))
    m, report = mellangan.bake_bands(path, project / "out", None)
    page = np.asarray(Image.open(project / "out" / "mb.png"))
    assert page.shape == (56, 72, 4)
    assert page[1:17, 37:53, 3].any() and not page[0, 36:54, 3].any()
    side = page[39:55, :, 3]
    assert side[:, 37:53].any() and side[:, 55:71].any() and not side[:, 53:55].any()
    cells = {s["name"]: s for s in json.loads((project / "out" / "mb.json").read_text())["sprites"]}
    assert cells["mb_slab_16_0"]["cells"] == [2, 3] and (cells["mb_slab_16_0"]["x"], cells["mb_slab_16_0"]["y"]) == (37, 39)
    assert report["new"] == ["mb_dot_16_0", "mb_slab_16_0"] and m.lock_path.exists()


def test_rebake_reports_moves_and_check_catches_a_stale_lock(project):
    mellangan.bake_bands(manifest(project, ("top", 0, "mb_dot")), project / "out", None)
    _, report = mellangan.bake_bands(manifest(project, ("top", 0, "mb_dot")), project / "out", None, check=True)
    assert not any(report.values())
    path = manifest(project, ("top", 1, "mb_dot"))
    with pytest.raises(ValueError, match="stale"):
        mellangan.bake_bands(path, project / "out", None, check=True)
    _, report = mellangan.bake_bands(path, project / "out", None)
    assert report["moved"] == ["mb_dot_16_0"]


@pytest.mark.parametrize("sprites, message", [
    ((("top", 3, "mb_slab"),), "does not fit"),
    ((("top", 0, "mb_slab"), ("top", 1, "mb_dot")), "share top cell 1"),
    ((("nowhere", 0, "mb_dot"),), "unknown band"),
    ((("top", 0, "mb_missing"),), "no sprite named"),
])
def test_bad_placements_are_refused(project, sprites, message):
    with pytest.raises(ValueError, match=message):
        mellangan.bake_bands(manifest(project, *sprites), project / "out", None)
