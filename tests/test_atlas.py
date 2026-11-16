"""The atlas baker: packing, edges, stable placements, exports."""
import json
import shutil
import subprocess

import numpy as np
import pytest
from PIL import Image

from doteshi.atlas import bake, bleed
from doteshi.atlas.pack import MaxRects, first_page, overlaps, place
from doteshi.core.rng import Rng

CONTENT = '''
from doteshi import mat, profile, sdf, sprite, style

@sprite("dot")
def dot(s, rng):
    s.part(sdf.circle(rng.uniform(0.3, 0.8)), mat.glossy(rng.choice(["#c0563f", "#3f6fc0", "#4f8f52"])))

@sprite("bar", aspect=2.0)
def bar(s, rng):
    s.part(sdf.box(rng.uniform(0.8, 1.8), 0.4, 0.1), mat.matte("#d9a441"), profile=profile.bevel(0.3), relief=0.5)

@sprite("slab", style=style.TINY.but(outline="none", fit=None))
def slab(s, rng):
    s.part(sdf.box(1.2, 1.2), mat.matte(rng.choice(["#6c9440", "#6e583e"])), profile=profile.flat(0.02), height=0.01)
'''


def _project(tmp_path, body, name="manifest.toml"):
    (tmp_path / "sprites").mkdir(exist_ok=True)
    (tmp_path / "sprites" / "shapes.py").write_text(CONTENT, encoding="utf-8")
    manifest = tmp_path / name
    manifest.write_text(body, encoding="utf-8")
    return manifest


PACKED = '''
[atlas]
name = "atlas"
content = "sprites"
padding = 2

[[sprite]]
id = "dot"
sizes = [24, 12]
variants = {dots}

[[sprite]]
id = "bar"
size = 16
variants = {bars}
pivot = "center"
'''


def _bake(manifest, tmp_path, **kw):
    return bake.bake(manifest, tmp_path / "out", cache_dir=None, **kw)


def _lock(tmp_path, name="atlas"):
    return json.loads((tmp_path / f"{name}.lock.json").read_text(encoding="utf-8"))


# --- packing ---

def test_maxrects_never_overlaps_and_stays_on_the_page():
    r = Rng("pack")
    b = MaxRects(256, 256)
    placed = []
    for _ in range(120):
        w, h = r.int(4, 40), r.int(4, 40)
        spot = b.insert(w, h)
        if spot:
            placed.append((spot[0], spot[1], w, h))
    assert len(placed) > 60
    for i, a in enumerate(placed):
        assert a[0] >= 0 and a[1] >= 0 and a[0] + a[2] <= 256 and a[1] + a[3] <= 256
        assert not any(overlaps(a, c) for c in placed[i + 1:])
    assert sum(w * h for _, _, w, h in placed) > 0.6 * 256 * 256


def test_place_is_repeatable_and_grows_pages():
    r = Rng("sizes")
    sizes = {f"s{i}": (r.int(8, 60), r.int(8, 60)) for i in range(80)}
    a, pages_a = place(sizes, {}, [], max_size=512)
    b, pages_b = place(dict(reversed(list(sizes.items()))), {}, [], max_size=512)
    assert a == b and pages_a == pages_b
    assert all(w <= 512 and h <= 512 and (w & (w - 1)) == 0 for w, h in pages_a)
    many, pages = place({f"s{i}": (100, 100) for i in range(40)}, {}, [], max_size=256)
    assert len(pages) == 10 and len({(p, x, y) for p, x, y, _, _ in many.values()}) == 40


def test_place_keeps_what_is_already_there():
    first, pages = place({"a": (40, 40), "b": (30, 50), "c": (20, 20)}, {}, [])
    more, pages2 = place({f"n{i}": (25, 25) for i in range(30)}, first, pages)
    assert all(more[k] == first[k] for k in first)
    rects = list(more.values())
    assert not any(a[0] == b[0] and overlaps(a[1:], b[1:]) for i, a in enumerate(rects) for b in rects[i + 1:])
    assert pages2[0][0] >= pages[0][0] and pages2[0][1] >= pages[0][1]


def test_first_page_fits_the_total_area():
    assert first_page({"a": (100, 100)}, 2048) == (128, 128)
    w, h = first_page({f"s{i}": (60, 60) for i in range(100)}, 2048)
    assert w * h >= 360000 and (w, h) == (1024, 512)
    with pytest.raises(ValueError):
        place({"huge": (300, 10)}, {}, [], max_size=256)


# --- edges ---

def test_trim_and_extrude():
    px = np.zeros((10, 12, 4), np.uint8)
    px[3:7, 2:9] = (10, 20, 30, 255)
    crop, x, y = bleed.trim(px)
    assert crop.shape == (4, 7, 4) and (x, y) == (2, 3)
    back = np.zeros_like(px)
    back[y:y + 4, x:x + 7] = crop
    assert np.array_equal(back, px)
    assert bleed.trim(np.zeros((5, 5, 4), np.uint8))[0].shape == (1, 1, 4)
    wide = bleed.extrude(crop, 2)
    assert wide.shape == (8, 11, 4) and wide[..., 3].min() == 255


