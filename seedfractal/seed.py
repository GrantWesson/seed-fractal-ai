"""
Variable-width hierarchical Seed with prototype support.

Logical field widths can be 1/2/4/8/16/32.
Allocation unit is the next power-of-two.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .arena import SeedArena


def _next_pow2(x: int) -> int:
    if x <= 0:
        return 1
    return 1 << (x - 1).bit_length()


@dataclass(slots=True, frozen=True)
class SeedLayout:
    addressing_bits: int = 16
    payload_bits: int = 16
    child_ref_bits: int = 16
    extra_bits: int = 0          # can hold prototype index or holographic state

    def __post_init__(self):
        total = self.total_bits
        object.__setattr__(self, "_alloc_bits", _next_pow2(max(total, 8)))

    @property
    def total_bits(self) -> int:
        return (
            self.addressing_bits
            + self.payload_bits
            + self.child_ref_bits
            + self.extra_bits
        )

    @property
    def alloc_bits(self) -> int:
        return getattr(self, "_alloc_bits", _next_pow2(self.total_bits))

    def pack(self) -> int:
        return (
            (self.addressing_bits & 0xFF)
            | ((self.payload_bits & 0xFF) << 8)
            | ((self.child_ref_bits & 0xFF) << 16)
            | ((self.extra_bits & 0xFF) << 24)
        )

    @classmethod
    def unpack(cls, v: int) -> "SeedLayout":
        return cls(
            addressing_bits=v & 0xFF,
            payload_bits=(v >> 8) & 0xFF,
            child_ref_bits=(v >> 16) & 0xFF,
            extra_bits=(v >> 24) & 0xFF,
        )


# Dense default: 16+16+16 = 48 logical → 64-bit allocation
DEFAULT_LAYOUT = SeedLayout(16, 16, 16, 0)
# Ultra-dense for bulk knowledge
TINY_LAYOUT = SeedLayout(8, 8, 8, 0)
# Prototype reference layout (small index in extra)
PROTO_LAYOUT = SeedLayout(12, 12, 12, 8)


class Seed:
    __slots__ = ("arena", "bit_offset", "layout")

    def __init__(
        self,
        arena: "SeedArena",
        bit_offset: int,
        layout: SeedLayout = DEFAULT_LAYOUT,
    ):
        self.arena = arena
        self.bit_offset = bit_offset
        self.layout = layout

    def addressing(self) -> int:
        return self.arena.read_bits(self.bit_offset, self.layout.addressing_bits)

    def set_addressing(self, v: int) -> None:
        self.arena.write_bits(self.bit_offset, self.layout.addressing_bits, v)

    def payload(self) -> int:
        off = self.bit_offset + self.layout.addressing_bits
        return self.arena.read_bits(off, self.layout.payload_bits)

    def set_payload(self, v: int) -> None:
        off = self.bit_offset + self.layout.addressing_bits
        self.arena.write_bits(off, self.layout.payload_bits, v)

    def child_ref(self) -> int:
        off = self.bit_offset + self.layout.addressing_bits + self.layout.payload_bits
        return self.arena.read_bits(off, self.layout.child_ref_bits)

    def set_child_ref(self, relative: int) -> None:
        off = self.bit_offset + self.layout.addressing_bits + self.layout.payload_bits
        self.arena.write_bits(off, self.layout.child_ref_bits, relative)

    def extra(self) -> int:
        if self.layout.extra_bits == 0:
            return 0
        off = (
            self.bit_offset
            + self.layout.addressing_bits
            + self.layout.payload_bits
            + self.layout.child_ref_bits
        )
        return self.arena.read_bits(off, self.layout.extra_bits)

    def set_extra(self, v: int) -> None:
        if self.layout.extra_bits == 0:
            return
        off = (
            self.bit_offset
            + self.layout.addressing_bits
            + self.layout.payload_bits
            + self.layout.child_ref_bits
        )
        self.arena.write_bits(off, self.layout.extra_bits, v)

    def child(self) -> "Seed | None":
        rel = self.child_ref()
        if rel == 0:
            return None
        return Seed(self.arena, self.bit_offset + rel, self.layout)

    def child_offset(self) -> int:
        rel = self.child_ref()
        return (self.bit_offset + rel) * (rel != 0)

    def __repr__(self) -> str:
        return (
            f"Seed(@{self.bit_offset}, w={self.layout.total_bits}b, "
            f"addr={self.addressing():#x}, pay={self.payload():#x})"
        )
