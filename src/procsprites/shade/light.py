"""The lighting pass: turns a surface buffer into colour.

Light never multiplies colour. It is gathered into one exposure value per sample, and that value picks a tone
from the material's hue-shifted ramp, the way a painter picks from a mixed row of tones. Highlights, rim light
and glow are then added on top.
"""
import math
from dataclasses import dataclass

import numpy as np

from ..core.color import oklab_to_linear, tone
from ..core.mathx import blur, shift, smoothstep

FAR = -1e3


@dataclass(frozen=True)
class Lighting:
    key: tuple = (-0.6, -0.8, 0.95)       # toward the light: top left, in front
    key_strength: float = 1.0
    ambient: float = 0.42
    sky: tuple = (-0.15, -0.75, 0.65)     # where the soft fill light comes from
    pivot: float = 1.04                   # light level that shows the base colour unchanged
    gain_up: float = 3.4                  # ramp steps per unit of light above the pivot
    gain_down: float = 2.75               # and below it
    rim: float = 0.55
    rim_dir: tuple = (0.78, 0.55)         # the rim light sits behind, low on the right
    rim_color: tuple = (0.42, 0.6, 1.0)
    key_color: tuple = (1.0, 0.96, 0.88)
    ao_radius: float = 0.2
    ao_strength: float = 1.25
    shadow_length: float = 0.75
    shadow_soft: float = 0.3
    shadow_depth: float = 0.9             # how much of the key light a cast shadow removes
    bloom: float = 0.07                   # glow spread, in sprite units


def _unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def _coarse(a, f, how):
    """Reduce an array by a whole factor f, taking the mean or the maximum of each block."""
    h, w = a.shape[0] // f, a.shape[1] // f
    block = a[:h * f, :w * f].reshape(h, f, w, f)
    return block.max(axis=(1, 3)) if how == "max" else block.mean(axis=(1, 3))


def _fine(a, f, shape):
    """Undo _coarse: enlarge by f, pad to `shape`, and smooth away the blocks."""
    big = np.repeat(np.repeat(a, f, axis=0), f, axis=1)
    big = np.pad(big, ((0, shape[0] - big.shape[0]), (0, shape[1] - big.shape[1])), mode="edge")
    return blur(big, f * 0.5, passes=2) if f > 1 else big


def cast_shadow(H, light, spx, length, soft, steps=30):
    """1 where the key light reaches the surface, falling to 0 where something stands in its way."""
    H = H.astype(np.float32)
    lx, ly, lz = light
    flat = math.hypot(lx, ly)
    dx, dy, rise = lx / flat, ly / flat, lz / flat
    lit = np.ones(H.shape, np.float32)
    seen = set()
    for i in range(1, steps + 1):
        reach = length * (i / steps) ** 1.6
        ox, oy = int(round(dx * reach / spx)), int(round(dy * reach / spx))
        if (ox, oy) in seen or (ox, oy) == (0, 0):
            continue
        seen.add((ox, oy))
        dist = math.hypot(ox, oy) * spx
        over = shift(H, ox, oy, FAR) - (H + dist * rise)
        lit = np.minimum(lit, 1.0 - np.clip(over / (soft * dist + 1.5 * spx), 0.0, 1.0))
    return lit


def ambient_occlusion(H, SX, SY, spx, radius, strength, dirs=8, steps=5):
    """How open each sample is to the sky, 0..1, measured against its own tangent plane so that round
    forms stay clean and only creases, pits and contacts darken."""
    H, SX, SY = H.astype(np.float32), SX.astype(np.float32), SY.astype(np.float32)
    occ = np.zeros(H.shape, np.float32)
    for k in range(dirs):
        a = (k + 0.5) * 2.0 * math.pi / dirs
        dx, dy = math.cos(a), math.sin(a)
        best = np.zeros(H.shape, np.float32)
        seen = set()
        for j in range(1, steps + 1):
            reach = radius * (j / steps) ** 1.7
            ox, oy = int(round(dx * reach / spx)), int(round(dy * reach / spx))
            if (ox, oy) in seen or (ox, oy) == (0, 0):
                continue
            seen.add((ox, oy))
            dist = math.hypot(ox, oy) * spx
            above = (shift(H, ox, oy, FAR) - H) / dist - (SX * ox + SY * oy) * spx / dist
            best = np.maximum(best, above * max(0.0, 1.0 - (dist / radius) ** 2))
        occ += best / np.sqrt(1.0 + best * best)
    return np.clip(1.0 - strength * occ / dirs, 0.0, 1.0)


