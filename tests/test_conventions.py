"""Mellangan's conventions: living things face south, and everything is built from 16-pixel cells."""
import json
import shutil
import subprocess

import numpy as np
import pytest
from PIL import Image

from doteshi import api, mat, pat, profile, sdf
from doteshi.atlas import bake
from doteshi.core.rng import Rng
from doteshi.form.scene import Scene
from doteshi.resolve.style import for_size

from test_atlas import _project

GRID = '''
[atlas]
name = "cells"
layout = "grid"
content = "sprites"
{extra}

[[sprite]]
id = "dot"
variants = {dots}

[[sprite]]
id = "tower"
size = 32
variants = {towers}

[[sprite]]
id = "wall"
size = 16
variants = 1
'''

MORE = '''
@sprite("tower", sizes=[32])
def tower(s, rng):
    s.part(sdf.box(0.5, 0.9, 0.05), mat.matte("#8a8f9c"), profile=profile.bevel(0.2), relief=0.3)

@sprite("wall", sizes=[16], aspect=3.0)
def wall(s, rng):
    s.part(sdf.box(2.9, 0.9), mat.matte("#9a6a4a"), profile=profile.flat(0.02), height=0.01)

@sprite("crab", living=True)
def crab(s, rng):
    s.part(sdf.ellipse(0.7, 0.5), mat.glossy("#c0563f"))
'''


def _grid(tmp_path, dots=3, towers=2, extra=""):
    manifest = _project(tmp_path, GRID.format(dots=dots, towers=towers, extra=extra))
    shapes = tmp_path / "sprites" / "shapes.py"
    shapes.write_text(shapes.read_text(encoding="utf-8") + MORE, encoding="utf-8")
    return manifest


# --- facing ---

def test_turning_a_scene_moves_geometry_but_not_the_light():
    def build(turn):
        s = Scene(Rng("turn"))
        if turn:
            s.turn(turn)
        s.part(sdf.circle(0.5), mat.matte("#888888"))
        s.part(sdf.circle(0.15).at(0.0, -0.7), mat.matte("#ff0000"))                 # a head, built pointing up
        return s.rasterize(64, 64, 1)

    def head(gb):
        ys, xs = np.nonzero(gb.pid == 2)
        return gb.xs[int(xs.mean())], gb.ys[int(ys.mean())]

    assert head(build(0))[1] < -0.6                                                  # north
    x, y = head(build(180 - 15))                                                     # south, a little to the east
    assert y > 0.6 and 0.1 < x < 0.3
    # The body is a plain dome either way: its lit side stays top left.
    a, b = build(0), build(165)
    assert np.allclose(a.SX[32, 20:44], b.SX[32, 20:44], atol=1e-6)


def test_patterns_turn_with_the_scene():
    def build(turn):
        s = Scene(Rng("turn"))
        s.turn(turn)
        s.part(sdf.circle(0.8), mat.matte("#888888")).tint("#ffffff", pat.custom(lambda c: (c.y < -0.4).astype(float)))
        return s.rasterize(64, 64, 1)

    cap = lambda gb: gb.lab[..., 0] > 0.9
    assert cap(build(0))[10, 32] and not cap(build(0))[54, 32]                       # painted on the north side
    assert cap(build(180))[54, 32] and not cap(build(180))[10, 32]                   # and it turns with the body


