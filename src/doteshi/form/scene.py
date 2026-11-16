"""Parts and scenes. A sprite is a scene of parts; each part is a shape with a height profile, a material, relief
patterns and colour patterns. Rasterising a scene fills a surface buffer at any resolution."""
import numpy as np

from ..core.color import lab_of, linear_of
from ..core.gbuffer import PROPS, GBuffer
from ..core.mathx import smax, smoothstep, spread
from . import profile as profiles

MAX_SLOPE = 7.0       # about 82 degrees: the steepest a surface may tilt away from the viewer
MIN_FEATURE = 1.5     # patterns finer than this many output pixels are dropped
MIN_PART = 1.0        # so are whole parts no larger than this, unless marked keep
MIN_KEPT = 1.6        # patterns marked keep are coarsened until their features are this many pixels


class Ctx:
    """What a pattern can see of the part it is drawn on."""
    __slots__ = ("x", "y", "d", "u", "v", "t", "r", "mu", "mv", "px")


class Part:
    def __init__(self, shape, material, profile=profiles.dome, z=0.0, relief=1.0, height=None, join=0.0,
                 onlay=False, on=None, keep=False, min_size=None, soft=False, name=None):
        self.shape, self.material, self.profile = shape, material, profile
        self.z, self.relief, self.height, self.join = z, relief, height, join
        self.onlay, self.on, self.keep, self.name = onlay or on is not None, on, keep, name
        self.min_size, self.soft = min_size, soft
        self.bumps, self.tints = [], []
        self.pid = 0

    def bump(self, pattern, depth, fade=0.12):
        """Add relief: `depth` sprite units where the pattern is 1. `fade` eases it out toward the part's edge."""
        self.bumps.append((pattern, depth, fade))
        return self

    def tint(self, color, pattern=None, amount=1.0, **props):
        """Mix toward `color` where the pattern is 1 (everywhere if none). Extra keywords set surface
        properties under the same mask: rough, spec, metal, trans, irid, emit."""
        self.tints.append((None if color is None else lab_of(color), None if color is None else linear_of(color),
                           pattern, amount, props))
        return self

    def rasterize(self, gb):
        b = self.shape.bounds
        if self.min_size and gb.nominal < self.min_size:
            return
        if not self.keep and max(b[2] - b[0], b[3] - b[1]) < MIN_PART * gb.px:
            return
        win = gb.window(b)
        if win is None:
            return
        x, y = np.meshgrid(gb.xs[win[1]], gb.ys[win[0]])
        f = self.shape.eval(x, y)
        d = f.d
        gy, gx = np.gradient(d, gb.spx)
        cov = np.clip(0.5 - d / (np.maximum(np.hypot(gx, gy), 0.3) * gb.spx), 0.0, 1.0)
        if self.soft:
            gb.soft.add(self.pid)
        if self.keep:
            total = float(cov.sum())
            at = ((x * cov).sum() / total, (y * cov).sum() / total) if total > 0 else ((b[0] + b[2]) / 2,
                                                                                         (b[1] + b[3]) / 2)
            gb.keeps.append((self.pid, float(at[0]), float(at[1]), lab_of(self.material.color)))
        if not cov.any():
            return
        r = f.r if f.r is not None else max(float(-d.min()), gb.spx)
        t = f.t if f.t is not None else np.clip(-d / r, 0.0, 1.0)

        c = Ctx()
        c.x, c.y, c.d, c.u, c.v, c.t, c.r, c.mu, c.mv, c.px = x, y, d, f.u, f.v, t, r, f.mu, f.mv, gb.px

        def drawn(p):
            """What a pattern sees at this size: the surface itself, a coarsened one for patterns that must
            stay readable, or None when the pattern is too fine to draw."""
            if p is None or p.size is None or p.size >= MIN_FEATURE * gb.px:
                return c
            if not p.kept:
                return None
            k = MIN_KEPT * gb.px / p.size
            coarse = Ctx()
            for name in Ctx.__slots__:
                setattr(coarse, name, getattr(c, name))
            coarse.mu, coarse.mv = c.mu / k, c.mv / k
            return coarse

        rise = self.profile(t) * (self.height if self.height is not None else self.relief * r)
        for pattern, depth, fade in self.bumps:
            at = drawn(pattern)
            if at is not None:
                rise = rise + depth * pattern(at) * (smoothstep(0.0, fade, t) if fade else 1.0)
        sy, sx = np.gradient(rise, gb.spx)
        steep = np.hypot(sx, sy)
        ease = np.minimum(1.0, MAX_SLOPE / np.maximum(steep, 1e-9))
        sx, sy = sx * ease, sy * ease

        m = self.material
        lab = np.broadcast_to(lab_of(m.color), d.shape + (3,)).copy()
        props = {k: np.full(d.shape, float(getattr(m, k))) for k in PROPS}
        emit = np.broadcast_to(linear_of(m.emit_color or m.color) * m.emit, d.shape + (3,)).copy()
        for tlab, tlin, pattern, amount, extra in self.tints:
            at = drawn(pattern)
            if at is None:
                continue
            mask = np.clip((1.0 if pattern is None else pattern(at)) * amount, 0.0, 1.0) * np.ones(d.shape)
            if tlab is not None:
                lab += (tlab - lab) * mask[..., None]
            for k, value in extra.items():
                if k == "emit":
                    glow = (tlin if tlab is not None else linear_of(m.emit_color or m.color)) * value
                    emit += (glow - emit) * mask[..., None]
                else:
                    props[k] += (value - props[k]) * mask

        A, H = gb.A[win], gb.H[win]
        empty = A < 1e-3
        if self.onlay:
            # Sits on whatever is already there and follows its form.
            h = H + self.z + rise
            sx, sy = sx + gb.SX[win], sy + gb.SY[win]
            w = cov * ~empty
            if self.on is not None:
                w = w * (gb.pid[win] == self.on.pid)
            raised = h
        else:
            h = self.z + rise
            k = max(self.join, gb.spx * 0.75)
            w = np.where(empty, cov > 0, cov * np.clip(0.5 + (h - H) / (2.0 * k), 0.0, 1.0))
            raised = np.where(empty, h, H + (smax(H, h, self.join) - H) * cov)
        if self.onlay:
            gb.H[win] = H + (raised - H) * w
        else:
            gb.H[win] = np.where(cov > 0, raised, H)
            gb.A[win] = np.maximum(A, cov)
        w3 = w[..., None]
        gb.SX[win] += (sx - gb.SX[win]) * w
        gb.SY[win] += (sy - gb.SY[win]) * w
        gb.lab[win] += (lab - gb.lab[win]) * w3
        gb.emit[win] += (emit - gb.emit[win]) * w3
        for k in PROPS:
            getattr(gb, k)[win] += (props[k] - getattr(gb, k)[win]) * w
        own = w > 0.5
        gb.E[win] = np.where(own, -d, gb.E[win])
        gb.pid[win] = np.where(own, self.pid, gb.pid[win])


