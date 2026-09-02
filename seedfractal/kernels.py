"""
Fused packed kernels. Everything stays in the bit domain.
"""

from __future__ import annotations

from .arena import SeedArena
from .seed import Seed
from .addressing import AddressingRule


def lookup(arena: SeedArena, question: int, rule: AddressingRule) -> Seed:
    """
    The fundamental operation:
        question → address → seed (already aligned, already the answer)
    Cost: a few bit ops + one aligned load.
    """
    addr = rule(question)
    return Seed(arena, addr)


def deposit_answer(arena: SeedArena, question: int, answer_payload: int, rule: AddressingRule) -> Seed:
    """Write an answer seed at the location the question points to."""
    addr = rule(question)
    # Ensure the slot exists (bump if necessary – toy version)
    if addr + 96 > arena.next_free_bit:  # rough size check
        # For the prototype we just force the allocator forward
        arena.next_free_bit = max(arena.next_free_bit, addr + 128)
    s = Seed(arena, addr)
    s.set_addressing(question)          # store the question so we can walk back
    s.set_payload(answer_payload)
    s.set_child_ref(0)
    return s


def step(arena: SeedArena, current: int, rule: AddressingRule) -> int:
    """One inference step: current bits → next payload bits."""
    s = lookup(arena, current, rule)
    return s.payload()
