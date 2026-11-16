"""Branching structures grown by space colonisation: scatter points where growth is wanted, and let a skeleton
reach for them. Limbs fork where the points pull apart, which gives the uneven, searching look of real trees,
roots, veins, antlers and coral."""
import math

import numpy as np


def scatter(rng, cx, cy, rx, ry, n):
    """`n` points spread evenly over an ellipse."""
    pts = [rng.on_disc() for _ in range(n)]
    return np.array([(cx + x * rx, cy + y * ry) for x, y in pts])


class Skeleton:
    """A grown structure: node positions and each node's parent (-1 for the root). Children always come after
    their parents."""

    def __init__(self, pos, parent):
        self.pos = np.asarray(pos, np.float64)
        self.parent = list(parent)
        self.children = [[] for _ in self.parent]
        for i, p in enumerate(self.parent):
            if p >= 0:
                self.children[p].append(i)

    def tips(self):
        return [i for i, c in enumerate(self.children) if not c]

    def radii(self, tip=0.01, power=2.3, base=None):
        """Thickness at every node by the pipe model: a limb is as thick as the limbs it feeds, combined.
        `base` rescales everything so the root has that radius, without thinning the tips below `tip`."""
        r = np.full(len(self.parent), float(tip))
        for i in range(len(self.parent) - 1, -1, -1):
            if self.children[i]:
                r[i] = sum(r[c] ** power for c in self.children[i]) ** (1.0 / power)
        if base:
            r = tip + (r - tip) * (base - tip) / max(r[0] - tip, 1e-9)
        return r

    def limbs(self, radii):
        """The skeleton as continuous limbs: [(points, radii, order)]. At each fork the thickest child carries
        the limb on and the others start new ones; order counts the forks back to the trunk."""
        out = []
        starts = [(0, None, 0)]
        while starts:
            node, came_from, order = starts.pop(0)
            pts, rs = [], []
            if came_from is not None:
                pts.append(self.pos[came_from])
                rs.append(radii[node])
            while True:
                pts.append(self.pos[node])
                rs.append(radii[node])
                kids = sorted(self.children[node], key=lambda c: (-radii[c], c))
                if not kids:
                    break
                starts += [(k, node, order + 1) for k in kids[1:]]
                node = kids[0]
            if len(pts) > 1:
                out.append((np.array(pts), np.array(rs), order))
        return out


def colonize(rng, root, targets, step=0.06, reach=0.35, kill=0.09, heading=(0.0, -1.0), wander=0.12,
             max_nodes=700):
    """Grow a skeleton from `root` toward a cloud of target points.

    step:    distance between nodes; smaller gives smoother, denser limbs.
    reach:   how far away a target can be and still pull on a node.
    kill:    a target is used up once a node comes this close; smaller gives finer twigs.
    heading: the direction the trunk takes before it comes within reach of any target.
    wander:  random sideways drift per step, for limbs that are not ruler-straight.
    """
    targets = np.asarray(targets, np.float64).copy()
    pos, parent = [np.asarray(root, np.float64)], [-1]
    hx, hy = heading
    for _ in range(200):                                     # the trunk
        if len(targets) == 0 or np.hypot(*(targets - pos[-1]).T).min() < reach:
            break
        a = math.atan2(hy, hx) + wander * rng.uniform(-1.0, 1.0)
        pos.append(pos[-1] + step * np.array([math.cos(a), math.sin(a)]))
        parent.append(len(pos) - 2)
    while len(targets) and len(pos) < max_nodes:             # the crown
        P = np.array(pos)
        D = np.hypot(targets[:, None, 0] - P[None, :, 0], targets[:, None, 1] - P[None, :, 1])
        nearest = D.argmin(axis=1)
        live = D.min(axis=1) < reach
        grew = False
        for node in sorted(set(nearest[live].tolist())):
            pull = targets[live & (nearest == node)] - P[node]
            pull = (pull / np.maximum(np.hypot(pull[:, 0], pull[:, 1]), 1e-9)[:, None]).sum(axis=0)
            a = math.atan2(pull[1], pull[0]) + wander * rng.uniform(-1.0, 1.0)
            new = P[node] + step * np.array([math.cos(a), math.sin(a)])
            if np.hypot(*(np.array(pos) - new).T).min() < step * 0.35:
                continue
            pos.append(new)
            parent.append(node)
            grew = True
        if not grew:
            break
        P = np.array(pos)
        D = np.hypot(targets[:, None, 0] - P[None, :, 0], targets[:, None, 1] - P[None, :, 1])
        targets = targets[D.min(axis=1) >= kill]
    return Skeleton(pos, parent)
