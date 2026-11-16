"""A cut gem. Generated at every size except 16px, where a hand-drawn cell takes over: at that size a few
deliberately placed pixels read better than any rendering of facets."""
from doteshi import mat, override, pat, profile, sdf, sprite
from doteshi.core.color import ramp, rgb8
from doteshi.resolve.style import OUTLINE

KINDS = ["#d8344f", "#2fa866", "#3b76d6", "#8d58c9", "#e0a12f", "#35b5b0"]


@sprite("gem", sizes=[64, 16], variants=6)
def gem(s, rng):
    color = rng.choice(KINDS)
    seed = rng.seed32()
    w, girdle = rng.uniform(0.62, 0.8), rng.uniform(-0.3, -0.15)       # half-width, height of the widest line
    table = w * rng.uniform(0.5, 0.65)
    outline = sdf.polygon([(-table, -0.72), (table, -0.72), (w, girdle), (0.0, 0.8), (-w, girdle)])
    body = s.part(outline.grow(0.02), mat.glossy(color, rough=0.16, spec=0.9, trans=0.6),
                  profile=profile.bevel(0.5), relief=0.9)
    body.bump(pat.facets(rng.uniform(0.3, 0.42), seed), 0.1, fade=0.05)
    body.tint("#ffffff", pat.facets(0.36, seed + 1).step(0.75, 0.9), 0.35)
    body.tint("#1a1026", pat.facets(0.36, seed + 2).step(0.7, 0.95) * pat.gradient("y", -0.2, 0.7), 0.4)
    # The flat top face.
    s.part(sdf.polygon([(-table, -0.72), (table, -0.72), (w * 0.72, girdle - 0.06), (-w * 0.72, girdle - 0.06)]),
           mat.glossy(color, rough=0.1, spec=1.0, trans=0.7), profile=profile.flat(0.1), height=0.03, on=body
           ).tint("#ffffff", pat.gradient("x", w * 0.5, -w * 0.6), 0.3)


CELL = ["................",
        "................",
        "....hhhlllll....",
        "...hwhlllllmm...",
        "..hwhllllmmmmm..",
        "..hhllllmmmmmd..",
        "..lllllmmmmmdd..",
        "...lllmmmmmdd...",
        "...llmmmmmddd...",
        "....lmmmmddd....",
        "....mmmmddd.....",
        ".....mmmdd......",
        "......mdd.......",
        ".......d........",
        "................",
        "................"]


@override("gem", 16)
def gem_16(rng):
    dark, mid, light, high = ramp(rgb8(rng.choice(KINDS)), 5)[:4]
    return CELL, {"d": dark, "m": mid, "l": light, "h": high, "w": (255, 255, 255)}, OUTLINE
