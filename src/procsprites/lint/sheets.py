"""Review sheets: images tiled on a neutral ground with labels, for judging results by eye."""
import numpy as np
from PIL import Image, ImageDraw

GROUND = (58, 62, 70)
INK = (198, 204, 214)


def sheet(images, labels=None, cols=None, scale=1, pad=10, ground=GROUND, title=None):
    """Tile images into a grid. Small sprites can be enlarged by a whole-number `scale` with hard pixels."""
    images = list(images)
    cols = cols or max(1, int(np.ceil(np.sqrt(len(images)))))
    rows = -(-len(images) // cols)
    cw = max(im.width for im in images) * scale
    ch = max(im.height for im in images) * scale
    label_h = 14 if labels else 0
    top = 22 if title else 0
    out = Image.new("RGBA", (pad + cols * (cw + pad), top + pad + rows * (ch + label_h + pad)), ground + (255,))
    draw = ImageDraw.Draw(out)
    if title:
        draw.text((pad, 6), title, fill=INK)
    for i, im in enumerate(images):
        if scale != 1:
            im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        x = pad + (i % cols) * (cw + pad) + (cw - im.width) // 2
        y = top + pad + (i // cols) * (ch + label_h + pad) + (ch - im.height)
        out.alpha_composite(im.convert("RGBA"), (x, y))
        if labels:
            draw.text((pad + (i % cols) * (cw + pad), y + im.height + 1), str(labels[i]), fill=INK)
    return out


def grey(a, lo=None, hi=None):
    """A scalar layer as a greyscale image."""
    lo = float(np.min(a)) if lo is None else lo
    hi = float(np.max(a)) if hi is None else hi
    v = np.clip((a - lo) / max(hi - lo, 1e-9), 0.0, 1.0)
    return Image.fromarray(np.round(v * 255).astype(np.uint8), "L").convert("RGBA")


def rgb(a):
    return Image.fromarray(np.round(np.clip(a, 0.0, 1.0) * 255).astype(np.uint8), "RGB").convert("RGBA")
