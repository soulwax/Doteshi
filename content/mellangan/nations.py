"""Mellangan's four nations, two soldiers each, three poses each (idle, step, attack): the Crownlands (a human
crown in violet and gold), Anvilmark (dwarves of the mountain holds, iron and forge orange), the Sandwells (desert
water-lords in teal and sand) and Silverbough (elves of the moon woods, silver and pale green). Bodies differ per
people so a group reads at a glance: dwarves short and broad with beards to the belt, elves tall and narrow with
pointed ears, humans in between."""
from doteshi import mat, pat, profile, sdf, sprite

G = 0.9
POSES = ("idle", "step", "attack")
SKIN = {"human": "#e6b48c", "dwarf": "#d89a70", "desert": "#b07850", "elf": "#f2dcc8"}
IRON, STEEL, GOLD, LEATHER, DARK = "#8a909c", "#b8c0cc", "#e8b830", "#6a4426", "#2a2230"
EYE = "#1b1420"
BODY = {
    "human": dict(hy=-0.36, head=(0.4, 0.34), torso=(0.34, 0.3), ty=0.3, leg=0.16, foot=0.72, arm=0.4),
    "dwarf": dict(hy=-0.14, head=(0.44, 0.34), torso=(0.48, 0.28), ty=0.42, leg=0.1, foot=0.78, arm=0.52),
    "elf": dict(hy=-0.5, head=(0.34, 0.32), torso=(0.26, 0.36), ty=0.24, leg=0.2, foot=0.7, arm=0.32),
}


def flat(s, shape, colour, z=0.3, **kw):
    return s.part(shape, mat.matte(colour, rough=0.6), profile=profile.flat(0.03), z=z, keep=True, **kw)


def figure(s, people, pose, outfit, trim, skin=None, legs=DARK):
    b = BODY[people]
    bob = -0.04 if pose == "step" else 0.0
    lean = 0.06 if pose == "attack" else 0.0
    stride = 0.13 if pose == "step" else 0.0
    for side, dz in ((-1, -stride), (1, stride)):
        x = side * 0.17
        s.part(sdf.box(0.1, b["leg"], 0.03).at(x, b["foot"] - b["leg"] + dz * 0.4), mat.matte(legs), z=0.0)
        s.part(sdf.box(0.13, 0.08, 0.04).at(x + 0.03, b["foot"] + 0.06 + dz * 0.3), mat.matte("#3a2a22"), z=0.01)
    tw, th = b["torso"]
    torso = s.part(sdf.box(tw, th, 0.1).at(lean, b["ty"] + bob), mat.matte(outfit, rough=0.85), relief=0.6, z=0.04)
    torso.tint("#000000", pat.gradient("y", b["ty"], b["ty"] + th), 0.35)
    flat(s, sdf.box(tw, 0.05).at(lean, b["ty"] + th * 0.55 + bob), trim, z=0.2)
    hw, hh = b["head"]
    head = s.part(sdf.box(hw, hh, 0.18).at(lean, b["hy"] + bob), mat.satin(skin or SKIN[people], rough=0.3, spec=0.1),
                  relief=0.42, z=0.1)
    return dict(b=b, bob=bob, lean=lean, head=head, hx=lean, hy=b["hy"] + bob, hw=hw, hh=hh, tw=tw,
                ty=b["ty"] + bob)


def eyes(s, f, gap=0.17, y=0.04, colour=EYE):
    for side in (-1, 1):
        s.part(sdf.ellipse(0.055, 0.075).at(f["hx"] + 0.07 + side * gap, f["hy"] + y),
               mat.glossy(colour, rough=0.15, spec=0.9), height=0.01, on=f["head"], keep=True)


def hands(s, f, colour, front=(0.5, 0.5), back=(-0.5, 0.5)):
    for (x, y) in (front, back):
        s.part(sdf.circle(0.09).at(x, y + f["bob"]), mat.satin(colour, rough=0.3), z=0.5, limb=True)


def arm(s, f, a, b, cloth):
    s.part(sdf.capsule((a[0], a[1] + f["bob"]), (b[0], b[1] + f["bob"]), 0.1, 0.09), mat.matte(cloth), z=0.45,
           limb=True)


