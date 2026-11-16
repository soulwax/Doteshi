"""Materials: what a surface is made of. Colour is the base tone; light decides which tone of its ramp shows."""
from dataclasses import dataclass, replace

from ..core.color import rgb8


@dataclass(frozen=True)
class Material:
    color: tuple
    rough: float = 0.7     # 0 mirror-smooth .. 1 chalky; sets how tight the highlight is
    spec: float = 0.12     # highlight strength
    metal: float = 0.0     # 0..1: tinted highlights and a reflected surround
    trans: float = 0.0     # 0..1: light wraps round and glows through thin edges
    irid: float = 0.0      # hue swing with viewing angle, as on beetle shell or oil
    emit: float = 0.0      # light given off, in the material's own colour unless emit_color is set
    emit_color: tuple = None

    def but(self, **changes):
        if "color" in changes:
            changes["color"] = rgb8(changes["color"])
        return replace(self, **changes)


def _make(color, kw, **defaults):
    return Material(rgb8(color), **{**defaults, **kw})


def matte(color, **kw):
    return _make(color, kw, rough=0.9, spec=0.04)


def satin(color, **kw):
    return _make(color, kw, rough=0.55, spec=0.22)


def glossy(color, **kw):
    return _make(color, kw, rough=0.26, spec=0.6)


def metal(color, **kw):
    return _make(color, kw, rough=0.3, spec=0.75, metal=1.0)


def translucent(color, **kw):
    return _make(color, kw, rough=0.6, spec=0.18, trans=0.8)


def glowing(color, **kw):
    return _make(color, kw, rough=0.8, spec=0.0, emit=1.0)
