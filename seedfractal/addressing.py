"""
Addressing rules optimised for density.

- Involutive permutes
- Holographic binding (multi-pair capable)
- Simple perfect-hash style mapping over a compact span
"""

from __future__ import annotations

from dataclasses import dataclass
import random


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
    mask = (1 << width) - 1
    x = (x ^ seed) & mask
    x = rotl(x, (seed >> 8) % width, width)
    x = bit_reverse(x, width)
    x = (x ^ (seed >> 16)) & mask
    return x


def holographic_bind(a: int, b: int, width: int = 32) -> int:
    mask = (1 << width) - 1
    return (rotl(a, 7, width) ^ b) & mask


def holographic_unbind(bound: int, key: int, width: int = 32) -> int:
    return holographic_bind(bound, key, width)


@dataclass
class AddressingRule:
    width: int = 24
    seed: int = 0xDEADBEEF
    base_offset: int = 512
    mode: str = "involutive"          # or "holographic"
    span_bits: int = 20               # log2 of addressable span (density control)

    def __call__(self, question: int) -> int:
        q = question & ((1 << self.width) - 1)
        if self.mode == "holographic":
            h = holographic_bind(q, self.seed, self.width)
        else:
            h = involutive_permute(q, self.width, self.seed)
        span = 1 << self.span_bits
        off = self.base_offset + (h & (span - 1))
        return (off + 63) & ~63

    def inverse_approx(self, offset: int) -> int:
        raw = (offset - self.base_offset) & ((1 << self.width) - 1)
        if self.mode == "holographic":
            return holographic_unbind(raw, self.seed, self.width)
        return involutive_permute(raw, self.width, self.seed)

    def mutate(self, strength: float = 0.05) -> "AddressingRule":
        new_seed = self.seed
        bits = max(16, self.width)
        n_flips = max(1, int(bits * strength))
        for _ in range(n_flips):
            new_seed ^= 1 << random.randint(0, bits - 1)
        # Occasionally mutate span_bits toward denser packing
        new_span = self.span_bits
        if random.random() < 0.1:
            new_span = max(12, min(24, self.span_bits + random.choice([-1, 0, 1])))
        return AddressingRule(
            width=self.width,
            seed=new_seed,
            base_offset=self.base_offset,
            mode=self.mode,
            span_bits=new_span,
        )
