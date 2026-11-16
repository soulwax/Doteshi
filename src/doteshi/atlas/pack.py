"""Placing rectangles on atlas pages. MaxRects for mixed sizes; existing placements can be re-occupied first, so
new sprites only ever take free space."""


class MaxRects:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.free = [(0, 0, w, h)]

    def grow(self, w, h):
        """Enlarge the page; everything already placed stays where it is."""
        if w > self.w:
            self.free.append((self.w, 0, w - self.w, max(h, self.h)))
        if h > self.h:
            self.free.append((0, self.h, max(w, self.w), h - self.h))
        self.w, self.h = max(w, self.w), max(h, self.h)
        self._prune()

    def occupy(self, x, y, w, h):
        """Mark a rectangle as used, splitting any free space it touches."""
        out = []
        for fx, fy, fw, fh in self.free:
            if x >= fx + fw or x + w <= fx or y >= fy + fh or y + h <= fy:
                out.append((fx, fy, fw, fh))
                continue
            if x > fx:
                out.append((fx, fy, x - fx, fh))
            if x + w < fx + fw:
                out.append((x + w, fy, fx + fw - x - w, fh))
            if y > fy:
                out.append((fx, fy, fw, y - fy))
            if y + h < fy + fh:
                out.append((fx, y + h, fw, fy + fh - y - h))
        self.free = out
        self._prune()

    def insert(self, w, h):
        """Place a w x h rectangle in the tightest free space. Returns (x, y), or None if it does not fit."""
        best = None
        for fx, fy, fw, fh in self.free:
            if w <= fw and h <= fh:
                score = (min(fw - w, fh - h), max(fw - w, fh - h), fy, fx)
                if best is None or score < best[0]:
                    best = (score, fx, fy)
        if best is None:
            return None
        self.occupy(best[1], best[2], w, h)
        return best[1], best[2]

    def _prune(self):
        free = sorted(set(self.free), key=lambda r: (-r[2] * r[3], r[1], r[0]))
        keep = []
        for r in free:
            if not any(k[0] <= r[0] and k[1] <= r[1] and k[0] + k[2] >= r[0] + r[2] and k[1] + k[3] >= r[1] + r[3]
                       for k in keep):
                keep.append(r)
        self.free = keep


def overlaps(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def next_pow2(n):
    p = 1
    while p < n:
        p *= 2
    return p


def first_page(sizes, max_size, start=64):
    """A power-of-two page, square or twice as wide as high, just large enough for the total area."""
    area = sum(w * h for w, h in sizes.values()) * 1.12
    edge = max([start] + [next_pow2(max(s)) for s in sizes.values()])
    w = h = min(edge, max_size)
    while w * h < area and (w < max_size or h < max_size):
        if w <= h and w < max_size:
            w *= 2
        else:
            h *= 2
    return w, h


def place(sizes, placed, pages, max_size=4096, start=64):
    """Place new rectangles on pages without moving old ones.

    sizes:  {name: (w, h)} still to place.
    placed: {name: (page, x, y, w, h)} already fixed.
    pages:  [(w, h)] current page sizes.
    Returns (placements, pages) with every name placed. Pages grow by doubling, then a new page is added.
    """
    pages = [tuple(p) for p in pages] or [first_page(sizes, max_size, start)]
    bins = [MaxRects(w, h) for w, h in pages]
    for page, x, y, w, h in placed.values():
        bins[page].occupy(x, y, w, h)
    out = dict(placed)
    for name in sorted(sizes, key=lambda n: (-max(sizes[n]), -sizes[n][0] * sizes[n][1], n)):
        w, h = sizes[name]
        if w > max_size or h > max_size:
            raise ValueError(f"{name} is {w}x{h}, larger than the {max_size}px page limit")
        spot = None
        for i, b in enumerate(bins):
            spot = b.insert(w, h)
            while spot is None and (b.w < max_size or b.h < max_size):
                # Grow the narrower side first so pages stay roughly square.
                if b.w <= b.h and b.w < max_size:
                    b.grow(min(max_size, b.w * 2), b.h)
                else:
                    b.grow(b.w, min(max_size, b.h * 2))
                spot = b.insert(w, h)
            if spot is not None:
                out[name] = (i, spot[0], spot[1], w, h)
                break
        if spot is None:
            side = max(start, next_pow2(max(w, h)))
            bins.append(MaxRects(side, side))
            x, y = bins[-1].insert(w, h)
            out[name] = (len(bins) - 1, x, y, w, h)
    return out, [(b.w, b.h) for b in bins]
