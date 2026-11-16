"""Splines and polylines: smooth curves through control points, sampled evenly by arc length."""
import numpy as np


def catmull_rom(points, per_segment=12, closed=False):
    """A smooth curve through `points` as an (n, 2) polyline."""
    p = np.asarray(points, np.float64)
    if len(p) < 3:
        return p.copy()
    if closed:
        ext = np.vstack([p[-1], p, p[0], p[1]])
        segs = len(p)
    else:
        ext = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
        segs = len(p) - 1
    t = np.linspace(0.0, 1.0, per_segment, endpoint=False)[:, None]
    t2, t3 = t * t, t * t * t
    out = []
    for i in range(segs):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(ext[segs + 1][None, :])
    return np.vstack(out)


def bezier(p0, p1, p2, p3, n=24):
    t = np.linspace(0.0, 1.0, n)[:, None]
    p0, p1, p2, p3 = (np.asarray(p, np.float64) for p in (p0, p1, p2, p3))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3


def lengths(poly):
    """Cumulative arc length at each vertex, starting at 0."""
    seg = np.hypot(*np.diff(np.asarray(poly, np.float64), axis=0).T)
    return np.concatenate([[0.0], np.cumsum(seg)])


def resample(poly, n):
    """`n` points spaced evenly by arc length along a polyline."""
    poly = np.asarray(poly, np.float64)
    s = lengths(poly)
    at = np.linspace(0.0, s[-1], n)
    return np.stack([np.interp(at, s, poly[:, 0]), np.interp(at, s, poly[:, 1])], axis=1)


def smooth(points, n=24, closed=False):
    """Control points -> `n` evenly spaced points on the Catmull-Rom curve through them."""
    return resample(catmull_rom(points, 16, closed), n)


def tangents(poly):
    """Unit tangent at each vertex."""
    d = np.gradient(np.asarray(poly, np.float64), axis=0)
    return d / np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-12)[:, None]


def normals(poly):
    """Unit normal at each vertex (tangent turned a quarter turn)."""
    t = tangents(poly)
    return np.stack([-t[:, 1], t[:, 0]], axis=1)


def curve1d(values, n=129):
    """A smooth 1D profile through `values` (plain numbers, evenly spaced, or (t, value) pairs) as a lookup
    table of `n` samples over t in 0..1."""
    v = [p if isinstance(p, (tuple, list)) else (i / max(1, len(values) - 1), p) for i, p in enumerate(values)]
    pts = catmull_rom(np.asarray(v, np.float64), 24)
    order = np.argsort(pts[:, 0], kind="stable")
    return np.interp(np.linspace(0.0, 1.0, n), pts[order, 0], pts[order, 1])