def blade(s, a, b, colour=STEEL, w=0.05):
    s.part(sdf.capsule(a, b, w, w * 0.6), mat.metal(colour, rough=0.25), z=0.6, limb=True)


def crown_knight(s, pose):
    f = figure(s, "human", pose, "#7854c4", GOLD)
    s.part(sdf.box(0.36, 0.1, 0.05).at(f["lean"], f["ty"] - 0.2), mat.metal(STEEL, rough=0.35), z=0.15)
    helm = sdf.box(0.44, 0.4, 0.2).at(f["hx"], f["hy"] - 0.04)
    s.part(helm - sdf.box(0.3, 0.05).at(f["hx"] + 0.07, f["hy"] + 0.02), mat.metal("#7c8494", rough=0.4), relief=0.3,
           z=0.16)
    s.part(sdf.polygon([(f["hx"] - 0.38, f["hy"] - 0.38), (f["hx"] - 0.4, f["hy"] - 0.66), (f["hx"] - 0.18, f["hy"] - 0.5),
                        (f["hx"], f["hy"] - 0.72), (f["hx"] + 0.18, f["hy"] - 0.5), (f["hx"] + 0.4, f["hy"] - 0.66),
                        (f["hx"] + 0.38, f["hy"] - 0.38)]).grow(0.04), mat.metal(GOLD, rough=0.3), relief=0.2, z=0.3)
    shield = sdf.polygon([(-0.86, 0.0), (-0.38, 0.0), (-0.42, 0.42), (-0.62, 0.66), (-0.82, 0.42)])
    s.part(shield.at(0, f["bob"]), mat.matte("#5a3aa0"), relief=0.5, z=0.55, limb=True)
    flat(s, sdf.box(0.04, 0.24).at(-0.62, 0.26 + f["bob"]), GOLD, z=0.7)
    flat(s, sdf.box(0.14, 0.04).at(-0.62, 0.16 + f["bob"]), GOLD, z=0.7)
    if pose == "attack":
        arm(s, f, (0.36, 0.1), (0.62, -0.12), STEEL)
        blade(s, (0.66, -0.16), (0.98, -0.76))
        hands(s, f, STEEL, (0.66, -0.14), (-0.5, 0.5))
    else:
        arm(s, f, (0.36, 0.1), (0.5, 0.42), STEEL)
        blade(s, (0.56, 0.4), (0.72, -0.5))
        hands(s, f, STEEL, (0.54, 0.46), (-0.5, 0.5))


def crown_arbalist(s, pose):
    f = figure(s, "human", pose, "#6a48b0", GOLD, legs="#3a2a4a")
    eyes(s, f)
    brim = sdf.ellipse(0.62, 0.1).at(f["hx"], f["hy"] - 0.2)
    s.part(sdf.ellipse(0.42, 0.3).at(f["hx"], f["hy"] - 0.26).above(f["hy"] - 0.2) | brim, mat.metal(STEEL, rough=0.4),
           relief=0.3, z=0.2)
    flat(s, sdf.box(0.4, 0.04).at(f["hx"], f["hy"] - 0.26), GOLD, z=0.35)
    y = 0.2 if pose != "attack" else 0.08
    s.part(sdf.box(0.36, 0.05).at(0.3, y + f["bob"]), mat.matte(LEATHER), z=0.6, limb=True)
    s.part(sdf.stroke([(0.58, y - 0.3 + f["bob"]), (0.7, y + f["bob"]), (0.58, y + 0.3 + f["bob"])], [0.04, 0.05, 0.04]),
           mat.metal(IRON, rough=0.3), z=0.62, limb=True)
    if pose == "attack":
        flat(s, sdf.box(0.18, 0.025).at(0.9, y + f["bob"]), "#f0e8d0", z=0.7, limb=True)
    hands(s, f, SKIN["human"], (0.1, y + 0.06), (0.46, y + 0.06))


