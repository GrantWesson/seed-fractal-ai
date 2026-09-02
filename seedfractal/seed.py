"""
Seed – zero-copy view onto a region of the arena.
A seed is both data and address.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .arena import SeedArena


@dataclass(slots=True)
class SeedLayout:
    """Static description of how bits are laid out inside a seed."""
    addressing_bits: int = 32   # bits that turn a question into an offset
    payload_bits: int = 32      # the "answer" bits (or further seed)
    child_ref_bits: int = 32    # relative bit-offset to a child seed
    # total width is sum of the above (can be made variable later)

    @property
    def total_bits(self) -> int:
        return self.addressing_bits + self.payload_bits + self.child_ref_bits


DEFAULT_LAYOUT = SeedLayout()


class Seed:
    """
    Lightweight view. Never copies the underlying bits.
    All operations are pure extract / deposit on the arena.
    """

    __slots__ = ("arena", "bit_offset", "layout")

    def __init__(self, arena: "SeedArena", bit_offset: int, layout: SeedLayout = DEFAULT_LAYOUT):
        self.arena = arena
        self.bit_offset = bit_offset
        self.layout = layout

    # --- field accessors (zero-cost) ---

    def addressing(self) -> int:
        return self.arena.read_bits(self.bit_offset, self.layout.addressing_bits)

    def set_addressing(self, value: int) -> None:
        self.arena.write_bits(self.bit_offset, self.layout.addressing_bits, value)

    def payload(self) -> int:
        off = self.bit_offset + self.layout.addressing_bits
        return self.arena.read_bits(off, self.layout.payload_bits)

    def set_payload(self, value: int) -> None:
        off = self.bit_offset + self.layout.addressing_bits
        self.arena.write_bits(off, self.layout.payload_bits, value)

    def child_ref(self) -> int:
        off = self.bit_offset + self.layout.addressing_bits + self.layout.payload_bits
        return self.arena.read_bits(off, self.layout.child_ref_bits)

    def set_child_ref(self, relative_bit_offset: int) -> None:
        off = self.bit_offset + self.layout.addressing_bits + self.layout.payload_bits
        self.arena.write_bits(off, self.layout.child_ref_bits, relative_bit_offset)

    def child(self) -> Optional["Seed"]:
        rel = self.child_ref()
        if rel == 0:
            return None
        return Seed(self.arena, self.bit_offset + rel, self.layout)

    def __repr__(self) -> str:
        return (
            f"Seed(off={self.bit_offset}, "
            f"addr={self.addressing():#x}, "
            f"payload={self.payload():#x}, "
            f"child_rel={self.child_ref()})"
        )
