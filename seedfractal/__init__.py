"""
Seed-Fractal AI
---------------
Nested bidirectional seeds. Question points directly to answer (and back).
Zero-cost packed bit operations. Continuous self-improvement.
"""

__version__ = "0.1.0"

from .arena import SeedArena
from .seed import Seed
from .addressing import AddressingRule, involutive_permute
from .improver import Improver
from .runtime import Runtime

__all__ = [
    "SeedArena",
    "Seed",
    "AddressingRule",
    "involutive_permute",
    "Improver",
    "Runtime",
]
