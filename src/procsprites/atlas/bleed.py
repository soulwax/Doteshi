"""Edge handling, so texture filtering never pulls in a neighbour or a dark halo."""
import numpy as np


def trim(px):
    """Crop an RGBA array to its visible pixels. Returns (cropped, x, y); a blank image keeps one pixel."""
    ys, xs = np.nonzero(px[..., 3])
    if len(xs) == 0:
        return px[:1, :1], 0, 0
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    return px[y0:y1, x0:x1], int(x0), int(y0)


def extrude(px, n):
    """Repeat the outermost pixels `n` times on every side. For tiles that meet edge to edge."""
    return np.pad(px, ((n, n), (n, n), (0, 0)), mode="edge") if n > 0 else px


def bleed(px, rounds):
    """Spread colour into fully transparent pixels, leaving them transparent. A filtered sample at a sprite's
    edge then blends toward the sprite's own colour instead of toward black."""
    rgb = px[..., :3].astype(np.float64)
    known = px[..., 3] > 0
    rgb[~known] = 0.0
    for _ in range(rounds):
        total = np.zeros_like(rgb)
        count = np.zeros(known.shape)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            src = (slice(max(0, -dy), known.shape[0] - max(0, dy)), slice(max(0, -dx), known.shape[1] - max(0, dx)))
            dst = (slice(max(0, dy), known.shape[0] - max(0, -dy)), slice(max(0, dx), known.shape[1] - max(0, -dx)))
            total[dst] += rgb[src] * known[src][..., None]
            count[dst] += known[src]
        grow = ~known & (count > 0)
        if not grow.any():
            break
        rgb[grow] = total[grow] / count[grow][..., None]
        known = known | grow
    out = px.copy()
    out[..., :3] = np.round(rgb).astype(np.uint8)
    return out
