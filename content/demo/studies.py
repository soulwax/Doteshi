"""Engine studies: plain forms for checking profiles, materials, relief patterns and lighting."""
from doteshi import mat, pat, profile, sdf, sprite

CLAY = "#b9a48c"


@sprite("study.profiles", aspect=5.0)
def profiles(s, rng):
    kinds = [profile.flat(), profile.dome, profile.bevel(0.35), profile.ridge, profile.pillow(3.0)]
    for i, kind in enumerate(kinds):
        s.part(sdf.circle(0.8).at(-4.0 + i * 2.0, 0.0), mat.satin(CLAY), profile=kind, relief=0.6)


@sprite("study.materials", aspect=6.0)
def materials(s, rng):
    kinds = [mat.matte("#c0563f"), mat.satin("#4f8f52"), mat.glossy("#3f6fc0"), mat.metal("#d9a441"),
             mat.translucent("#8fd06a"), mat.glowing("#ffb347")]
    for i, m in enumerate(kinds):
        s.part(sdf.circle(0.8).at(-5.0 + i * 2.0, 0.0), m)


@sprite("study.relief", aspect=5.0)
def relief(s, rng):
    kinds = [(pat.grain(0.07), 0.03), (pat.ridges(0.16), 0.05), (pat.pores(0.14), -0.04), (pat.scales(0.22), 0.06),
             (pat.cracks(0.3), -0.04), (pat.dimples(0.2), 0.04), (pat.lumps(0.3), 0.07), (pat.rings(0.2), 0.04),
             (pat.scratches(0.03), -0.012), (pat.facets(0.25), 0.05)]
    for i, (p, depth) in enumerate(kinds):
        ball = sdf.ellipse(0.46, 0.46, sphere=True).at(-4.0 + (i % 5) * 2.0, -0.5 + (i // 5) * 1.0)
        s.part(ball, mat.satin(CLAY)).bump(p, depth)


@sprite("study.shadow")
def shadow(s, rng):
    s.part(sdf.box(0.85, 0.7, 0.08), mat.matte("#8a9a7a"), profile=profile.flat(0.05), height=0.05)
    s.part(sdf.circle(0.3).at(-0.2, -0.1), mat.glossy("#c0563f"), z=0.05)
    s.part(sdf.capsule((0.1, 0.3), (0.6, 0.45), 0.09, 0.05), mat.metal("#c9cdd6"), z=0.05)
