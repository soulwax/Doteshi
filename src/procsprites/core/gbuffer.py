"""The surface buffer: everything the lighting pass needs to know about each sample, before any colour exists."""
import math

import numpy as np

# Per-sample surface properties, blended where parts overlap.
PROPS = ("rough", "spec", "metal", "trans", "irid")


class GBuffer:
    def __init__(self, w, h, ss=1, nominal=None, view=None):
        self.w, self.h, self.ss = int(w), int(h), int(ss)
        self.nominal = nominal or self.h     # the sprite size asked for, which may include an outline margin
        self.keeps = []                      # key features: (part id, x, y, base colour as OKLab)
        self.soft = set()                    # ids of parts that take no outline
        self.W, self.Hn = self.w * self.ss, self.h * self.ss
        # The view is the part of sprite space the canvas shows: (left, top, height). By default the canvas
        # spans -1..1 top to bottom and is centred on x = 0.
        self.aspect = self.w / self.h
        self.x0, self.y0, span = view or (-self.aspect, -1.0, 2.0)
        self.px = span / self.h             # one output pixel, in sprite units
        self.spx = self.px / self.ss        # one sample
        self.xs = (np.arange(self.W) + 0.5) * self.spx + self.x0
        self.ys = (np.arange(self.Hn) + 0.5) * self.spx + self.y0
        shape = (self.Hn, self.W)
        self.A = np.zeros(shape)            # coverage
        self.H = np.zeros(shape)            # height toward the viewer
        self.SX = np.zeros(shape)           # height slope along x and y; the normal is (-SX, -SY, 1) normalised
        self.SY = np.zeros(shape)
        self.E = np.zeros(shape)            # distance inside the owning part's edge
        self.lab = np.zeros(shape + (3,))   # base colour, OKLab
        self.emit = np.zeros(shape + (3,))  # emitted light, linear RGB
        self.pid = np.zeros(shape, np.int32)
        for name in PROPS:
            setattr(self, name, np.zeros(shape))

    def window(self, bounds, margin=3):
        """Index slices (rows, columns) covering a bounding box in sprite units, or None if it misses."""
        x0 = max(0, int(math.floor((bounds[0] - self.x0) / self.spx)) - margin)
        x1 = min(self.W, int(math.ceil((bounds[2] - self.x0) / self.spx)) + margin)
        y0 = max(0, int(math.floor((bounds[1] - self.y0) / self.spx)) - margin)
        y1 = min(self.Hn, int(math.ceil((bounds[3] - self.y0) / self.spx)) + margin)
        if x1 - x0 < 2 or y1 - y0 < 2:
            return None
        return slice(y0, y1), slice(x0, x1)

    def normals(self):
        inv = 1.0 / np.sqrt(self.SX * self.SX + self.SY * self.SY + 1.0)
        return -self.SX * inv, -self.SY * inv, inv