def test_bleed_spreads_colour_but_not_alpha():
    px = np.zeros((9, 9, 4), np.uint8)
    px[4, 4] = (200, 100, 50, 255)
    out = bleed.bleed(px, 2)
    assert np.array_equal(out[..., 3], px[..., 3])
    assert tuple(out[4, 6, :3]) == (200, 100, 50) and tuple(out[2, 2, :3]) == (200, 100, 50)
    assert tuple(out[4, 7, :3]) == (0, 0, 0)                 # two rounds reach two pixels, no further
    # A bilinear sample half way off the sprite's edge keeps the sprite's colour.
    assert tuple((out[4, 4, :3].astype(int) + out[4, 5, :3]) // 2) == (200, 100, 50)


# --- baking ---

def test_bake_writes_everything_and_placements_are_sound(tmp_path):
    files, st = _bake(_project(tmp_path, PACKED.format(dots=4, bars=3)), tmp_path)
    assert set(files) == {"atlas.png", "atlas.json", "atlas.gen.hpp"}
    assert st["sprites"] == 11 and st["new"] == 11 and bake.check(_lock(tmp_path)) == []
    atlas = np.asarray(Image.open(tmp_path / "out" / "atlas.png"))
    data = json.loads(files["atlas.json"])
    assert data["pages"] == [{"file": "atlas.png", "w": atlas.shape[1], "h": atlas.shape[0]}]
    assert len(data["sprites"]) == 11
    for s in data["sprites"]:
        cut = atlas[s["y"]:s["y"] + s["h"], s["x"]:s["x"] + s["w"]]
        assert cut[..., 3].max() > 0
        assert cut[0, :, 3].any() and cut[-1, :, 3].any() and cut[:, 0, 3].any() and cut[:, -1, 3].any()   # trimmed tight
        ring = atlas[s["y"] - 1:s["y"] + s["h"] + 1, s["x"] - 1:s["x"] + s["w"] + 1].copy()
        ring[1:-1, 1:-1] = 0
        assert ring[..., 3].max() == 0 and ring[..., :3].max() > 0      # clear padding, with bled colour under it
        assert s["source"]["h"] == s["size"] and 0 <= s["trim"]["x"] and s["trim"]["x"] + s["w"] <= s["source"]["w"]
    bar = next(s for s in data["sprites"] if s["name"] == "bar_16_0")
    assert bar["source"] == {"w": 32, "h": 16}
    assert bar["pivot"] == [16 - bar["trim"]["x"], 8 - bar["trim"]["y"]]
    dot = next(s for s in data["sprites"] if s["name"] == "dot_24_0")
    assert dot["pivot"] == [12 - dot["trim"]["x"], 24 - dot["trim"]["y"]]


def test_adding_sprites_moves_nothing(tmp_path):
    _bake(_project(tmp_path, PACKED.format(dots=3, bars=2)), tmp_path)
    before = _lock(tmp_path)["sprites"]
    _, st = _bake(_project(tmp_path, PACKED.format(dots=9, bars=7)), tmp_path)
    after = _lock(tmp_path)
    assert st["kept"] == len(before) == 8 and st["new"] == 17 and st["moved"] == 0
    for name, s in before.items():
        assert {k: after["sprites"][name][k] for k in ("page", "x", "y", "w", "h")} == \
               {k: s[k] for k in ("page", "x", "y", "w", "h")}
    assert bake.check(after) == []


def test_removed_sprites_keep_their_slot_until_pruned(tmp_path):
    _bake(_project(tmp_path, PACKED.format(dots=4, bars=3)), tmp_path)
    slot = _lock(tmp_path)["sprites"]["dot_24_3"]["slot"]
    files, st = _bake(_project(tmp_path, PACKED.format(dots=3, bars=3)), tmp_path)
    assert st["retired"] == 2 and not _lock(tmp_path)["sprites"]["dot_24_3"]["live"]
    assert "dot_24_3" not in files["atlas.json"].decode() and "dot_24_3" not in files["atlas.gen.hpp"].decode()
    _bake(_project(tmp_path, PACKED.format(dots=4, bars=3)), tmp_path)
    assert _lock(tmp_path)["sprites"]["dot_24_3"]["slot"] == slot and _lock(tmp_path)["sprites"]["dot_24_3"]["live"]
    _bake(_project(tmp_path, PACKED.format(dots=3, bars=3)), tmp_path, prune=True)
    assert "dot_24_3" not in _lock(tmp_path)["sprites"]


def test_two_bakes_are_byte_identical(tmp_path):
    manifest = _project(tmp_path, PACKED.format(dots=4, bars=3))
    a, _ = _bake(manifest, tmp_path, repack=True)
    lock_a = (tmp_path / "atlas.lock.json").read_bytes()
    b, _ = _bake(manifest, tmp_path, repack=True)
    assert a == b and lock_a == (tmp_path / "atlas.lock.json").read_bytes()


def test_cache_gives_the_same_atlas(tmp_path):
    manifest = _project(tmp_path, PACKED.format(dots=3, bars=2))
    cold, _ = bake.bake(manifest, tmp_path / "out", cache_dir=tmp_path / "cache", repack=True)
    seen = []
    warm, _ = bake.bake(manifest, tmp_path / "out", cache_dir=tmp_path / "cache", repack=True, report=seen.append)
    assert cold == warm and seen == []


GRID = '''
[atlas]
name = "tiles"
layout = "grid"
content = "sprites"
cell = 16
gutter = 1
columns = 24

[[sprite]]
id = "slab"
size = 16
variants = {slabs}
tile = true

[[sprite]]
id = "dot"
size = 16
variants = {dots}
'''


def test_grid_cells_match_the_mellangan_layout(tmp_path):
    files, _ = _bake(_project(tmp_path, GRID.format(slabs=20, dots=10)), tmp_path)
    lock = _lock(tmp_path, "tiles")
    assert lock["pages"] == [[24 * 18, 2 * 18]]
    for s in lock["sprites"].values():
        assert (s["x"], s["y"], s["w"], s["h"]) == (s["index"] % 24 * 18 + 1, s["index"] // 24 * 18 + 1, 16, 16)
    assert sorted(s["index"] for s in lock["sprites"].values()) == list(range(30))
    atlas = np.asarray(Image.open(tmp_path / "out" / "tiles.png"))
    dot = lock["sprites"]["dot_16_0"]
    assert atlas[dot["y"] - 1, dot["x"]:dot["x"] + 16, 3].max() == 0          # sprites keep a clear gutter
    slab = lock["sprites"]["slab_16_0"]
    assert atlas[slab["y"] - 1, slab["x"]:slab["x"] + 16, 3].min() == 255     # tiles extrude into it


def test_grid_indices_are_append_only(tmp_path):
    _bake(_project(tmp_path, GRID.format(slabs=3, dots=2)), tmp_path)
    before = {k: v["index"] for k, v in _lock(tmp_path, "tiles")["sprites"].items()}
    _bake(_project(tmp_path, GRID.format(slabs=6, dots=2)), tmp_path)
    after = {k: v["index"] for k, v in _lock(tmp_path, "tiles")["sprites"].items()}
    assert all(after[k] == v for k, v in before.items())
    assert sorted(after.values()) == list(range(8)) and after["slab_16_5"] == 7


def test_bad_manifests_say_what_is_wrong(tmp_path):
    with pytest.raises(ValueError, match="no sprite named 'ghost'"):
        _bake(_project(tmp_path, '[atlas]\ncontent = "sprites"\n[[sprite]]\nid = "ghost"\n'), tmp_path)
    with pytest.raises(ValueError, match="unknown .atlas. keys: colour"):
        _bake(_project(tmp_path, '[atlas]\ncontent = "sprites"\ncolour = 1\n'), tmp_path)
    with pytest.raises(ValueError, match="holds 16x16"):
        _bake(_project(tmp_path, GRID.format(slabs=1, dots=1).replace('id = "dot"\nsize = 16', 'id = "dot"\nsize = 24'),
                       "grid.toml"), tmp_path)
    _bake(_project(tmp_path, PACKED.format(dots=1, bars=1)), tmp_path)
    with pytest.raises(ValueError, match="--repack"):
        _bake(_project(tmp_path, PACKED.format(dots=1, bars=1).replace('padding = 2', 'layout = "grid"')), tmp_path)


@pytest.mark.skipif(shutil.which("g++") is None, reason="no C++ compiler on this machine")
def test_header_compiles(tmp_path):
    _bake(_project(tmp_path, PACKED.format(dots=2, bars=2)), tmp_path)
    lock = _lock(tmp_path)["sprites"]["dot_24_1"]
    (tmp_path / "out" / "check.cpp").write_text(
        '#include "atlas.gen.hpp"\n'
        "static_assert(atlas::gen::SPRITE_COUNT == 6);\n"
        f"static_assert(atlas::gen::dot_24_1.x == {lock['x']} && atlas::gen::dot_24_1.w == {lock['w']});\n"
        "static_assert(atlas::gen::PAGE_SIZE[0][0] > 0);\n"
        "int main() { return atlas::gen::bar_16_0.page; }\n", encoding="utf-8")
    run = subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-fsyntax-only", "check.cpp"],
                         cwd=tmp_path / "out", capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
