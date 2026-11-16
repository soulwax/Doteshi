"""A beetle seen from above: ridged wing cases, a shield behind the head, jointed legs, feelers and jaws.
Like every living thing it faces south, a little to the south-south-east; the game mirrors it."""
import numpy as np

from doteshi import mat, pat, profile, sdf, sprite

#            shell      marking    limbs      sheen
KINDS = [("#b5651d", "#3a1f10", "#2a1a14", 0.15),    # amber
         ("#1f6f4a", "#d9c04a", "#14221c", 0.75),    # jewel green
         ("#a8261f", "#17120f", "#17120f", 0.05),    # ladybird red
         ("#27407f", "#8fd0ff", "#12172a", 0.85),    # sapphire
         ("#2a2622", "#c9712b", "#191614", 0.25),    # carrion black
         ("#7a4b8f", "#f0c95a", "#201628", 0.7),     # violet
         ("#c9962b", "#3b2a12", "#2b1f10", 0.35)]    # gold


@sprite("beetle", sizes=[16], variants=16, living=True)
def beetle(s, rng):
    shell_c, mark_c, limb_c, sheen = rng.choice(KINDS)
    seed = rng.seed32()
    # Built head-up, then turned to face south with the head a little to the south-south-east.
    s.turn(180.0 - rng.uniform(10.0, 18.0))
    W = rng.uniform(0.36, 0.5)                  # half-width of the wing cases
    y_head, y_neck, y_waist, y_tail = -0.6, -0.42, rng.uniform(-0.2, -0.1), rng.uniform(0.72, 0.82)
    limb = mat.glossy(limb_c, rough=0.34, spec=0.5)
    shell = mat.glossy(shell_c, rough=0.24, spec=0.7, irid=sheen, trans=0.12)

    # Legs: thigh, then shin and foot, three pairs fanned front to back.
    for hip_y, knee, foot, toe in [(y_waist - 0.14, (0.20, -0.20), (0.36, -0.36), (0.40, -0.48)),
                                   (y_waist + 0.10, (0.26, -0.02), (0.44, 0.10), (0.52, 0.16)),
                                   (y_waist + 0.36, (0.22, 0.16), (0.36, 0.40), (0.40, 0.52))]:
        j = lambda v, a=0.03: v + rng.uniform(-a, a)
        hip = (W * 0.55, hip_y)
        k = (W + j(knee[0]), hip_y + j(knee[1]))
        f = (W + j(foot[0]), hip_y + j(foot[1]))
        t = (W + j(toe[0]), hip_y + j(toe[1]))
        s.pair(sdf.stroke([hip, k], [0.05, 0.062, 0.04], spline=False), limb, z=0.0, limb=True)
        shin = s.pair(sdf.stroke([k, f, t], [0.034, 0.02, 0.007], spline=False), limb, z=0.004, limb=True)
        shin.bump(pat.rings(0.03) * pat.gradient("u", 0.5, 0.7), 0.004)

    # Feelers and jaws.
    reach = rng.uniform(0.28, 0.42)
    feel = s.pair(sdf.stroke([(0.07, y_head - 0.04), (0.2, y_head - reach * 0.75), (0.36, y_head - reach)],
                             [0.016, 0.012, rng.choice([0.01, 0.022])]), limb, z=0.01, limb=True)
    feel.bump(pat.rings(0.04), 0.006)
    jaw = rng.uniform(0.1, 0.2)
    s.pair(sdf.stroke([(0.07, y_head - 0.06), (0.12, y_head - 0.06 - jaw * 0.6), (0.035, y_head - 0.06 - jaw)],
                      [0.03, 0.022, 0.004]), limb, z=0.03, limb=True)

    # Head and eyes.
    head = s.part(sdf.lathe((0.0, y_head - 0.12), (0.0, y_neck + 0.06), [0.07, 0.15, 0.18, 0.17]),
                  mat.glossy(limb_c, rough=0.3, spec=0.55, irid=sheen * 0.5), relief=0.75, z=0.05)
    head.bump(pat.pores(0.03, seed + 1), -0.004)
    head.tint(shell_c, None, 0.4)                # lighter than the eyes, so the face reads at 16 pixels
    s.pair(sdf.circle(0.046).at(0.148, y_head + 0.035), mat.glossy("#1c0f0c", rough=0.1, spec=1.0), z=0.065,
           keep=True, asym=0)

    # Shield behind the head.
    sw = W * rng.uniform(0.78, 0.92)
    shield = s.part(sdf.lathe((0.0, y_neck - 0.02), (0.0, y_waist + 0.04),
                              [(0.0, sw * 0.55), (0.3, sw * 0.9), (0.75, sw), (1.0, sw * 0.93)]).warp(
        0.006, 5.0, seed), shell, relief=0.62, z=0.07)
    shield.bump(pat.lumps(0.18, seed + 2), 0.008).bump(pat.pores(0.028, seed + 3, 0.8), -0.004)
    shield.tint(mark_c, pat.edge(0.05), 0.55)

    # Wing cases: one rounded back with a seam down the middle and ridges running its length.
    back = sdf.lathe((0.0, y_waist), (0.0, y_tail), [(0.0, W * 0.8), (0.12, W * 0.97), (0.35, W), (0.65, W * 0.9),
                                                     (0.88, W * 0.55), (1.0, W * 0.1)]).warp(0.006, 5.0, seed + 4)
    cases = s.part(back, shell, relief=0.72, z=0.06)
    seam = pat.custom(lambda c: np.exp(-(c.x / 0.012) ** 2), size=0.012)
    cases.bump(seam, -0.03, fade=0)
    cases.bump(pat.ridges(W * rng.uniform(0.12, 0.2), axis="u", sharp=1.5), 0.009)
    cases.bump(pat.pores(0.03, seed + 5, 0.9), -0.005)
    cases.tint("#0c0a0a", seam, 0.7)
    style = rng.int(0, 3)
    if style == 0:
        cases.tint(mark_c, pat.spots(W * rng.uniform(0.45, 0.7), rng.uniform(0.6, 0.95), seed + 6, vary=0.4).keep(), 0.92, irid=0.0)
    elif style == 1:
        cases.tint(mark_c, pat.stripes(W * rng.uniform(0.3, 0.5), 0.45, axis="u", wobble=0.25, seed=seed + 6).keep(), 0.9, irid=0.0)
    elif style == 2:
        cases.tint(mark_c, pat.stripes(rng.uniform(0.2, 0.34), 0.4, axis="v", wobble=0.5, seed=seed + 6).keep(), 0.9, irid=0.0)
    cases.tint(mark_c, pat.edge(0.045), 0.5)
    # The small plate where the wing cases meet the shield.
    s.part(sdf.polygon([(-0.05, y_waist + 0.01), (0.05, y_waist + 0.01), (0.0, y_waist + 0.11)]), shell,
           profile=profile.pillow(2.0), height=0.012, z=0.006, on=cases).tint(mark_c, None, 0.6)
