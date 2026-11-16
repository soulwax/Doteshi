"""The sprite from the README: a berry on a stalk with one leaf.

    uv run doteshi --content examples ladder berry
"""
from doteshi import mat, pat, sdf, sprite


@sprite("berry", sizes=[16], variants=8)
def berry(s, rng):
    colour = rng.choice(["#c0304a", "#3b4fb8", "#7a3fa0"])
    r = rng.uniform(0.5, 0.62)

    # A short stalk. It is a limb: at 16 pixels the fruit fills the cell and the stalk may run off it.
    s.part(sdf.stroke([(0.05, -0.35), (0.12, -0.62), (0.3, -0.8)], [0.05, 0.04, 0.03]),
           mat.matte("#5b7a35"), limb=True)

    # The fruit: a glossy ball with fine pores and a paler bloom toward the top.
    fruit = s.part(sdf.ellipse(r, r * 0.95, sphere=True).at(0.0, 0.2), mat.glossy(colour), z=0.02)
    fruit.bump(pat.pores(0.09, rng.seed32()), -0.015)
    fruit.tint("#f2d9e0", pat.gradient("y", 0.1, -0.4), 0.25)

    # A leaf with a raised midrib.
    leaf = s.part(sdf.leaf((0.1, -0.5), (-0.55, -0.72), 0.14), mat.satin("#4f8a3c", trans=0.4), z=0.05)
    leaf.bump(pat.custom(lambda c: 1.0 - abs(c.v) ** 0.5, size=0.04), 0.015)
