"""Small sizes: style profiles, the pixel resolver, key features, per-size overrides, measurements."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from doteshi import api, mat, pat, profile, sdf
from doteshi.core.rng import Rng
from doteshi.form.scene import Scene
from doteshi.lint import metrics
from doteshi.resolve import pixel
from doteshi.resolve.style import OUTLINE, PAINTED, PIXEL_HD, TINY, for_size, get

KIT = Path("C:/Users/soulwax/Workspace/c++/mellangan/tools/sprite_kit.py")
RED, WHITE, GREEN = "#c0302a", "#f4f0e6", "#3f9a4a"


def _resolve(build, size=16, style=TINY):
    s = Scene(Rng("pixel"))
    build(s)
    m = style.inset
    view = s.fit(size - 2 * m, size - 2 * m, size, style.fit == "body") if style.fit else None
    return np.asarray(pixel.resolve(s.rasterize(size - 2 * m, size - 2 * m, style.ss, nominal=size, view=view), style))


def _near(px, color, within=60):
    """Mask of visible pixels close to an sRGB colour."""
    want = np.array([int(color[i:i + 2], 16) for i in (1, 3, 5)])
    return (px[..., 3] > 0) & (np.abs(px[..., :3].astype(int) - want).sum(axis=-1) < within)


def _ink(px):
    return (px[..., 3] > 0) & (px[..., :3] == np.array(OUTLINE, np.uint8)).all(axis=-1)


# --- profiles ---

def test_profile_follows_size():
    assert [for_size(s).name for s in (16, 24, 32, 64, 96, 256)] == ["tiny", "tiny", "tiny", "tiny",
                                                                    "painted", "painted"]
    assert get("pixel-hd", 256) is PIXEL_HD and get(None, 16) is TINY and get(PAINTED, 16) is PAINTED
    assert TINY.inset == 1 and TINY.but(outline="none").inset == 0 and PAINTED.inset == 0
    with pytest.raises(ValueError, match="no style named 'chunky'"):
        get("chunky", 16)


# --- the resolver ---

def _ball(s):
    s.part(sdf.circle(0.7), mat.glossy(RED))


def test_pixels_are_hard_and_outlined():
    for style in (TINY.but(fit=None), PIXEL_HD):
        px = _resolve(_ball, 16 if style.name == "tiny" else 32, style)
        assert px.shape[0] == px.shape[1] == (16 if style.name == "tiny" else 32)
        assert set(np.unique(px[..., 3])) == {0, 255}
        solid = px[..., 3] > 0
        p = np.pad(solid, 1)
        rim = solid & ~(p[1:-1, :-2] & p[1:-1, 2:] & p[:-2, 1:-1] & p[2:, 1:-1])
        dark = px[..., :3].astype(int).sum(axis=-1) < 200
        assert (rim & dark).sum() == rim.sum()                      # the whole silhouette is closed by dark ink
        assert px[0, 0, 3] == 0 and (px[..., :3][~solid] == 0).all()
    tiny = _resolve(_ball, 16, TINY.but(fit=None))
    solid = tiny[..., 3] > 0
    p = np.pad(solid, 1)
    assert (_ink(tiny) == solid & ~(p[1:-1, :-2] & p[1:-1, 2:] & p[:-2, 1:-1] & p[2:, 1:-1])).all()   # one flat ink


def test_palette_is_capped():
    def busy(s):
        s.part(sdf.circle(0.8), mat.glossy(RED)).tint(GREEN, pat.mottle(0.5, 3)).tint(WHITE, pat.mottle(0.3, 9), 0.6)

    for style, size in ((TINY, 16), (PIXEL_HD, 48)):
        px = _resolve(busy, size, style)
        colours = {tuple(c) for c in px[px[..., 3] > 0][:, :3].tolist()}
        assert 3 <= len(colours) <= style.colors + style.bases       # tones, plus at most one ink per family
    assert len({tuple(c) for c in _resolve(busy)[_resolve(busy)[..., 3] > 0][:, :3].tolist()}) <= TINY.colors + 1


def test_resolve_is_repeatable():
    assert np.array_equal(_resolve(_ball), _resolve(_ball))


def test_fit_fills_the_cell():
    small = lambda s: s.part(sdf.circle(0.3).at(0.2, 0.3), mat.glossy(RED))
    assert (_resolve(small, 16, TINY.but(fit=None))[..., 3] > 0).mean() < 0.2
    fitted = _resolve(small, 16, TINY)[..., 3] > 0
    assert fitted.mean() > 0.6 and fitted[:, 0].any() and fitted[0].any() and fitted[-1].any()


def test_slender_features_keep_one_pixel():
    def stick(s):
        s.part(sdf.circle(0.45).at(0.0, 0.5), mat.matte(RED))
        s.part(sdf.capsule((0.0, 0.2), (0.0, -0.85), 0.025), mat.matte(GREEN))     # 0.35px wide, on a pixel seam

    px = _resolve(stick, 16, TINY.but(fit=None))
    line = _near(px, GREEN)
    rows = np.nonzero(line.any(axis=1))[0]
    assert len(rows) >= 6 and (np.diff(rows) == 1).all()            # unbroken
    assert (line.sum(axis=1) <= 1).all()                            # never two wide
    assert not _ink(px)[rows[0]:rows[-1] - 1].any()                 # tiny draws it as a bare line
    hd = _resolve(stick, 16, PIXEL_HD)
    stem = _near(hd, GREEN, 120) & ~_ink(hd)
    assert stem.any() and (hd[..., 3] > 0)[2:7].sum() >= 3 * stem[2:7].sum()      # pixel-hd outlines it


def test_key_features_survive_and_plain_ones_do_not():
    def face(keep):
        def build(s):
            s.part(sdf.circle(0.8), mat.matte(RED))
            s.part(sdf.circle(0.03).at(-0.31, -0.2), mat.matte(WHITE), z=0.9, keep=keep)
            s.part(sdf.circle(0.03).at(0.33, -0.2), mat.matte(WHITE), z=0.9, keep=keep)
        return build

    kept = _near(_resolve(face(True)), WHITE, 150)
    assert kept.sum() == 2 and len(set(np.nonzero(kept)[0])) == 1   # one pixel each, level with each other
    assert _near(_resolve(face(False)), WHITE, 150).sum() == 0


def test_parts_respect_their_minimum_size():
    def build(s):
        s.part(sdf.circle(0.6), mat.matte(RED))
        s.part(sdf.circle(0.3).at(0.4, -0.4), mat.matte(GREEN), z=0.9, min_size=32)

    assert not _near(_resolve(build, 16), GREEN).any()
    assert _near(_resolve(build, 32, PIXEL_HD), GREEN).any()


def test_kept_patterns_coarsen_instead_of_vanishing():
    def cap(kept):
        spots = pat.spots(0.14, 0.9, 5, vary=0.2)
        return lambda s: s.part(sdf.circle(0.8), mat.matte(RED)).tint(WHITE, spots.keep() if kept else spots)

    assert _near(_resolve(cap(True)), WHITE, 200).sum() >= 4
    assert _near(_resolve(cap(False)), WHITE, 200).sum() == 0
    joined = (pat.spots(0.1) * pat.edge(0.2).step(0.1, 0.5) + 0.0).clip()
    assert not joined.kept and (pat.spots(0.1).keep() * pat.edge(0.2)).step(0.1, 0.5).kept


def test_a_marking_is_one_colour_or_the_other():
    # A stripe edge crossing pixels must not produce in-between pinks.
    def build(s):
        s.part(sdf.box(0.9, 0.9), mat.matte(RED), profile=profile.flat(0.02), height=0.01).tint(
            WHITE, pat.custom(lambda c: (c.x > 0.031).astype(float)))

    px = _resolve(build, 16, TINY.but(outline="none", fit=None, flecks=0.0, waver=0.0))
    row = px[8][px[8, :, 3] > 0][:, :3]
    assert len(row) >= 12 and len({tuple(c) for c in row.tolist()}) == 2


# --- overrides and hand-drawn cells ---

def test_pixelmap():
    img = np.asarray(pixel.pixelmap([".....", ".aab.", ".....", "....."], {"a": (200, 0, 0), "b": (0, 0, 200)}, OUTLINE))
    assert tuple(img[1, 1]) == (200, 0, 0, 255) and tuple(img[1, 3]) == (0, 0, 200, 255)
    assert tuple(img[0, 1]) == (*OUTLINE, 255) and tuple(img[1, 0]) == (*OUTLINE, 255) and img[0, 0, 3] == 0
    assert img[3, 1, 3] == 0
    with pytest.raises(ValueError, match="row 1 is 2 wide"):
        pixel.pixelmap(["...", ".."], {})


def test_override_replaces_one_size_only():
    api.load("content")
    cell = np.asarray(api.render("gem", 16, 2))
    drawn = [(y, x) for y, row in enumerate(api.OVERRIDES[("gem", 16)](Rng("gem", 2))[0])
             for x, ch in enumerate(row) if ch != "."]
    assert cell.shape == (16, 16, 4) and all(cell[y, x, 3] == 255 for y, x in drawn)
    assert metrics.measure(api.render("gem", 16, 2))["outlined"] == 1.0
    assert not np.array_equal(cell, np.asarray(api.render("gem", 16, 2, "tiny")))     # a named style bypasses it
    assert api.render("gem", 24, 2).size == (24, 24)

    @api.override("gem", 20)
    def wrong(rng):
        return ["...."] * 4, {}

    try:
        with pytest.raises(ValueError, match="override of 'gem' is 4x4, expected 20x20"):
            api.render("gem", 20, 0)
    finally:
        del api.OVERRIDES[("gem", 20)]


# --- measurements ---

def test_measure():
    img = pixel.pixelmap(["......", ".aaaa.", ".abaa.", ".aaaa.", ".aaaa.", "......"],
                         {"a": (200, 60, 50), "b": (214, 70, 58)}, OUTLINE)
    m = metrics.measure(img)
    assert m["colours"] == 3 and m["orphans"] == 1 and m["hard_alpha"] and m["outlined"] == 1.0
    assert m["pixels"] == 32 and m["fill"] == pytest.approx(32 / 36)


@pytest.mark.skipif(not KIT.exists(), reason="Mellangan's sprite_kit.py is not on this machine")
def test_orphans_match_sprite_kit():
    spec = importlib.util.spec_from_file_location("sprite_kit_ref2", KIT)
    kit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kit)
    api.load("content")
    for id in ("mushroom", "beetle"):
        for seed in (1, 5, 9):
            img = api.render(id, 32, seed)
            assert metrics.orphans(np.asarray(img)) == kit.orphans(img)


def test_demo_sprites_meet_the_tiny_bar():
    """Kenney's 16px sprites, measured from the unmodified cells in Mellangan's atlas, average 5.8 colours and
    0.4 orphans. The tiny profile is deliberately richer: up to 18 tones and the outline, and a few stray
    pixels left on purpose on rough material. Both stay bounded."""
    api.load("content")
    for id in ("mushroom", "beetle"):
        rows = [metrics.measure(api.render(id, 16, seed)) for seed in range(1, 9)]
        assert all(r["hard_alpha"] for r in rows)
        # 18 tones, the outline, and up to two key-feature colours (eyes keep exactly their own).
        assert max(r["colours"] for r in rows) <= 21 and max(r["orphans"] for r in rows) <= 8
        assert np.mean([r["fill"] for r in rows]) > 0.4
