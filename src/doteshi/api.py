"""Authoring and rendering entry points: the @sprite decorator, the registry, and render()."""
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .core.rng import Rng
from .form.scene import Scene
from .resolve import painted, pixel
from .resolve import style as styles

REGISTRY = {}
OVERRIDES = {}
_LOADED = set()


@dataclass(frozen=True)
class SpriteDef:
    id: str
    fn: object
    sizes: tuple
    variants: int
    aspect: float
    style: object


def sprite(id, sizes=(256,), variants=1, aspect=1.0, style=None):
    """Register a sprite. The function receives a Scene and a seeded Rng and adds parts to the scene.
    `aspect` is width over height; sizes are heights in pixels. `style` fixes a style profile (a name or a
    Style); without it the profile follows the size."""

    def register(fn):
        REGISTRY[id] = SpriteDef(id, fn, tuple(sizes), variants, aspect, style)
        return fn

    return register


def override(id, size):
    """Register a hand-made version of a sprite for one size. The function receives a seeded Rng and returns
    an RGBA image, or (rows, palette) or (rows, palette, outline colour) for `pixel.pixelmap`."""

    def register(fn):
        OVERRIDES[(id, int(size))] = fn
        return fn

    return register


def load(path):
    """Import every .py file under a content folder so its sprites register."""
    for file in sorted(Path(path).resolve().rglob("*.py")):
        if file in _LOADED:
            continue
        _LOADED.add(file)
        name = f"_doteshi_content_{len(_LOADED)}_{file.stem}"
        spec = importlib.util.spec_from_file_location(name, file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)


def build(id, variant=0):
    d = REGISTRY[id]
    rng = Rng(id, variant)
    scene = Scene(rng, d.aspect)
    d.fn(scene, rng)
    return scene


def supersample(size):
    """Samples per pixel edge: small sprites get more, so every size is lit from a detailed surface."""
    want = 720 / size
    return next((s for s in (2, 3, 4, 6, 8) if s >= want), 8)


def rasterize(id, size=256, variant=0, ss=None, inset=0, fit=None):
    """The surface buffer of one sprite. `inset` leaves that many pixels clear on every side; `fit` frames the
    sprite ("all" of it, or its "body" without limbs) to fill what remains."""
    scene = build(id, variant)
    w, h = int(round(size * scene.aspect)) - 2 * inset, size - 2 * inset
    view = scene.fit(w, h, size, body_only=fit == "body") if fit else None
    return scene.rasterize(w, h, ss or supersample(size), nominal=size, view=view)


def render(id, size=256, variant=0, style=None, ss=None):
    """One sprite as an RGBA image `size` pixels high. `style` is a profile name or a Style; by default the
    sprite's own, else the one that suits the size."""
    d = REGISTRY[id]
    w = int(round(size * d.aspect))
    if (id, size) in OVERRIDES and style is None:
        made = OVERRIDES[(id, size)](Rng(id, variant))
        image = made if isinstance(made, Image.Image) else pixel.pixelmap(*made)
        if image.size != (w, size):
            raise ValueError(f"the {size}px override of '{id}' is {image.width}x{image.height}, expected {w}x{size}")
        return image.convert("RGBA")
    st = styles.get(style if style is not None else d.style, size)
    if st.resolver == "pixel":
        return pixel.resolve(rasterize(id, size, variant, ss or st.ss, st.inset, st.fit), st)
    return painted.resolve(rasterize(id, size, variant, ss), outline=st.line, outline_width=st.line_width)
