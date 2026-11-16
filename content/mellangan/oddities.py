"""Fourteen biome curiosities for Mellangan: standing objects and landmarks, one variant each."""
import math

from doteshi import mat, pat, profile, sdf, sprite

G = 0.9


def rock(s, rx=0.7, ry=0.2, cy=G - 0.12, color="#6f6a72", seed=1, z=-0.02):
    r = s.part(sdf.ellipse(rx, ry).at(0, cy).warp(0.03, 3.0, seed), mat.matte(color), relief=1.0, z=z)
    r.bump(pat.lumps(0.2, seed), 0.03)
    return r


def crystal(s, x, base, h, w, tilt, color, seed, z=0.0):
    shape = sdf.polygon([(-w, 0), (-w, -h * 0.72), (0, -h), (w, -h * 0.72), (w, 0)]).rot(tilt).at(x, base)
    p = s.part(shape, mat.glossy(color, rough=0.15, spec=0.9, trans=0.5), profile=profile.bevel(0.5), relief=0.9, z=z)
    p.bump(pat.facets(0.3, seed), 0.08, fade=0.05)
    p.tint("#ffffff", pat.gradient("x", w * 0.3, -w), 0.35)
    return p


@sprite("oddity_geode", sizes=[16], variants=1)
def geode(s, rng):
    rock(s, 0.75, 0.22, G - 0.15, "#5d5866", 3)
    for x, h, w, t, c, z in [(-0.38, 0.9, 0.17, -14, "#79d9dc", 0.0), (0.4, 0.75, 0.16, 16, "#5cc3cf", 0.0),
                             (0.0, 1.3, 0.22, 2, "#bdf4f2", 0.05), (-0.16, 0.8, 0.14, -6, "#46a9b6", 0.1),
                             (0.18, 0.6, 0.12, 8, "#8fe6e4", 0.1)]:
        crystal(s, x, G - 0.2, h, w, t, c, int(x * 40) + 5, z)


@sprite("oddity_mushroom_ring", sizes=[16], variants=1)
def mushroom_ring(s, rng):
    s.part(sdf.ellipse(0.85, 0.14).at(0, G - 0.06).warp(0.02, 3, 4), mat.matte("#5f7a3a"), relief=0.5, z=-0.05
           ).tint("#86a84a", pat.mottle(0.2, 2), 0.6)
    for x, base, sc, z in [(-0.62, G - 0.02, 0.9, 0.02), (0.62, G - 0.02, 0.85, 0.02), (0.0, G - 0.34, 0.62, -0.03)]:
        s.part(sdf.box(0.09 * sc, 0.26 * sc, 0.02).at(x, base - 0.26 * sc), mat.satin("#e8dcc0"), z=z)
        s.part(sdf.ellipse(0.34 * sc, 0.07 * sc).at(x, base - 0.5 * sc), mat.matte("#8e66c4"), z=z + 0.02)
        cap = s.part(sdf.ellipse(0.36 * sc, 0.36 * sc, sphere=True).at(x, base - 0.52 * sc).above(base - 0.52 * sc),
                     mat.satin("#efe2c4", rough=0.4), z=z + 0.04)
        cap.tint("#b5532f", pat.spots(0.2 * sc, 0.8, 11 + int(x * 10), vary=0.4, soft=0.3).keep(), 0.95)


@sprite("oddity_hoodoo", sizes=[16], variants=1)
def hoodoo(s, rng):
    shaft = sdf.polygon([(-0.32, G), (-0.24, -0.1), (-0.3, -0.45), (0.3, -0.45), (0.22, -0.1), (0.36, G)])
    p = s.part(shaft.warp(0.02, 3, 7), mat.matte("#c98a4a"), relief=1.0)
    p.tint("#8e4a2a", pat.stripes(0.2, 0.4, axis="v", seed=3), 0.55)
    p.bump(pat.cracks(0.3, 5), -0.03)
    cap = s.part(sdf.ellipse(0.58, 0.22).at(0.02, -0.62).warp(0.02, 3, 9), mat.matte("#9c5a34"), relief=1.0, z=0.05)
    cap.tint("#d9a05c", pat.gradient("y", -0.85, -0.5), 0.5)
    s.part(sdf.ellipse(0.2, 0.3).at(0.1, G - 0.2), mat.matte("#2a160c"), profile=profile.flat(0.05), z=0.6, keep=True)


