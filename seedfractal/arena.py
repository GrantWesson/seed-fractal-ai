"""
SeedArena – single contiguous, page-aligned packed bit buffer.
All seeds live here. No unpacking. Ever.
"""

from __future__ import annotations

import numpy as np
from typing import Optional


class SeedArena:
    """
    The entire model is one arena of packed bits.

    Memory layout:
        [ header | seed0 | seed1 | ... | free ]

    Every seed is a fixed or variable-width packed record whose
    absolute bit-offset is its identity.
    """

    def __init__(self, capacity_bytes: int = 64 * 1024 * 1024):
        # We work in uint64 words for natural alignment.
        self.n_words = (capacity_bytes + 7) // 8
        self.buf = np.zeros(self.n_words, dtype=np.uint64)
        self.bit_len = self.n_words * 64
        self.next_free_bit = 0  # bump allocator for new seeds

        # Tiny header: version + root seed offset
        self._write_header()

    def _write_header(self) -> None:
        # bits 0..63 : magic + version
        self.buf[0] = np.uint64(0xSEEDFACA)  # magic
        # root seed will be placed at a known offset later

    @property
    def root_offset(self) -> int:
        return int(self.buf[1])  # we store root bit-offset in word 1

    @root_offset.setter
    def root_offset(self, bit_off: int) -> None:
        self.buf[1] = np.uint64(bit_off)

    def alloc(self, n_bits: int) -> int:
        """Bump-allocate a packed region. Returns starting bit offset."""
        # Align to 64-bit boundary for free loads
        aligned = (self.next_free_bit + 63) & ~63
        if aligned + n_bits > self.bit_len:
            raise MemoryError("SeedArena exhausted")
        self.next_free_bit = aligned + n_bits
        return aligned

    def read_bits(self, bit_offset: int, n_bits: int) -> int:
        """Extract up to 64 bits starting at bit_offset. Zero-copy view."""
        if n_bits > 64:
            raise ValueError("Use read_bits_wide for >64 bits")
        word_idx = bit_offset >> 6
        shift = bit_offset & 63
        if shift + n_bits <= 64:
            val = int(self.buf[word_idx]) >> shift
            return val & ((1 << n_bits) - 1)
        # Spans two words
        low = int(self.buf[word_idx]) >> shift
        high = int(self.buf[word_idx + 1]) << (64 - shift)
        return (low | high) & ((1 << n_bits) - 1)

    def write_bits(self, bit_offset: int, n_bits: int, value: int) -> None:
        """Deposit up to 64 bits. In-place, no temporaries."""
        if n_bits > 64:
            raise ValueError("Use write_bits_wide for >64 bits")
        mask = (1 << n_bits) - 1
        value &= mask
        word_idx = bit_offset >> 6
        shift = bit_offset & 63
        if shift + n_bits <= 64:
            clear = ~np.uint64(mask << shift)
            self.buf[word_idx] = (self.buf[word_idx] & clear) | np.uint64(value << shift)
        else:
            # Spans two words – still pure bit ops
            bits_in_first = 64 - shift
            low_mask = (1 << bits_in_first) - 1
            self.buf[word_idx] = (self.buf[word_idx] & ~np.uint64(low_mask << shift)) | np.uint64(
                (value & low_mask) << shift
            )
            high_bits = n_bits - bits_in_first
            high_mask = (1 << high_bits) - 1
            self.buf[word_idx + 1] = (self.buf[word_idx + 1] & ~np.uint64(high_mask)) | np.uint64(
                value >> bits_in_first
            )

    def load_aligned_word(self, bit_offset: int) -> np.uint64:
        """Require bit_offset % 64 == 0. Fast path."""
        assert bit_offset % 64 == 0
        return self.buf[bit_offset >> 6]

    def store_aligned_word(self, bit_offset: int, word: np.uint64) -> None:
        assert bit_offset % 64 == 0
        self.buf[bit_offset >> 6] = word

    def used_bytes(self) -> int:
        return (self.next_free_bit + 7) // 8

    def __repr__(self) -> str:
        return f"SeedArena(used={self.used_bytes()} B / {self.n_words * 8} B)"
