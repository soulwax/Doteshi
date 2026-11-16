"""Height profiles: how a part rises from its edge (t = 0) to its core (t = 1). Each returns 0..1."""
import numpy as np

from ..core.mathx import smoothstep


def dome(t):
    """A round body: a hemisphere over a disc, a round tube over a stroke."""
    return np.sqrt(np.clip(1.0 - (1.0 - t) ** 2, 0.0, 1.0))


def flat(edge=0.08):
    """A slab with a softened rim."""
    return lambda t: smoothstep(0.0, edge, t)


def bevel(width=0.3):
    """A straight chamfer up to a flat top."""
    return lambda t: np.clip(t / width, 0.0, 1.0)


def pillow(power=2.0):
    """Between flat and dome: higher powers give a flatter top with rounder shoulders."""
    return lambda t: 1.0 - (1.0 - np.clip(t, 0.0, 1.0)) ** power


def ridge(t):
    """A sharp crest along the middle, like a roof, a blade or a crystal face."""
    return np.clip(t, 0.0, 1.0)


def dish(rim=0.25):
    """A raised rim around a sunken middle."""
    return lambda t: smoothstep(0.0, rim, t) * (1.0 - 0.6 * smoothstep(rim, 1.0, t))
