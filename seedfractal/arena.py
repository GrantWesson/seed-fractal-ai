"""
SeedArena – single contiguous, perfectly aligned packed-bit buffer.

Invariants for zero cache-miss / zero-branch hot path:
- One contiguous uint64 array → perfect spatial locality, sequential
  or low-entropy strided access only.
- All permanent allocations 64-bit (or higher power-of-two) aligned.
- Fixed power-of-two seed sizes preferred so indexing = shifts + masks.
- read_bits / write_bits are straight-line: both the single-word and
  two-word cases are computed, then selected with a mask. No data-
  dependent branches in the common path.
- No pointer chasing; child links are bit offsets computed from the
  base of the same arena.
- Working set is the arena itself; keep capacity tight relative to
  last-level cache when possible.
"""

from __future__ import annotations

import numpy as np
from pathlib import Path

from .branchless import select, align_up, bit_width_mask

MAGIC = np.uint64(0xSEEDFACA)
VERSION = np.uint64(3)


class SeedArena:
    __slots__ = ("buf", "n_words", "bit_len", "next_free_bit")

    def __init__(self, capacity_bytes: int = 64 * 1024 * 1024):
        # Round capacity up to whole words; keep it a multiple of
        # a large power of two for nicest cache behaviour.
        self.n_words = max(16, (capacity_bytes + 7) // 8)
        self.buf = np.zeros(self.n_words, dtype=np.uint64)
        self.bit_len = self.n_words * 64
        self.next_free_bit = 256  # header + padding for alignment
        self._write_header()

    def _write_header(self) -> None:
        self.buf[0] = MAGIC
        self.buf[1] = VERSION
        self.buf[2] = np.uint64(0)          # root bit-offset
        self.buf[3] = np.uint64(self.next_free_bit)

    @property
    def root_offset(self) -> int:
        return int(self.buf[2])

    @root_offset.setter
    def root_offset(self, bit_off: int) -> None:
        self.buf[2] = np.uint64(bit_off)

    def alloc(self, n_bits: int, align: int = 64) -> int:
        """
        Bump allocator. align must be power-of-two.
        On exhaustion we still return a value (saturating) so callers
        that must stay branchless can test later if needed; the hot
        path never branches on the check.
        """
        aligned = align_up(self.next_free_bit, align)
        # Saturating add – no exception in the arithmetic itself
        new_free = aligned + n_bits
        # Branchless saturate to bit_len
        overflow = int(new_free > self.bit_len)
        new_free = select(overflow, self.bit_len, new_free)
        self.next_free_bit = new_free
        self.buf[3] = np.uint64(self.next_free_bit)
        return aligned

    def read_bits(self, bit_offset: int, n_bits: int) -> int:
        """
        Extract 1..64 bits. Completely branchless.

        Both the single-word and two-word paths are evaluated;
        a mask selects the correct result. When lowered to C this
        becomes a short straight-line sequence with a cmov or blend.
        """
        # Clamp n_bits into legal range without a branch
        n_bits = 1 + ((n_bits - 1) & 63)          # maps any int into 1..64
        word_idx = bit_offset >> 6
        shift = bit_offset & 63
        mask = bit_width_mask(n_bits)

        # Path A: entirely inside one word
        w0 = int(self.buf[word_idx])
        single = (w0 >> shift) & mask

        # Path B: spans two words (always computed)
        w1 = int(self.buf[min(word_idx + 1, self.n_words - 1)])
        low = w0 >> shift
        high = w1 << ((64 - shift) & 63)
        spanning = (low | high) & mask

        # Select: if shift + n_bits <= 64 then single else spanning
        fits = int(shift + n_bits <= 64)
        return select(fits, single, spanning)

    def write_bits(self, bit_offset: int, n_bits: int, value: int) -> None:
        """
        Deposit 1..64 bits. Branchless.
        Both the single-word and spanning stores are prepared;
        masks decide which words are actually modified.
        """
        n_bits = 1 + ((n_bits - 1) & 63)
        word_idx = bit_offset >> 6
        shift = bit_offset & 63
        mask = bit_width_mask(n_bits)
        value &= mask

        fits = int(shift + n_bits <= 64)

        # --- single-word deposit ---
        single_clear = ~(mask << shift)
        single_new = (int(self.buf[word_idx]) & single_clear) | (value << shift)

        # --- spanning deposit ---
        bits_in_first = 64 - shift
        low_mask = bit_width_mask(bits_in_first)
        high_bits = n_bits - bits_in_first
        # high_bits can be negative if fits; we mask it away later
        high_bits_pos = high_bits & 63
        high_mask = bit_width_mask(high_bits_pos)

        low_new = (int(self.buf[word_idx]) & ~(low_mask << shift)) | ((value & low_mask) << shift)
        high_new = (int(self.buf[min(word_idx + 1, self.n_words - 1)]) & ~high_mask) | ((value >> bits_in_first) & high_mask)

        # Blend: if fits use single_new for word0 and leave word1 untouched;
        # else use low_new / high_new.
        word0 = select(fits, single_new, low_new)
        word1 = select(fits, int(self.buf[min(word_idx + 1, self.n_words - 1)]), high_new)

        self.buf[word_idx] = np.uint64(word0)
        # Always write the second word; when fits==1 it is a no-op store of the old value
        self.buf[min(word_idx + 1, self.n_words - 1)] = np.uint64(word1)

    def load_aligned(self, bit_offset: int) -> np.uint64:
        # Hot path assumes caller already aligned; no check
        return self.buf[bit_offset >> 6]

    def store_aligned(self, bit_offset: int, word: np.uint64) -> None:
        self.buf[bit_offset >> 6] = word

    def used_bits(self) -> int:
        return int(self.next_free_bit)

    def used_bytes(self) -> int:
        return (self.next_free_bit + 7) // 8

    # ---------- persistence ----------

    def save(self, path: str | Path) -> None:
        path = Path(path)
        header = np.array(
            [MAGIC, VERSION, self.root_offset, self.next_free_bit, self.n_words],
            dtype=np.uint64,
        )
        with path.open("wb") as f:
            header.tofile(f)
            self.buf[: self.n_words].tofile(f)

    @classmethod
    def load(cls, path: str | Path) -> "SeedArena":
        path = Path(path)
        with path.open("rb") as f:
            header = np.fromfile(f, dtype=np.uint64, count=5)
            # Even the magic check can be made soft; for load we keep a hard fail
            if int(header[0]) != int(MAGIC):
                raise ValueError("Bad magic")
            n_words = int(header[4])
            buf = np.fromfile(f, dtype=np.uint64, count=n_words)
        arena = cls.__new__(cls)
        arena.n_words = n_words
        arena.buf = buf
        arena.bit_len = n_words * 64
        arena.next_free_bit = int(header[3])
        return arena

    def __repr__(self) -> str:
        return f"SeedArena(used={self.used_bytes()}B / {self.n_words*8}B)"
