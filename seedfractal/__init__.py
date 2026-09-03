"""
Seed-Fractal AI
---------------
Density-first: variable bit-width, prototype sharing, size-penalized fitness,
holographic seeds, branchless kernels, self-modifying representation.
Target ≤ 512 MB.
"""

__version__ = "0.5.0"

from .arena import SeedArena
from .seed import Seed, SeedLayout, DEFAULT_LAYOUT, TINY_LAYOUT, PROTO_LAYOUT
from .addressing import AddressingRule, involutive_permute, holographic_bind
from .prototype import PrototypeTable
from .improver import Improver
from .runtime import Runtime
from .fitness import evaluate
from .branchless import select, align_up

__all__ = [
    "SeedArena",
    "Seed",
    "SeedLayout",
    "DEFAULT_LAYOUT",
    "TINY_LAYOUT",
    "PROTO_LAYOUT",
    "AddressingRule",
    "involutive_permute",
    "holographic_bind",
    "PrototypeTable",
    "Improver",
    "Runtime",
    "evaluate",
    "select",
    "align_up",
]
