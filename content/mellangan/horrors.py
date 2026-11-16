"""What lurks in Mellangan's dark: three horrors that live below ground and shun light, woken where the dwarves dug
too deep. Near-black bodies with a cold violet rim so they read on a dark cave floor, and pale eyes that glow.
Three poses each (idle, step, attack): the Lightless, a long-armed stalker; the Hollow Maw, a heavy crawling mouth;
the Whisperer, a floating veiled thing that hexes."""
from doteshi import mat, pat, profile, sdf, sprite

G = 0.9
POSES = ("idle", "step", "attack")
BODY, RIM, EYE, MAW, TOOTH = "#1a1424", "#5a3c88", "#e8f0ff", "#4a0e1e", "#e8e0cc"


def glow(s, x, y, r=0.07, colour=EYE):
    s.part(sdf.circle(r).at(x, y), mat.glowing(colour, emit=0.9), z=0.9, keep=True, limb=True)


def dark(s, shape, z=0.1, relief=0.6, **kw):
    part = s.part(shape, mat.matte(BODY, rough=0.9), relief=relief, z=z, **kw)
    part.tint(RIM, pat.gradient("y", -1.0, 0.4), 0.55)
    return part


def lightless(s, pose):
    bob = -0.05 if pose == "step" else 0.0
    reach = 0.3 if pose == "attack" else 0.0
    for side, dz in ((-1, 0.0), (1, 0.12 if pose == "step" else 0.0)):
        dark(s, sdf.capsule((side * 0.14, 0.3 + bob), (side * 0.22, G - dz * 0.3), 0.06, 0.04), z=0.0, limb=True)
    dark(s, sdf.ellipse(0.24, 0.42).at(0.0, 0.0 + bob).warp(0.04, 4.0, 11), z=0.05)
    dark(s, sdf.ellipse(0.26, 0.24).at(0.04, -0.5 + bob), z=0.1, relief=0.8)
    for side in (-1, 1):
        tip = (side * (0.62 + reach), 0.5 - reach * 1.4 + bob) if side > 0 else (-0.6, 0.62 + bob)
        dark(s, sdf.stroke([(side * 0.2, -0.16 + bob), (side * 0.5, 0.1 + bob), tip], [0.06, 0.05, 0.03]), z=0.2,
             limb=True)
        for f in (-1, 0, 1):
            dark(s, sdf.capsule(tip, (tip[0] + side * 0.1 + f * 0.04, tip[1] + 0.14 + f * 0.05), 0.02, 0.01), z=0.25,
                 limb=True)
    glow(s, -0.04, -0.52 + bob, 0.06)
    glow(s, 0.14, -0.52 + bob, 0.06)


def hollow_maw(s, pose):
    open_ = 0.3 if pose == "attack" else 0.18
    lift = -0.04 if pose == "step" else 0.0
    body = sdf.ellipse(0.84, 0.6).at(0.0, 0.26 + lift).warp(0.07, 3.0, 5).above(G)
    dark(s, body, z=0.05, relief=0.9).bump(pat.grain(0.06, 3, stretch=2, axis="u"), 0.02)
    for x in (-0.66, -0.3, 0.3, 0.66):
        step = 0.08 if pose == "step" and x > 0 else 0.0
        dark(s, sdf.capsule((x, 0.5 + lift), (x * 1.15, G - step), 0.07, 0.05), z=0.0, limb=True)
    my = 0.3 + lift
    s.part(sdf.ellipse(0.58, open_).at(0.04, my), mat.matte(MAW), z=0.3, keep=True)
    s.part(sdf.ellipse(0.4, open_ * 0.5).at(0.04, my + open_ * 0.2), mat.matte("#14040a"), z=0.32, keep=True)
    for i in range(4):
        x = -0.36 + i * 0.26
        s.part(sdf.polygon([(x - 0.04, my - open_), (x + 0.04, my - open_), (x, my - open_ * 0.3)]),
               mat.matte(TOOTH), z=0.4, keep=True)
        s.part(sdf.polygon([(x + 0.09, my + open_), (x + 0.17, my + open_), (x + 0.13, my + open_ * 0.3)]),
               mat.matte(TOOTH), z=0.4, keep=True)
    for x, y in ((-0.5, -0.06), (-0.22, -0.2), (0.12, -0.24), (0.42, -0.14), (0.62, 0.02)):
        glow(s, x, y + lift, 0.05, "#f0c8ff")


def whisperer(s, pose):
    sway = 0.08 if pose == "step" else 0.0
    rise = -0.08 if pose == "attack" else 0.0
    hood = sdf.ellipse(0.4, 0.36).at(0.02, -0.52 + rise)
    robe = sdf.polygon([(-0.3, -0.4 + rise), (0.34, -0.4 + rise), (0.56, 0.62), (0.38 + sway, 0.5), (0.2, 0.78),
                        (0.02, 0.56), (-0.16 - sway, 0.8), (-0.34, 0.54), (-0.54, 0.66)])
    dark(s, (hood | robe).warp(0.03, 5.0, 7), z=0.05, relief=0.5)
    s.part(sdf.ellipse(0.24, 0.22).at(0.06, -0.46 + rise), mat.matte("#040208"), z=0.2, keep=True)
    glow(s, -0.03, -0.46 + rise, 0.055)
    glow(s, 0.15, -0.46 + rise, 0.055)
    for side in (-1, 1):
        hand = (side * (0.6 + (0.16 if pose == "attack" else 0.0)), 0.08 + rise * 3)
        dark(s, sdf.stroke([(side * 0.24, -0.12 + rise), (side * 0.44, 0.0 + rise), hand], [0.06, 0.05, 0.03]),
             z=0.25, limb=True)
        if pose == "attack":
            s.part(sdf.circle(0.11).at(*hand), mat.glowing("#9a6ae8", emit=0.8), z=0.5, keep=True, limb=True)


KINDS = (("lightless", lightless), ("hollow_maw", hollow_maw), ("whisperer", whisperer))


def horror(key, fn, pose):
    @sprite(f"horror_{key}_{pose}", sizes=[16], variants=1, living=True)
    def _horror(s, rng):
        fn(s, pose)
    return _horror


for _p in POSES:
    for _k, _fn in KINDS:
        horror(_k, _fn, _p)
