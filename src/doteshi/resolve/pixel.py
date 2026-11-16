"""The pixel resolver: hard edges, a small palette of hue-shifted tones, a one-pixel outline.

It works from a surface buffer several samples finer than the output, and decides each pixel as a whole:
  1. Coverage. A pixel is solid when half of it is covered. Features under a pixel wide (legs, feelers, stems)
     would vanish under that rule, so they are found separately and given a one-pixel line along their ridge.
  2. Ownership. Each pixel belongs to the part covering most of it; colour and light are taken from that part's
     samples only, so neighbours never smear into each other.
  3. Colour. Base colours are grouped into a few families. Each family gets a ramp of tones; a pixel takes the
     tone whose lightness is nearest its lit colour. Rare and near-duplicate colours are merged away.
  4. Cleanup. Stray single pixels are absorbed into their surroundings; key features are left alone.
  5. Outline.
"""
import numpy as np
from PIL import Image

from ..core.color import (lab_of, linear_to_oklab, linear_to_srgb, oklab_to_linear, srgb_to_linear, tone)
from ..core.mathx import shift, spread
from ..shade.light import shade

BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16.0
N4 = ((0, 1), (0, -1), (1, 0), (-1, 0))
MARGIN = 0.04


def _blocks(a, h, w, ss):
    """Group samples by output pixel: (h*ss, w*ss[, c]) -> (h, w, ss*ss[, c])."""
    if a.ndim == 2:
        return a.reshape(h, ss, w, ss).transpose(0, 2, 1, 3).reshape(h, w, ss * ss)
    return a.reshape(h, ss, w, ss, -1).transpose(0, 2, 1, 3, 4).reshape(h, w, ss * ss, a.shape[-1])


def _around(a, fill=0.0):
    p = np.pad(a, 1, constant_values=fill)
    return p[1:-1, :-2], p[1:-1, 2:], p[:-2, 1:-1], p[2:, 1:-1]     # left, right, up, down


def _thin_lines(ct, solid, least):
    """Pixels that carry a feature under a pixel wide: one pixel along its ridge, never two side by side."""
    l, r, u, d = _around(ct)
    ridge_x = (ct >= l - MARGIN) & (ct > r + MARGIN) & (np.maximum(u, d) <= ct + MARGIN)
    ridge_y = (ct >= u - MARGIN) & (ct > d + MARGIN) & (np.maximum(l, r) <= ct + MARGIN)
    # A line lying on a pixel seam is split between two pixels, so its width is judged across the ridge.
    wide_x, wide_y = ct + np.maximum(l, r) >= least, ct + np.maximum(u, d) >= least
    thin = ~solid & (ct > 0.02) & ((ridge_x & wide_x) | (ridge_y & wide_y))
    # Take the corner pixel out of every L, so slanted lines step cleanly.
    full = solid | thin
    h, w = thin.shape
    at = lambda y, x: 0 <= y < h and 0 <= x < w and full[y, x]
    for y, x in zip(*np.nonzero(thin)):
        for dy, dx in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            if at(y + dy, x) and at(y, x + dx) and not at(y - dy, x) and not at(y, x - dx):
                thin[y, x] = full[y, x] = False
                break
    return thin


def _families(P, k, min_dist):
    """Group colours (n, 3 in OKLab) into at most k families at least min_dist apart. Returns centres, labels."""
    first = int(np.argmin(((P - P.mean(axis=0)) ** 2).sum(axis=1)))
    centres = [P[first]]
    near = np.sqrt(((P - centres[0]) ** 2).sum(axis=1))
    while len(centres) < k:
        far = int(np.argmax(near))
        if near[far] < min_dist:
            break
        centres.append(P[far])
        near = np.minimum(near, np.sqrt(((P - P[far]) ** 2).sum(axis=1)))
    C = np.array(centres)
    for _ in range(6):
        labels = np.argmin(((P[:, None, :] - C[None]) ** 2).sum(axis=2), axis=1)
        for i in range(len(C)):
            if (labels == i).any():
                C[i] = P[labels == i].mean(axis=0)
    return C, np.argmin(((P[:, None, :] - C[None]) ** 2).sum(axis=2), axis=1)


