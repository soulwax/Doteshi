"""Colour: sRGB, linear and OKLab on arrays, a continuous hue-shifted tone curve for painted output, and an exact
port of the stepped ramp from Mellangan's sprite_kit.py for pixel output."""
import math

import numpy as np

SHADOW_HUE, LIGHT_HUE = 300.0, 85.0
STEP = 0.135

_M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                [0.2119034982, 0.6806995451, 0.1073969566],
                [0.0883024619, 0.2817188376, 0.6299787005]])
_M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                [1.9779984951, -2.4285922050, 0.4505937099],
                [0.0259040371, 0.7827717662, -0.8086757660]])
_M2I = np.array([[1.0, 0.3963377774, 0.2158037573],
                 [1.0, -0.1055613458, -0.0638541728],
                 [1.0, -0.0894841775, -1.2914855480]])
_M1I = np.array([[4.0767416621, -3.3077115913, 0.2309699292],
                 [-1.2684380046, 2.6097574011, -0.3413193965],
                 [-0.0041960863, -0.7034186147, 1.7076147010]])


def srgb_to_linear(c):
    c = np.asarray(c, np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((np.maximum(c, 0.0) + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1.0 / 2.4) - 0.055)


def linear_to_oklab(rgb):
    return np.cbrt(np.asarray(rgb, np.float64) @ _M1.T) @ _M2.T


def oklab_to_linear(lab):
    return (np.asarray(lab, np.float64) @ _M2I.T) ** 3 @ _M1I.T


def rgb8(c):
    """'#rrggbb' or an (r, g, b) tuple of 0..255 -> tuple of ints."""
    if isinstance(c, str):
        c = c.lstrip("#")
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(int(v) for v in c[:3])


def lab_of(c):
    """An sRGB colour ('#hex' or 0..255 tuple) as an OKLab array of 3."""
    return linear_to_oklab(srgb_to_linear(np.array(rgb8(c), np.float64) / 255.0))


def linear_of(c):
    return srgb_to_linear(np.array(rgb8(c), np.float64) / 255.0)


def tone(lab, e, sat=1.0, hue=0.0, shadow_hue=SHADOW_HUE, light_hue=LIGHT_HUE):
    """The continuous ramp. `lab` is the base colour per pixel, `e` the exposure in ramp steps (0 keeps the base,
    negative is shadow, positive is light). Shadows lose lightness in proportion, drift toward violet and keep
    their richness; lights gain lightness, drift warm and wash out. `hue` rotates the base hue in degrees first."""
    L0, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    C0 = np.hypot(a, b)
    H0 = np.degrees(np.arctan2(b, a)) + hue
    dark = np.minimum(e, 0.0)
    lite = np.maximum(e, 0.0)
    # Vivid colours brighten less: a lit red stays red and leaves the white to the highlight.
    L = L0 * (1.0 + 0.215 * dark) + lite * STEP * (1.12 - 0.45 * L0) * (1.0 - np.minimum(1.9 * C0, 0.5))
    L = np.clip(L, 0.045, 0.988)
    ratio = L / np.maximum(L0, 1e-6)
    C = C0 * np.where(e < 0, np.minimum(ratio, 1.0) ** 0.55 * (1.0 - 0.05 * dark), 1.0 / (1.0 + 0.10 * lite))
    C = C * sat
    coloured = np.clip((C0 - 0.012) / 0.03, 0.0, 1.0)
    target = np.where(e < 0, shadow_hue, light_hue)
    t = np.minimum(0.5, 0.11 * np.abs(e)) * coloured
    H = H0 + ((target - H0 + 540.0) % 360.0 - 180.0) * t
    h = np.radians(H)
    # Greys pick up a little of the shadow or light hue so they never read as dead neutral.
    tint = (1.0 - coloured) * np.where(e < 0, -0.010 * dark, 0.007 * lite)
    ht = np.radians(target)
    return np.stack([L, C * np.cos(h) + tint * np.cos(ht), C * np.sin(h) + tint * np.sin(ht)], axis=-1)


# --- Stepped ramp, ported unchanged from Mellangan tools/sprite_kit.py (scalar maths, same operation order) ---

KENNEY = (
    (118, 59, 54), (195, 75, 53), (232, 69, 55), (242, 132, 98), (189, 108, 74), (227, 134, 40),
    (207, 130, 84), (234, 165, 108), (253, 190, 83), (247, 194, 130), (252, 188, 143),
    (132, 198, 105), (71, 159, 74), (37, 149, 106), (67, 225, 179), (105, 255, 212),
    (117, 227, 255), (0, 154, 220), (82, 96, 124), (139, 155, 180), (192, 203, 220), (38, 43, 68),
    (155, 76, 163), (209, 118, 208), (255, 255, 255),
)


def _lin(v):
    v /= 255
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _gam(v):
    v = max(0.0, min(1.0, v))
    return int(round(255 * (v * 12.92 if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055)))


def oklab(c):
    r, g, b = (_lin(v) for v in c[:3])
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def rgb(lab):
    L, a, b = lab
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (_gam(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
            _gam(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
            _gam(-0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s))


def lch(c):
    L, a, b = oklab(c)
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def _toward(h, target, t):
    d = (target - h + 540) % 360 - 180
    return (h + d * t) % 360


def delta(p, q):
    a, b = oklab(p), oklab(q)
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def ramp(base, n=5, snap=KENNEY):
    """`n` tones around `base`, darkest first, snapped onto the reference palette where close."""
    L0, C0, H0 = lch(base)
    mid = n // 2
    out = []
    for i in range(n):
        k = i - mid
        L = min(0.97, max(0.24, L0 + k * STEP))
        C = C0 * (1 - 0.18 * abs(k)) if k < 0 else C0 * (1 - 0.22 * k)
        H = _toward(H0, SHADOW_HUE if k < 0 else LIGHT_HUE, min(0.5, 0.11 * abs(k)) if C0 > 0.025 else 0)
        c = rgb((L, C * math.cos(math.radians(H)), C * math.sin(math.radians(H))))
        if snap:
            near = min(snap, key=lambda q: delta(c, q))
            c = near if delta(c, near) < 0.035 else c
        out.append(c)
    return out