class Group:
    """Several parts that take the same relief and colour, such as a mirrored pair."""

    def __init__(self, parts):
        self.parts = list(parts)

    def bump(self, *a, **kw):
        for p in self.parts:
            p.bump(*a, **kw)
        return self

    def tint(self, *a, **kw):
        for p in self.parts:
            p.tint(*a, **kw)
        return self

    def __iter__(self):
        return iter(self.parts)


class Scene:
    def __init__(self, rng, aspect=1.0):
        self.rng, self.aspect = rng, aspect
        self.parts = []

    def part(self, shape, material, **kw):
        p = Part(shape, material, **kw)
        p.pid = len(self.parts) + 1
        self.parts.append(p)
        return p

    def pair(self, shape, material, axis=0.0, asym=1.0, **kw):
        """A part and its mirror image across x = axis. The twin is nudged slightly so the two sides are
        never an exact reflection; asym=0 turns that off."""
        r = self.rng.stream(f"pair{len(self.parts)}")
        b = shape.bounds
        twin = shape.mirror(axis)
        if asym:
            cx, cy = 2 * axis - (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            twin = twin.rot(r.uniform(-2.0, 2.0) * asym, cx, cy).at(r.uniform(-0.006, 0.006) * asym,
                                                                    r.uniform(-0.008, 0.008) * asym)
        return Group([self.part(shape, material, **kw), self.part(twin, material, **kw)])

    def fit(self, w, h, nominal=None, probe=96):
        """The view that makes the scene's solid mass fill a w x h canvas. Slender features (legs, feelers,
        blades) are not counted, so a creature's body fills the frame and its extremities may run off it,
        which is how a sprite this small is drawn by hand."""
        gb = self.rasterize(max(8, int(round(probe * w / h))), probe, 1, nominal)
        mask = gb.A > 0.5
        r = max(1, int(round(0.5 * probe / h)))
        mass = spread(spread(mask, r, False), r, True)
        ys, xs = np.nonzero(mass if mass.any() else mask)
        if len(xs) == 0:
            return None
        x0, x1 = gb.xs[xs.min()] - gb.spx / 2, gb.xs[xs.max()] + gb.spx / 2
        y0, y1 = gb.ys[ys.min()] - gb.spx / 2, gb.ys[ys.max()] + gb.spx / 2
        span = max(y1 - y0, (x1 - x0) * h / w)
        return (x0 + x1) / 2 - span * w / h / 2, (y0 + y1) / 2 - span / 2, span

    def rasterize(self, w, h, ss=1, nominal=None, view=None):
        gb = GBuffer(w, h, ss, nominal, view)
        for p in self.parts:
            p.rasterize(gb)
        return gb
