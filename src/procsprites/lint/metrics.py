"""Measurements of a finished sprite, for comparing generated pixels against reference art."""
import numpy as np

from ..core.color import delta
from ..resolve.style import OUTLINE

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIAG = ((1, 1), (-1, 1), (1, -1), (-1, -1))


def orphans(px, outline=OUTLINE):
    """Lone pixels that differ only slightly from the four identical pixels round them. The definition is that
    of Mellangan's sprite_kit.orphans, so numbers are comparable with its measurements of Kenney's art."""
    h, w = px.shape[:2]
    at = lambda x, y: tuple(int(v) for v in px[y, x])
    n = 0
    for y in range(h):
        for x in range(w):
            p = at(x, y)
            if p[3] == 0 or p[:3] == outline:
                continue
            nb = [at(x + dx, y + dy) for dx, dy in N4 if 0 <= x + dx < w and 0 <= y + dy < h]
            diag = [at(x + dx, y + dy) for dx, dy in DIAG if 0 <= x + dx < w and 0 <= y + dy < h]
            if len(nb) == 4 and all(q == nb[0] for q in nb) and nb[0][3] and nb[0][:3] != outline \
                    and delta(nb[0], p) < 0.12 and diag.count(p) < 2:
                n += 1
    return n


def measure(image, outline=OUTLINE):
    """Counts for one sprite: visible pixels, colours, orphan pixels, how much of the canvas is filled, whether
    alpha is hard, and how much of the silhouette is closed off by the outline colour."""
    px = np.asarray(image.convert("RGBA"))
    solid = px[..., 3] > 0
    colours = {tuple(c) for c in px[solid][:, :3].tolist()}
    ink = solid & (px[..., :3] == np.array(outline, np.uint8)).all(axis=-1)
    p = np.pad(solid, 1)
    open_side = ~(p[1:-1, :-2] & p[1:-1, 2:] & p[:-2, 1:-1] & p[2:, 1:-1])     # touches empty space or the border
    rim = solid & open_side
    return {"pixels": int(solid.sum()), "colours": len(colours), "orphans": orphans(px, outline),
            "fill": float(solid.mean()), "hard_alpha": bool(np.isin(px[..., 3], (0, 255)).all()),
            "outlined": float((rim & ink).sum() / max(1, rim.sum()))}


def summary(images, outline=OUTLINE):
    """Averages over a set of sprites."""
    rows = [measure(im, outline) for im in images]
    return {k: float(np.mean([r[k] for r in rows])) for k in ("pixels", "colours", "orphans", "fill", "outlined")}