@sprite("oddity_spruce", sizes=[16], variants=1)
def spruce(s, rng):
    s.part(sdf.box(0.1, 0.3, 0.02).at(0, G - 0.28), mat.matte("#6a4426"), z=-0.02)
    tiers = [(0.72, 0.62, 0.36), (0.55, 0.28, 0.0), (0.38, -0.05, -0.38), (0.22, -0.35, -0.8)]
    cols = ["#1f5a34", "#276b3b", "#2e7a42", "#38904a"]
    for i, (w, y, top) in enumerate(tiers):
        t = s.part(sdf.polygon([(-w, y + 0.18), (0, top - 0.1), (w, y + 0.18)]).warp(0.015, 4, i),
                   mat.satin(cols[i], trans=0.4), z=0.02 * i, relief=0.8)
        t.tint("#133a24", pat.gradient("y", y - 0.1, y + 0.2), 0.5)
    s.part(sdf.ellipse(0.1, 0.07).at(0.5, G - 0.04).rot(-20), mat.matte("#8a5a30"), z=0.05).tint(
        "#5a3a1c", pat.stripes(0.05, 0.4, axis="u"), 0.5)


@sprite("oddity_salt_lick", sizes=[16], variants=1)
def salt_lick(s, rng):
    blk = sdf.polygon([(-0.62, G), (-0.66, 0.1), (-0.45, -0.3), (0.35, -0.38), (0.62, -0.05), (0.66, G)])
    p = s.part(blk.warp(0.02, 3, 2), mat.translucent("#eef2f4", trans=0.3), profile=profile.bevel(0.4), relief=0.9)
    p.bump(pat.facets(0.35, 4), 0.06, fade=0.05)
    p.tint("#a8b2bd", pat.gradient("y", 0.1, G), 0.5)
    s.part(sdf.ellipse(0.3, 0.24).at(0.0, 0.25), mat.matte("#e49aac"), profile=profile.flat(0.05), relief=0.4, z=0.6,
           keep=True)
    s.part(sdf.ellipse(0.12, 0.08).at(-0.3, 0.05), mat.matte("#7a8594"), z=0.6, keep=True)


@sprite("oddity_drowned_bell", sizes=[16], variants=1)
def drowned_bell(s, rng):
    s.part(sdf.box(0.68, 0.09, 0.02).at(0, -0.85), mat.matte("#6a4a2c"), z=0.0).tint("#3a2a1a", pat.grain(0.04, 3), 0.5)
    s.part(sdf.box(0.04, 0.12).at(0, -0.7), mat.matte("#3a2a1a"), z=0.0)
    bell = sdf.polygon([(-0.22, -0.6), (0.22, -0.6), (0.36, -0.15), (0.62, 0.4), (-0.62, 0.4), (-0.36, -0.15)])
    b = s.part(bell, mat.metal("#3d9c8c", rough=0.5), relief=1.0, z=0.05)
    b.tint("#2a6a5a", pat.mottle(0.2, 2), 0.5)
    s.part(sdf.box(0.64, 0.06, 0.02).at(0, 0.38), mat.metal("#d09a3a"), z=0.08, keep=True)
    for i, w in enumerate([0.75, 0.5]):
        s.part(sdf.ellipse(w, 0.09).at(0, 0.62 + 0.24 * i).warp(0.02, 3, i), mat.matte("#1c3a52"), z=-0.05).tint(
            "#4a8ab0", pat.gradient("y", 0.55 + 0.2 * i, 0.7 + 0.2 * i), 0.4)


@sprite("oddity_lunar_dial", sizes=[16], variants=1)
def lunar_dial(s, rng):
    s.part(sdf.box(0.5, 0.14, 0.03).at(0, G - 0.14), mat.matte("#5a5f6b"), z=-0.03)
    s.part(sdf.box(0.14, 0.2).at(0, 0.58), mat.matte("#4a4f5b"), z=-0.02)
    d = s.part(sdf.circle(0.74).at(0, -0.06), mat.matte("#98a0b4"), profile=profile.bevel(0.3), relief=0.6)
    moon = sdf.circle(0.4).at(-0.12, -0.06) - sdf.circle(0.34).at(0.08, -0.14)
    s.part(moon, mat.matte("#eef2fa"), profile=profile.flat(0.05), z=0.6, keep=True)
    s.part(sdf.capsule((0.1, -0.06), (0.45, -0.52), 0.07, 0.04), mat.matte("#2c303c"), profile=profile.flat(0.05),
           z=0.7, keep=True)
    s.part(sdf.circle(0.09).at(0.1, -0.06), mat.matte("#2c303c"), z=0.7, keep=True)
    for a in (150, 210, 330, 30):
        s.part(sdf.circle(0.06).at(0.6 * math.cos(math.radians(a)), -0.06 + 0.6 * math.sin(math.radians(a))),
               mat.matte("#d8dde8"), z=0.5, keep=True)


