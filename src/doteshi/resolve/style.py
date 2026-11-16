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
    grow_palette: bool = False         # allow more colours on sprites that span several 16px cells
    fit: str = None                    # frame the sprite to fill the canvas: "all" of it, or its "body"
                                       # only, letting parts marked limb run off the edge
    bases: int = 5                     # most base colours kept
    colors: int = 10                   # most colours in all, not counting the outline
    levels: tuple = (-2.0, -0.9, 0.0, 1.1, 2.2)   # the tones of each base colour, in ramp steps
    min_dist: float = 0.07             # base colours closer than this in OKLab are one colour
    snap: tuple = None                 # reference palette to snap onto where close
    dither: float = 0.0                # ordered dither between tones, 0..1
    lift: float = 0.0                  # lightness added before tones are chosen; keeps small sprites vivid
    contour: int = 1                   # tones to darken where one form passes behind another of the same colour
    contour_gap: float = 0.2           # how far behind, in pixels, before that line is drawn
    contrast: float = 1.0              # exaggeration of light and shade within each colour
    waver: float = 0.0                 # how unevenly the edges between tones run, in tone steps: a hand, not a ruler
    flecks: float = 0.0                # share of rough, flat areas that get a stray pixel one tone off
    glint: float = 0.7                 # how much of a highlight smaller than a pixel survives as a bright pixel
    threshold: float = 0.5             # coverage at which a pixel is solid
    thin: float = 0.15                 # coverage at which a feature under a pixel wide still gets a pixel

    @property
    def inset(self):
        """Margin kept clear for the outline, in pixels."""
        return 1 if self.resolver == "pixel" and self.outline != "none" else 0

    def but(self, **changes):
        return replace(self, **changes)


TINY = Style("tiny", "pixel", snap=KENNEY, ink_lines=True, fit="body", bases=6, colors=18, min_dist=0.06,
             levels=(-2.5, -1.7, -0.9, -0.3, 0.4, 1.1, 1.8, 2.6), lift=0.03, contrast=1.3, grow_palette=True,
             waver=0.45, flecks=0.07)
PIXEL_HD = Style("pixel-hd", "pixel", outline="tinted", fit="all", bases=9, colors=24, min_dist=0.05,
                 levels=(-3.0, -2.1, -1.3, -0.6, 0.0, 0.8, 1.6, 2.6))
PAINTED = Style("painted")
RELIEF = Style("relief", line=0.0)

STYLES = {s.name: s for s in (TINY, PIXEL_HD, PAINTED, RELIEF)}


def for_size(size):
    """The profile a sprite gets when it does not ask for one. Everything up to 64 pixels is drawn at the
    same pixel scale and in the same style, so a 32 pixel structure is four 16 pixel cells of the same art,
    not a finer drawing."""
    return TINY if size <= 64 else PAINTED


def get(style, size):
    if style is None:
        return for_size(size)
    if isinstance(style, Style):
        return style
    if style not in STYLES:
        raise ValueError(f"no style named '{style}'. Known: {', '.join(STYLES)}")
    return STYLES[style]
