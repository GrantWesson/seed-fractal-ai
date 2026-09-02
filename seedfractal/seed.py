"""
Variable-width hierarchical Seed.

A seed is a packed record:
  [ addressing | payload | child_ref | optional extra fields... ]

Layout is itself described by a small header so different seeds
can have different widths. All access remains pure bit extract/deposit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .arena import SeedArena


@dataclass(slots=True, frozen=True)
class SeedLayout:
    addressing_bits: int = 32
    payload_bits: int = 32
    child_ref_bits: int = 32
    extra_bits: int = 0  # for future holographic / mask data

    @property
    def total_bits(self) -> int:
        return (
            self.addressing_bits
            + self.payload_bits
            + self.child_ref_bits
            + self.extra_bits
        )

    def pack(self) -> int:
        """Pack layout descriptor into 32 bits for storage."""
        # 8 bits each for the four fields (max 255)
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


DEFAULT_LAYOUT = SeedLayout()


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

    # ---- zero-cost field access ----

    def _off(self, field: str) -> int:
        o = self.bit_offset
        if field == "addressing":
            return o
        o += self.layout.addressing_bits
        if field == "payload":
            return o
        o += self.layout.payload_bits
        if field == "child_ref":
            return o
        o += self.layout.child_ref_bits
        return o  # extra

    def addressing(self) -> int:
        return self.arena.read_bits(self._off("addressing"), self.layout.addressing_bits)

    def set_addressing(self, v: int) -> None:
        self.arena.write_bits(self._off("addressing"), self.layout.addressing_bits, v)

    def payload(self) -> int:
        return self.arena.read_bits(self._off("payload"), self.layout.payload_bits)

    def set_payload(self, v: int) -> None:
        self.arena.write_bits(self._off("payload"), self.layout.payload_bits, v)

    def child_ref(self) -> int:
        return self.arena.read_bits(self._off("child_ref"), self.layout.child_ref_bits)

    def set_child_ref(self, relative: int) -> None:
        self.arena.write_bits(self._off("child_ref"), self.layout.child_ref_bits, relative)

    def extra(self) -> int:
        if self.layout.extra_bits == 0:
            return 0
        return self.arena.read_bits(self._off("extra"), self.layout.extra_bits)

    def set_extra(self, v: int) -> None:
        if self.layout.extra_bits:
            self.arena.write_bits(self._off("extra"), self.layout.extra_bits, v)

    def child(self) -> Optional["Seed"]:
        rel = self.child_ref()
        if rel == 0:
            return None
        # child may have a different layout; for now we inherit
        return Seed(self.arena, self.bit_offset + rel, self.layout)

    def __repr__(self) -> str:
        return (
            f"Seed(@{self.bit_offset}, addr={self.addressing():#x}, "
            f"pay={self.payload():#x}, child={self.child_ref()}, "
            f"layout={self.layout.total_bits}b)"
        )
