"""Four human factions of Mellangan, each a colour pair and a motif on banner, camp prop and soldier."""
from doteshi import mat, pat, profile, sdf, sprite

G = 0.9
KEYS = ["crownlands", "anvilmark", "sandwells", "frostmarch"]
MAIN = {"crownlands": "#2f4fa8", "anvilmark": "#4a4a54", "sandwells": "#1fa8a0", "frostmarch": "#dce8f0"}
TRIM = {"crownlands": "#f0c838", "anvilmark": "#f0701c", "sandwells": "#e8b858", "frostmarch": "#b82e32"}
SKIN = "#e0b090"
IRON = "#9aa0ac"
LEATHER = "#6a4426"


def flat(s, shape, color, z=0.3, **kw):
    return s.part(shape, mat.glowing(color, emit=0.35), profile=profile.flat(0.02), z=z, keep=True, soft=False, **kw)


def motif(s, key, x, y, k=1.0):
    c = TRIM[key]
    if key == "crownlands":
        pts = [(-0.3, 0.22), (-0.3, -0.12), (-0.15, 0.02), (0, -0.2), (0.15, 0.02), (0.3, -0.12), (0.3, 0.22)]
        flat(s, sdf.polygon([(px * k + x, py * k + y) for px, py in pts]), c)
    elif key == "anvilmark":
        pts = [(-0.34, -0.16), (0.3, -0.16), (0.3, -0.04), (0.14, 0.04), (0.14, 0.12), (0.26, 0.2), (-0.26, 0.2),
               (-0.14, 0.12), (-0.14, 0.02)]
        flat(s, sdf.polygon([(px * k + x, py * k + y) for px, py in pts]), c)
    elif key == "sandwells":
        flat(s, (sdf.circle(0.3 * k) - sdf.circle(0.16 * k)).at(x, y), c)
        flat(s, sdf.circle(0.07 * k).at(x, y), c)
    else:
        for a in (0, 1):
            flat(s, sdf.capsule((x - 0.28 * k, y - 0.2 * k), (x + 0.28 * k, y + 0.2 * k), 0.07 * k, 0.07 * k).mirror()
                 if a else sdf.capsule((x - 0.28 * k, y - 0.2 * k), (x + 0.28 * k, y + 0.2 * k), 0.07 * k, 0.07 * k), c)


def pole(s, x=0.0, top=-0.9):
    s.part(sdf.box(0.06, (G - top) / 2).at(x, (G + top) / 2), mat.matte(LEATHER), z=0.0)
    s.part(sdf.circle(0.1).at(x, top), mat.metal(IRON, rough=0.4), z=0.05)


def banner(key):
    @sprite(f"{key}_banner", sizes=[16], variants=1)
    def _banner(s, rng):
        pole(s, -0.62)
        cloth = sdf.polygon([(-0.56, -0.78), (0.85, -0.78), (0.85, 0.6), (0.14, 0.34), (-0.56, 0.6)])
        s.part(cloth, mat.matte(MAIN[key]), profile=profile.flat(0.05), z=0.1)
        flat(s, sdf.box(0.7, 0.07).at(0.14, -0.7), TRIM[key], z=0.15)
        motif(s, key, 0.14, -0.12, 1.7)
    return _banner


