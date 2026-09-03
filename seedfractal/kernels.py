"""
Streaming, variable-width, prototype-aware kernels.
Activations never materialise as separate buffers.
"""

from __future__ import annotations

import numpy as np

from .arena import SeedArena
from .seed import Seed, SeedLayout, DEFAULT_LAYOUT, TINY_LAYOUT, PROTO_LAYOUT
from .addressing import AddressingRule
from .prototype import PrototypeTable


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
    new_free = addr + need + 64
    if new_free > arena.next_free_bit:
        arena.next_free_bit = new_free
        arena.buf[3] = np.uint64(arena.next_free_bit)

    s = Seed(arena, addr, layout)
    s.set_addressing(question & ((1 << layout.addressing_bits) - 1))
    s.set_payload(payload & ((1 << layout.payload_bits) - 1))
    s.set_child_ref(child_rel)
    if layout.extra_bits:
        s.set_extra(extra)
    return s


def deposit_proto(
    arena: SeedArena,
    question: int,
    proto_idx: int,
    rule: AddressingRule,
    protos: PrototypeTable,
    delta: int = 0,
) -> Seed:
    """Store only a prototype index + delta (extreme density)."""
    return deposit(
        arena, question, delta, rule,
        layout=PROTO_LAYOUT, extra=proto_idx
    )


def step(arena: SeedArena, current: int, rule: AddressingRule) -> int:
    """Streaming one-step inference – payload is the next question."""
    return lookup(arena, current, rule).payload()


def resolve(
    arena: SeedArena,
    question: int,
    rule: AddressingRule,
    protos: PrototypeTable | None = None,
) -> int:
    """
    Full resolve: follow ordinary seed, then prototype if present.
    Still pure loads + arithmetic.
    """
    s = lookup(arena, question, rule, PROTO_LAYOUT)
    if protos is not None and s.layout.extra_bits:
        idx = s.extra()
        p = protos.get(idx)
        if p is not None:
            return p.payload() ^ s.payload()  # delta
    return s.payload()
