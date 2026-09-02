"""
Seed-Fractal AI
---------------
Nested bidirectional seeds. Question points directly to answer.
Zero-cost packed operations. Continuous self-modification.
"""

__version__ = "0.2.0"

from .arena import SeedArena
from .seed import Seed, SeedLayout
from .addressing import AddressingRule, involutive_permute, holographic_bind
from .improver import Improver
from .runtime import Runtime
from .fitness import evaluate

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
]
