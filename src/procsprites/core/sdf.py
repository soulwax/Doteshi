"""Shapes as distance fields on numpy grids.

A Shape answers, for arrays of points, a Field: the signed distance `d` (negative inside), surface coordinates
`u`, `v`, and where the shape knows them, its own depth `t` (0 at the edge, 1 at the core), local radius `r`, and
metric surface coordinates `mu`, `mv` in sprite units that follow the form (wrapped round tubes and domes, so
patterns foreshorten toward the edges). Every shape carries a bounding box so it is only evaluated near itself.
"""
import math

import numpy as np

from . import curves, noise
from .mathx import smin


class Field:
    __slots__ = ("d", "u", "v", "t", "r", "mu", "mv")

    def __init__(self, d, u, v, t=None, r=None, mu=None, mv=None):
        self.d, self.u, self.v, self.t, self.r = d, u, v, t, r
        self.mu = u if mu is None else mu
        self.mv = v if mv is None else mv

    def with_d(self, d):
        return Field(d, self.u, self.v, self.t, self.r, self.mu, self.mv)


def _pick(m, a, b):
    """Per-pixel choice between two optional per-pixel values."""
    if a is None or b is None:
        return None
    return np.where(m, a, b)


class Shape:
    def __init__(self, fn, bounds):
        self.fn = fn
        self.bounds = tuple(float(b) for b in bounds)

    def eval(self, x, y):
        return self.fn(x, y)

    # --- placement ---

    def at(self, dx, dy=0.0):
        b = self.bounds
        return Shape(lambda x, y: self.fn(x - dx, y - dy), (b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy))

    def rot(self, deg, cx=0.0, cy=0.0):
        """Turn clockwise on screen (y points down) about (cx, cy)."""
        a = math.radians(deg)
        c, s = math.cos(a), math.sin(a)
        b = self.bounds
        cs = [(cx + c * (px - cx) - s * (py - cy), cy + s * (px - cx) + c * (py - cy))
              for px in (b[0], b[2]) for py in (b[1], b[3])]
        bounds = (min(p[0] for p in cs), min(p[1] for p in cs), max(p[0] for p in cs), max(p[1] for p in cs))

        def fn(x, y):
            px, py = x - cx, y - cy
            return self.fn(cx + c * px + s * py, cy - s * px + c * py)

        return Shape(fn, bounds)

    def mirror(self, axis=0.0):
        """Reflect left-right across the vertical line x = axis."""
        b = self.bounds

        def fn(x, y):
            f = self.fn(2 * axis - x, y)
            return Field(f.d, f.u, -f.v, f.t, f.r, f.mu, -f.mv)

        return Shape(fn, (2 * axis - b[2], b[1], 2 * axis - b[0], b[3]))

    def scale(self, s):
        b = self.bounds

        def fn(x, y):
            f = self.fn(x / s, y / s)
            return Field(f.d * s, f.u, f.v, f.t, None if f.r is None else f.r * s, f.mu * s, f.mv * s)

        return Shape(fn, tuple(v * s for v in b))

    # --- deformation ---

    def grow(self, amount):
        b = self.bounds
        return Shape(lambda x, y: (lambda f: f.with_d(f.d - amount))(self.fn(x, y)),
                     (b[0] - amount, b[1] - amount, b[2] + amount, b[3] + amount))

    def warp(self, amp, freq, seed=0, octaves=2):
        """Push the outline around with smooth noise: `amp` in sprite units, `freq` in waves per unit."""
        b = self.bounds

        def fn(x, y):
            ox = noise.fbm(x * freq, y * freq, seed, octaves)
            oy = noise.fbm(x * freq + 31.7, y * freq - 17.3, seed + 101, octaves)
            return self.fn(x + amp * ox, y + amp * oy)

        return Shape(fn, (b[0] - amp, b[1] - amp, b[2] + amp, b[3] + amp))

    # --- combination ---

    def union(self, other, k=0.0):
        a, b = self.bounds, other.bounds

        def fn(x, y):
            f, g = self.fn(x, y), other.fn(x, y)
            m = f.d <= g.d
            return Field(smin(f.d, g.d, k), np.where(m, f.u, g.u), np.where(m, f.v, g.v), _pick(m, f.t, g.t),
                         _pick(m, f.r, g.r), np.where(m, f.mu, g.mu), np.where(m, f.mv, g.mv))

        return Shape(fn, (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])))

    __or__ = union

    def cut(self, other, k=0.0):
        """This shape with `other` removed."""
        return Shape(lambda x, y: (lambda f: f.with_d(-smin(-f.d, other.fn(x, y).d, k)))(self.fn(x, y)), self.bounds)

    __sub__ = cut

    def clip(self, other, k=0.0):
        """The part of this shape inside `other`."""
        a, b = self.bounds, other.bounds
        return Shape(lambda x, y: (lambda f: f.with_d(-smin(-f.d, -other.fn(x, y).d, k)))(self.fn(x, y)),
                     (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))

    __and__ = clip

    def above(self, y0, k=0.0):
        """Keep what is above the horizontal line y = y0 (smaller y)."""
        b = self.bounds
        return Shape(lambda x, y: (lambda f: f.with_d(-smin(-f.d, y0 - y, k)))(self.fn(x, y)),
                     (b[0], b[1], b[2], min(b[3], y0)))

    def below(self, y0, k=0.0):
        b = self.bounds
        return Shape(lambda x, y: (lambda f: f.with_d(-smin(-f.d, y - y0, k)))(self.fn(x, y)),
                     (b[0], max(b[1], y0), b[2], b[3]))