@sprite("oddity_rubble_stash", sizes=[16], variants=1)
def rubble_stash(s, rng):
    chest = s.part(sdf.box(0.62, 0.45, 0.05).at(0.05, G - 0.55), mat.matte("#8a6238"), relief=0.8)
    chest.tint("#4a3420", pat.stripes(0.2, 0.2, axis="u", seed=2), 0.5)
    s.part(sdf.box(0.62, 0.07).at(0.05, G - 0.75), mat.matte("#4a3420"), z=0.05)
    s.part(sdf.box(0.09, 0.12).at(0.12, G - 0.66), mat.metal("#f0c030", rough=0.3), z=0.2, keep=True)
    for x, y, rx, ry, c in [(-0.5, G - 0.22, 0.4, 0.3, "#8a8c92"), (0.55, G - 0.15, 0.42, 0.22, "#6c6e76"),
                            (-0.05, G - 0.1, 0.3, 0.14, "#9a9ca2"), (-0.6, G - 0.58, 0.22, 0.2, "#7a7c84"),
                            (0.7, G - 0.4, 0.2, 0.18, "#8a8c92")]:
        s.part(sdf.ellipse(rx, ry).at(x, y).warp(0.03, 3, int(x * 30)), mat.matte(c), relief=1.0, z=0.3).bump(
            pat.facets(0.3, 3), 0.04)


@sprite("oddity_kiln", sizes=[16], variants=1)
def kiln(s, rng):
    s.part(sdf.box(0.13, 0.3, 0.02).at(0.38, -0.32), mat.matte("#7a4a34"), z=-0.02)
    dome = sdf.ellipse(0.86, 0.95).at(0, G - 0.02) & sdf.box(1.0, 0.5).at(0, G - 0.5)
    body = s.part(dome, mat.matte("#b8603a"), relief=1.0)
    body.bump(pat.rings(0.25, 3), 0.03).tint("#e0885a", pat.gradient("y", -0.2, 0.4), 0.4)
    s.part(sdf.box(0.92, 0.07, 0.02).at(0, G - 0.04), mat.matte("#3a3236"), z=0.3)
    mouth = sdf.box(0.36, 0.22, 0.02).at(0, G - 0.3) | sdf.circle(0.36).at(0, G - 0.46)
    s.part(mouth.grow(0.07), mat.matte("#2e2a2e"), z=0.4)
    s.part(mouth, mat.glowing("#ff8a20", emit=1.0), profile=profile.flat(0.05), z=0.6).tint(
        "#ffe070", pat.gradient("y", G - 0.1, G - 0.7), 0.7)


@sprite("oddity_amber_beetle", sizes=[16], variants=1)
def amber_beetle(s, rng):
    blob = sdf.ellipse(0.8, 0.72).at(0, 0.16).warp(0.03, 3, 6) & sdf.box(1.0, 0.8).at(0, 0.1)
    a = s.part(blob, mat.translucent("#f8c850", trans=0.5), profile=profile.flat(0.1), relief=0.5, z=-0.02)
    a.tint("#ffe090", pat.gradient("y", 0.0, -0.5), 0.5)
    s.part(sdf.ellipse(0.3, 0.4).at(0, 0.25), mat.matte("#150a02"), profile=profile.flat(0.1), z=0.7, keep=True)
    s.part(sdf.circle(0.16).at(0, -0.15), mat.matte("#150a02"), profile=profile.flat(0.1), z=0.7, keep=True)
    for dy in (0.05, 0.22, 0.4):
        for sx in (-1, 1):
            s.part(sdf.capsule((sx * 0.15, dy), (sx * 0.52, dy + 0.1 - 0.16 * (dy > 0.3)), 0.07, 0.06),
                   mat.matte("#150a02"), profile=profile.flat(0.1), z=0.7, keep=True)
    s.part(sdf.ellipse(0.1, 0.06).at(-0.4, -0.2).rot(-30), mat.glossy("#fff6d8"), z=0.9, keep=True)


