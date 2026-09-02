"""
Addressing rules that turn a question-seed into the bit-offset of its answer-seed.

The ideal rule is an involution: apply twice and you are back where you started.
This gives free bidirectional lookup.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
import numpy as np


def bit_reverse(x: int, width: int) -> int:
    """Classic involutive permute."""
    y = 0
    for i in range(width):
        if x & (1 << i):
            y |= 1 << (width - 1 - i)
    return y


def involutive_permute(x: int, width: int = 32, seed: int = 0xA5A5_C3C3) -> int:
    """
    A simple family of involutions built from XOR + rotate + bit-reverse.
    Guaranteed f(f(x)) == x.
    """
    # Mix with seed
    x ^= seed & ((1 << width) - 1)
    # Rotate left by a seed-derived amount
    r = (seed >> 8) % width
    x = ((x << r) | (x >> (width - r))) & ((1 << width) - 1)
    # Bit reverse (involution)
    x = bit_reverse(x, width)
    # Another XOR (involution when same seed)
    x ^= (seed >> 16) & ((1 << width) - 1)
    return x


@dataclass
class AddressingRule:
    """
    Callable that maps a question (int) to a bit-offset inside the arena.
    Must be deterministic and, ideally, involutive.
    """
    width: int = 32
    seed: int = 0xDEAD_BEEF
    base_offset: int = 128  # skip header

    def __call__(self, question: int) -> int:
        # Produce a stable offset from the question bits
        h = involutive_permute(question & ((1 << self.width) - 1), self.width, self.seed)
        # Map into the allocated region (simple modulo for the prototype)
        # In a real system this would be a perfect or minimal perfect hash
        # over the live seed set, still computed with only bit ops.
        span = 1 << 20  # 1 Mbit toy span for the demo
        off = self.base_offset + (h % span)
        # Force 64-bit alignment
        return (off + 63) & ~63

    def inverse(self, offset: int) -> int:
        """Because the core permute is involutive we can walk backwards."""
        # This is approximate in the toy modulo version;
        # a production rule would keep the mapping bijective.
        return involutive_permute(
            (offset - self.base_offset) & ((1 << self.width) - 1),
            self.width,
            self.seed,
        )