# --- primitives, centred on the origin unless they take end points ---

def circle(r):
    return Shape(lambda x, y: Field(np.hypot(x, y) - r, x, y), (-r, -r, r, r))


def ellipse(rx, ry, sphere=False):
    """An ellipse whose depth is that of the ellipsoid it outlines, so a dome profile gives a true rounded
    body. With `sphere`, the metric coordinates wrap over that body like longitude and latitude."""
    small = min(rx, ry)

    def fn(x, y):
        k0 = np.hypot(x / rx, y / ry)
        k1 = np.hypot(x / (rx * rx), y / (ry * ry))
        d = np.where(k1 > 1e-12, k0 * (k0 - 1.0) / np.maximum(k1, 1e-12), -small)
        t = np.clip(1.0 - k0, 0.0, 1.0)
        if not sphere:
            return Field(d, x, y, t, small)
        yy = np.clip(y / ry, -1.0, 1.0)
        lat = np.arcsin(yy)
        lon = np.arcsin(np.clip(x / rx / np.maximum(np.sqrt(1.0 - yy * yy), 1e-6), -1.0, 1.0))
        return Field(d, x, y, t, small, lon * rx, lat * ry)

    return Shape(fn, (-rx, -ry, rx, ry))


def box(hw, hh, r=0.0):
    def fn(x, y):
        qx, qy = np.abs(x) - (hw - r), np.abs(y) - (hh - r)
        d = np.hypot(np.maximum(qx, 0.0), np.maximum(qy, 0.0)) + np.minimum(np.maximum(qx, qy), 0.0) - r
        return Field(d, x, y)

    return Shape(fn, (-hw, -hh, hw, hh))


def polygon(points):
    pts = np.asarray(points, np.float64)

    def fn(x, y):
        d2 = np.full(np.shape(x), np.inf)
        inside = np.zeros(np.shape(x), bool)
        n = len(pts)
        for i in range(n):
            ax, ay = pts[i]
            bx, by = pts[(i + 1) % n]
            ex, ey = bx - ax, by - ay
            wx, wy = x - ax, y - ay
            h = np.clip((wx * ex + wy * ey) / (ex * ex + ey * ey), 0.0, 1.0)
            d2 = np.minimum(d2, (wx - ex * h) ** 2 + (wy - ey * h) ** 2)
            if ay != by:
                inside ^= ((ay > y) != (by > y)) & (x < ax + ex * (y - ay) / ey)
        return Field(np.where(inside, -1.0, 1.0) * np.sqrt(d2), x, y)

    return Shape(fn, (pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max()))


def _segment(x, y, ax, ay, bx, by, ra, rb):
    ex, ey = bx - ax, by - ay
    wx, wy = x - ax, y - ay
    h = np.clip((wx * ex + wy * ey) / max(ex * ex + ey * ey, 1e-18), 0.0, 1.0)
    rr = ra + (rb - ra) * h
    dist = np.hypot(wx - ex * h, wy - ey * h)
    side = np.where(ex * wy - ey * wx < 0, -1.0, 1.0)
    return dist - rr, h, rr, dist * side