@sprite("oddity_lightning_rod", sizes=[16], variants=1)
def lightning_rod(s, rng):
    s.part(sdf.box(0.5, 0.22, 0.04).at(0, G - 0.22), mat.matte("#767a84"), relief=0.9).bump(pat.facets(0.3, 3), 0.04)
    s.part(sdf.box(0.09, 0.5).at(0, 0.4), mat.metal("#8a8f9a", rough=0.4), z=0.05)
    bolt = sdf.stroke([(0.3, -0.98), (-0.12, -0.62), (0.14, -0.46), (-0.04, -0.2), (0.0, -0.05)],
                      [0.09, 0.1, 0.1, 0.09, 0.07])
    s.part(bolt, mat.matte("#eef8ff"), profile=profile.flat(0.05), z=0.8, keep=True)


@sprite("oddity_glass_heron", sizes=[16], variants=1)
def glass_heron(s, rng):
    for x in (-0.06, 0.14):
        s.part(sdf.stroke([(x, G), (x + 0.02, 0.2)], [0.045, 0.04]), mat.satin("#4a4e5c"), z=0.0, keep=True)
    s.part(sdf.polygon([(-0.4, 0.15), (-0.7, -0.3), (-0.45, -0.1), (-0.1, 0.1)]), mat.glossy("#7ec0e6", rough=0.15),
           z=0.0)
    body = s.part(sdf.ellipse(0.52, 0.31).at(-0.05, 0.0).rot(-18), mat.glossy("#a8d8f0", rough=0.15, trans=0.5),
                  relief=1.0, z=0.05)
    body.bump(pat.facets(0.28, 4), 0.07, fade=0.05)
    s.part(sdf.polygon([(-0.4, 0.05), (-0.05, -0.25), (0.3, 0.1), (-0.2, 0.3)]),
           mat.glossy("#6fb4e0", rough=0.15, trans=0.5), z=0.12).bump(pat.facets(0.3, 5), 0.06)
    s.part(sdf.stroke([(0.3, -0.1), (0.5, -0.4), (0.3, -0.6), (0.4, -0.78)], [0.08, 0.06, 0.05, 0.06]),
           mat.glossy("#c8eefc", rough=0.15, trans=0.5), z=0.08)
    s.part(sdf.polygon([(0.42, -0.88), (0.95, -0.78), (0.42, -0.72)]), mat.satin("#e8c470"), z=0.09, keep=True)
    s.part(sdf.circle(0.025).at(0.42, -0.82), mat.matte("#1a2030"), z=0.2, keep=True)
    s.part(sdf.circle(0.05).at(-0.2, -0.05), mat.glossy("#ffffff"), z=0.3, keep=True)


@sprite("oddity_echo_pit", sizes=[16], variants=1)
def echo_pit(s, rng):
    r = s.part(sdf.ellipse(0.95, 0.55).at(0, 0.34).warp(0.02, 3, 3), mat.matte("#8c8f99"), relief=1.0)
    r.bump(pat.facets(0.3, 2), 0.04).tint("#c4c8d2", pat.gradient("y", 0.0, 0.5), 0.4)
    s.part(sdf.ellipse(0.74, 0.4).at(0, 0.38), mat.matte("#1c1840"), profile=profile.flat(0.05), z=0.5)
    for i, k in enumerate((0.85, 0.5)):
        ring = sdf.ellipse(0.74 * k + 0.09, 0.4 * k + 0.06).at(0, 0.38) - sdf.ellipse(0.74 * k - 0.05, 0.4 * k - 0.03).at(0, 0.38)
        s.part(ring, mat.matte("#c4c6ff"), profile=profile.flat(0.05), z=0.9 + 0.01 * i, keep=True)


@sprite("oddity_starfall_well", sizes=[16], variants=1)
def starfall_well(s, rng):
    wall = s.part(sdf.box(0.62, 0.28, 0.04).at(0, G - 0.28), mat.matte("#9fc0dc"), relief=0.9)
    wall.bump(pat.facets(0.28, 2), 0.03).tint("#7a98b8", pat.gradient("y", 0.6, G), 0.4)
    s.part(sdf.ellipse(0.62, 0.12).at(0, G - 0.56), mat.matte("#2c3550"), z=0.1, profile=profile.flat(0.05))
    pts = []
    for i in range(10):
        a = math.radians(-90 + 36 * i)
        rad = 0.52 if i % 2 == 0 else 0.22
        pts.append((rad * math.cos(a), -0.4 + rad * math.sin(a)))
    s.part(sdf.polygon(pts).grow(0.06), mat.glowing("#ffd860", emit=0.6), z=0.1, soft=True)
    s.part(sdf.polygon(pts), mat.glowing("#ffcf3f", emit=1.0), profile=profile.bevel(0.4), z=0.2, keep=True)
