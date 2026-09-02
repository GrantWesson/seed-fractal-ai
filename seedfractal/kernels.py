"""
Fused packed kernels – straight-line, zero data-dependent branches.

All control flow is either compile-time (layout constants) or pure
arithmetic. The generated machine code for the hot path should contain
no taken/not-taken branches that depend on seed content.
"""

from __future__ import annotations

import numpy as np

from .arena import SeedArena
from .seed import Seed, SeedLayout, DEFAULT_LAYOUT
from .addressing import AddressingRule
from .branchless import align_up


def lookup(
    arena: SeedArena,
    question: int,
    rule: AddressingRule,
    layout: SeedLayout = DEFAULT_LAYOUT,
) -> Seed:
    """question → seed. Pure compute + one aligned load."""
    addr = rule(question)                  # pure bit ops
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
    """
    Write a seed at the address derived from the question.
    Allocation is bump-style and branchless (saturates).
    """
    addr = rule(question)
    need = layout.total_bits
    # Ensure the region exists by bumping next_free_bit if necessary.
    # Pure arithmetic; no conditional raise.
    new_free = addr + need + 64
    arena.next_free_bit = max(arena.next_free_bit, new_free)  # still one cmp, but rare
    arena.buf[3] = np.uint64(arena.next_free_bit)

    s = Seed(arena, addr, layout)
    s.set_addressing(question)
    s.set_payload(payload)
    s.set_child_ref(child_rel)
    if layout.extra_bits:                  # compile-time constant in practice
        s.set_extra(extra)
    return s


def step(arena: SeedArena, current: int, rule: AddressingRule) -> int:
    """One inference step: current → payload. Straight-line."""
    return lookup(arena, current, rule).payload()


def batch_lookup(
    arena: SeedArena,
    questions: np.ndarray,
    rule: AddressingRule,
    layout: SeedLayout = DEFAULT_LAYOUT,
) -> np.ndarray:
    """
    Vectorised path for many questions.
    Designed so a future C/SIMD lowering is a pure load + shuffle loop
    with no per-element branches.
    """
    # For the prototype we still loop; the structure is ready for vectorisation.
    out = np.empty(len(questions), dtype=np.uint64)
    for i, q in enumerate(questions):
        out[i] = lookup(arena, int(q), rule, layout).payload()
    return out
