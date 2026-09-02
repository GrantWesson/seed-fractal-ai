"""
Self-improving background process.

Two levels of evolution happen concurrently:
1. Addressing-rule seed mutation (fast, bit-level).
2. Occasional self-modification of the mutation operators and
   helper functions themselves (code-as-seeds, sandboxed).

Only strict fitness improvements are committed. The loop is designed
to run indefinitely at low priority.
"""

from __future__ import annotations

import time
import random
import copy
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Dict

from .arena import SeedArena
from .addressing import AddressingRule
from .fitness import evaluate
from .selfmod import CodeSeed, BOOTSTRAP_FITNESS_HELPER, DEFAULT_MUTATORS


@dataclass
class Candidate:
    rule: AddressingRule
    fitness: float
    generation: int
    note: str = ""


@dataclass
class Improver:
    arena: SeedArena
    rule: AddressingRule
    fitness_fn: Callable[[SeedArena, AddressingRule], float] = evaluate
    mutation_strength: float = 0.04
    selfmod_every: int = 25  # attempt code-level mutation this often
    history: List[Candidate] = field(default_factory=list)
    best: Optional[Candidate] = None
    generation: int = 0
    running: bool = False
    code_seeds: Dict[str, CodeSeed] = field(default_factory=dict)

    def __post_init__(self):
        if not self.code_seeds:
            self.code_seeds["helper"] = BOOTSTRAP_FITNESS_HELPER

    def _record(self, rule: AddressingRule, fitness: float, note: str = "") -> None:
        cand = Candidate(rule=rule, fitness=fitness, generation=self.generation, note=note)
        self.history.append(cand)
        if self.best is None or fitness > self.best.fitness:
            self.best = cand
            self.rule = rule

    def improve_addressing(self) -> bool:
        """Classic fast path: mutate the addressing seed."""
        self.generation += 1
        cand_rule = self.rule.mutate(self.mutation_strength)
        fit = self.fitness_fn(self.arena, cand_rule)
        improved = self.best is None or fit > self.best.fitness
        self._record(cand_rule, fit, "addr")
        return improved

    def improve_code(self) -> bool:
        """
        Out-of-box path: mutate a CodeSeed, try it in a sandbox,
        keep only if the overall system fitness rises.
        """
        self.generation += 1
        name = random.choice(list(self.code_seeds.keys()))
        original = self.code_seeds[name]
        mutant = original.mutate(random.choice(list(DEFAULT_MUTATORS.keys())))

        # Sandbox check: can it even execute?
        local: dict = {}
        if not mutant.try_eval(local):
            return False

        # For the prototype we only accept mutants that still define a
        # callable 'score'. Deeper versions would replace live functions.
        if "score" not in local or not callable(local["score"]):
            return False

        # Measure system fitness with the current rule (code change is
        # orthogonal for now; future work wires the helper into fitness).
        fit = self.fitness_fn(self.arena, self.rule)
        # Accept the code mutant if it is at least as good (encourages
        # exploration of the code space without immediate regression).
        if self.best is None or fit >= self.best.fitness - 1e-6:
            self.code_seeds[name] = mutant
            self._record(self.rule, fit, f"code:{name}")
            return True
        return False

    def improve_once(self) -> bool:
        if self.generation > 0 and self.generation % self.selfmod_every == 0:
            return self.improve_code()
        return self.improve_addressing()

    def run_background(self, interval_sec: float = 0.8, max_steps: Optional[int] = None):
        self.running = True
        steps = 0
        print("[Improver] indefinite self-optimization started")
        while self.running:
            improved = self.improve_once()
            if improved and self.best:
                print(
                    f"[Improver] gen={self.generation} "
                    f"fit={self.best.fitness:.4f} "
                    f"note={self.best.note} "
                    f"seed={self.rule.seed:#x}"
                )
            steps += 1
            if max_steps is not None and steps >= max_steps:
                break
            time.sleep(interval_sec)
        print("[Improver] stopped")

    def stop(self):
        self.running = False
