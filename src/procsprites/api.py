"""Authoring and rendering entry points: the @sprite decorator, the registry, and render()."""
import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path

from .core.rng import Rng
from .form.scene import Scene
from .resolve import painted

REGISTRY = {}


@dataclass(frozen=True)
class SpriteDef:
    id: str
    fn: object
    sizes: tuple
    variants: int
    aspect: float


def sprite(id, sizes=(256,), variants=1, aspect=1.0):
    """Register a sprite. The function receives a Scene and a seeded Rng and adds parts to the scene.
    `aspect` is width over height; sizes are heights in pixels."""

    def register(fn):
        REGISTRY[id] = SpriteDef(id, fn, tuple(sizes), variants, aspect)
        return fn

    return register


def load(path):
    """Import every .py file under a content folder so its sprites register."""
    for i, file in enumerate(sorted(Path(path).rglob("*.py"))):
        name = f"_procsprites_content_{i}_{file.stem}"
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


def rasterize(id, size=256, variant=0, ss=None):
    scene = build(id, variant)
    return scene.rasterize(int(round(size * scene.aspect)), size, ss or supersample(size))


def render(id, size=256, variant=0, ss=None, **style):
    """One sprite as an RGBA image `size` pixels high."""
    return painted.resolve(rasterize(id, size, variant, ss), **style)
