"""
SeedArena – single contiguous, perfectly aligned packed-bit buffer.

Design invariants:
- All permanent state lives in one uint64 array.
- Allocations are 64-bit aligned.
- read/write of arbitrary bit fields never materializes temporaries beyond registers.
- Persistence = dump/load the raw buffer + a tiny header.
"""

from __future__ import annotations

import numpy as np
from pathlib import Path
from typing import Optional, BinaryIO

MAGIC = np.uint64(0xSEEDFACA)
VERSION = np.uint64(2)


class SeedArena:
    __slots__ = ("buf", "n_words", "bit_len", "next_free_bit")

    def __init__(self, capacity_bytes: int = 64 * 1024 * 1024):
        self.n_words = max(16, (capacity_bytes + 7) // 8)
        self.buf = np.zeros(self.n_words, dtype=np.uint64)
        self.bit_len = self.n_words * 64
        self.next_free_bit = 128  # leave header space
        self._write_header()

    def _write_header(self) -> None:
        self.buf[0] = MAGIC
        self.buf[1] = VERSION
        self.buf[2] = np.uint64(0)  # root bit-offset
        self.buf[3] = np.uint64(self.next_free_bit)

    @property
    def root_offset(self) -> int:
        return int(self.buf[2])

    @root_offset.setter
    def root_offset(self, bit_off: int) -> None:
        self.buf[2] = np.uint64(bit_off)

    def alloc(self, n_bits: int, align: int = 64) -> int:
        """Bump-allocate. Returns bit offset aligned to `align`."""
        assert align & (align - 1) == 0, "align must be power of two"
        mask = align - 1
        aligned = (self.next_free_bit + mask) & ~mask
        if aligned + n_bits > self.bit_len:
            raise MemoryError(
                f"SeedArena exhausted: need {n_bits} bits, have {self.bit_len - aligned}"
            )
        self.next_free_bit = aligned + n_bits
        self.buf[3] = np.uint64(self.next_free_bit)
        return aligned

    def read_bits(self, bit_offset: int, n_bits: int) -> int:
        """Extract 1..64 bits. Pure shifts + masks."""
        if not (1 <= n_bits <= 64):
            raise ValueError("n_bits must be 1..64")
        word_idx = bit_offset >> 6
        shift = bit_offset & 63
        mask = (1 << n_bits) - 1
        if shift + n_bits <= 64:
            return (int(self.buf[word_idx]) >> shift) & mask
        # spans two words
        low = int(self.buf[word_idx]) >> shift
        high = int(self.buf[word_idx + 1]) << (64 - shift)
        return (low | high) & mask

    def write_bits(self, bit_offset: int, n_bits: int, value: int) -> None:
        """Deposit 1..64 bits in place."""
        if not (1 <= n_bits <= 64):
            raise ValueError("n_bits must be 1..64")
        mask = (1 << n_bits) - 1
        value &= mask
        word_idx = bit_offset >> 6
        shift = bit_offset & 63
        if shift + n_bits <= 64:
            clear = ~np.uint64(mask << shift)
            self.buf[word_idx] = (self.buf[word_idx] & clear) | np.uint64(value << shift)
            return
        bits_in_first = 64 - shift
        low_mask = (1 << bits_in_first) - 1
        self.buf[word_idx] = (
            self.buf[word_idx] & ~np.uint64(low_mask << shift)
        ) | np.uint64((value & low_mask) << shift)
        high_bits = n_bits - bits_in_first
        high_mask = (1 << high_bits) - 1
        self.buf[word_idx + 1] = (
            self.buf[word_idx + 1] & ~np.uint64(high_mask)
        ) | np.uint64(value >> bits_in_first)

    def load_aligned(self, bit_offset: int) -> np.uint64:
        assert bit_offset % 64 == 0
        return self.buf[bit_offset >> 6]

    def store_aligned(self, bit_offset: int, word: np.uint64) -> None:
        assert bit_offset % 64 == 0
        self.buf[bit_offset >> 6] = word

    def used_bits(self) -> int:
        return int(self.next_free_bit)

    def used_bytes(self) -> int:
        return (self.next_free_bit + 7) // 8

    # ---------- persistence (the arena *is* the checkpoint) ----------

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
            if header[0] != MAGIC:
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
        return f"SeedArena(used={self.used_bytes()}B / {self.n_words*8}B, free_bit={self.next_free_bit})"
