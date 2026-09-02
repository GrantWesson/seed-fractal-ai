"""
Fused packed kernels. The only operations that ever touch the arena.
"""

from __future__ import annotations

from .arena import SeedArena
from .seed import Seed, SeedLayout, DEFAULT_LAYOUT
from .addressing import AddressingRule


def lookup(arena: SeedArena, question: int, rule: AddressingRule, layout: SeedLayout = DEFAULT_LAYOUT) -> Seed:
    addr = rule(question)
    return Seed(arena, addr, layout)


def deposit(
    arena: SeedArena,
    question: int,
    payload: int,
    rule: AddressingRule,
    layout: SeedLayout = DEFAULT_LAYOUT,
    child_rel: int = 0,
    extra: int = 0,
) -> Seed:
    addr = rule(question)
    need = layout.total_bits
    # ensure space (toy bump)
    if addr + need > arena.next_free_bit:
        arena.next_free_bit = max(arena.next_free_bit, addr + need + 64)
        arena.buf[3] = np.uint64(arena.next_free_bit)  # type: ignore
    s = Seed(arena, addr, layout)
    s.set_addressing(question)
    s.set_payload(payload)
    s.set_child_ref(child_rel)
    if layout.extra_bits:
        s.set_extra(extra)
    return s


def step(arena: SeedArena, current: int, rule: AddressingRule) -> int:
    return lookup(arena, current, rule).payload()


# import numpy only where needed to keep kernels pure
import numpy as np  # noqa: E402
