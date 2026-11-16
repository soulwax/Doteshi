"""A toadstool seen from slightly below: domed cap, gills in the shade under it, a fibrous stem, moss and grass."""
import math

import numpy as np

from doteshi import mat, pat, profile, sdf, sprite
from doteshi.core import curves
from doteshi.core.mathx import smoothstep

#            cap        spots      stem       gills
KINDS = [("#c23b2a", "#f6ecd9", "#eadfc8", "#dcc097"),   # fly agaric
         ("#8c5a32", "#dcc49c", "#e8dbc0", "#c2a47c"),   # penny bun
         ("#7a4fa6", "#eadbf7", "#ded5e6", "#b99bd2"),   # amethyst deceiver
         ("#2c8c86", "#d9f4e7", "#dfe8dc", "#9ccab9"),   # verdigris
         ("#d88a2a", "#fce8ba", "#ebe0c5", "#d8b87e"),   # golden
         ("#b03868", "#ffe1eb", "#ebdad7", "#d4a1ab"),   # rosy
         ("#56708f", "#e0e7f2", "#dddcd5", "#a8b3c5")]   # slate
GRASS = ["#4f8a3c", "#6aa046", "#3f7a48", "#86b04e"]


def toadstool(s, rng, x, ground, scale, kind, z0=0.0):
    cap_c, spot_c, stem_c, gill_c = kind
    seed = rng.seed32()
    R = scale * rng.uniform(0.50, 0.70)                 # half-width of the cap at its widest
    hc = R * rng.uniform(0.62, 1.02)                    # cap height above its widest line
    lean = scale * rng.uniform(-0.13, 0.13)
    rs = R * rng.uniform(0.17, 0.25)                    # stem radius
    rim_y = ground - scale * rng.uniform(0.78, 1.0)     # height of the cap's rim
    cx = x + lean
    drop = hc * rng.uniform(0.2, 0.34)                  # the rim hangs this far below the widest line
    Rr = R * math.sqrt(1.0 - (drop / hc) ** 2)          # rim radius
    g = Rr * rng.uniform(0.17, 0.27)                    # how much of the underside shows

    # Stem: a bent tube, swollen at the foot.
    foot = (x - lean * 0.7, ground - rs * 1.25)
    mid = ((foot[0] + cx) / 2 + scale * rng.uniform(-0.09, 0.09), (foot[1] + rim_y) / 2)
    stem = s.part(sdf.stroke([foot, mid, (cx, rim_y + g * 0.15)], [rs * 1.4, rs * 0.92, rs * 0.86]).warp(
        0.01 * scale, 3.5 / scale, seed), mat.satin(stem_c, trans=0.3), z=z0 + 0.02)
    stem.bump(pat.grain(0.02 * scale, seed, stretch=16), 0.0045 * scale)
    stem.tint(gill_c, pat.grain(0.02 * scale, seed, stretch=16).step(0.1, 0.6), 0.3)
    stem.tint("#8a6f52", pat.gradient("u", 0.5, 0.0) * pat.mottle(0.12 * scale, seed + 1), 0.75)
    stem.tint(gill_c, pat.gradient("u", 0.8, 1.0), 0.5)
    if rng.chance(0.6):
        # A collar left by the veil, drooping round the stem.
        spine = curves.smooth([foot, mid, (cx, rim_y + g * 0.15)], 40)
        i = int(rng.uniform(0.55, 0.72) * 39)
        (px, py), (tx, ty) = spine[i], curves.tangents(spine)[i]
        tilt = math.degrees(math.atan2(tx, -ty)) + rng.uniform(-6, 6)
        collar = s.part(sdf.ellipse(rs * rng.uniform(1.12, 1.3), rs * rng.uniform(0.22, 0.32)).warp(
            0.012 * scale, 9.0 / scale, seed + 7).rot(tilt).at(px, py), mat.matte(stem_c, trans=0.5),
            relief=0.5, z=z0 + 0.02 + rs * 0.78)
        collar.bump(pat.custom(lambda c: 0.5 + 0.5 * np.cos(c.u / (rs * 0.11)), size=rs * 0.11), 0.006 * scale)
        collar.tint(gill_c, None, 0.35).tint("#8a6f52", pat.gradient("v", -rs * 0.1, rs * 0.3), 0.6)

    # Underside: a tilted dish of gills, facing down and away from the light.
    under = sdf.ellipse(Rr * 0.985, g).at(cx, rim_y)
    radial = pat.custom(lambda c: 0.5 + 0.5 * np.cos(np.arctan2((c.y - rim_y) / g, (c.x - cx) / Rr) * 52.0),
                        size=Rr * 0.05)
    gills = s.part(under, mat.matte(gill_c, trans=0.25), profile=profile.flat(0.02), height=0.0, z=z0 - 0.1)
    gills.bump(pat.custom(lambda c: (rim_y - c.y) / g), g * 2.2, fade=0)
    gills.bump(radial, 0.012 * scale, fade=0)
    gills.tint("#6b4a3a", 1.0 - radial, 0.45)
    gills.tint("#5a3d33", pat.custom(lambda c: smoothstep(0.75, 0.1, np.hypot((c.x - cx) / Rr, (c.y - rim_y) / g))),
               0.5)

    # Cap: an ellipsoid cut off at the rim, with the dish cut out of it.
    body = sdf.ellipse(R, hc, sphere=True).at(cx, rim_y - drop).warp(0.014 * scale, 2.6 / scale, seed + 2)
    cap = s.part(body.above(rim_y).cut(under), mat.satin(cap_c, rough=0.36, spec=0.42), z=z0)
    lip = pat.custom(lambda c: smoothstep(0.035 * scale, 0.0, under.eval(c.x, c.y).d) * (c.y < rim_y))
    cap.bump(pat.lumps(0.5 * scale, seed + 3), 0.02 * scale)
    cap.bump(lip, 0.014 * scale, fade=0)
    cap.tint("#3a1c1c", pat.mottle(0.3 * scale, seed + 4), 0.22)
    cap.tint(spot_c, lip, 0.35)
    if rng.chance(0.75):
        warts = pat.spots(scale * rng.uniform(0.13, 0.24), rng.uniform(0.45, 0.85), seed + 5, vary=0.7, soft=0.3).keep()
        cap.tint(spot_c, warts, 0.95, rough=0.95, spec=0.03)
        cap.bump(warts, 0.016 * scale)
    else:
        cap.tint(spot_c, pat.stripes(0.07 * scale, 0.35, axis="v", seed=seed + 6) * pat.edge(0.22 * scale), 0.35)
    return foot[0]