def _to_rgb8(lab):
    return np.round(linear_to_srgb(np.clip(oklab_to_linear(lab), 0.0, 1.0)) * 255.0).astype(np.uint8)


def _to_lab(rgb8):
    return linear_to_oklab(srgb_to_linear(np.asarray(rgb8, np.float64) / 255.0))


def _snap(rgb8, palette, within=0.035):
    """Move colours onto a reference palette where one is close."""
    ref = np.array(palette, np.uint8)
    dist = np.sqrt(((_to_lab(rgb8)[:, None, :] - _to_lab(ref)[None]) ** 2).sum(axis=2))
    near = dist.argmin(axis=1)
    hit = dist.min(axis=1) < within
    out = rgb8.copy()
    out[hit] = ref[near[hit]]
    return out


def _reduce(index, lab, cap, protect, tidy=0.0015):
    """Merge colours until at most `cap` remain, always making the merge that changes the picture least."""
    locked = set(index[protect].tolist())
    while True:
        used, counts = np.unique(index[index >= 0], return_counts=True)
        if len(used) < 2:
            return
        D = np.sqrt(((lab[used][:, None, :] - lab[used][None]) ** 2).sum(axis=2))
        np.fill_diagonal(D, np.inf)
        cost = counts * D.min(axis=1) ** 2
        cost[[u in locked for u in used]] = np.inf
        i = int(np.argmin(cost))
        if not np.isfinite(cost[i]) or (len(used) <= cap and cost[i] > tidy):
            return
        index[index == used[i]] = used[int(np.argmin(D[i]))]


def _absorb_strays(index, lab, protect, passes=2):
    """A lone pixel that differs only slightly from what surrounds it is noise; give it its neighbours' colour.
    Lone pixels that differ strongly (a spot, a glint, an eye) are detail and stay."""
    h, w = index.shape
    for _ in range(passes):
        src = index.copy()
        changed = False
        for y, x in zip(*np.nonzero((src >= 0) & ~protect)):
            i = src[y, x]
            nb = [src[y + dy, x + dx] for dy, dx in N4
                  if 0 <= y + dy < h and 0 <= x + dx < w and src[y + dy, x + dx] >= 0]
            if len(nb) < 3 or i in nb:
                continue
            top = max(set(nb), key=lambda q: (nb.count(q), -q))
            if nb.count(top) < 3 or np.sqrt(((lab[i] - lab[top]) ** 2).sum()) >= 0.13:
                continue
            if sum(src[y + dy, x + dx] == i for dy, dx in ((1, 1), (1, -1), (-1, 1), (-1, -1))
                   if 0 <= y + dy < h and 0 <= x + dx < w) >= 2:
                continue
            index[y, x] = top
            changed = True
        if not changed:
            break


