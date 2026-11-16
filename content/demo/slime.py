"""A slime, seen from the front. Like every living thing it faces south and glances a little to the
south-south-east: its eyes sit right of centre and low on the body. The game mirrors it for the other direction."""
from doteshi import mat, pat, sdf, sprite

KINDS = ["#4fb86a", "#3fa7d6", "#d65c9a", "#e0a12f", "#8d6fe0", "#3fc2b4", "#d6553f"]


@sprite("slime", sizes=[16], variants=16, living=True)
def slime(s, rng):
    colour = rng.choice(KINDS)
    seed = rng.seed32()
    ground = 0.82
    w, h = rng.uniform(0.66, 0.8), rng.uniform(0.5, 0.68)
    lean = rng.uniform(-0.05, 0.05)

    # The body: a dome that spreads where it meets the ground, cut flat underneath.
    body = sdf.ellipse(w * 0.86, h).at(lean, ground - h * 0.92).union(
        sdf.ellipse(w, h * 0.5).at(0.0, ground - h * 0.4), 0.2).warp(0.03, 2.5, seed).above(ground)
    jelly = s.part(body, mat.glossy(colour, rough=0.2, spec=0.8, trans=0.55), relief=0.9)
    jelly.tint("#10202a", pat.gradient("y", ground - h * 0.5, ground + 0.05), 0.45)        # darker toward the ground
    jelly.tint("#ffffff", pat.gradient("y", ground - h * 1.2, ground - h * 1.9), 0.3)       # paler crown
    jelly.bump(pat.lumps(0.3, seed + 1), 0.02)

    # Eyes: right of centre and low, so the slime looks down and a little to its left (our right).
    look = rng.uniform(0.1, 0.16)
    gap = w * rng.uniform(0.26, 0.32)
    ey = ground - h * rng.uniform(0.62, 0.74)
    eye = mat.glossy("#1b1420", rough=0.12, spec=1.0)
    for side in (-1, 1):
        ex = lean + look + side * gap
        s.part(sdf.ellipse(0.075, 0.11).at(ex, ey), eye, relief=0.4, z=0.9, keep=True)
        s.part(sdf.circle(0.03).at(ex + 0.025, ey - 0.045), mat.matte("#ffffff"), z=0.95, min_size=32)   # glint

    # A drip or two at the foot.
    for _ in range(rng.int(0, 2)):
        dx = rng.choice([-1, 1]) * w * rng.uniform(0.85, 1.05)
        s.part(sdf.ellipse(rng.uniform(0.07, 0.11), 0.05).at(dx, ground - 0.03), mat.glossy(colour, trans=0.55),
               relief=0.8, limb=True)
