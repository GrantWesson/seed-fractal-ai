"""
Tiny runtime that ties arena + addressing + improver together.
"""

from __future__ import annotations

import threading
from typing import Optional

from .arena import SeedArena
from .addressing import AddressingRule
from .improver import Improver, default_fitness
from .kernels import step, deposit_answer, lookup


class Runtime:
    def __init__(self, capacity_mb: int = 64):
        self.arena = SeedArena(capacity_bytes=capacity_mb * 1024 * 1024)
        self.rule = AddressingRule()
        self.improver = Improver(
            arena=self.arena,
            rule=self.rule,
            fitness_fn=default_fitness,
        )
        self._bg_thread: Optional[threading.Thread] = None

    def start_self_improvement(self, interval_sec: float = 2.0):
        """Launch the indefinite background improver."""
        if self._bg_thread and self._bg_thread.is_alive():
            return
        self._bg_thread = threading.Thread(
            target=self.improver.run_background,
            kwargs={"interval_sec": interval_sec},
            daemon=True,
        )
        self._bg_thread.start()

    def stop_self_improvement(self):
        self.improver.stop()

    def teach(self, question: int, answer: int):
        """Insert a question↔answer pair into the seed arena."""
        deposit_answer(self.arena, question, answer, self.rule)

    def ask(self, question: int) -> int:
        """One-step inference."""
        return step(self.arena, question, self.rule)

    def status(self) -> str:
        best = self.improver.best
        fit = f"{best.fitness:.4f}" if best else "n/a"
        return (
            f"Runtime(used={self.arena.used_bytes()} B, "
            f"best_fitness={fit}, "
            f"rule_seed={self.rule.seed:#x})"
        )
