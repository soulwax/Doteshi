"""Style profiles: how a lit surface becomes pixels at a given size.

A 16px sprite is not a shrunken 256px one. Small sizes go through the pixel resolver (hard edges, a small palette
of hue-shifted tones, a one-pixel outline); large sizes go through the painted resolver.
"""
from dataclasses import dataclass, replace

from ..core.color import KENNEY

OUTLINE = (63, 38, 49)     # the outline colour of Mellangan's sprite_kit


@dataclass(frozen=True)
class Style:
    name: str
    resolver: str = "painted"          # "painted" or "pixel"
    # painted
    line: float = 0.75                 # strength of the silhouette line, 0 for none
    line_width: float = 1.1            # in output pixels
    # pixel
    ss: int = 8                        # samples per pixel edge
    outline: str = "flat"              # "flat" (one colour), "tinted" (each surface's own darkest tone), "none"
    outline_color: tuple = OUTLINE
    ink_lines: bool = False            # draw features under a pixel wide as flat unoutlined lines
    fit: bool = False                  # frame the sprite's solid mass to fill the canvas
    bases: int = 5                     # most base colours kept
    colors: int = 10                   # most colours in all, not counting the outline
    levels: tuple = (-2.0, -0.9, 0.0, 1.1, 2.2)   # the tones of each base colour, in ramp steps
    min_dist: float = 0.07             # base colours closer than this in OKLab are one colour
    snap: tuple = None                 # reference palette to snap onto where close
    dither: float = 0.0                # ordered dither between tones, 0..1
    lift: float = 0.0                  # lightness added before tones are chosen; keeps small sprites vivid
    threshold: float = 0.5             # coverage at which a pixel is solid
    thin: float = 0.15                 # coverage at which a feature under a pixel wide still gets a pixel

    @property
    def inset(self):
        """Margin kept clear for the outline, in pixels."""
        return 1 if self.resolver == "pixel" and self.outline != "none" else 0

    def but(self, **changes):
        return replace(self, **changes)


TINY = Style("tiny", "pixel", snap=KENNEY, ink_lines=True, fit=True, bases=4, colors=7,
             levels=(-1.8, -0.7, 0.0, 1.2), lift=0.04)
PIXEL_HD = Style("pixel-hd", "pixel", outline="tinted", bases=9, colors=24, min_dist=0.05,
                 levels=(-3.0, -2.1, -1.3, -0.6, 0.0, 0.8, 1.6, 2.6))
PAINTED = Style("painted")
RELIEF = Style("relief", line=0.0)

STYLES = {s.name: s for s in (TINY, PIXEL_HD, PAINTED, RELIEF)}


def for_size(size):
    """The profile a sprite gets when it does not ask for one."""
    return TINY if size <= 24 else PIXEL_HD if size <= 64 else PAINTED


def get(style, size):
    if style is None:
        return for_size(size)
    if isinstance(style, Style):
        return style
    if style not in STYLES:
        raise ValueError(f"no style named '{style}'. Known: {', '.join(STYLES)}")
    return STYLES[style]