def capsule(a, b, ra, rb=None):
    """A round-ended limb from `a` to `b`, tapering from radius ra to rb."""
    return stroke([a, b], [ra, ra if rb is None else rb], samples=2, spline=False)


def stroke(points, radii, samples=None, spline=True):
    """A tube along a curve through `points`, with a radius that varies along it. u runs 0..1 along the curve,
    v runs -1..1 across it, and depth is that of a round tube."""
    pts = np.asarray(points, np.float64)
    if spline and len(pts) > 2:
        n = samples or max(12, 8 * (len(pts) - 1))
        poly = curves.smooth(pts, n)
    else:
        poly = pts
    s = curves.lengths(poly)
    total = max(float(s[-1]), 1e-9)
    # Radii sit at the control points when there is one each, else evenly along the curve.
    if len(radii) == len(pts):
        ctrl = curves.lengths(pts)
        where = ctrl / max(float(ctrl[-1]), 1e-9)
    else:
        where = np.linspace(0.0, 1.0, len(radii))
    table = curves.curve1d(list(zip(where.tolist(), radii)), 129)
    rad = np.maximum(np.interp(s / total, np.linspace(0.0, 1.0, 129), table), 0.0)
    rmax = float(rad.max())

    def fn(x, y):
        best = np.full(np.shape(x), np.inf)
        u = np.zeros(np.shape(x))
        rr = np.full(np.shape(x), 1e-6)
        sd = np.zeros(np.shape(x))
        for i in range(len(poly) - 1):
            d, h, r, sgn = _segment(x, y, poly[i, 0], poly[i, 1], poly[i + 1, 0], poly[i + 1, 1], rad[i], rad[i + 1])
            m = d < best
            best = np.where(m, d, best)
            u = np.where(m, (s[i] + h * (s[i + 1] - s[i])) / total, u)
            rr = np.where(m, r, rr)
            sd = np.where(m, sgn, sd)
        rr = np.maximum(rr, 1e-6)
        v = np.clip(sd / rr, -1.0, 1.0)
        return Field(best, u, v, np.clip(1.0 - np.abs(sd) / rr, 0.0, 1.0), rr, u * total, np.arcsin(v) * rr)

    return Shape(fn, (poly[:, 0].min() - rmax, poly[:, 1].min() - rmax, poly[:, 0].max() + rmax,
                      poly[:, 1].max() + rmax))


def lathe(a, b, widths):
    """A solid of revolution seen from the side: an axis from `a` to `b` and a half-width profile along it
    (numbers evenly spaced, or (t, width) pairs). u runs 0..1 along the axis, v runs -1..1 across, and depth is
    that of the round body, so shading and wrapped patterns come out as on a turned form."""
    ax, ay = a
    bx, by = b
    length = math.hypot(bx - ax, by - ay)
    ex, ey = (bx - ax) / length, (by - ay) / length
    table = np.maximum(curves.curve1d(list(widths), 257), 0.0)
    slope = np.gradient(table, length / 256.0)
    ts = np.linspace(0.0, 1.0, 257)
    wmax = float(table.max())

    def fn(x, y):
        px, py = x - ax, y - ay
        along = px * ex + py * ey
        across = -px * ey + py * ex
        tt = np.clip(along / length, 0.0, 1.0)
        w = np.interp(tt, ts, table)
        dw = np.interp(tt, ts, slope)
        d = np.maximum((np.abs(across) - w) / np.sqrt(1.0 + dw * dw), np.maximum(-along, along - length))
        ws = np.maximum(w, 1e-6)
        v = np.clip(across / ws, -1.0, 1.0)
        return Field(d, tt, v, np.clip(1.0 - np.abs(across) / ws, 0.0, 1.0), ws, along, np.arcsin(v) * ws)

    cs = [(px + sx * wmax * -ey, py + sx * wmax * ex) for px, py in (a, b) for sx in (-1, 1)]
    return Shape(fn, (min(c[0] for c in cs), min(c[1] for c in cs), max(c[0] for c in cs), max(c[1] for c in cs)))


def leaf(a, b, width, belly=0.4, tip=0.0):
    """A pointed leaf or petal from `a` (stalk end) to `b` (tip), widest at `belly` along its length."""
    return lathe(a, b, [(0.0, tip), (belly * 0.5, width * 0.78), (belly, width),
                        (belly + (1 - belly) * 0.55, width * 0.6), (1.0, 0.0)])
