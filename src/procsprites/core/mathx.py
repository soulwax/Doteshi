"""Small array helpers shared by every module."""
import numpy as np


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(e0, e1, x):
    """0 at e0, 1 at e1; e0 > e1 gives the falling version."""
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def smax(a, b, k):
    """Smooth maximum with blend width k (plain maximum when k is 0)."""
    m = np.maximum(a, b)
    if k <= 0:
        return m
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return m + h * h * k * 0.25


def smin(a, b, k):
    return -smax(-a, -b, k)


def shift(a, ox, oy, fill=0.0):
    """out[y, x] = a[y + oy, x + ox], with `fill` where that falls outside."""
    out = np.full_like(a, fill)
    h, w = a.shape[:2]
    x0, x1 = max(0, -ox), min(w, w - ox)
    y0, y1 = max(0, -oy), min(h, h - oy)
    if x0 < x1 and y0 < y1:
        out[y0:y1, x0:x1] = a[y0 + oy:y1 + oy, x0 + ox:x1 + ox]
    return out


def spread(mask, r, grow):
    """Grow or shrink a boolean mask by r samples (square neighbourhood)."""
    for axis in (0, 1):
        acc = mask.copy()
        for k in range(1, r + 1):
            for s in (-k, k):
                moved = shift(mask, s if axis else 0, 0 if axis else s, False)
                acc = (acc | moved) if grow else (acc & moved)
        mask = acc
    return mask


def box_blur(a, r):
    """Box blur of half-width r samples along both axes, edges clamped."""
    r = int(r)
    if r < 1:
        return a
    for axis in (0, 1):
        pad = [(0, 0)] * a.ndim
        pad[axis] = (r + 1, r)
        c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axis)
        n = a.shape[axis]
        hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
        lo = np.take(c, np.arange(0, n), axis=axis)
        a = (hi - lo) / (2 * r + 1)
    return a


def blur(a, r, passes=3):
    """Near-Gaussian blur: repeated box blurs."""
    for _ in range(passes):
        a = box_blur(a, max(1, int(round(r))))
    return a
