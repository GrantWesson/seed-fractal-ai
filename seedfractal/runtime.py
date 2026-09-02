"""
Runtime orchestrator.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from .arena import SeedArena
from .addressing import AddressingRule
from .improver import Improver
from .kernels import deposit, step, lookup
from .fitness import evaluate


class Runtime:
    def __init__(self, capacity_mb: int = 32, mode: str = "involutive"):
        self.arena = SeedArena(capacity_bytes=capacity_mb * 1024 * 1024)
        self.rule = AddressingRule(mode=mode)
        self.improver = Improver(
            arena=self.arena,
            rule=self.rule,
            fitness_fn=evaluate,
        )
        self._bg: Optional[threading.Thread] = None

    def start_self_improvement(self, interval_sec: float = 1.0):
        if self._bg and self._bg.is_alive():
            return
        self._bg = threading.Thread(
            target=self.improver.run_background,
            kwargs={"interval_sec": interval_sec},
            daemon=True,
            name="seed-improver",
        )
        self._bg.start()

    def stop_self_improvement(self):
        self.improver.stop()
        if self._bg:
            self._bg.join(timeout=2.0)

    def teach(self, question: int, answer: int):
        deposit(self.arena, question, answer, self.rule)

    def ask(self, question: int) -> int:
        return step(self.arena, question, self.rule)

    def save(self, path: str | Path):
        self.arena.save(path)

    def load(self, path: str | Path):
        self.arena = SeedArena.load(path)
        # rule seed is not yet persisted in header; future work

    def status(self) -> str:
        b = self.improver.best
        fit = f"{b.fitness:.4f}" if b else "n/a"
        return (
            f"Runtime(used={self.arena.used_bytes()}B, "
            f"gen={self.improver.generation}, "
            f"best={fit}, rule={self.rule.seed:#x}, mode={self.rule.mode})"
        )
