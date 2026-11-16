"""Surface patterns. A Pattern is a field over a part's surface; a part uses one either as relief
(`part.bump(pattern, depth)`, so light reacts to it) or as a mask for colour (`part.tint(colour, pattern)`).

Patterns are laid out in the part's metric surface coordinates, so they follow tubes and domes and foreshorten
toward the edges. Each carries a `size`: the smallest feature it draws, in sprite units. Parts drop patterns
whose features would be smaller than about a pixel and a half at the size being rendered, unless the pattern is
marked with .keep(), in which case it is coarsened to stay readable.
"""
import numpy as np

from ..core import noise
from ..core.mathx import smoothstep

_TAU = 2.0 * np.pi


class Pattern:
    def __init__(self, fn, size=None, kept=False):
        self.fn, self.size, self.kept = fn, size, kept

    def __call__(self, c):
        return self.fn(c)

    def keep(self):
        """Mark as essential: at sizes where it would be too fine to draw, it is coarsened (fewer, larger
        features) instead of dropped. For markings a sprite is recognised by, such as a toadstool's spots."""
        return Pattern(self.fn, self.size, True)

    def _join(self, other, op):
        if isinstance(other, Pattern):
            sizes = [s for s in (self.size, other.size) if s is not None]
            return Pattern(lambda c: op(self.fn(c), other.fn(c)), min(sizes) if sizes else None,
                           self.kept or other.kept)
        return Pattern(lambda c: op(self.fn(c), other), self.size, self.kept)

    def _map(self, fn):
        return Pattern(lambda c: fn(self.fn(c)), self.size, self.kept)

    def __mul__(self, other):
        return self._join(other, lambda a, b: a * b)

    __rmul__ = __mul__

    def __add__(self, other):
        return self._join(other, lambda a, b: a + b)

    def __rsub__(self, other):
        return self._map(lambda v: other - v)

    def __neg__(self):
        return self._map(lambda v: -v)

    def clip(self, lo=0.0, hi=1.0):
        return self._map(lambda v: np.clip(v, lo, hi))

    def step(self, lo, hi):
        """Remap through a smooth threshold: 0 below lo, 1 above hi."""
        return self._map(lambda v: smoothstep(lo, hi, v))


def custom(fn, size=None):
    return Pattern(fn, size)


def _axes(c, axis):
    """(along, across) metric coordinates for a pattern running along 'u' or 'v'."""
    return (c.mu, c.mv) if axis == "u" else (c.mv, c.mu)


# --- smooth variation ---

def mottle(size, seed=0, octaves=4, contrast=1.0):
    """Cloudy blotches, 0..1."""
    return Pattern(lambda c: np.clip(0.5 + 0.5 * contrast * noise.fbm(c.mu / size, c.mv / size, seed, octaves), 0, 1),
                   size / 2 ** (octaves - 1))


def lumps(size, seed=0, octaves=3):
    """Rolling unevenness, -1..1. For relief."""
    return Pattern(lambda c: noise.fbm(c.mu / size, c.mv / size, seed, octaves), size)


def gradient(attr, a=0.0, b=1.0):
    """A ramp over one of the part's own measures: 'u', 'v', 't', 'x', 'y', 'mu', 'mv'. 0 at a, 1 at b."""
    return Pattern(lambda c: np.clip((getattr(c, attr) - a) / (b - a), 0.0, 1.0))


def edge(width):
    """1 at the silhouette of the part, fading to 0 `width` inside it."""
    return Pattern(lambda c: 1.0 - smoothstep(0.0, width, -c.d))


def core(start=0.3, end=1.0):
    """0 near the edge of the part, 1 toward its core (by depth)."""
    return Pattern(lambda c: smoothstep(start, end, c.t))


# --- directional ---

def grain(size, seed=0, stretch=9.0, axis="u"):
    """Fibres running along the part, -1..1: stem fibre, wood, muscle, hair combed flat."""

    def fn(c):
        along, across = _axes(c, axis)
        fine = noise.gnoise(along / (size * stretch), across / size, seed)
        return 0.65 * fine + 0.35 * noise.gnoise(along / (size * stretch * 0.45), across / (size * 0.45), seed + 53)

    return Pattern(fn, size * 0.5)


def ridges(size, axis="u", sharp=1.0, wobble=0.0, seed=0):
    """Evenly spaced ridges running along the part, 0..1, one every `size`."""

    def fn(c):
        along, across = _axes(c, axis)
        if wobble:
            across = across + wobble * size * noise.gnoise(along / (size * 6.0), across / (size * 3.0), seed)
        w = 0.5 + 0.5 * np.cos(across / size * _TAU)
        return w ** sharp

    return Pattern(fn, size * 0.5)


