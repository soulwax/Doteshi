"""A broadleaf tree, a big structure of 32x32 pixels (a 2x2 block of cells): a skeleton grown toward a cloud of points, thickened by the pipe model, with a clump of
foliage at every twig end."""
import numpy as np

from doteshi import mat, pat, sdf, sprite
from doteshi.grow import branch

#           bark       leaf       leaf light  leaf shade
KINDS = [("#6b4a35", "#4c8a3a", "#9cc24e", "#27543a"),    # summer oak
         ("#5d4636", "#3f7d52", "#7fbf7a", "#1f4a40"),    # deep green
         ("#6a4b3a", "#d9822b", "#f3c04a", "#8e3b22"),    # autumn
         ("#5a4040", "#e58fb0", "#fbd3df", "#a4486e"),    # blossom
         ("#c9c2b4", "#86b340", "#c9dc62", "#4a7a3a"),    # birch
         ("#4f3b33", "#b53a2c", "#ee7b3a", "#6b1f24")]    # maple red


@sprite("tree", sizes=[32], variants=16)
def tree(s, rng):
    bark_c, leaf_c, light_c, shade_c = rng.choice(KINDS)
    seed = rng.seed32()
    ground = 0.88
    root = (rng.uniform(-0.08, 0.08), ground)

    # Where the crown should be: two or three overlapping lobes of target points.
    cx, cy = rng.uniform(-0.06, 0.06), rng.uniform(-0.34, -0.2)
    lobes = [(cx, cy, rng.uniform(0.5, 0.62), rng.uniform(0.38, 0.5))]
    for _ in range(rng.int(1, 2)):
        lobes.append((cx + rng.uniform(-0.3, 0.3), cy + rng.uniform(-0.12, 0.2), rng.uniform(0.3, 0.42),
                      rng.uniform(0.26, 0.36)))
    targets = np.vstack([branch.scatter(rng, *lobe, 70) for lobe in lobes])
    grown = branch.colonize(rng.stream("grow"), root, targets, step=0.075, reach=0.42, kill=0.11,
                            heading=(rng.uniform(-0.12, 0.12), -1.0), wander=0.16)
    radii = grown.radii(tip=0.011, power=2.1, base=rng.uniform(0.085, 0.115))

    # A patch of ground.
    mound = s.part(sdf.ellipse(rng.uniform(0.42, 0.56), 0.075).at(root[0], ground + 0.03).warp(0.02, 3.0, seed),
                   mat.matte("#6e583e"), relief=1.0, z=-0.03)
    mound.bump(pat.lumps(0.08, seed), 0.025).tint("#6c9440", pat.mottle(0.2, seed + 1, contrast=1.8).step(0.3, 0.6), 0.9)

    # Foliage behind the limbs, then the limbs, then the foliage in front.
    leaves = rng.stream("leaves")
    tips = grown.tips()

    def clump(x, y, r, z):
        k = leaves.seed32()
        blob = sdf.ellipse(r, r * leaves.uniform(0.78, 0.95), sphere=True).warp(r * 0.16, 2.2 / r, k).warp(
            r * 0.05, 9.0 / r, k + 1).at(x, y)
        part = s.part(blob, mat.satin(leaf_c, rough=0.7, spec=0.1, trans=0.4), relief=0.85, z=z, join=0.03)
        part.bump(pat.lumps(r * 0.5, k), r * 0.16).bump(pat.scales(r * 0.3), r * 0.06)
        part.tint(shade_c, pat.gradient("y", y - r * 0.1, y + r * 0.9), 0.75)
        part.tint(light_c, pat.gradient("y", y, y - r * 0.9) * pat.mottle(r * 0.6, k + 2), 0.75)

    for i in tips:
        if leaves.chance(0.6):
            x, y = grown.pos[i]
            clump(x + leaves.uniform(-0.05, 0.05), y + leaves.uniform(-0.02, 0.06), leaves.uniform(0.13, 0.2),
                  leaves.uniform(-0.12, 0.0))

    bark = mat.matte(bark_c, rough=0.85, spec=0.06)
    for pts, rs, order in grown.limbs(radii):
        if order == 0:
            rs = rs * np.linspace(1.5, 1.0, len(rs)) ** np.where(np.arange(len(rs)) < 3, 1.0, 0.0)   # flared foot
        limb = s.part(sdf.stroke(pts, rs, samples=max(6, 3 * len(pts))), bark, z=0.03 - 0.004 * order,
                      join=0.02 if order else 0.0)
        limb.bump(pat.grain(0.022, seed + 2, stretch=10), 0.012).bump(pat.cracks(0.09, seed + 3, 0.12), -0.01)
        limb.tint("#2a1c18", pat.cracks(0.09, seed + 3, 0.12), 0.5)
        limb.tint("#6c9440", pat.mottle(0.12, seed + 4, contrast=2.0).step(0.62, 0.8) * pat.gradient("u", 0.5, 0.0), 0.6)

    for i in tips:
        x, y = grown.pos[i]
        clump(x + leaves.uniform(-0.04, 0.04), y + leaves.uniform(-0.05, 0.02), leaves.uniform(0.12, 0.21),
              leaves.uniform(0.05, 0.3))
    for _ in range(leaves.int(4, 8)):                        # fill out the middle of the crown
        lx, ly, rx, ry = leaves.choice(lobes)
        dx, dy = leaves.on_disc(0.6)
        clump(lx + dx * rx, ly + dy * ry, leaves.uniform(0.15, 0.23), leaves.uniform(0.1, 0.34))