def hammerdwarf(s, pose):
    f = figure(s, "dwarf", pose, "#8a5a34", "#d66828", legs="#3a3a42")
    s.part(sdf.box(0.52, 0.12, 0.05).at(f["lean"], f["ty"] - 0.22), mat.metal(IRON, rough=0.4), z=0.15)
    helm = sdf.ellipse(0.48, 0.36).at(f["hx"], f["hy"] - 0.12).above(f["hy"] - 0.04)
    s.part(helm, mat.metal("#6a6e7a", rough=0.35), relief=0.4, z=0.2)
    s.part(sdf.box(0.05, 0.16).at(f["hx"] + 0.07, f["hy"] + 0.04), mat.metal("#6a6e7a"), z=0.25)
    eyes(s, f, 0.19, 0.0)
    beard = sdf.polygon([(f["hx"] - 0.4, f["hy"] + 0.1), (f["hx"] + 0.46, f["hy"] + 0.1), (f["hx"] + 0.3, f["hy"] + 0.62),
                         (f["hx"] + 0.07, f["hy"] + 0.78), (f["hx"] - 0.18, f["hy"] + 0.62)])
    s.part(beard, mat.matte("#c8501c", rough=0.6), relief=0.5, z=0.3).bump(pat.grain(0.05, 7, stretch=6, axis="v"),
                                                                           0.02)
    if pose == "attack":
        arm(s, f, (0.4, f["ty"] - 0.1), (0.64, -0.3), "#8a5a34")
        s.part(sdf.capsule((0.66, -0.3), (0.4, 0.5), 0.05, 0.05), mat.matte(LEATHER), z=0.55, limb=True)
        s.part(sdf.box(0.24, 0.15, 0.04).at(0.7, -0.42).rot(-30, 0.7, -0.42), mat.metal("#5c606c", rough=0.3),
               relief=0.6, z=0.65, limb=True)
        hands(s, f, SKIN["dwarf"], (0.64, -0.26), (-0.56, f["ty"] + 0.1))
    else:
        arm(s, f, (0.44, f["ty"] - 0.1), (0.58, f["ty"] + 0.12), "#8a5a34")
        s.part(sdf.capsule((0.62, 0.86), (0.62, -0.3), 0.05, 0.05), mat.matte(LEATHER), z=0.55, limb=True)
        s.part(sdf.box(0.26, 0.16, 0.04).at(0.62, -0.38), mat.metal("#5c606c", rough=0.3), relief=0.6, z=0.65,
               limb=True)
        hands(s, f, SKIN["dwarf"], (0.62, f["ty"] + 0.14), (-0.56, f["ty"] + 0.1))


def runesmith(s, pose):
    f = figure(s, "dwarf", pose, "#5a3a24", "#f08020", legs="#3a3a42")
    flat(s, sdf.box(0.3, 0.26).at(f["lean"], f["ty"] + 0.04), "#4a2e1c", z=0.12)
    s.part(sdf.ellipse(0.48, 0.24).at(f["hx"], f["hy"] - 0.22).above(f["hy"] - 0.12), mat.matte("#3a2a22"), relief=0.3,
           z=0.2)
    eyes(s, f, 0.19, 0.0)
    beard = sdf.polygon([(f["hx"] - 0.4, f["hy"] + 0.1), (f["hx"] + 0.46, f["hy"] + 0.1), (f["hx"] + 0.24, f["hy"] + 0.7),
                         (f["hx"] + 0.07, f["hy"] + 0.84), (f["hx"] - 0.12, f["hy"] + 0.7)])
    s.part(beard, mat.matte("#e8e2d4", rough=0.6), relief=0.5, z=0.3).bump(pat.grain(0.05, 9, stretch=6, axis="v"), 0.02)
    top = (0.7, -0.62) if pose == "attack" else (0.62, -0.5)
    s.part(sdf.capsule((0.6, 0.86), top, 0.04, 0.04), mat.matte(LEATHER), z=0.5, limb=True)
    glow = 0.6 if pose == "attack" else 0.35
    s.part(sdf.circle(0.16 if pose == "attack" else 0.13).at(*top), mat.glowing("#ffa030", emit=glow), z=0.7,
           keep=True, limb=True)
    hands(s, f, SKIN["dwarf"], (0.62, f["ty"]), (-0.56, f["ty"] + 0.1))


