"""
Prototype / shared seed table.

Common payloads and sub-structures live once.
Ordinary seeds hold only a short prototype index + optional delta.
Still pure packed bits and offsets – no expansion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict
import numpy as np

from .arena import SeedArena
from .seed import Seed, SeedLayout, DEFAULT_LAYOUT


@dataclass
class PrototypeTable:
    """
    Fixed-capacity table of shared seeds.
    Index is a small integer that fits in few bits.
    """
    capacity: int = 256
    layout: SeedLayout = field(default_factory=lambda: SeedLayout(16, 32, 16, 0))
    entries: List[int] = field(default_factory=list)  # bit offsets into arena
    arena: SeedArena | None = None

    def bind(self, arena: SeedArena) -> None:
        self.arena = arena
        self.entries = []

    def add(self, payload: int, child_rel: int = 0) -> int:
        """Allocate a prototype and return its index."""
        if self.arena is None:
            raise RuntimeError("PrototypeTable not bound to arena")
        if len(self.entries) >= self.capacity:
            # Simple replacement: overwrite oldest (can be evolved later)
            idx = len(self.entries) % self.capacity
        else:
            idx = len(self.entries)
            self.entries.append(0)
        off = self.arena.alloc(self.layout.alloc_bits)
        s = Seed(self.arena, off, self.layout)
        s.set_addressing(idx)          # self-index
        s.set_payload(payload)
        s.set_child_ref(child_rel)
        self.entries[idx] = off
        return idx

    def get(self, idx: int) -> Seed | None:
        if idx < 0 or idx >= len(self.entries):
            return None
        return Seed(self.arena, self.entries[idx], self.layout)

    def __len__(self) -> int:
        return len(self.entries)
