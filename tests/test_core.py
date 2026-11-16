"""Core maths: generator, noise, shapes, curves, colour."""
import hashlib
import importlib.util
import math
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from procsprites.core import color, curves, noise, sdf
from procsprites.core.rng import Rng

KIT = Path("C:/Users/soulwax/Workspace/c++/mellangan/tools/sprite_kit.py")


# --- generator ---

def test_rng_golden():
    golden = {("a",): [4192132519135618423, 5914708556773729588, 11359034459365304104, 18252637113872205732],
              ("mushroom", 1): [9618456759134674953, 15604951096711651373, 542218890929545661, 3798285681404369482],
              ("beetle", 7, "legs"): [3897217148140404284, 1767606459209773519, 18039881399961108149,
                                      17169889432106063448]}
    for key, want in golden.items():
        r = Rng(*key)
        assert [r.u64() for _ in range(4)] == want


def test_rng_streams_ignore_draw_order():
    a, b = Rng("x", 1), Rng("x", 1)
    for _ in range(5):
        a.float()
    assert a.stream("legs").u64() == b.stream("legs").u64()
    assert a.stream("legs").u64() != a.stream("wings").u64()


def test_rng_is_even():
    counts = Counter(Rng("s", i).choice(range(7)) for i in range(3500))
    assert min(counts.values()) > 420 and max(counts.values()) < 580
    r = Rng("ints")
    assert {r.int(2, 5) for _ in range(200)} == {2, 3, 4, 5}
    assert all(0.0 <= Rng("f", i).float() < 1.0 for i in range(200))


# --- noise ---

def _grid(n=64, span=5.0):
    return np.meshgrid(np.linspace(0, span, n), np.linspace(0, span, n))


def test_noise_golden():
    x, y = _grid()
    golden = {"gnoise": "31d7f9024371a43c", "fbm": "76473363ae58deca", "ridged": "fa7aa77cb24d11d6",
              "worley": "54dbd30dadd03282"}
    got = {"gnoise": noise.gnoise(x, y, 3), "fbm": noise.fbm(x, y, 3), "ridged": noise.ridged(x, y, 3),
           "worley": noise.worley(x, y, 3)[0]}
    for name, a in got.items():
        assert hashlib.sha256(np.round(a, 9).tobytes()).hexdigest()[:16] == golden[name], name


def test_noise_seeds_differ():
    x, y = _grid()
    assert not np.allclose(noise.gnoise(x, y, 1), noise.gnoise(x, y, 2))


@pytest.mark.parametrize("fn", [noise.gnoise, noise.fbm, noise.ridged, lambda *a, **k: noise.worley(*a, **k)[0]])
def test_noise_tiles(fn):
    t = np.linspace(0.0, 4.0, 97)
    zero, four = np.zeros_like(t), np.full_like(t, 4.0)
    assert np.allclose(fn(zero, t, 5, period=4), fn(four, t, 5, period=4), atol=1e-6)
    assert np.allclose(fn(t, zero, 5, period=4), fn(t, four, 5, period=4), atol=1e-6)


# --- shapes ---

def _d(shape, x, y):
    return float(shape.eval(np.array([[float(x)]]), np.array([[float(y)]])).d[0, 0])


def test_circle_and_box_distances():
    assert _d(sdf.circle(0.5), 0, 0) == pytest.approx(-0.5)
    assert _d(sdf.circle(0.5), 1, 0) == pytest.approx(0.5)
    assert _d(sdf.circle(0.5).at(1, 1), 1, 1.5) == pytest.approx(0.0, abs=1e-9)
    assert _d(sdf.box(0.4, 0.2), 0, 0) == pytest.approx(-0.2)
    assert _d(sdf.box(0.4, 0.2), 0.7, 0) == pytest.approx(0.3)
    assert _d(sdf.box(0.4, 0.2), 0.7, 0.6) == pytest.approx(0.5)


def test_ellipse_signs_and_axes():
    e = sdf.ellipse(0.6, 0.3)
    assert _d(e, 0, 0) < 0 and _d(e, 0.59, 0) < 0 and _d(e, 0.61, 0) > 0 and _d(e, 0, 0.31) > 0
    assert _d(e, 0.8, 0) == pytest.approx(0.2, abs=0.01)
    assert _d(e, 0, -0.5) == pytest.approx(0.2, abs=0.01)


def test_capsule_tapers():
    c = sdf.capsule((0, 0), (1, 0), 0.2, 0.1)
    assert _d(c, 0, 0.3) == pytest.approx(0.1)
    assert _d(c, 1, 0.3) == pytest.approx(0.2)
    assert _d(c, 0.5, 0) == pytest.approx(-0.15)
    assert _d(c, -0.5, 0) == pytest.approx(0.3)


def test_polygon_inside_and_out():
    tri = sdf.polygon([(0, 0), (1, 0), (0, 1)])
    assert _d(tri, 0.2, 0.2) == pytest.approx(-0.2)
    assert _d(tri, -0.3, 0.5) == pytest.approx(0.3)
    assert _d(tri, 1.0, 1.0) == pytest.approx(math.sqrt(0.5))


