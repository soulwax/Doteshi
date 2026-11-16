"""Four faction chieftains for Mellangan, each a crowned variant of a camp leader. They face south and glance a
little to the south-south-east, so the held object hangs on the right and the face sits right of centre.

At 16 pixels a face is a few pixels and no render of lit parts reads as well as a placed pixel, so the 16 pixel
cell of every chief is hand drawn (`@override`). Other sizes are built from parts by `figure`."""
import math

from doteshi import mat, override, pat, profile, sdf, sprite
from doteshi.core.color import rgb8
from doteshi.resolve.style import OUTLINE


def pal(**colours):
    return {k: rgb8(v) for k, v in colours.items()}


def stamp(rows, marks):
    grid = [list(r) for r in rows]
    for x, y, ch in marks:
        grid[y][x] = ch
    return ["".join(r) for r in grid]


def line(x, y0, y1, ch):
    return [(x, y, ch) for y in range(y0, y1 + 1)]


def figure(s, cloak, cloth, skin, head, held):
    """The generated figure for sizes above 16: a cloak behind, a body, a head, a headpiece, a held object."""
    s.part(sdf.polygon([(-0.55, -0.3), (0.55, -0.3), (0.72, 0.85), (-0.72, 0.85)]).warp(0.02, 3, 2),
           mat.satin(cloak), relief=0.8, z=-0.04)
    s.part(sdf.box(0.36, 0.42, 0.06).at(0, 0.38), mat.satin(cloth), relief=0.8, z=0.0)
    s.part(sdf.circle(0.3).at(0.06, -0.38), mat.matte(skin), relief=1.0, z=0.05, keep=True)
    s.part(head, mat.metal(cloak, rough=0.5), z=0.1)
    s.part(held, mat.satin("#c8a45c"), z=0.1, limb=True)


C1 = ["................",
      "................",
      ".....rRR........",
      "....rRRRr.......",
      "....sSSSss......",
      "...gsSSSssg.....",
      "....sffFfs......",
      "....sfkfks......",
      "...rssSSssr.....",
      "..rrSsGsGSrr....",
      "..rCsSsssSCr....",
      "..rCsSgggsCr....",
      "..rCCssssCCr....",
      "...CCkkkkCC.....",
      "....kk..kk......",
      "...kkk..kkk....."]

C1_MARKS = (line(13, 0, 8, "w") + [(13, 0, "W"), (12, 9, "g"), (13, 9, "g"), (14, 9, "g"), (13, 10, "f"), (13, 11, "k")])


@sprite("chief_freeblades", sizes=[16], variants=1, living=True)
def chief_freeblades(s, rng):
    figure(s, "#8c2a2e", "#7a8494", "#e0b090", sdf.polygon([(-0.34, -0.5), (0.4, -0.5), (0.3, -0.85), (-0.3, -0.85)]),
           sdf.box(0.05, 0.6).at(0.75, 0.0))


@override("chief_freeblades", 16)
def chief_freeblades_16(rng):
    p = pal(r="#d8484a", R="#f08a6a", C="#8c2a2e", s="#7e8898", S="#bcc6d4", g="#e8bc3c", G="#e8bc3c", f="#e8b890",
            F="#c88a68", k="#2c2432", w="#dfe8f2", W="#ffffff")
    return stamp(C1, C1_MARKS), p, OUTLINE


C2 = ["................",
      "................",
      "......gg........",
      "....hhhhhh......",
      "...hhhHHhhh.....",
      "..HhhhhhhhhH....",
      "....hffFfh......",
      "....fkfkff......",
      "....ffFFfF......",
      "...ccttttcc.....",
      "..ccctyyytcc....",
      "..cctttyttcc....",
      "..ccttytttcc....",
      "..ccctttttcc....",
      "...cc.kk.kk.....",
      "...kkk.kkkk....."]

C2_MARKS = [(2, 9, "b"), (3, 9, "b"), (2, 10, "b"), (3, 10, "b"), (2, 11, "b"), (3, 11, "B"), (2, 12, "b"), (3, 12, "b"),
            (11, 10, "u"), (11, 11, "g")]
C2 = [r for r in C2]


@sprite("chief_coinroad", sizes=[16], variants=1, living=True)
def chief_coinroad(s, rng):
    figure(s, "#2f6a6a", "#3f8a8a", "#e0b090", sdf.ellipse(0.7, 0.14).at(0, -0.72), sdf.box(0.18, 0.24).at(-0.7, 0.3))


@override("chief_coinroad", 16)
def chief_coinroad_16(rng):
    p = pal(h="#5a3a28", H="#8a6038", g="#f0c030", f="#e8b890", F="#c88a68", k="#2c2432", c="#2a5a5a", t="#3f8a8a",
            y="#e8bc3c", b="#7a4a28", B="#4a2c18", u="#c8c0a0")
    return stamp(C2, C2_MARKS), p, OUTLINE


C3 = ["................",
      ".a.a..aa.a......",
      ".a.aa.aa.aa.....",
      "..aaabbbaa......",
      "...lbmmmmbl.....",
      "...mmffFfmm.....",
      "..mmmfkfkmm.....",
      "..mmmwwwwmm.....",
      "..mmsmwwmsmm.l..",
      "..mmsmmmmsmm.o..",
      "..mmmmmmmmmm.o..",
      "..mmnmmmmnmm.o..",
      "...mmmmmmmm..o..",
      "...mmmmmmmm..o..",
      "....nn..nn...o..",
      "................"]


@sprite("chief_rootsworn", sizes=[16], variants=1, living=True)
def chief_rootsworn(s, rng):
    figure(s, "#3f6a34", "#5a8a3c", "#d8a880", sdf.polygon([(-0.4, -0.5), (0.4, -0.5), (0.0, -0.95)]),
           sdf.box(0.04, 0.8).at(0.8, 0.1))


@override("chief_rootsworn", 16)
def chief_rootsworn_16(rng):
    p = pal(a="#7a5430", b="#5a3a22", l="#7ed05a", m="#3f7a3a", n="#285a2a", s="#7ec85a", f="#d8a880", F="#b88860",
            k="#2c2432", w="#d8d4c0", o="#6a4a2a")
    return C3, p, OUTLINE


C4 = ["................",
      "..h..........h..",
      "..hh........hh..",
      "...hh.hhhh.hh...",
      "....hpqpqph.....",
      "....pqqqqpq.....",
      "....pkkkkpq.....",
      "....pkykyp......",
      "...qpppppqp.....",
      "..pqqrqpppqq.l..",
      "..qppqppqpqp.L..",
      "..pqpqqpqqpp.o..",
      "..qppqpppqpq.o..",
      "...pqqpqpqq..o..",
      "....pp..qq......",
      "................"]


@sprite("chief_unmoored", sizes=[16], variants=1, living=True)
def chief_unmoored(s, rng):
    figure(s, "#6a4a7a", "#8a6a5a", "#3a2a3a", sdf.polygon([(-0.4, -0.5), (0.4, -0.5), (0.0, -0.95)]),
           sdf.circle(0.14).at(0.78, 0.2))


@override("chief_unmoored", 16)
def chief_unmoored_16(rng):
    p = pal(h="#d8cfb8", p="#7a5a8a", q="#9a7a6a", r="#4a7a8a", k="#1c1424", y="#ffe070", l="#ffd860", L="#ffb030",
            o="#5a4a3a")
    return C4, p, OUTLINE
