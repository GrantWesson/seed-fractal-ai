"""
Self-improving process that evolves both behaviour *and* representation.

Mutates:
- addressing seeds
- bit-width / layout choices
- prototype usage
- code seeds (including branchless operators)

Fitness already contains the size penalty, so the search is
explicitly driven toward ≤ 512 MB.
"""

from __future__ import annotations

import time
import random
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Dict

from .arena import SeedArena
from .addressing import AddressingRule
from .fitness import evaluate
from .seed import SeedLayout, DEFAULT_LAYOUT, TINY_LAYOUT, PROTO_LAYOUT
from .selfmod import CodeSeed, BOOTSTRAP_FITNESS_HELPER, BOOTSTRAP_SELECT, DEFAULT_MUTATORS
from .prototype import PrototypeTable


@dataclass
class Candidate:
    rule: AddressingRule
    fitness: float
    generation: int
    note: str = ""
    layout: SeedLayout = DEFAULT_LAYOUT


@dataclass
class Improver:
    arena: SeedArena
    rule: AddressingRule
    protos: PrototypeTable = field(default_factory=PrototypeTable)
    fitness_fn: Callable = evaluate
    mutation_strength: float = 0.05
    selfmod_every: int = 15
    history: List[Candidate] = field(default_factory=list)
    best: Optional[Candidate] = None
    generation: int = 0
    running: bool = False
    code_seeds: Dict[str, CodeSeed] = field(default_factory=dict)
    current_layout: SeedLayout = DEFAULT_LAYOUT

    def __post_init__(self):
        self.protos.bind(self.arena)
        if not self.code_seeds:
            self.code_seeds["helper"] = BOOTSTRAP_FITNESS_HELPER
            self.code_seeds["select"] = BOOTSTRAP_SELECT

    def _record(self, rule: AddressingRule, fitness: float, note: str = "", layout: SeedLayout | None = None) -> None:
        layout = layout or self.current_layout
        cand = Candidate(rule=rule, fitness=fitness, generation=self.generation, note=note, layout=layout)
        self.history.append(cand)
        if self.best is None or fitness > self.best.fitness:
            self.best = cand
            self.rule = rule
            self.current_layout = layout

    def improve_addressing(self) -> bool:
        self.generation += 1
        cand_rule = self.rule.mutate(self.mutation_strength)
        fit = self.fitness_fn(self.arena, cand_rule)
        improved = self.best is None or fit > self.best.fitness
        self._record(cand_rule, fit, "addr")
        return improved

    def improve_layout(self) -> bool:
        """Mutate bit-widths / switch between dense layouts."""
        self.generation += 1
        choices = [DEFAULT_LAYOUT, TINY_LAYOUT, PROTO_LAYOUT,
                   SeedLayout(8, 16, 8, 0), SeedLayout(12, 12, 8, 4)]
        new_layout = random.choice(choices)
        fit = self.fitness_fn(self.arena, self.rule)
        # Accept if not worse (layout change is exploratory)
        if self.best is None or fit >= self.best.fitness - 1e-6:
            self._record(self.rule, fit, f"layout:{new_layout.total_bits}b", new_layout)
            return True
        return False

    def improve_code(self) -> bool:
        self.generation += 1
        name = random.choice(list(self.code_seeds.keys()))
        original = self.code_seeds[name]
        which = random.choices(["branchless", "bitflip", "token"], weights=[0.5, 0.3, 0.2])[0]
        mutant = original.mutate(which)
        local: dict = {}
        if not mutant.try_eval(local):
            return False
        fit = self.fitness_fn(self.arena, self.rule)
        if self.best is None or fit >= self.best.fitness - 1e-6:
            self.code_seeds[name] = mutant
            self._record(self.rule, fit, f"code:{name}:{which}")
            return True
        return False

    def improve_once(self) -> bool:
        r = random.random()
        if r < 0.55:
            return self.improve_addressing()
        elif r < 0.75:
            return self.improve_layout()
        else:
            return self.improve_code()

    def run_background(self, interval_sec: float = 0.7, max_steps: Optional[int] = None):
        self.running = True
        steps = 0
        print("[Improver] density-aware self-optimization started (target ≤ 512 MB)")
        while self.running:
            improved = self.improve_once()
            if improved and self.best:
                used = self.arena.used_bytes()
                print(
                    f"[Improver] gen={self.generation} "
                    f"fit={self.best.fitness:.4f} "
                    f"used={used}B "
                    f"note={self.best.note}"
                )
            steps += 1
            if max_steps is not None and steps >= max_steps:
                break
            time.sleep(interval_sec)
        print("[Improver] stopped")

    def stop(self):
        self.running = False