def test_demo_living_things_face_south():
    api.load("content")
    assert api.REGISTRY["slime"].living and api.REGISTRY["beetle"].living and not api.REGISTRY["tree"].living
    for seed in range(1, 9):
        # The slime's eyes sit right of the middle of its body: a glance to the south-south-east.
        gb = api.rasterize("slime", 64, seed, ss=2)
        ys, xs = np.nonzero(gb.A > 0.5)
        middle = gb.xs[(xs.min() + xs.max()) // 2]
        eyes = [x for _, x, _, _ in gb.keeps]
        assert len(eyes) == 2 and sum(eyes) / 2 > middle + 0.05
        # The beetle's head (its eyes) is in the lower half and right of centre.
        gb = api.rasterize("beetle", 64, seed, ss=2)
        ex, ey = np.mean([k[1] for k in gb.keeps]), np.mean([k[2] for k in gb.keeps])
        assert ey > 0.3 and ex > 0.0


# --- cells ---

def test_one_pixel_scale_up_to_64():
    assert {for_size(s).name for s in (16, 32, 48, 64)} == {"tiny"}


def test_big_sprites_take_a_block_of_cells(tmp_path):
    files, st = bake.bake(_grid(tmp_path), tmp_path / "out", cache_dir=None)
    lock = json.loads((tmp_path / "cells.lock.json").read_text(encoding="utf-8"))
    data = json.loads(files["cells.json"])
    assert data["meta"]["cell"] == 16 and data["meta"]["pitch"] == 18 and data["meta"]["columns"] == 24
    atlas = np.asarray(Image.open(tmp_path / "out" / "cells.png"))
    assert atlas.shape[1] == 24 * 18 and atlas.shape[0] % 18 == 0

    by = {s["name"]: s for s in data["sprites"]}
    tower, wall, dot = by["tower_32_0"], by["wall_16_0"], by["dot_16_0"]
    assert (tower["cols"], tower["rows"], tower["source"]) == (2, 2, {"w": 32, "h": 32})
    assert (wall["cols"], wall["rows"], wall["source"]) == (3, 1, {"w": 48, "h": 16})
    assert (dot["cols"], dot["rows"], dot["w"], dot["h"]) == (1, 1, 16, 16)

    # No two sprites share a cell, and blocks never wrap round the end of a row.
    cells = []
    for s in data["sprites"]:
        assert s["index"] % 24 + s["cols"] <= 24
        assert (s["x"], s["y"]) == (s["index"] % 24 * 18 + 1, s["index"] // 24 * 18 + 1)
        cells += [s["index"] + r * 24 + c for r in range(s["rows"]) for c in range(s["cols"])]
    assert len(cells) == len(set(cells))
    assert bake.check(lock) == []

    # The pieces, put back together, are the sprite; the gutters between them are clear.
    whole = np.asarray(api.render("tower", 32, 0))
    for r in range(2):
        for c in range(2):
            x, y = tower["x"] + c * 18, tower["y"] + r * 18
            assert np.array_equal(atlas[y:y + 16, x:x + 16], whole[r * 16:(r + 1) * 16, c * 16:(c + 1) * 16])
    assert atlas[tower["y"]:tower["y"] + 34, tower["x"] + 16:tower["x"] + 18, 3].max() == 0
    assert atlas[tower["y"] + 16:tower["y"] + 18, tower["x"]:tower["x"] + 34, 3].max() == 0


def test_blocks_keep_their_cells_when_more_are_added(tmp_path):
    bake.bake(_grid(tmp_path, dots=2, towers=1), tmp_path / "out", cache_dir=None)
    before = {k: v["index"] for k, v in json.loads((tmp_path / "cells.lock.json").read_text())["sprites"].items()}
    _, st = bake.bake(_grid(tmp_path, dots=6, towers=3), tmp_path / "out", cache_dir=None)
    lock = json.loads((tmp_path / "cells.lock.json").read_text())
    assert st["kept"] == 4 and st["new"] == 6 and st["moved"] == 0
    assert all(lock["sprites"][k]["index"] == v for k, v in before.items())
    assert bake.check(lock) == []


def test_sizes_must_split_into_cells(tmp_path):
    manifest = _grid(tmp_path)
    manifest.write_text(manifest.read_text(encoding="utf-8").replace("size = 32", "size = 24"), encoding="utf-8")
    with pytest.raises(ValueError, match="tower_24_0 is 24x24; every sprite in this grid must be a multiple of 16"):
        bake.bake(manifest, tmp_path / "out", cache_dir=None)


def test_manifest_style_and_living_flag(tmp_path):
    manifest = _grid(tmp_path, extra='style = "pixel-hd"')
    manifest.write_text(manifest.read_text(encoding="utf-8") + '\n[[sprite]]\nid = "crab"\nstyle = "tiny"\n',
                        encoding="utf-8")
    settings, instances = bake.read_manifest(manifest)
    styles = {i.id: i.style for i in instances}
    assert styles["dot"] == "pixel-hd" and styles["crab"] == "tiny"
    files, _ = bake.bake(manifest, tmp_path / "out", cache_dir=None)
    by = {s["name"]: s for s in json.loads(files["cells.json"])["sprites"]}
    assert by["crab_16_0"]["living"] is True and "living" not in by["dot_16_0"]


@pytest.mark.skipif(shutil.which("g++") is None, reason="no C++ compiler on this machine")
def test_grid_header_compiles_and_addresses_pieces(tmp_path):
    bake.bake(_grid(tmp_path), tmp_path / "out", cache_dir=None)
    t = json.loads((tmp_path / "cells.lock.json").read_text())["sprites"]["tower_32_1"]
    (tmp_path / "out" / "check.cpp").write_text(
        '#include "cells.gen.hpp"\n'
        "using namespace atlas::gen;\n"
        "static_assert(CELL == 16 && PITCH == 18 && COLUMNS == 24);\n"
        "static_assert(tower_32_1.cols == 2 && tower_32_1.rows == 2 && tower_32_1.sw == 32 && !tower_32_1.living);\n"
        f"static_assert(piece(tower_32_1, 1, 1).x == {t['x'] + 18} && piece(tower_32_1, 1, 1).y == {t['y'] + 18});\n"
        "static_assert(piece(tower_32_1, 1, 1).w == 16 && piece(tower_32_1, 1, 1).ox == 16);\n"
        "int main() { return dot_16_0.page; }\n", encoding="utf-8")
    run = subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-fsyntax-only", "check.cpp"],
                         cwd=tmp_path / "out", capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
