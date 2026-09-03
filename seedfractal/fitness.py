"""
Multi-task fitness with explicit size penalty.

Primary objective: capability per megabyte.
This forces the improver under the 512 MB preference.
"""

from __future__ import annotations

import random
from typing import Callable, List, Tuple

from .arena import SeedArena
from .addressing import AddressingRule, involutive_permute, holographic_bind
from .kernels import deposit, lookup
from .seed import DEFAULT_LAYOUT, TINY_LAYOUT


def task_roundtrip(arena: SeedArena, rule: AddressingRule, n: int = 48) -> float:
    rng = random.Random(0xC0FFEE)
    hits = 0
    for _ in range(n):
        q = rng.randint(0, 2**18 - 1)
        expected = involutive_permute(q, 18) & 0xFFFF
        deposit(arena, q, expected, rule)
        if lookup(arena, q, rule).payload() == expected:
            hits += 1
    return hits / n


def task_bidirectional(arena: SeedArena, rule: AddressingRule, n: int = 24) -> float:
    rng = random.Random(0xBEEF)
    score = 0.0
    for _ in range(n):
        q = rng.randint(0, 2**14 - 1)
        deposit(arena, q, q ^ 0xA5A5, rule)
        s = lookup(arena, q, rule)
        back = rule.inverse_approx(s.bit_offset)
        if (back & 0x3FFF) == (q & 0x3FFF):
            score += 1.0
    return score / n


def task_holographic(arena: SeedArena, rule: AddressingRule, n: int = 24) -> float:
    rng = random.Random(0xF00D)
    hits = 0
    for _ in range(n):
        a = rng.randint(0, 2**14 - 1)
        b = rng.randint(0, 2**14 - 1)
        bound = holographic_bind(a, b, 16)
        if holographic_bind(bound, b, 16) == a:
            hits += 1
    return hits / n


def task_popcount(arena: SeedArena, rule: AddressingRule, n: int = 24) -> float:
    rng = random.Random(0x1234)
    hits = 0
    for _ in range(n):
        q = rng.randint(0, 2**10 - 1)
        expected = bin(q).count("1")
        deposit(arena, q, expected, rule)
        if lookup(arena, q, rule).payload() == expected:
            hits += 1
    return hits / n


DEFAULT_TASKS: List[Tuple[str, Callable]] = [
    ("roundtrip", task_roundtrip),
    ("bidirectional", task_bidirectional),
    ("holographic", task_holographic),
    ("popcount", task_popcount),
]


def evaluate(
    arena: SeedArena,
    rule: AddressingRule,
    tasks=None,
    size_penalty: bool = True,
) -> float:
    """
    Returns a score that *decreases* as memory grows.
    This is the primary lever forcing ≤ 512 MB.
    """
    tasks = tasks or DEFAULT_TASKS
    raw = 0.0
    for _, fn in tasks:
        raw += fn(arena, rule)
    raw /= max(1, len(tasks))

    if not size_penalty:
        return raw

    used_mb = max(arena.used_bytes() / (1024 * 1024), 0.001)
    # Capability per MB. Strongly prefers smaller arenas.
    return raw / (used_mb ** 0.6)  # sub-linear so tiny arenas are not over-favoured