def wellspear(s, pose):
    f = figure(s, "human", pose, "#28aaa0", "#e8c070", skin=SKIN["desert"], legs="#c8a068")
    s.part(sdf.polygon([(-0.4, G - 0.1), (-0.34, 0.12), (0.34, 0.12), (0.4, G - 0.1)]).at(f["lean"], f["bob"]),
           mat.matte("#28aaa0", rough=0.8), relief=0.5, z=0.06)
    wrap = sdf.box(0.46, 0.42, 0.22).at(f["hx"], f["hy"] - 0.04) - sdf.box(0.32, 0.06).at(f["hx"] + 0.07, f["hy"] - 0.02)
    s.part(wrap, mat.matte("#c89858", rough=0.8), relief=0.3, z=0.2)
    flat(s, sdf.box(0.46, 0.06).at(f["hx"], f["hy"] - 0.3), "#28aaa0", z=0.35)
    s.part(sdf.ellipse(0.04, 0.05).at(f["hx"] - 0.08, f["hy"] - 0.02), mat.glossy(EYE), z=0.3, keep=True)
    s.part(sdf.ellipse(0.04, 0.05).at(f["hx"] + 0.22, f["hy"] - 0.02), mat.glossy(EYE), z=0.3, keep=True)
    tip = (0.92, -0.62) if pose == "attack" else (0.62, -0.92)
    base = (0.2, 0.5) if pose == "attack" else (0.62, 0.86)
    s.part(sdf.capsule(base, tip, 0.035, 0.035), mat.matte(LEATHER), z=0.5, limb=True)
    s.part(sdf.circle(0.07).at(*tip), mat.metal(STEEL, rough=0.2), z=0.6, limb=True)
    hands(s, f, SKIN["desert"], (0.58 if pose != "attack" else 0.5, 0.2 + (0 if pose != "attack" else -0.06)),
          (-0.46, 0.46))


def sandveil(s, pose):
    f = figure(s, "human", pose, "#1a6a68", "#e8c070", skin=SKIN["desert"], legs="#1a4a48")
    wrap = sdf.box(0.46, 0.42, 0.22).at(f["hx"], f["hy"] - 0.04) - sdf.box(0.32, 0.06).at(f["hx"] + 0.07, f["hy"] - 0.02)
    s.part(wrap, mat.matte("#1a5a58", rough=0.8), relief=0.3, z=0.2)
    s.part(sdf.ellipse(0.04, 0.05).at(f["hx"] - 0.08, f["hy"] - 0.02), mat.glowing("#f0d070", emit=0.4), z=0.3,
           keep=True)
    s.part(sdf.ellipse(0.04, 0.05).at(f["hx"] + 0.22, f["hy"] - 0.02), mat.glowing("#f0d070", emit=0.4), z=0.3,
           keep=True)
    s.part(sdf.stroke([(-0.3, f["hy"] + 0.3), (-0.6, f["hy"] + 0.5), (-0.8, f["hy"] + 0.8)], [0.08, 0.06, 0.04]),
           mat.matte("#e8c070"), z=0.05, limb=True)
    if pose == "attack":
        blade(s, (0.5, 0.2), (0.96, -0.1), "#d8dce4", 0.045)
        blade(s, (-0.5, 0.2), (-0.9, -0.24), "#d8dce4", 0.045)
        hands(s, f, SKIN["desert"], (0.5, 0.22), (-0.5, 0.22))
    else:
        blade(s, (0.5, 0.46), (0.72, 0.86), "#d8dce4", 0.045)
        blade(s, (-0.5, 0.46), (-0.72, 0.86), "#d8dce4", 0.045)
        hands(s, f, SKIN["desert"], (0.5, 0.46), (-0.5, 0.46))


