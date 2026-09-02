"""
Branchless primitives.

Every helper here is straight-line code using only arithmetic, shifts,
masks and bitwise ops. No data-dependent branches. When lowered to
C/SIMD these become single instructions or short predicated sequences.
"""

from __future__ import annotations

import numpy as np


def select(cond: int, a: int, b: int) -> int:
    """
    Branchless select: returns a if cond != 0 else b.
    cond is treated as a full-bit mask (0 or ~0) for best codegen;
    we also accept 0/1 and convert.
    """
    # Turn any non-zero into all-1s mask without a branch
    mask = -int(cond != 0)          # 0 or -1
    return (a & mask) | (b & ~mask)


def select64(cond: np.uint64, a: np.uint64, b: np.uint64) -> np.uint64:
    """Same for uint64 / numpy."""
    mask = np.uint64(0) - (cond != 0).astype(np.uint64)  # 0 or all-1s
    return (a & mask) | (b & ~mask)


def clamp_u(x: int, lo: int, hi: int) -> int:
    """Branchless clamp for unsigned-style ranges."""
    # x = max(lo, x); x = min(hi, x) using arithmetic
    x = x ^ ((x ^ lo) & -(x < lo))
    x = hi ^ ((x ^ hi) & -(x > hi))
    return x


def is_pow2(x: int) -> int:
    """1 if power-of-two (or zero), 0 otherwise. Branchless."""
    return int((x & (x - 1)) == 0)


def align_up(x: int, align: int) -> int:
    """align must be power-of-two. Branchless."""
    return (x + (align - 1)) & ~(align - 1)


def bit_width_mask(n_bits: int) -> int:
    """(1 << n_bits) - 1 without undefined behaviour for n_bits==64."""
    # For n_bits==64 we want all 1s; shift by 64 is UB in some languages,
    # so we do it branchlessly.
    return select(n_bits == 64, -1, (1 << n_bits) - 1)


def extract_bits_word(word: int, shift: int, n_bits: int) -> int:
    """Extract from a single 64-bit word. Straight-line."""
    mask = bit_width_mask(n_bits)
    return (word >> shift) & mask


def deposit_bits_word(word: int, shift: int, n_bits: int, value: int) -> int:
    """Deposit into a single 64-bit word. Straight-line."""
    mask = bit_width_mask(n_bits)
    value &= mask
    return (word & ~(mask << shift)) | (value << shift)