def resolve(gb, style, env=None):
    """Light a surface buffer and resolve it to hard pixels. The image is larger than the buffer by the
    style's outline margin on every side."""
    rgb, _, _ = shade(gb, env)
    h, w, ss = gb.h, gb.w, gb.ss

    # 1. Coverage, and features under a pixel wide.
    Ab = _blocks(gb.A, h, w, ss)
    cov = Ab.mean(axis=-1)
    covered = gb.A > 0.5
    r = max(1, ss // 2)
    slender = covered & ~spread(spread(covered, r, False), r, True)
    solid = cov >= style.threshold
    fine = _blocks(slender.astype(np.float64), h, w, ss).mean(axis=-1)
    thin = _thin_lines(fine, solid, style.thin)
    solid |= thin
    # At the smallest sizes, anything slender is drawn as a flat line with no outline: outlined, a one-pixel
    # leg would become three pixels wide and a six-legged creature a blot.
    wiry = thin | (solid & (fine >= 0.5 * cov))
    lines = wiry if style.ink_lines else np.zeros((h, w), bool)

    # 2. Ownership: the part covering most of each pixel, and that part's own colour and light.
    pidb = _blocks(gb.pid, h, w, ss)
    owner = np.zeros((h, w), np.int64)
    best = np.zeros((h, w))
    for p in np.unique(gb.pid):
        if p:
            score = (Ab * (pidb == p)).sum(axis=-1)
            win = score > best
            owner[win], best[win] = p, score[win]
    wt = np.where((best > 0)[..., None], Ab * (pidb == owner[..., None]), Ab)
    # Where a marking crosses a pixel, take the commoner of the two colours, not a blend of both.
    labb = _blocks(gb.lab, h, w, ss)
    mean_l = (labb[..., 0] * wt).sum(axis=-1) / np.maximum(wt.sum(axis=-1), 1e-9)
    lighter = wt * (labb[..., 0] > mean_l[..., None])
    darker = wt - lighter
    split = np.abs(labb[..., 0] - mean_l[..., None]).max(axis=-1) > 0.06
    wt = np.where(split[..., None], np.where((lighter.sum(axis=-1) >= darker.sum(axis=-1))[..., None],
                                              lighter, darker), wt)
    ws = np.maximum(wt.sum(axis=-1), 1e-9)[..., None]
    base = (labb * wt[..., None]).sum(axis=2) / ws
    rgbb = _blocks(rgb, h, w, ss)
    lit = (rgbb * wt[..., None]).sum(axis=2) / ws
    height = (_blocks(gb.H, h, w, ss) * wt).sum(axis=-1) / ws[..., 0]
    # A highlight smaller than a pixel would average away; remember how far the brightest samples stand out.
    lum = rgbb @ np.array([0.2126, 0.7152, 0.0722])
    peak = np.where(wt > 0, lum, 0.0)
    peak = np.sort(peak, axis=-1)[..., -max(2, ss * ss // 10):].mean(axis=-1)
    spark = np.clip(np.cbrt(np.clip(peak, 0, 1)) - np.cbrt(np.clip(lit @ np.array([0.2126, 0.7152, 0.0722]), 0, 1))
                    - 0.08, 0.0, 0.5)

    # Key features land on the pixel under their centre, whatever their size.
    keep = np.zeros((h, w), bool)
    for pid, cx, cy, lab in gb.keeps:
        col, row = int((cx - gb.x0) // gb.px), int((cy - gb.y0) // gb.px)
        if 0 <= row < h and 0 <= col < w:
            own = gb.pid == pid
            solid[row, col] = keep[row, col] = True
            owner[row, col] = pid
            base[row, col] = lab
            lit[row, col] = rgb[own].mean(axis=0) if own.any() else np.maximum(oklab_to_linear(lab), 0.0)

    # Tidy the silhouette: no lone pixels, no pinholes.
    l, r_, u, d = _around(solid, False)
    p = np.pad(solid, 1)
    diag = p[:-2, :-2] | p[:-2, 2:] | p[2:, :-2] | p[2:, 2:]
    solid &= l | r_ | u | d | diag | keep
    hole = ~solid & l & r_ & u & d
    for y, x in zip(*np.nonzero(hole)):
        if cov[y, x] < 0.05:
            base[y, x], lit[y, x], owner[y, x] = base[y - 1, x], lit[y - 1, x], owner[y - 1, x]
    solid |= hole
    # One-pixel notches in the silhouette are filled, one-pixel burrs shaved off: edges step evenly.
    l, r_, u, d = _around(solid, False)
    count = l.astype(int) + r_ + u + d
    notch = ~solid & (count >= 3) & (cov > 0.2)
    for y, x in zip(*np.nonzero(notch)):
        yy, xx = (y - 1, x) if y > 0 and solid[y - 1, x] else (y, x - 1) if x > 0 and solid[y, x - 1] else (y + 1, x)
        base[y, x], lit[y, x], owner[y, x], height[y, x] = base[yy, xx], lit[yy, xx], owner[yy, xx], height[yy, xx]
    solid |= notch
    solid &= ~((count <= 1) & (cov < 0.75) & ~wiry & ~keep)
    if not solid.any():
        m = style.inset
        return Image.new("RGBA", (w + 2 * m, h + 2 * m), (0, 0, 0, 0))

    # 3. Colour: families of base colour, a ramp of tones for each, the nearest tone by lightness.
    centres, labels = _families(base[solid], style.bases, style.min_dist)
    levels = np.array(style.levels, np.float64)
    T = len(levels)
    ramp = _to_rgb8(tone(np.repeat(centres, T, axis=0), np.tile(levels, len(centres))))
    if style.snap:
        ramp = _snap(ramp, style.snap)
    ramp_lab = _to_lab(ramp)
    light = linear_to_oklab(np.maximum(lit[solid], 0.0))[:, 0] + style.lift + style.glint * spark[solid]
    if style.dither:
        ys, xs = np.nonzero(solid)
        light = light + style.dither * 0.1 * (BAYER[ys % 4, xs % 4] - 0.5)
    mid = centres[labels, 0]
    light = mid + (light - mid) * style.contrast
    pick = np.argmin(np.abs(ramp_lab[:, 0].reshape(len(centres), T)[labels] - light[:, None]), axis=1)
    pick[(lines | keep)[solid]] = int(np.argmin(np.abs(levels)))   # lines and key features: base colour, unlit
    family = np.full((h, w), -1, np.int64)
    family[solid] = labels
    tones = np.zeros((h, w), np.int64)
    tones[solid] = pick
    if style.contour:
        # Where one form passes behind another of the same colour, a darker line keeps them apart.
        crease = np.zeros((h, w), bool)
        gap = style.contour_gap * gb.px
        for dy, dx in N4:
            other = shift(owner, dx, dy, 0)
            crease |= (solid & shift(solid, dx, dy, False) & (other != owner) & (shift(family, dx, dy, -1) == family)
                       & (shift(height, dx, dy, 0.0) - height > gap))
        crease &= ~lines & ~keep
        tones[crease] = np.maximum(tones[crease] - style.contour, 0)
    index = np.full((h, w), -1, np.int64)
    index[solid] = family[solid] * T + tones[solid]

    # 4. Cleanup.
    _reduce(index, ramp_lab, style.colors, keep)
    _absorb_strays(index, ramp_lab, keep)

    # 5. Compose, with the outline in the margin.
    m = style.inset
    out = np.zeros((h + 2 * m, w + 2 * m, 4), np.uint8)
    inner = out[m:h + m, m:w + m]
    inner[solid, :3] = ramp[index[solid]]
    inner[solid, 3] = 255
    if style.outline != "none":
        hard = np.pad(solid & ~lines & ~np.isin(owner, list(gb.soft)), m)
        fam = np.pad(family, m, constant_values=-1)
        edge = np.zeros(hard.shape, bool)
        src = np.full(hard.shape, -1, np.int64)
        for dy, dx in ((1, 0), (0, 1), (-1, 0), (0, -1)):       # the surface below wins, then right, up, left
            moved = shift(hard, dx, dy, False) & (out[..., 3] == 0)
            src = np.where(moved & ~edge, shift(fam, dx, dy, -1), src)
            edge |= moved
        if style.outline == "flat":
            out[edge, :3] = style.outline_color
        else:
            ink = _to_rgb8(tone(centres, np.full(len(centres), -3.4), sat=1.1))
            out[edge, :3] = ink[src[edge]]
        out[edge, 3] = 255
    return Image.fromarray(out, "RGBA")


def pixelmap(rows, palette, outline=None):
    """A hand-drawn sprite from rows of characters: '.' is empty, every other character is a palette entry.
    With an outline colour, empty pixels beside drawn ones are filled with it."""
    h, w = len(rows), len(rows[0])
    out = np.zeros((h, w, 4), np.uint8)
    for y, row in enumerate(rows):
        if len(row) != w:
            raise ValueError(f"row {y} is {len(row)} wide, the first row is {w}")
        for x, ch in enumerate(row):
            if ch != ".":
                out[y, x] = (*palette[ch][:3], 255)
    if outline is not None:
        drawn = out[..., 3] > 0
        l, r, u, d = _around(drawn, False)
        edge = ~drawn & (l | r | u | d)
        out[edge] = (*outline, 255)
    return Image.fromarray(out, "RGBA")
