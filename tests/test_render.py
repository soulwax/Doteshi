"""The renderer end to end: scenes, the surface buffer, lighting and the painted resolver."""
import numpy as np
import pytest

from procsprites import api, mat, pat, profile, sdf
from procsprites.core.rng import Rng
from procsprites.form.scene import Scene
from procsprites.resolve import painted
from procsprites.shade.light import ambient_occlusion, cast_shadow, shade


def _scene():
    s = Scene(Rng("test"))
    s.part(sdf.box(0.8, 0.6, 0.1), mat.matte("#8a9a7a"), profile=profile.flat(0.05), height=0.05)
    s.part(sdf.circle(0.3).at(-0.2, -0.1), mat.glossy("#c0563f"), z=0.05).bump(pat.pores(0.1), -0.02)
    s.part(sdf.capsule((0.1, 0.3), (0.6, 0.45), 0.09, 0.05), mat.metal("#c9cdd6"), z=0.05)
    return s


def _pixels(image):
    return np.asarray(image).astype(np.float64)


def test_render_is_repeatable():
    a = painted.resolve(_scene().rasterize(64, 64, 4))
    b = painted.resolve(_scene().rasterize(64, 64, 4))
    assert a.tobytes() == b.tobytes()


def test_framing_is_the_same_at_every_size():
    boxes = []
    for size, ss in ((64, 4), (256, 2), (1024, 1)):
        gb = _scene().rasterize(size, size, ss)
        ys, xs = np.nonzero(gb.A > 0.5)
        boxes.append(np.array([xs.min(), ys.min(), xs.max() + 1, ys.max() + 1]) / gb.W)
    assert np.allclose(boxes[0], boxes[1], atol=0.01) and np.allclose(boxes[1], boxes[2], atol=0.01)


def test_higher_parts_cover_lower_ones():
    gb = _scene().rasterize(128, 128, 2)
    slab, ball = 1, 2
    row, col = np.argmin(np.abs(gb.ys - -0.1)), np.argmin(np.abs(gb.xs - -0.2))
    assert gb.pid[row, col] == ball and gb.H[row, col] > 0.3
    assert gb.pid[np.argmin(np.abs(gb.ys - -0.5)), np.argmin(np.abs(gb.xs - 0.6))] == slab
    assert gb.A[0, 0] == 0.0


def test_dome_normals_face_outward():
    s = Scene(Rng("dome"))
    s.part(sdf.circle(0.8), mat.matte("#888888"))
    nx, ny, nz = s.rasterize(128, 128, 1).normals()
    assert nz[64, 64] > 0.99
    assert nx[64, 20] < -0.5 and nx[64, 108] > 0.5 and ny[20, 64] < -0.5 and ny[108, 64] > 0.5


def test_light_comes_from_the_top_left():
    s = Scene(Rng("ball"))
    s.part(sdf.circle(0.8), mat.matte("#888888"))
    px = _pixels(painted.resolve(s.rasterize(64, 64, 4), outline=0))
    assert px[20, 20, :3].mean() > px[44, 44, :3].mean() + 40


def test_cast_shadow_falls_down_and_right():
    H = np.zeros((80, 80))
    H[30:40, 30:40] = 0.5
    lit = cast_shadow(H, (-0.44, -0.58, 0.69), 0.025, 0.75, 0.3)
    assert lit[45, 45] < 0.3 and lit[20, 20] > 0.99 and lit[35, 35] > 0.99


def test_occlusion_darkens_creases_only():
    H = np.zeros((60, 60))
    H[:, 30:] = 0.4
    zero = np.zeros_like(H)
    ao = ambient_occlusion(H, zero, zero, 0.02, 0.2, 1.25)
    assert ao[30, 28] < 0.9 and ao[30, 5] > 0.99 and ao[30, 40] > 0.99
    # A smooth slope is not a crease.
    ramp = np.tile(np.arange(60) * 0.02 * 0.5, (60, 1))
    assert ambient_occlusion(ramp, np.full_like(ramp, 0.5), zero, 0.02, 0.2, 1.25)[30, 30] > 0.99


def test_edges_carry_no_dark_fringe():
    # Half-covered pixels must keep the surface colour at half alpha, not a darkened mix with nothing.
    alpha = np.zeros((8, 8))
    alpha[:, :3] = 1.0
    rgb = np.where(alpha[..., None] > 0, [0.8, 0.5, 0.2], 0.0)
    out, a = painted.downsample(rgb, alpha, 2)
    assert a[0, 1] == pytest.approx(0.5) and np.allclose(out[0, 1], [0.8, 0.5, 0.2])
    image = _pixels(painted.to_image(out, a))
    assert image[0, 1, 3] == 128 and image[0, 3].max() == 0      # nothing stored under full transparency


def test_fine_patterns_drop_out_at_small_sizes():
    def build():
        s = Scene(Rng("detail"))
        s.part(sdf.circle(0.8), mat.matte("#888888")).bump(pat.pores(0.05), -0.05)
        return s

    plain = Scene(Rng("detail"))
    plain.part(sdf.circle(0.8), mat.matte("#888888"))
    small = build().rasterize(16, 16, 4)
    assert np.allclose(small.SX, plain.rasterize(16, 16, 4).SX)      # pores are under 1.5px: not drawn
    assert not np.allclose(build().rasterize(256, 256, 1).SX, plain.rasterize(256, 256, 1).SX)


def test_onlay_follows_what_is_under_it():
    s = Scene(Rng("onlay"))
    base = s.part(sdf.circle(0.8), mat.matte("#888888"))
    s.part(sdf.circle(0.2).at(1.2, 0), mat.matte("#ff0000"), height=0.02, on=base)     # off the base: nothing
    s.part(sdf.circle(0.2), mat.matte("#ff0000"), height=0.02, on=base)
    gb = s.rasterize(64, 64, 2)
    assert gb.A[64, 127] == 0.0 and gb.pid[64, 64] == 3
    assert gb.H[64, 64] == pytest.approx(0.8 + 0.02, abs=0.01)


def test_glow_spills_onto_neighbours():
    def lit(glow):
        s = Scene(Rng("glow"))
        s.part(sdf.box(0.9, 0.9), mat.matte("#404040"), profile=profile.flat(0.02), height=0.01)
        s.part(sdf.circle(0.15), mat.glowing("#ffb347") if glow else mat.matte("#ffb347"), z=0.01)
        return shade(s.rasterize(64, 64, 2))[0]

    assert lit(True)[64, 76].sum() > lit(False)[64, 76].sum() + 0.02      # just outside the glowing disc


def test_registry_and_demo_content():
    api.load("content")
    assert {"mushroom", "beetle"} <= set(api.REGISTRY)
    for id in ("mushroom", "beetle"):
        a, b = api.render(id, 48, 3), api.render(id, 48, 3)
        assert a.size == (48, 48) and a.tobytes() == b.tobytes()
        assert api.render(id, 48, 4).tobytes() != a.tobytes()
        alpha = np.asarray(a)[..., 3]
        assert 0.1 < (alpha > 128).mean() < 0.8
