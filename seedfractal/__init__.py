"""
Seed-Fractal AI
---------------
Nested bidirectional seeds. Zero unpack. Zero data-dependent branches.
Continuous self-modification.
"""

__version__ = "0.3.0"

from .arena import SeedArena
from .seed import Seed, SeedLayout
from .addressing import AddressingRule, involutive_permute, holographic_bind
from .improver import Improver
from .runtime import Runtime
from .fitness import evaluate
from .branchless import select, align_up

__all__ = [
    "SeedArena",
    "Seed",
    "SeedLayout",
    "AddressingRule",
    "involutive_permute",
    "holographic_bind",
    "Improver",
    "Runtime",
    "evaluate",
    "select",
    "align_up",
]