@sprite("mushroom", sizes=[256], variants=16)
def mushroom(s, rng):
    kind = rng.choice(KINDS)
    ground = 0.86
    seed = rng.seed32()

    # A mound of moss and earth to stand on.
    mound = s.part(sdf.ellipse(rng.uniform(0.5, 0.68), 0.1).at(rng.uniform(-0.05, 0.05), ground + 0.02).warp(
        0.025, 3.0, seed), mat.matte("#6e583e"), relief=1.1, z=-0.02)
    mound.bump(pat.lumps(0.09, seed), 0.03).bump(pat.pores(0.05, seed + 1, 0.7), -0.008)
    mound.tint("#6c9440", pat.mottle(0.22, seed + 2, contrast=1.8).step(0.3, 0.6), 0.9)

    blades = rng.stream("grass")

    def grass(count, z):
        for _ in range(count):
            bx = blades.uniform(-0.6, 0.6)
            tall = blades.uniform(0.14, 0.36)
            sway = blades.uniform(-0.16, 0.16)
            w = blades.uniform(0.016, 0.026)
            blade = s.part(sdf.stroke([(bx, ground + 0.04), (bx + sway * 0.35, ground - tall * 0.55),
                                       (bx + sway, ground - tall)], [w, w * 0.75, 0.0]),
                           mat.satin(blades.choice(GRASS), trans=0.55), z=z, limb=True)
            blade.tint("#2f5a2c", pat.gradient("u", 0.5, 0.0), 0.55)

    grass(blades.int(3, 6), -0.03)
    if rng.chance(0.45):
        side = rng.choice([-1, 1])
        toadstool(s, rng.stream("small"), side * rng.uniform(0.42, 0.56), ground + 0.01,
                  rng.uniform(0.34, 0.46), kind, z0=-0.015)
    toadstool(s, rng.stream("main"), rng.uniform(-0.06, 0.06), ground, 1.0, kind)
    grass(blades.int(3, 6), 0.3)
