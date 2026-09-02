"""
Multi-task fitness suite.

Every candidate change is scored on a battery of cheap, deterministic
tasks that probe:
- round-trip fidelity of the bidirectional map
- payload retrieval accuracy
- hierarchical child consistency
- simple algorithmic patterns (parity, popcount, small arithmetic)
- holographic binding integrity

All tasks operate exclusively on packed seeds; no external datasets.
"""

from __future__ import annotations

import random
from typing import Callable, List, Tuple

from .arena import SeedArena
from .addressing import AddressingRule, involutive_permute, holographic_bind
from .kernels import deposit, lookup
from .seed import DEFAULT_LAYOUT


def task_roundtrip(arena: SeedArena, rule: AddressingRule, n: int = 64) -> float:
    rng = random.Random(0xC0FFEE)
    hits = 0
    for _ in range(n):
        q = rng.randint(0, 2**20 - 1)
        expected = involutive_permute(q, 20) & 0xFFFF
        deposit(arena, q, expected, rule)
        got = lookup(arena, q, rule).payload()
        if got == expected:
            hits += 1
    return hits / n


def task_bidirectional(arena: SeedArena, rule: AddressingRule, n: int = 32) -> float:
    rng = random.Random(0xBEEF)
    score = 0.0
    for _ in range(n):
        q = rng.randint(0, 2**16 - 1)
        deposit(arena, q, q ^ 0xA5A5, rule)
        s = lookup(arena, q, rule)
        back = rule.inverse_approx(s.bit_offset)
        if (back & 0xFFFF) == (q & 0xFFFF):
            score += 1.0
    return score / n


def task_hierarchy(arena: SeedArena, rule: AddressingRule, n: int = 16) -> float:
    """Parent seed points to a child; child payload must be recoverable."""
    rng = random.Random(0xDEAD)
    hits = 0
    for i in range(n):
        q = 1000 + i
        child_q = 5000 + i
        child_pay = (child_q * 7) & 0xFFFF
        # first place the child
        child_seed = deposit(arena, child_q, child_pay, rule)
        # parent holds relative offset to child
        rel = child_seed.bit_offset  # absolute for toy; real system uses relative
        parent = deposit(arena, q, 0, rule, child_rel=rel)
        # walk
        child = parent.child()
        if child is not None and child.payload() == child_pay:
            hits += 1
    return hits / n


def task_holographic(arena: SeedArena, rule: AddressingRule, n: int = 32) -> float:
    if rule.mode != "holographic":
        # still test the bind primitive itself
        rng = random.Random(0xF00D)
        hits = 0
        for _ in range(n):
            a = rng.randint(0, 2**16 - 1)
            b = rng.randint(0, 2**16 - 1)
            bound = holographic_bind(a, b, 16)
            recovered = holographic_bind(bound, b, 16)
            if recovered == a:
                hits += 1
        return hits / n
    return task_roundtrip(arena, rule, n)


def task_popcount_pattern(arena: SeedArena, rule: AddressingRule, n: int = 32) -> float:
    """Can the arena store and retrieve a simple function of the key?"""
    rng = random.Random(0x1234)
    hits = 0
    for _ in range(n):
        q = rng.randint(0, 2**12 - 1)
        expected = bin(q).count("1")  # popcount
        deposit(arena, q, expected, rule)
        if lookup(arena, q, rule).payload() == expected:
            hits += 1
    return hits / n


DEFAULT_TASKS: List[Tuple[str, Callable]] = [
    ("roundtrip", task_roundtrip),
    ("bidirectional", task_bidirectional),
    ("hierarchy", task_hierarchy),
    ("holographic", task_holographic),
    ("popcount", task_popcount_pattern),
]


def evaluate(arena: SeedArena, rule: AddressingRule, tasks=None) -> float:
    """Weighted average of all tasks. Higher is better."""
    tasks = tasks or DEFAULT_TASKS
    total = 0.0
    for name, fn in tasks:
        total += fn(arena, rule)
    return total / len(tasks)
