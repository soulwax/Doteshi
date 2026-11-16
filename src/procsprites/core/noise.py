"""Seeded lattice noise on numpy arrays. Every function takes an integer seed and an optional period for tiling."""
import numpy as np

_TAU = 2.0 * np.pi


def hash2(ix, iy, seed=0):
    """Integer lattice hash -> uint32 array."""
    with np.errstate(over="ignore"):
        h = ix.astype(np.uint32) * np.uint32(0x27D4EB2D)
        h ^= iy.astype(np.uint32) * np.uint32(0x165667B1)
        h ^= np.uint32((int(seed) * 0x9E3779B9 + 0x7F4A7C15) & 0xFFFFFFFF)
        h ^= h >> np.uint32(15)
        h *= np.uint32(0x2C1B3C6D)
        h ^= h >> np.uint32(12)
        h *= np.uint32(0x297A2D39)
        h ^= h >> np.uint32(15)
    return h


def _unit(h):
    return h.astype(np.float64) * (1.0 / 4294967296.0)


def _wrap(i, period):
    return i if not period else np.mod(i, int(period))


def gnoise(x, y, seed=0, period=None):
    """Gradient noise in about [-1, 1]. `period` (cells) makes it tile on both axes."""
    x, y = np.asarray(x, np.float64), np.asarray(y, np.float64)
    x0, y0 = np.floor(x), np.floor(y)
    fx, fy = x - x0, y - y0
    ix, iy = x0.astype(np.int64), y0.astype(np.int64)

    def corner(dx, dy):
        a = _unit(hash2(_wrap(ix + dx, period), _wrap(iy + dy, period), seed)) * _TAU
        return np.cos(a) * (fx - dx) + np.sin(a) * (fy - dy)

    u = fx * fx * fx * (fx * (fx * 6.0 - 15.0) + 10.0)
    v = fy * fy * fy * (fy * (fy * 6.0 - 15.0) + 10.0)
    c00, c10, c01, c11 = corner(0, 0), corner(1, 0), corner(0, 1), corner(1, 1)
    top = c00 + (c10 - c00) * u
    bot = c01 + (c11 - c01) * u
    return (top + (bot - top) * v) * 1.4142


def fbm(x, y, seed=0, octaves=4, lacunarity=2.0, gain=0.5, period=None):
    """Fractal sum of gradient noise, about [-1, 1]. A period needs an integer lacunarity to keep tiling."""
    x, y = np.asarray(x, np.float64), np.asarray(y, np.float64)
    total, amp, norm, f = 0.0, 1.0, 0.0, 1.0
    for o in range(octaves):
        p = None if not period else int(round(period * f))
        total = total + amp * gnoise(x * f, y * f, seed + o * 1013, p)
        norm += amp
        amp *= gain
        f *= lacunarity
    return total / norm


def ridged(x, y, seed=0, octaves=4, lacunarity=2.0, gain=0.5, period=None):
    """Ridged fractal noise in [0, 1]: sharp crests where the base noise crosses zero."""
    x, y = np.asarray(x, np.float64), np.asarray(y, np.float64)
    total, amp, norm, f = 0.0, 1.0, 0.0, 1.0
    for o in range(octaves):
        p = None if not period else int(round(period * f))
        n = 1.0 - np.abs(gnoise(x * f, y * f, seed + o * 1013, p))
        total = total + amp * n * n
        norm += amp
        amp *= gain
        f *= lacunarity
    return total / norm


def worley(x, y, seed=0, period=None, jitter=1.0):
    """Cell noise. Returns (f1, f2, cell): distances to the nearest and second-nearest feature points in cell
    units, and a 0..1 value that is constant over each cell."""
    x, y = np.asarray(x, np.float64), np.asarray(y, np.float64)
    x0, y0 = np.floor(x), np.floor(y)
    fx, fy = x - x0, y - y0
    ix, iy = x0.astype(np.int64), y0.astype(np.int64)
    f1 = np.full(x.shape, 9.0)
    f2 = np.full(x.shape, 9.0)
    cell = np.zeros(x.shape)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            cx, cy = _wrap(ix + dx, period), _wrap(iy + dy, period)
            h = hash2(cx, cy, seed)
            px = dx + 0.5 + jitter * (_unit(h) - 0.5)
            py = dy + 0.5 + jitter * (_unit(hash2(cx, cy, seed + 7919)) - 0.5)
            d = np.hypot(px - fx, py - fy)
            near = d < f1
            f2 = np.where(near, f1, np.minimum(f2, d))
            cell = np.where(near, _unit(hash2(cx, cy, seed + 104729)), cell)
            f1 = np.where(near, d, f1)
    return f1, f2, cell
