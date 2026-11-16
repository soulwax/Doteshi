"""The painted resolver: smooth edges, full detail, an optional tinted line round the silhouette."""
import numpy as np
from PIL import Image

from ..core.color import linear_to_srgb, oklab_to_linear, tone
from ..core.mathx import box_blur
from ..shade.light import shade


def downsample(rgb, alpha, ss):
    """Average samples into pixels, weighting colour by coverage so edges carry no dark fringe."""
    h, w = alpha.shape[0] // ss, alpha.shape[1] // ss
    a = alpha.reshape(h, ss, w, ss).mean(axis=(1, 3))
    pre = (rgb * alpha[..., None]).reshape(h, ss, w, ss, 3).mean(axis=(1, 3))
    return pre / np.maximum(a, 1e-6)[..., None], a


def to_image(rgb, alpha):
    out = np.zeros(alpha.shape + (4,), np.uint8)
    out[..., :3] = np.round(linear_to_srgb(rgb) * 255.0).astype(np.uint8)
    out[..., 3] = np.round(np.clip(alpha, 0.0, 1.0) * 255.0).astype(np.uint8)
    out[out[..., 3] == 0] = 0
    return Image.fromarray(out, "RGBA")


def resolve(gb, env=None, outline=0.75, outline_width=1.1):
    """Light the buffer and resolve it to an RGBA image. `outline` is the strength of the silhouette line
    (0 for none); the line is each surface's own deepest shadow tone, not a flat black. Its width is in
    output pixels."""
    rgb, alpha, _ = shade(gb, env)
    if outline > 0:
        r = max(1, int(round(outline_width * gb.ss)))
        near = np.clip((1.0 - box_blur(box_blur(alpha, r), r)) * 2.0, 0.0, 1.0)
        at = (near > 0.004) & (alpha > 0.004)
        ink = np.maximum(oklab_to_linear(tone(gb.lab[at], np.full(int(at.sum()), -3.6), sat=1.15)), 0.0)
        rgb[at] += (ink - rgb[at]) * (near[at] * outline)[:, None]
    rgb, alpha = downsample(np.clip(rgb, 0.0, 1.0), alpha, gb.ss)
    return to_image(rgb, alpha)