def shade(gb, env=None):
    """Light a surface buffer. Returns linear RGB, alpha, and the intermediate layers for debug views."""
    env = env or Lighting()
    L = _unit(env.key)
    S = _unit(env.sky)
    solid = gb.A > 0.004
    H = np.where(solid, gb.H, FAR)

    lit2 = cast_shadow(H, L, gb.spx, env.shadow_length, env.shadow_soft)
    # Occlusion is broad and soft, so it is gathered on a grid of about one sample per output pixel.
    f = max(1, gb.ss // 2) if gb.ss % 2 == 0 else (gb.ss if gb.ss > 2 else 1)
    ao2 = _fine(ambient_occlusion(_coarse(H, f, "max"), _coarse(gb.SX, f, "mean"), _coarse(gb.SY, f, "mean"),
                                  gb.spx * f, env.ao_radius, env.ao_strength), f, H.shape)

    # From here on only covered samples are lit, as flat vectors.
    lit, ao = lit2[solid].astype(np.float64), ao2[solid].astype(np.float64)
    sx, sy = gb.SX[solid], gb.SY[solid]
    inv = 1.0 / np.sqrt(sx * sx + sy * sy + 1.0)
    nx, ny, nz = -sx * inv, -sy * inv, inv
    lab, trans, metal, spec = gb.lab[solid], gb.trans[solid], gb.metal[solid], gb.spec[solid]

    ndl = nx * L[0] + ny * L[1] + nz * L[2]
    wrap = 0.12 + 0.55 * trans
    shadow = 1.0 - env.shadow_depth * (1.0 - lit) * (1.0 - 0.45 * trans)
    key = np.clip((ndl + wrap) / (1.0 + wrap), 0.0, 1.0) * shadow
    sky = 0.5 + 0.5 * (nx * S[0] + ny * S[1] + nz * S[2])
    illum = env.ambient * sky * ao + env.key_strength * key * (0.5 + 0.5 * ao)
    over = illum - env.pivot
    e = np.where(over > 0, over * env.gain_up, over * env.gain_down)

    # Metal shows its surroundings: a bright band toward the light, a dark horizon, a faint bounce below.
    if metal.any():
        toward = -(2.0 * nz * nx * 0.6 + 2.0 * nz * ny * 0.8)
        surround = (1.7 * smoothstep(0.05, 0.55, toward) - 1.5 * smoothstep(0.12, -0.3, toward)
                    + 1.0 * smoothstep(-0.45, -0.95, toward))
        e = e + metal * (surround * (0.6 + 0.4 * ao) - 0.2)

    # Translucent material glows where it is thin and where the light is behind it.
    thin = np.exp(-np.maximum(gb.E[solid], 0.0) / 0.05)
    through = trans * (0.55 * thin + 0.35 * np.clip(-ndl, 0.0, 1.0)) * (0.4 + 0.6 * lit)
    e = e + through * 1.6

    hue = gb.irid[solid] * (95.0 * (1.0 - nz) + 40.0 * nx - 20.0 * ny)
    rgb = np.maximum(oklab_to_linear(tone(lab, e, sat=1.0 + 0.45 * through, hue=hue)), 0.0)
    base = np.maximum(oklab_to_linear(lab), 0.0)

    # Highlights: a tight one whose size follows roughness, and a broad soft sheen under it.
    hx, hy, hz = _unit((L[0], L[1], L[2] + 1.0))
    ndh = np.clip(nx * hx + ny * hy + nz * hz, 0.0, 1.0)
    power = np.clip(2.0 / np.maximum(gb.rough[solid], 0.05) ** 3.2, 2.0, 1500.0)
    glint = spec * (ndh ** power * np.minimum(0.55 + power * 0.012, 2.6) + 0.10 * ndh ** (power * 0.09 + 1.0))
    glint = glint * (0.25 + 0.75 * lit) * (0.35 + 0.65 * ao)
    shine = np.array(env.key_color) * (1.0 - metal[:, None]) + (base * 1.6 + 0.12) * metal[:, None]
    rgb = rgb + shine * glint[:, None]

    # A cool light from behind catches the edges that face away from the key.
    facing = np.clip(nx * env.rim_dir[0] + ny * env.rim_dir[1] + 0.15, 0.0, 1.0)
    rim = env.rim * (1.0 - nz) ** 2.6 * facing * (0.3 + 0.7 * ao)
    rgb = rgb + np.array(env.rim_color) * (rim * (0.35 + 0.65 * (0.3 + spec)))[:, None]

    # Glow: the emitter itself, plus light spilling onto whatever is nearby.
    if gb.emit.any():
        spill = blur(gb.emit * gb.A[..., None], env.bloom / gb.spx)
        rgb = rgb + gb.emit[solid] + spill[solid] * (0.9 + 0.6 * base)

    def spread(v, fill=0.0):
        out = np.full(gb.A.shape + v.shape[1:], fill)
        out[solid] = v
        return out

    layers = {"lit": lit2, "ao": ao2, "exposure": spread(e), "normal": spread(np.stack([nx, ny, nz], axis=-1)),
              "solid": solid}
    return spread(rgb), gb.A.copy(), layers
