"""
Straight-line packed kernels.
Power-of-two layouts, no residual data-dependent Python branches
in the arithmetic itself.
"""

from __future__ import annotations

import numpy as np

from .arena import SeedArena
from .seed import Seed, SeedLayout, DEFAULT_LAYOUT
from .addressing import AddressingRule


def lookup(
    arena: SeedArena,
    question: int,
    rule: AddressingRule,
    layout: SeedLayout = DEFAULT_LAYOUT,
) -> Seed:
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
    need = layout.alloc_bits
    # Bump without a hard failure path in the arithmetic
    new_free = addr + need + 64
    if new_free > arena.next_free_bit:
        arena.next_free_bit = new_free
        arena.buf[3] = np.uint64(arena.next_free_bit)

    s = Seed(arena, addr, layout)
    s.set_addressing(question)
    s.set_payload(payload)
    s.set_child_ref(child_rel)
    # extra_bits is a layout constant; specialised kernels omit this entirely
    if layout.extra_bits:
        s.set_extra(extra)
    return s


def step(arena: SeedArena, current: int, rule: AddressingRule) -> int:
    return lookup(arena, current, rule).payload()


def batch_lookup(
    arena: SeedArena,
    questions: np.ndarray,
    rule: AddressingRule,
    layout: SeedLayout = DEFAULT_LAYOUT,
) -> np.ndarray:
    out = np.empty(len(questions), dtype=np.uint64)
    for i, q in enumerate(questions):
        out[i] = lookup(arena, int(q), rule, layout).payload()
    return out
