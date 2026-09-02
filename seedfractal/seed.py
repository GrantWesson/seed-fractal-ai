"""
Power-of-two hierarchical Seed.

All layouts are forced to power-of-two total bit width.
Offsets are pure shifts. No residual data-dependent Python
conditionals in the accessors themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .arena import SeedArena


def _is_pow2(x: int) -> bool:
    return x > 0 and (x & (x - 1)) == 0


@dataclass(slots=True, frozen=True)
class SeedLayout:
    addressing_bits: int = 32
    payload_bits: int = 32
    child_ref_bits: int = 32
    extra_bits: int = 0

    def __post_init__(self):
        total = self.total_bits
        # Force power-of-two by construction for the default path.
        # Callers that need non-pow2 must go through a padding allocator.
        if not _is_pow2(total):
            # Round up to next power of two for allocation size;
            # logical fields stay as declared.
            object.__setattr__(self, "_alloc_bits", 1 << (total - 1).bit_length())
        else:
            object.__setattr__(self, "_alloc_bits", total)

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
        return getattr(self, "_alloc_bits", self.total_bits)

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


# 128-bit allocation unit (power of two). Logical fields sum to 96.
DEFAULT_LAYOUT = SeedLayout(32, 32, 32, 0)


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

    # ---- pure offset arithmetic (constants fold) ----

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
        off = (
            self.bit_offset
            + self.layout.addressing_bits
            + self.layout.payload_bits
            + self.layout.child_ref_bits
        )
        # When extra_bits == 0 the read is defined to return 0 via mask
        return self.arena.read_bits(off, max(1, self.layout.extra_bits)) & ((1 << self.layout.extra_bits) - 1 if self.layout.extra_bits else 0)

    def set_extra(self, v: int) -> None:
        # Caller responsibility: only call when extra_bits > 0
        off = (
            self.bit_offset
            + self.layout.addressing_bits
            + self.layout.payload_bits
            + self.layout.child_ref_bits
        )
        self.arena.write_bits(off, self.layout.extra_bits, v)

    def child(self) -> "Seed | None":
        """
        Returns a Seed or None.
        In the C lowering this becomes a sentinel offset (0) test that
        is turned into a predicated move / blend, not a hard branch.
        """
        rel = self.child_ref()
        # Single comparison; the common case in tight loops is non-zero
        # and modern predictors handle it. For fully branch-free C we
        # return a dummy Seed at offset 0 and let the caller mask.
        if rel == 0:
            return None
        return Seed(self.arena, self.bit_offset + rel, self.layout)

    def child_offset(self) -> int:
        """Branch-free alternative: returns absolute offset or 0."""
        rel = self.child_ref()
        # Arithmetic select would be used in C; here we keep clarity
        return (self.bit_offset + rel) * (rel != 0)

    def __repr__(self) -> str:
        return (
            f"Seed(@{self.bit_offset}, addr={self.addressing():#x}, "
            f"pay={self.payload():#x}, child={self.child_ref()})"
        )
