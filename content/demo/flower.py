"""A daisy-like flower facing the viewer: two rings of petals, a seed head packed by the golden angle, a stem
with leaves."""
import math

from doteshi import mat, pat, profile, sdf, sprite
from doteshi.grow import phyllotaxis

#           petal      petal base  disc       seeds
KINDS = [("#f6c531", "#d9741f", "#5a3a22", "#2e1d14"),    # sunflower
         ("#f4f1e6", "#f3d9a0", "#e0a81e", "#9a6a12"),    # daisy
         ("#e56aa0", "#a8306c", "#f0c23c", "#a3741a"),    # cosmos
         ("#8f6fe0", "#4d38a6", "#f2c94c", "#9c7418"),    # aster
         ("#f0703a", "#b8321f", "#3d2a20", "#1f1512"),    # gaillardia
         ("#7cc7ee", "#3b7fc4", "#f5e28a", "#b39a2e")]    # cornflower


@sprite("flower", sizes=[256, 64, 16], variants=16)
def flower(s, rng):
    petal_c, base_c, disc_c, seed_c = rng.choice(KINDS)
    seed = rng.seed32()
    ground = 0.9
    hx, hy = rng.uniform(-0.1, 0.1), rng.uniform(-0.42, -0.3)       # centre of the flower head
    R = rng.uniform(0.15, 0.21)                                     # radius of the seed head
    L = rng.uniform(0.34, 0.46)                                     # petal length
    green = mat.satin("#4f8a3c", trans=0.45)

    # Stem and leaves.
    foot = (hx * 0.3 + rng.uniform(-0.1, 0.1), ground)
    mid = ((foot[0] + hx) / 2 + rng.uniform(-0.12, 0.12), (ground + hy) / 2)
    stem = s.part(sdf.stroke([foot, mid, (hx, hy)], [0.034, 0.028, 0.024]), green, z=-0.05)
    stem.bump(pat.grain(0.012, seed, stretch=14), 0.004).tint("#2f5a2c", pat.gradient("u", 0.6, 0.0), 0.5)
    for side in (-1, 1):
        t = rng.uniform(0.25, 0.6)
        ax, ay = foot[0] + (mid[0] - foot[0]) * t * 1.6, ground + (hy - ground) * t * 0.8
        tip = (ax + side * rng.uniform(0.28, 0.42), ay - rng.uniform(0.05, 0.22))
        leaf = s.part(sdf.leaf((ax, ay), tip, rng.uniform(0.07, 0.1)), green, profile=profile.pillow(2.0),
                      relief=0.5, z=-0.04)
        leaf.bump(pat.custom(lambda c: 1.0 - abs(c.v) ** 0.5, size=0.03), 0.012)
        leaf.bump(pat.ridges(0.035, axis="v", sharp=2.0), 0.004)
        leaf.tint("#2f5a2c", pat.gradient("u", 0.5, 0.0), 0.5).tint("#86b04e", pat.core(0.6, 1.0), 0.35)

    # Petals: a back ring, then a front ring sitting in its gaps.
    petal = mat.satin(petal_c, rough=0.6, spec=0.14, trans=0.55)
    width = L * rng.uniform(0.17, 0.25)
    turn = rng.uniform(0.0, math.pi)
    rings = [(rng.choice([13, 16, 21]), 1.0, 0.0), (rng.choice([8, 13]), 0.86, 0.02)]
    for count, reach, z in rings:
        for cx, sy, a in phyllotaxis.ring(count, turn + z * 40.0):
            length = (R + L * reach) * rng.uniform(0.9, 1.06)
            a += rng.uniform(-0.06, 0.06)
            cx, sy = math.cos(a), math.sin(a)
            p = s.part(sdf.leaf((hx + cx * R * 0.6, hy + sy * R * 0.6), (hx + cx * length, hy + sy * length),
                                width * rng.uniform(0.85, 1.1), belly=0.6), petal, profile=profile.pillow(2.0),
                       relief=0.42, z=z)
            p.bump(pat.ridges(width * 0.45, axis="u", sharp=1.5), 0.006)
            p.tint(base_c, pat.gradient("u", 0.62, 0.2), 0.85)

    # The seed head: a low dome, with seeds placed by the golden angle and growing toward the rim.
    head = s.part(sdf.ellipse(R, R, sphere=True).at(hx, hy), mat.matte(disc_c), relief=0.5, z=0.05)
    head.tint(seed_c, pat.custom(lambda c: 1.0 - c.t), 0.5)
    grain = mat.satin(seed_c, rough=0.5, spec=0.25)
    n = rng.int(70, 110)
    for x, y, t in phyllotaxis.spiral(n, R * 0.93, turn=turn):
        r = R * (0.035 + 0.045 * t)
        s.part(sdf.circle(r).at(hx + x, hy + y), grain, height=r * 0.9, on=head).tint(disc_c, None, 0.75 * (1.0 - t))
