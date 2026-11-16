"""Spiral placement by the golden angle: the packing of seeds in a flower head, scales on a cone, petals in a
rosette. Each new element sits 137.5 degrees round from the last, so no two ever line up."""
import math

GOLDEN_ANGLE = math.pi * (3.0 - math.sqrt(5.0))


def spiral(n, radius, start=0.0, turn=0.0):
    """`n` points filling a disc of the given radius evenly, innermost first.
    Returns [(x, y, t)] with t running 0 at the centre to 1 at the rim. `start` leaves a hole of that
    radius in the middle; `turn` rotates the whole arrangement (radians)."""
    out = []
    for i in range(n):
        t = (i + 0.5) / n
        r = math.sqrt(start * start + (radius * radius - start * start) * t)
        a = turn + i * GOLDEN_ANGLE
        out.append((r * math.cos(a), r * math.sin(a), (r - start) / max(radius - start, 1e-9)))
    return out


def ring(n, turn=0.0):
    """`n` directions round a circle, as (cos, sin, angle)."""
    return [(math.cos(turn + i * 2.0 * math.pi / n), math.sin(turn + i * 2.0 * math.pi / n),
             turn + i * 2.0 * math.pi / n) for i in range(n)]