def test_lathe_follows_its_profile():
    vase = sdf.lathe((0, -1), (0, 1), [0.2, 0.5, 0.2])
    f = vase.eval(np.array([[0.0, 0.25]]), np.array([[0.0, 0.0]]))
    assert f.d[0, 0] < 0 and _d(vase, 0.6, 0) > 0 and _d(vase, 0.3, -0.98) > 0 and _d(vase, 0, 1.2) > 0
    assert f.v[0, 1] == pytest.approx(0.5, abs=0.02) and f.u[0, 0] == pytest.approx(0.5)
    assert f.t[0, 0] == pytest.approx(1.0) and f.t[0, 1] == pytest.approx(0.5, abs=0.02)


def test_stroke_runs_along_its_curve():
    s = sdf.stroke([(0, 0), (0.5, 0.2), (1, 0)], [0.1, 0.1, 0.1])
    assert _d(s, 0.5, 0.2) == pytest.approx(-0.1, abs=0.01)
    assert _d(s, 0.5, -0.3) > 0
    f = s.eval(np.array([[0.0, 1.0]]), np.array([[0.0, 0.0]]))
    assert f.u[0, 0] == pytest.approx(0.0, abs=0.02) and f.u[0, 1] == pytest.approx(1.0, abs=0.02)


def test_combining_shapes():
    a, b = sdf.circle(0.5), sdf.circle(0.5).at(0.6, 0)
    assert _d(a | b, 0.9, 0) < 0 and _d(a - b, 0.3, 0) > 0 and _d(a - b, -0.3, 0) < 0
    assert _d(a & b, 0.3, 0) < 0 and _d(a & b, -0.3, 0) > 0
    assert _d(a.union(b, 0.2), 0.3, 0.45) < _d(a | b, 0.3, 0.45)       # the smooth join fills the notch
    assert _d(a.above(0.0), 0, 0.2) > 0 and _d(a.above(0.0), 0, -0.2) < 0
    assert (a | b).bounds == (-0.5, -0.5, 1.1, 0.5)


def test_placement():
    s = sdf.box(0.4, 0.1)
    assert _d(s.rot(90), 0, 0.3) < 0 and _d(s.rot(90), 0.3, 0) > 0
    assert _d(s.at(0.3, 0).mirror(), -0.6, 0) < 0 and _d(s.at(0.3, 0).mirror(), 0.6, 0) > 0
    assert _d(s.scale(2.0), 0.7, 0) < 0
    b = s.rot(90).bounds
    assert b == pytest.approx((-0.1, -0.4, 0.1, 0.4))


# --- curves ---

def test_resample_is_even_by_arc_length():
    poly = curves.smooth([(0, 0), (0.2, 0.9), (1.0, 1.0), (1.4, 0.1), (2.5, 0.3)], 80)
    steps = np.diff(curves.lengths(poly))
    assert steps.max() / steps.min() < 1.01
    assert np.allclose(poly[0], (0, 0)) and np.allclose(poly[-1], (2.5, 0.3))


def test_curve_passes_through_its_points():
    pts = [(0, 0), (1, 2), (3, 1), (4, 4)]
    poly = curves.catmull_rom(pts, 16)
    for p in pts:
        assert np.min(np.hypot(poly[:, 0] - p[0], poly[:, 1] - p[1])) < 1e-9


# --- colour ---

def test_colour_round_trip():
    rgb = np.random.default_rng(0).random((200, 3))
    lin = color.srgb_to_linear(rgb)
    assert np.allclose(color.linear_to_srgb(lin), rgb, atol=1e-9)
    assert np.allclose(color.oklab_to_linear(color.linear_to_oklab(lin)), lin, atol=1e-6)


def test_array_and_scalar_oklab_agree():
    for c in [(194, 59, 42), (10, 200, 120), (250, 250, 250), (3, 3, 3)]:
        assert np.allclose(color.lab_of(c), color.oklab(c), atol=1e-9)


def test_tone_keeps_base_and_moves_the_right_way():
    lab = np.broadcast_to(color.lab_of("#c23b2a"), (5, 3))
    out = color.tone(lab, np.array([-3.0, -1.0, 0.0, 1.0, 2.0]))
    assert np.allclose(out[2], lab[2], atol=1e-9)
    assert np.all(np.diff(out[:, 0]) > 0)                                  # lightness rises with exposure
    hue = np.degrees(np.arctan2(out[:, 2], out[:, 1]))
    assert hue[0] < hue[2] < hue[4]                                        # red: shadows cooler, lights warmer
    grey = color.tone(np.broadcast_to(color.lab_of("#808080"), (2, 3)), np.array([-2.0, 2.0]))
    assert np.hypot(grey[:, 1], grey[:, 2]).max() < 0.03                   # greys stay near neutral


@pytest.mark.skipif(not KIT.exists(), reason="Mellangan's sprite_kit.py is not on this machine")
def test_ramp_matches_sprite_kit():
    spec = importlib.util.spec_from_file_location("sprite_kit_ref", KIT)
    kit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kit)
    bases = [(194, 59, 42), (140, 90, 50), (122, 79, 166), (44, 140, 134), (216, 138, 42), (86, 112, 143),
             (234, 223, 200), (79, 138, 60), (42, 38, 34), (128, 128, 128)]
    for base in bases:
        for n in (5, 7):
            assert color.ramp(base, n) == kit.ramp(base, n), (base, n)