def camp(key):
    @sprite(f"{key}_camp", sizes=[16], variants=1)
    def _camp(s, rng):
        main, trim = MAIN[key], TRIM[key]
        if key == "crownlands":
            tent = sdf.polygon([(-0.85, G), (-0.85, 0.3), (0, -0.5), (0.85, 0.3), (0.85, G)])
            s.part(tent, mat.matte(main), z=0.0, relief=0.6).bump(pat.stripes(0.28, 0.4, axis="u", seed=3), 0.03)
            s.part(sdf.polygon([(-0.2, G), (0, 0.25), (0.2, G)]), mat.matte("#171a30"), z=0.1, keep=True)
            s.part(sdf.capsule((0, -0.5), (0, -0.92), 0.04, 0.03), mat.matte(LEATHER), z=0.05)
            flat(s, sdf.polygon([(0, -0.92), (0.4, -0.8), (0, -0.68)]), trim)
            flat(s, sdf.box(0.85, 0.06).at(0, 0.32), trim, z=0.3)
        elif key == "anvilmark":
            s.part(sdf.box(0.75, 0.16, 0.04).at(0, G - 0.16), mat.matte("#3a3a42"), z=-0.02)
            s.part(sdf.box(0.18, 0.2).at(0, G - 0.45), mat.matte("#5a4a3a"), z=0.0)
            a = sdf.polygon([(-0.7, -0.2), (0.45, -0.2), (0.7, -0.05), (0.3, 0.05), (0.2, 0.2), (0.4, 0.3), (-0.4, 0.3),
                             (-0.2, 0.2), (-0.2, 0.05), (-0.5, 0.0)])
            s.part(a.at(0, 0.0), mat.metal("#5c606c", rough=0.35), z=0.1, relief=0.8, profile=profile.bevel(0.3))
            flat(s, sdf.ellipse(0.35, 0.08).at(-0.05, -0.2), trim, z=0.5)
            for x, y in [(-0.7, G - 0.1), (0.7, G - 0.14)]:
                s.part(sdf.circle(0.1).at(x, y), mat.glowing(trim), z=0.2, keep=True)
        elif key == "sandwells":
            s.part(sdf.ellipse(0.7, 0.14).at(0, G - 0.1), mat.matte("#c49a60"), z=-0.02)
            ring = s.part(sdf.box(0.55, 0.42, 0.1).at(0, 0.38), mat.matte("#d8a868"), z=0.0, relief=0.7)
            ring.bump(pat.cracks(0.25, 2), -0.02)
            s.part(sdf.ellipse(0.46, 0.12).at(0, -0.02), mat.matte("#0f3a48"), z=0.1, keep=True)
            s.part(sdf.box(0.06, 0.55).at(-0.62, -0.3), mat.matte(LEATHER), z=0.1)
            s.part(sdf.box(0.06, 0.55).at(0.62, -0.3), mat.matte(LEATHER), z=0.1)
            cloth = sdf.polygon([(-0.8, -0.78), (0.8, -0.78), (0.92, -0.5), (0.0, -0.62), (-0.92, -0.5)])
            s.part(cloth, mat.matte(main), z=0.3, relief=0.4)
            flat(s, sdf.box(0.75, 0.05).at(0, -0.75), trim, z=0.4)
        else:
            s.part(sdf.box(0.72, 0.34).at(0, G - 0.34), mat.matte("#7a5a38"), z=0.0, relief=0.5).bump(
                pat.stripes(0.2, 0.3, axis="u", seed=3), 0.03)
            s.part(sdf.polygon([(-0.95, 0.42), (0, -0.4), (0.95, 0.42)]), mat.matte("#e4eef4"), z=0.1, relief=0.6)
            s.part(sdf.box(0.14, 0.26).at(0, G - 0.26), mat.matte("#3a1a1a"), z=0.15, keep=True)
            flat(s, sdf.box(0.9, 0.05).at(0, 0.4), trim, z=0.3)
            s.part(sdf.capsule((0, -0.38), (0, -0.62), 0.04, 0.04), mat.matte("#d8c8a0"), z=0.2)
            for sgn in (-1, 1):
                s.part(sdf.stroke([(0, -0.6), (sgn * 0.2, -0.78), (sgn * 0.34, -0.92)], [0.05, 0.04, 0.03]),
                       mat.matte("#d8c8a0"), z=0.2, limb=True)
    return _camp


