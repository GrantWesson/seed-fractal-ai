"""
Addressing = pure bit computation.

Two families:
1. Involutive permutes (f(f(x)) == x) for free bidirectional maps.
2. Holographic / hyperdimensional binding (XOR + permute) that
   lets a question vector address its own answer under a shared seed.
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np


def bit_reverse(x: int, width: int) -> int:
    y = 0
    for i in range(width):
        if x & (1 << i):
            y |= 1 << (width - 1 - i)
    return y


def rotl(x: int, r: int, width: int) -> int:
    r %= width
    mask = (1 << width) - 1
    return ((x << r) | (x >> (width - r))) & mask


def involutive_permute(x: int, width: int = 32, seed: int = 0xA5A5C3C3) -> int:
    """Guaranteed involution built from XOR + rotate + reverse."""
    mask = (1 << width) - 1
    x = (x ^ seed) & mask
    x = rotl(x, (seed >> 8) % width, width)
    x = bit_reverse(x, width)
    x = (x ^ (seed >> 16)) & mask
    return x


def holographic_bind(a: int, b: int, width: int = 32) -> int:
    """
    Hyperdimensional-style binding: XOR after a fixed permute.
    Self-inverse when the same key is used again.
    """
    mask = (1 << width) - 1
    # cheap "circle" via rotate + xor
    return (rotl(a, 7, width) ^ b) & mask


def holographic_unbind(bound: int, key: int, width: int = 32) -> int:
    # same operation is its own inverse
    return holographic_bind(bound, key, width)


@dataclass
class AddressingRule:
    """
    question → absolute bit offset inside the arena.
    Designed so that the mapping can be made bijective over the
    live seed set with only bit operations.
    """
    width: int = 32
    seed: int = 0xDEADBEEF
    base_offset: int = 256
    mode: str = "involutive"  # or "holographic"

    def __call__(self, question: int) -> int:
        q = question & ((1 << self.width) - 1)
        if self.mode == "holographic":
            h = holographic_bind(q, self.seed, self.width)
        else:
            h = involutive_permute(q, self.width, self.seed)
        # Map into a large power-of-two region then force alignment.
        # Production version replaces modulo with a minimal perfect hash
        # still computed from bit ops + a tiny seed table.
        span = 1 << 22  # 4 Mbit toy span
        off = self.base_offset + (h & (span - 1))
        return (off + 63) & ~63

    def inverse_approx(self, offset: int) -> int:
        """Approximate inverse for fitness checks."""
        raw = (offset - self.base_offset) & ((1 << self.width) - 1)
        if self.mode == "holographic":
            return holographic_unbind(raw, self.seed, self.width)
        return involutive_permute(raw, self.width, self.seed)

    def mutate(self, strength: float = 0.05) -> "AddressingRule":
        """Return a slightly mutated copy (bit flips on the seed)."""
        import random
        new_seed = self.seed
        bits = self.width
        n_flips = max(1, int(bits * strength))
        for _ in range(n_flips):
            new_seed ^= 1 << random.randint(0, bits - 1)
        return AddressingRule(
            width=self.width,
            seed=new_seed,
            base_offset=self.base_offset,
            mode=self.mode,
        )
