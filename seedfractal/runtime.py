"""
Runtime with prototype table, variable layouts and density reporting.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from .arena import SeedArena
from .addressing import AddressingRule
from .improver import Improver
from .kernels import deposit, step, resolve
from .prototype import PrototypeTable
from .fitness import evaluate
from .seed import DEFAULT_LAYOUT


class Runtime:
    def __init__(self, capacity_mb: int = 64, mode: str = "involutive"):
        self.arena = SeedArena(capacity_bytes=capacity_mb * 1024 * 1024)
        self.rule = AddressingRule(mode=mode, span_bits=18)
        self.protos = PrototypeTable(capacity=128)
        self.protos.bind(self.arena)
        self.improver = Improver(
            arena=self.arena,
            rule=self.rule,
            protos=self.protos,
            fitness_fn=evaluate,
        )
        self._bg: Optional[threading.Thread] = None

    def start_self_improvement(self, interval_sec: float = 0.8):
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
        deposit(self.arena, question, answer, self.rule, layout=self.improver.current_layout)

    def ask(self, question: int) -> int:
        return resolve(self.arena, question, self.rule, self.protos)

    def save(self, path: str | Path):
        self.arena.save(path)

    def load(self, path: str | Path):
        self.arena = SeedArena.load(path)
        self.protos.bind(self.arena)

    def status(self) -> str:
        b = self.improver.best
        fit = f"{b.fitness:.4f}" if b else "n/a"
        used = self.arena.used_bytes()
        return (
            f"Runtime(used={used}B ({used/1024/1024:.3f} MB), "
            f"gen={self.improver.generation}, best={fit}, "
            f"layout={self.improver.current_layout.total_bits}b, "
            f"protos={len(self.protos)})"
        )