def rings(size, axis="u", sharp=1.0):
    """Ridges running round the part instead of along it: segments, growth rings, banded joints."""
    return ridges(size, "v" if axis == "u" else "u", sharp)


def stripes(size, duty=0.5, soft=0.15, axis="u", wobble=0.3, seed=0):
    """Bands of colour running along the part, 0..1."""

    def fn(c):
        along, across = _axes(c, axis)
        across = across + wobble * size * noise.fbm(along / (size * 3.0), across / (size * 3.0), seed, 2)
        w = 0.5 + 0.5 * np.cos(across / size * _TAU)
        edge_at = np.cos(np.pi * duty) * 0.5 + 0.5
        return smoothstep(edge_at - soft, edge_at + soft, w)

    return Pattern(fn, size * min(duty, 1 - duty))


# --- cellular ---

def spots(size, density=0.7, seed=0, vary=0.6, soft=0.2):
    """Scattered round spots, 0..1. `size` is the spacing; each spot fills a varying share of its cell."""

    def fn(c):
        f1, _, cell = noise.worley(c.mu / size, c.mv / size, seed, jitter=0.55)
        pick = (cell * 7.31) % 1.0
        rad = 0.36 * (1.0 - vary * ((cell * 3.17) % 1.0))
        return smoothstep(rad, rad * (1.0 - soft), f1) * (pick < density)

    return Pattern(fn, size * 0.3)


def speckle(size, density=0.5, seed=0):
    """Fine flecks, 0..1."""

    def fn(c):
        f1, _, cell = noise.worley(c.mu / size, c.mv / size, seed)
        return smoothstep(0.3, 0.12, f1) * ((cell * 5.77) % 1.0 < density)

    return Pattern(fn, size * 0.3)


def pores(size, seed=0, density=1.0):
    """Small pits, 0..1 (1 at the bottom of each pit). Use with a negative depth."""

    def fn(c):
        f1, _, cell = noise.worley(c.mu / size, c.mv / size, seed, jitter=0.8)
        return smoothstep(0.34, 0.08, f1) * ((cell * 9.13) % 1.0 < density)

    return Pattern(fn, size * 0.35)


def cracks(size, seed=0, width=0.07):
    """A network of lines between cells, 0..1: cracked mud, plated hide, leaf cells, cobbles."""

    def fn(c):
        f1, f2, _ = noise.worley(c.mu / size, c.mv / size, seed)
        return smoothstep(width, 0.0, f2 - f1)

    return Pattern(fn, size * width * 2.0)


def facets(size, seed=0):
    """A flat random value per cell, 0..1: hammered metal, crystal faces, mosaic."""
    return Pattern(lambda c: noise.worley(c.mu / size, c.mv / size, seed)[2], size * 0.5)


def dimples(size, seed=0):
    """A smooth bowl in every cell, 0..1 at the rim: hammer marks, orange peel."""
    return Pattern(lambda c: np.clip(noise.worley(c.mu / size, c.mv / size, seed)[0] * 1.4, 0, 1) ** 2, size * 0.5)


def scales(size, aspect=1.0):
    """Overlapping rounded scales in offset rows, 0..1, each rising toward its free edge along +u."""

    def fn(c):
        col, row = c.mv / size, c.mu / (size * aspect)
        best = np.zeros(np.shape(col))
        for dr in (0, 1):
            r0 = np.floor(row) - dr
            cx = col + 0.5 * (r0 % 2)
            fx = cx - np.floor(cx) - 0.5
            fy = row - r0
            inside = (fx * 2.0) ** 2 + (fy / 1.6) ** 2
            h = np.where(inside < 1.0, 0.35 + 0.65 * fy / 1.6, 0.0) * np.sqrt(np.clip(1.0 - inside, 0.0, 1.0)) ** 0.5
            best = np.maximum(best, h)
        return best

    return Pattern(fn, size * 0.5)


def scratches(size, seed=0, density=0.5):
    """Sparse fine straight scores at mixed angles, 0..1."""

    def fn(c):
        total = np.zeros(np.shape(c.mu))
        for i in range(3):
            a = 0.6 + 1.1 * i + (seed % 7) * 0.3
            p = c.mu * np.cos(a) + c.mv * np.sin(a)
            q = -c.mu * np.sin(a) + c.mv * np.cos(a)
            line = np.abs(noise.gnoise(p / (size * 14.0), q / size, seed + i * 17))
            gate = noise.gnoise(p / (size * 9.0), q / (size * 6.0), seed + 91 + i) > (0.55 - density)
            total = np.maximum(total, smoothstep(0.10, 0.0, line) * gate)
        return total

    return Pattern(fn, size * 0.3)