def soldier(key):
    @sprite(f"{key}_soldier", sizes=[16], variants=1, living=True)
    def _soldier(s, rng):
        main, trim = MAIN[key], TRIM[key]
        robe = key == "sandwells"
        bw = 0.5 if key == "anvilmark" else 0.42
        if robe:
            s.part(sdf.polygon([(-0.5, G), (-0.42, 0.0), (0.42, 0.0), (0.5, G)]), mat.satin(main), z=0.05, relief=0.6)
            flat(s, sdf.box(0.46, 0.06).at(0, 0.28), trim, z=0.3)
        else:
            s.part(sdf.box(0.15, 0.3).at(-0.2, G - 0.3), mat.matte("#3a2a22"), z=0.0)
            s.part(sdf.box(0.15, 0.3).at(0.2, G - 0.3), mat.matte("#3a2a22"), z=0.0)
            s.part(sdf.box(bw, 0.4, 0.08).at(0, 0.22), mat.satin(main), z=0.05, relief=0.7)
            if key == "crownlands":
                flat(s, sdf.box(0.07, 0.38).at(0, 0.22), trim, z=0.3)
            elif key == "anvilmark":
                s.part(sdf.box(0.34, 0.34).at(0, 0.3), mat.matte("#5a3a22"), z=0.1, relief=0.6)
                flat(s, sdf.box(bw, 0.05).at(0, 0.0), trim, z=0.3)
            else:
                flat(s, sdf.box(bw, 0.06).at(0, 0.5), trim, z=0.3)
        s.part(sdf.capsule((-0.52, -0.02), (-0.56, 0.42), 0.12, 0.1), mat.satin(main), z=0.04, limb=True)
        s.part(sdf.capsule((0.52, -0.02), (0.56, 0.42), 0.12, 0.1), mat.satin(main), z=0.04, limb=True)
        s.part(sdf.circle(0.09).at(0.56, 0.45), mat.matte(SKIN), z=0.06, limb=True)
        s.part(sdf.circle(0.09).at(-0.56, 0.45), mat.matte(SKIN), z=0.06, limb=True)
        head = sdf.ellipse(0.34, 0.34).at(0.03, -0.4)
        s.part(head, mat.matte(SKIN), z=0.1, relief=0.9)
        eye = mat.matte("#1b1420")
        if key == "crownlands":
            s.part(sdf.ellipse(0.4, 0.4).at(0.03, -0.46).above(-0.38) , mat.metal(IRON, rough=0.35), z=0.2, relief=0.9)
            flat(s, sdf.box(0.36, 0.05).at(0.1, -0.38), "#1b1420", z=0.4)
            s.part(sdf.capsule((0.0, -0.9), (-0.36, -0.55), 0.06, 0.05), mat.matte(trim), z=0.15, limb=True)
            s.part(sdf.box(0.04, 0.9).at(0.76, -0.1), mat.matte(LEATHER), z=0.0, limb=True)
            flat(s, sdf.polygon([(0.76, -1.0), (0.86, -0.78), (0.66, -0.78)]), IRON, z=0.2, limb=True)
        elif key == "anvilmark":
            s.part(sdf.ellipse(0.42, 0.34).at(0.03, -0.5).above(-0.34), mat.metal("#52565f", rough=0.4), z=0.2, relief=0.9)
            s.part(sdf.box(0.36, 0.1).at(0.1, -0.32), mat.matte("#1b1420"), z=0.25, keep=True)
            flat(s, sdf.box(0.2, 0.04).at(0.14, -0.32), trim, z=0.5)
            s.part(sdf.capsule((0.62, -0.7), (0.62, 0.0), 0.06, 0.06), mat.matte(LEATHER), z=0.0, limb=True)
            s.part(sdf.box(0.24, 0.14).at(0.62, -0.78), mat.metal("#6a6e7a", rough=0.35), z=0.1, limb=True)
        elif key == "sandwells":
            s.part(sdf.ellipse(0.42, 0.42).at(0.03, -0.42).above(-0.24), mat.matte(main), z=0.2, relief=0.9)
            s.part(sdf.ellipse(0.36, 0.18).at(0.0, -0.18), mat.matte(main), z=0.2)
            s.part(sdf.box(0.3, 0.07).at(0.12, -0.42), mat.matte(SKIN), z=0.22)
            flat(s, sdf.box(0.4, 0.05).at(0.03, -0.62), trim, z=0.4)
            s.part(sdf.stroke([(0.62, -0.5), (0.8, -0.1), (0.62, 0.3)], [0.05, 0.05, 0.04]), mat.metal(IRON, rough=0.3),
                   z=0.0, limb=True)
        else:
            s.part(sdf.ellipse(0.46, 0.42).at(0.03, -0.42).above(-0.2), mat.matte("#e8f0f6"), z=0.2, relief=0.9)
            s.part(sdf.ellipse(0.3, 0.26).at(0.12, -0.38), mat.matte(SKIN), z=0.24)
            s.part(sdf.box(0.46, 0.09).at(0.0, -0.1), mat.matte(trim), z=0.3, keep=True)
            s.part(sdf.circle(0.34).at(-0.7, 0.2), mat.matte("#7a5a38"), z=0.3, relief=0.6, limb=True)
            flat(s, sdf.circle(0.14).at(-0.7, 0.2), trim, z=0.5, limb=True)
        for ex in (0.07, 0.25):
            if key in ("crownlands", "anvilmark"):
                continue
            s.part(sdf.circle(0.04).at(ex, -0.3 if not robe else -0.4), eye, z=0.9, keep=True)
    return _soldier


for _k in KEYS:
    banner(_k)
    camp(_k)
    soldier(_k)
