"""
Background self-improvement loop.

The program continuously proposes small mutations to addressing rules
or seed payloads, runs a cheap simulation, and keeps the change only
if a fitness metric improves. This runs indefinitely as a low-priority
background process.
"""

from __future__ import annotations

import time
import random
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .arena import SeedArena
from .addressing import AddressingRule, involutive_permute
from .kernels import lookup, deposit_answer, step


@dataclass
class Candidate:
    rule_seed: int
    fitness: float = 0.0
    description: str = ""


@dataclass
class Improver:
    arena: SeedArena
    rule: AddressingRule
    fitness_fn: Callable[[SeedArena, AddressingRule], float]
    mutation_rate: float = 0.05
    history: List[Candidate] = field(default_factory=list)
    best: Optional[Candidate] = None
    running: bool = False

    def evaluate(self, rule: AddressingRule) -> float:
        return self.fitness_fn(self.arena, rule)

    def mutate_rule(self, rule: AddressingRule) -> AddressingRule:
        """Tiny mutation of the addressing seed."""
        new_seed = rule.seed
        if random.random() < self.mutation_rate:
            # Flip a few bits
            bit = 1 << random.randint(0, 31)
            new_seed ^= bit
        return AddressingRule(width=rule.width, seed=new_seed, base_offset=rule.base_offset)

    def improve_once(self) -> bool:
        """Propose → simulate → accept or reject. Returns True if improved."""
        candidate_rule = self.mutate_rule(self.rule)
        fitness = self.evaluate(candidate_rule)

        cand = Candidate(rule_seed=candidate_rule.seed, fitness=fitness)
        self.history.append(cand)

        if self.best is None or fitness > self.best.fitness:
            self.best = cand
            self.rule = candidate_rule
            return True
        return False

    def run_background(self, interval_sec: float = 1.0, max_steps: Optional[int] = None):
        """
        Indefinite improvement loop.
        Intended to be started in a daemon thread or as a separate process.
        """
        self.running = True
        steps = 0
        print("[Improver] background self-improvement started")
        while self.running:
            improved = self.improve_once()
            if improved:
                print(f"[Improver] improved → fitness={self.best.fitness:.4f} seed={self.best.rule_seed:#x}")
            steps += 1
            if max_steps is not None and steps >= max_steps:
                break
            time.sleep(interval_sec)
        print("[Improver] stopped")

    def stop(self):
        self.running = False


def default_fitness(arena: SeedArena, rule: AddressingRule) -> float:
    """
    Toy fitness: how consistently a random set of questions
    round-trip through the bidirectional mapping + a simple
    payload prediction task.
    """
    score = 0.0
    rng = random.Random(42)
    for _ in range(32):
        q = rng.randint(0, 2**20 - 1)
        # Deposit a deterministic "answer"
        expected = involutive_permute(q, 20) & 0xFFFF
        deposit_answer(arena, q, expected, rule)
        # Look it up again
        s = lookup(arena, q, rule)
        if s.payload() == expected:
            score += 1.0
        # Bidirectional check (approximate in the toy)
        back = rule.inverse(s.bit_offset)
        if (back & 0xFFFF) == (q & 0xFFFF):
            score += 0.5
    return score / 32.0
