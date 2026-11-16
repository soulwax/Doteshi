"""Seeded generator with named sub-streams. Pure integer maths, so results never depend on numpy's random code."""
import hashlib
import math

MASK = (1 << 64) - 1


def _seed(*key):
    data = "\x1f".join(str(k) for k in key).encode("utf-8")
    return int.from_bytes(hashlib.blake2b(data, digest_size=8).digest(), "little")


class Rng:
    __slots__ = ("seed", "state")

    def __init__(self, *key):
        self.seed = _seed(*key)
        self.state = self.seed

    def stream(self, name):
        """An independent generator; the same name always gives the same stream, whatever was drawn before."""
        return Rng(self.seed, name)

    def u64(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
        return z ^ (z >> 31)

    def float(self):
        return (self.u64() >> 11) / (1 << 53)

    def uniform(self, a, b):
        return a + (b - a) * self.float()

    def int(self, a, b):
        """Inclusive on both ends."""
        return a + self.u64() % (b - a + 1)

    def seed32(self):
        return self.u64() & 0x7FFFFFFF

    def chance(self, p):
        return self.float() < p

    def choice(self, seq):
        return seq[self.u64() % len(seq)]

    def gauss(self, mu=0.0, sigma=1.0):
        u = max(self.float(), 1e-12)
        return mu + sigma * math.sqrt(-2.0 * math.log(u)) * math.cos(2.0 * math.pi * self.float())

    def jitter(self, value, frac):
        return value * (1.0 + frac * (2.0 * self.float() - 1.0))

    def on_disc(self, r=1.0):
        a, d = 2.0 * math.pi * self.float(), r * math.sqrt(self.float())
        return d * math.cos(a), d * math.sin(a)