def elf_head(s, f, hair, hood=None):
    for side in (-1, 1):
        x = f["hx"] + side * f["hw"]
        s.part(sdf.polygon([(x, f["hy"] - 0.08), (x + side * 0.3, f["hy"] - 0.26), (x, f["hy"] + 0.08)]),
               mat.satin(SKIN["elf"], rough=0.3), relief=0.3, z=0.08)
    eyes(s, f, 0.15, 0.04, "#2a6a5a")
    if hood:
        h = sdf.box(0.42, 0.44, 0.24).at(f["hx"], f["hy"] - 0.06) - sdf.box(0.28, 0.24, 0.12).at(f["hx"] + 0.06,
                                                                                                  f["hy"] + 0.08)
        s.part(h, mat.matte(hood, rough=0.7), relief=0.3, z=0.2)
    else:
        s.part(sdf.box(0.38, 0.38, 0.2).at(f["hx"], f["hy"] - 0.08).above(f["hy"] - 0.16), mat.matte(hair, rough=0.4),
               relief=0.25, z=0.2)
        s.pair(sdf.box(0.07, 0.36, 0.04).at(0.36, f["hy"] + 0.2), mat.matte(hair, rough=0.4), z=0.12, asym=0)


def moonbow(s, pose):
    f = figure(s, "elf", pose, "#3a7a58", "#c8dce4", legs="#2a4a3a")
    s.part(sdf.polygon([(-0.36, 0.86), (-0.3, f["ty"] - 0.3), (0.3, f["ty"] - 0.3), (0.36, 0.86)]).at(0, f["bob"]),
           mat.matte("#7aa8bc", rough=0.7), relief=0.4, z=0.02)
    elf_head(s, f, "#e8eef0", hood="#a8c8d8")
    draw = 0.12 if pose == "attack" else 0.0
    s.part(sdf.stroke([(0.56, -0.6 + f["bob"]), (0.76 + draw, -0.1 + f["bob"]), (0.76 + draw, 0.3 + f["bob"]),
                       (0.56, 0.78 + f["bob"])], [0.03, 0.045, 0.045, 0.03]), mat.metal("#c8a050", rough=0.3), z=0.6,
           limb=True)
    s.part(sdf.capsule((0.56, -0.6 + f["bob"]), (0.56 - draw * 3, 0.1 + f["bob"]), 0.012) |
           sdf.capsule((0.56 - draw * 3, 0.1 + f["bob"]), (0.56, 0.78 + f["bob"]), 0.012), mat.matte("#f0f0e8"), z=0.55,
           limb=True)
    if pose == "attack":
        flat(s, sdf.box(0.3, 0.02).at(0.62, 0.1 + f["bob"]), "#f0f0e8", z=0.7, limb=True)
    hands(s, f, SKIN["elf"], (0.76 + draw, 0.1), (0.56 - draw * 3, 0.12))


def bladedancer(s, pose):
    f = figure(s, "elf", pose, "#5a8a70", "#d8e8ee", legs="#3a5a4a")
    elf_head(s, f, "#e8eef0")
    if pose == "attack":
        blade(s, (0.36, f["ty"] - 0.1), (0.9, -0.66), "#e4f0f4", 0.04)
        blade(s, (-0.36, f["ty"]), (-0.9, 0.16), "#e4f0f4", 0.04)
        hands(s, f, SKIN["elf"], (0.38, f["ty"] - 0.12), (-0.38, f["ty"] - 0.02))
    else:
        blade(s, (0.4, f["ty"] + 0.2), (0.62, -0.36), "#e4f0f4", 0.04)
        blade(s, (-0.4, f["ty"] + 0.2), (-0.62, -0.36), "#e4f0f4", 0.04)
        hands(s, f, SKIN["elf"], (0.4, f["ty"] + 0.22), (-0.4, f["ty"] + 0.22))


KINDS = (("crown_knight", crown_knight), ("crown_arbalist", crown_arbalist), ("hammerdwarf", hammerdwarf),
         ("runesmith", runesmith), ("wellspear", wellspear), ("sandveil", sandveil), ("moonbow", moonbow),
         ("bladedancer", bladedancer))


def soldier(key, fn, pose):
    @sprite(f"nation_{key}_{pose}", sizes=[16], variants=1, living=True)
    def _soldier(s, rng):
        fn(s, pose)
    return _soldier


for _p in POSES:
    for _k, _fn in KINDS:
        soldier(_k, _fn, _p)
